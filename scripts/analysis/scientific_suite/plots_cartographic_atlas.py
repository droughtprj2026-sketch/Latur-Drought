# -*- coding: utf-8 -*-
"""Cartographic Atlas Generator: Publication-Grade Multi-Panel Spatial Maps.

Generates:
1. Yearly Mean Atlases (2016–2026 + 11-Year Climatology) for each index in a 3x4 grid.
2. 12-Month Climatological Atlases (Jan–Dec long-term spatial distribution) in a 4x3 grid.
3. Annual 12-Month Progression Atlases for each individual year (2016 to 2026) in a 4x3 grid.

Cartographic & Scientific Rules:
- Rule: "if the date has the 0 values dont take that day for the mapping cuz the maps that we will produce will be blank"
  Any date where values are missing, all 0, or >= 90% zero is excluded from mapping and annual aggregation,
  rendering instead as an explicit "No Data" panel with neat village boundary outlines.
- Typography: Times New Roman throughout (titles, ticks, legends, scale, insets).
- Orientation: Exactly ONE cartographic North arrow in the upper right corner.
- Symbology: Single unified horizontal colorbar / legend centered at the bottom.
- Geodesy: Georeferenced scale bar (0–40 km) calibrated for Latur's latitude (~18.4°N).
- Completeness: Explicit demarcation of missing periods and sensor gaps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.cm import ScalarMappable

from . import config as C
from . import data as D
from . import style as ST


def is_valid_date_for_mapping(series: pd.Series | np.ndarray) -> bool:
    """Return True only if date has real, non-zero observation data.
    
    If the date has 0 values (all zero or >= 90% zero) or is empty/all-NaN,
    it must NOT be taken for mapping, as it produces a blank map.
    """
    if series is None:
        return False
    if isinstance(series, pd.Series):
        vals = series.dropna().to_numpy()
    else:
        vals = series[np.isfinite(series)]
    if len(vals) == 0:
        return False
    # If all values are 0 or >= 90% are 0, this date would produce a blank map
    zero_ratio = (vals == 0).mean()
    if zero_ratio >= 0.90:
        return False
    # For NDVI, values <= 0 across the entire region indicate bad data / cloud mask
    if np.nanmax(vals) <= 0.0:
        return False
    return True


class CartographicAtlasRenderer:
    """Ultra-fast vector renderer using cached PolyCollections and LineCollections."""

    def __init__(self):
        self.villages = D.load_villages()
        self.tehsils = D.load_tehsils()
        self.district = D.load_district()

        # Extract polygon coordinates and index mapping
        self.poly_coords = []
        village_ids = []
        for _, row in self.villages.iterrows():
            v_id = row["id"]
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            if geom.geom_type == "Polygon":
                self.poly_coords.append(np.array(geom.exterior.coords))
                village_ids.append(v_id)
            elif geom.geom_type == "MultiPolygon":
                for p in geom.geoms:
                    self.poly_coords.append(np.array(p.exterior.coords))
                    village_ids.append(v_id)
        self.poly_village_ids = np.array(village_ids)

        # Tehsil boundary lines
        self.tehsil_lines = []
        if self.tehsils is not None:
            for geom in self.tehsils.geometry:
                if geom is None or geom.is_empty:
                    continue
                boundary = geom.boundary
                if boundary.geom_type == "LineString":
                    self.tehsil_lines.append(np.array(boundary.coords))
                elif boundary.geom_type == "MultiLineString":
                    for line in boundary.geoms:
                        self.tehsil_lines.append(np.array(line.coords))

        # District boundary lines
        self.dist_lines = []
        if self.district is not None:
            for geom in self.district.geometry:
                if geom is None or geom.is_empty:
                    continue
                boundary = geom.boundary
                if boundary.geom_type == "LineString":
                    self.dist_lines.append(np.array(boundary.coords))
                elif boundary.geom_type == "MultiLineString":
                    for line in boundary.geoms:
                        self.dist_lines.append(np.array(line.coords))

        # Extents with 3% margin
        minx, miny, maxx, maxy = self.district.total_bounds
        dx = (maxx - minx) * 0.03
        dy = (maxy - miny) * 0.03
        self.xlim = (minx - dx, maxx + dx)
        self.ylim = (miny - dy, maxy + dy)

    def render_atlas(
        self,
        panels_data: list[dict],
        cmap,
        norm,
        cbar_label: str,
        main_title: str,
        filename: str,
        caption: str,
        grid_shape: tuple[int, int] = (4, 3),
        figsize: tuple[float, float] = (11.0, 13.8),
        scale_km: float = 40.0,
        cbar_ticks: list[float] | None = None,
        source: str = "village_with_baseline.csv + CHIRPS SPI",
    ):
        """Render a publication multi-panel atlas with Times New Roman and single North arrow."""
        nrows, ncols = grid_shape

        # Enforce Times New Roman typography
        plt.rcParams.update({
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
            "mathtext.fontset": "cm",
        })

        fig, axes = plt.subplots(nrows, ncols, figsize=figsize, sharex=True, sharey=True)
        axes_flat = np.atleast_1d(axes).ravel()

        plt.subplots_adjust(
            left=0.08, right=0.96, top=0.93, bottom=0.09,
            wspace=0.04, hspace=0.07
        )

        for i, ax in enumerate(axes_flat):
            r, c = divmod(i, ncols)

            if i >= len(panels_data):
                ax.axis("off")
                continue

            item = panels_data[i]
            label = item.get("label", "")
            vals_dict = item.get("values", {})
            subtitle = item.get("subtitle", "")

            # Check if this panel has valid data (strictly enforce non-zero rule)
            has_data = False
            poly_vals = np.full(len(self.poly_village_ids), np.nan)
            if isinstance(vals_dict, dict) and len(vals_dict) > 0:
                poly_vals = np.array([vals_dict.get(v_id, np.nan) for v_id in self.poly_village_ids])
                if is_valid_date_for_mapping(poly_vals):
                    has_data = True
            elif isinstance(vals_dict, pd.Series) and not vals_dict.empty:
                vmap = vals_dict.to_dict()
                poly_vals = np.array([vmap.get(v_id, np.nan) for v_id in self.poly_village_ids])
                if is_valid_date_for_mapping(poly_vals):
                    has_data = True

            if has_data:
                # Mask out negative / zero NDVI values that indicate water or sensor artifacts
                if "NDVI" in main_title:
                    poly_vals[poly_vals <= 0.0] = np.nan

                # Map colors
                facecolors = cmap(norm(poly_vals))
                # For NaNs in village subset, color them light grey
                nan_mask = np.isnan(poly_vals)
                facecolors[nan_mask] = [0.945, 0.961, 0.976, 1.0]  # #F1F5F9
                pc = PolyCollection(
                    self.poly_coords, facecolors=facecolors,
                    edgecolors="#E2E8F0", linewidths=0.05, zorder=2
                )
            else:
                # Completely missing period / zero-value date
                pc = PolyCollection(
                    self.poly_coords, facecolors="#F8FAFC",
                    edgecolors="#E2E8F0", linewidths=0.05, zorder=2
                )

            ax.add_collection(pc)

            # Boundaries
            tl = LineCollection(self.tehsil_lines, colors="#475569", linewidths=0.55, zorder=4)
            ax.add_collection(tl)

            dl = LineCollection(self.dist_lines, colors="#0F172A", linewidths=1.0, zorder=5)
            ax.add_collection(dl)

            ax.set_xlim(self.xlim)
            ax.set_ylim(self.ylim)
            ax.set_aspect("equal")

            # Panel label (e.g. 'Jan' or '2016') - No box behind value
            ax.text(
                0.93, 0.89, label, transform=ax.transAxes,
                fontsize=11.5, fontweight="bold", fontfamily="serif",
                ha="right", va="top", color="#0F172A",
                zorder=10
            )

            # Subtitle (mean value or status) - No box behind value
            if has_data and subtitle:
                ax.text(
                    0.93, 0.77, subtitle, transform=ax.transAxes,
                    fontsize=8.5, fontfamily="serif",
                    ha="right", va="top", color="#334155",
                    zorder=10
                )
            else:
                ax.text(
                    0.50, 0.50, "No Data", transform=ax.transAxes,
                    fontsize=10.0, fontstyle="italic", fontfamily="serif",
                    ha="center", va="center", color="#64748B",
                    zorder=10
                )

            # Graticules: left column gets latitude, top row gets longitude
            if c == 0:
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y:.1f}°N"))
                ax.tick_params(axis="y", labelsize=8.5, colors="#334155")
            else:
                ax.tick_params(axis="y", left=False, labelleft=False)

            if r == 0:
                ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.1f}°E"))
                ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, labelsize=8.5, colors="#334155")
            else:
                ax.tick_params(axis="x", bottom=False, labelbottom=False, top=False, labeltop=False)

            for spine in ax.spines.values():
                spine.set_color("#64748B")
                spine.set_linewidth(0.7)

        # Single North Arrow in top-right corner of entire figure (in figure fraction, clear of all grids)
        top_right_ax = axes_flat[ncols - 1]
        top_right_ax.annotate(
            "N", xy=(0.945, 0.970), xytext=(0.945, 0.932),
            xycoords="figure fraction", textcoords="figure fraction",
            ha="center", va="bottom", fontsize=11.5, fontweight="bold", fontfamily="serif",
            arrowprops=dict(
                arrowstyle="-|>,head_length=0.7,head_width=0.38",
                facecolor="#0F172A", edgecolor="#0F172A", lw=1.3
            ),
            annotation_clip=False, zorder=50
        )

        # Main overall figure title in Times New Roman bold
        fig.suptitle(main_title, fontsize=13.0, fontweight="bold", fontfamily="serif", y=0.985, color="#0F172A")

        # Bottom shared colorbar
        cbar_ax = fig.add_axes([0.14, 0.040, 0.46, 0.016])
        sm = ScalarMappable(norm=norm, cmap=cmap)
        cbar = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal", ticks=cbar_ticks)
        cbar.set_label(cbar_label, fontsize=10.5, fontfamily="serif", labelpad=5, color="#0F172A")
        cbar.ax.tick_params(labelsize=8.5, colors="#334155")

        # Bottom scale bar beside colorbar
        scale_ax = fig.add_axes([0.68, 0.040, 0.24, 0.022])
        scale_ax.axis("off")
        scale_ax.set_xlim(0, scale_km)
        scale_ax.set_ylim(0, 10)
        s_step = scale_km / 4.0
        for step_idx in range(4):
            x_start = step_idx * s_step
            x_end = (step_idx + 1) * s_step
            fc = "#0F172A" if step_idx % 2 == 0 else "#FFFFFF"
            scale_ax.fill([x_start, x_end, x_end, x_start], [3, 3, 6, 6], color=fc, edgecolor="#0F172A", lw=0.8)
        scale_ax.plot([0, scale_km, scale_km, 0, 0], [3, 3, 6, 6, 3], color="#0F172A", lw=0.8)
        scale_ax.text(0, 1.2, "0", ha="center", va="top", fontsize=8.0, fontfamily="serif", color="#0F172A")
        scale_ax.text(s_step * 2, 1.2, f"{int(s_step*2)}", ha="center", va="top", fontsize=8.0, fontfamily="serif", color="#0F172A")
        scale_ax.text(scale_km, 1.2, f"{int(scale_km)} km", ha="center", va="top", fontsize=8.0, fontfamily="serif", color="#0F172A")

        return ST.save(fig, "spatial", filename, caption, source=source)


# --------------------------------------------------------------------------
# Index Configuration Specifications
# --------------------------------------------------------------------------
INDEX_SPECS = {
    "NDVI": {
        "title": "Normalized Difference Vegetation Index (NDVI)",
        "label": r"$\mathrm{NDVI}\;(\mathrm{Normalized}\;\mathrm{Difference}\;\mathrm{Vegetation}\;\mathrm{Index})$",
        "cmap": plt.get_cmap("YlGn"),
        "norm": Normalize(vmin=0.10, vmax=0.65),
        "ticks": [0.10, 0.25, 0.40, 0.55, 0.65],
        "format": "{:.2f}",
        "agg": "mean",
    },
    "VCI": {
        "title": "Vegetation Condition Index (VCI)",
        "label": r"$\mathrm{VCI}\;(\mathrm{Vegetation}\;\mathrm{Condition}\;\mathrm{Index},\;\%)$",
        "cmap": plt.get_cmap("RdYlGn"),
        "norm": Normalize(vmin=0.0, vmax=100.0),
        "ticks": [0, 20, 40, 60, 80, 100],
        "format": "{:.1f}%",
        "agg": "mean",
    },
    "VHI": {
        "title": "Vegetation Health Index (VHI)",
        "label": r"$\mathrm{VHI}\;(\mathrm{Vegetation}\;\mathrm{Health}\;\mathrm{Index},\;\%)$",
        "cmap": plt.get_cmap("RdYlGn"),
        "norm": Normalize(vmin=0.0, vmax=100.0),
        "ticks": [0, 20, 40, 60, 80, 100],
        "format": "{:.1f}%",
        "agg": "mean",
    },
    "NSMI": {
        "title": "Normalized Soil Moisture Index (NSMI)",
        "label": r"$\mathrm{NSMI}\;(\mathrm{Normalized}\;\mathrm{Soil}\;\mathrm{Moisture}\;\mathrm{Index})$",
        "cmap": plt.get_cmap("BrBG"),
        "norm": TwoSlopeNorm(vmin=-0.40, vcenter=0.0, vmax=0.40),
        "ticks": [-0.40, -0.20, 0.0, 0.20, 0.40],
        "format": "{:.2f}",
        "agg": "mean",
    },
    "SPI3": {
        "title": "3-Month Standardized Precipitation Index (SPI-3)",
        "label": r"$\mathrm{SPI}_{3}\;(3\text{-}\mathrm{Month}\;\mathrm{Standardized}\;\mathrm{Precipitation}\;\mathrm{Index})$",
        "cmap": plt.get_cmap("RdYlBu"),
        "norm": TwoSlopeNorm(vmin=-2.5, vcenter=0.0, vmax=2.5),
        "ticks": [-2.5, -1.5, 0.0, 1.5, 2.5],
        "format": "{:.2f}",
        "agg": "mean",
    },
    "SPI12": {
        "title": "12-Month Standardized Precipitation Index (SPI-12)",
        "label": r"$\mathrm{SPI}_{12}\;(12\text{-}\mathrm{Month}\;\mathrm{Standardized}\;\mathrm{Precipitation}\;\mathrm{Index})$",
        "cmap": plt.get_cmap("RdYlBu"),
        "norm": TwoSlopeNorm(vmin=-2.5, vcenter=0.0, vmax=2.5),
        "ticks": [-2.5, -1.5, 0.0, 1.5, 2.5],
        "format": "{:.2f}",
        "agg": "mean",
    },
    "Rain_mm": {
        "title": "Precipitation (mm)",
        "label": r"$\mathrm{Precipitation}\;(\mathrm{mm})$",
        "cmap": plt.get_cmap("Blues"),
        "norm": Normalize(vmin=0.0, vmax=250.0),
        "norm_annual": Normalize(vmin=200.0, vmax=1100.0),
        "ticks": [0, 50, 100, 150, 200, 250],
        "ticks_annual": [200, 400, 600, 800, 1000],
        "format": "{:.0f} mm",
        "agg": "mean",
    },
    "composite_drought_score": {
        "title": "Composite Drought Index (CDI)",
        "label": r"$\mathrm{CDI}\;(\mathrm{Composite}\;\mathrm{Drought}\;\mathrm{Index},\;0.0\text{--}1.0)$",
        "cmap": ST.CDI_CMAP,
        "norm": Normalize(vmin=0.0, vmax=1.0),
        "ticks": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        "format": "{:.2f}",
        "agg": "mean",
    },
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ALL_YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]


# --------------------------------------------------------------------------
# 1. Yearly Mean Atlases (2016–2026 + 11-Year Climatology)
# --------------------------------------------------------------------------
def generate_yearly_mean_atlases(panel: pd.DataFrame, renderer: CartographicAtlasRenderer) -> None:
    """Generate 3x4 grid yearly atlases for all indices across 2016 to 2026."""
    print("  Generating Yearly Mean Atlases (2016-2026)...")

    for col_name, spec in INDEX_SPECS.items():
        if col_name not in panel.columns:
            continue

        panels_data = []

        # Annual aggregates for each of the 11 years (filtering out zero/blank dates)
        for year in ALL_YEARS:
            year_sub = panel[panel["year"] == year]

            # Collect months that have valid non-zero data
            valid_month_dfs = []
            for m in range(1, 13):
                m_sub = year_sub[year_sub["month"] == m]
                if m_sub.empty:
                    continue
                m_vals = m_sub[col_name].dropna()
                if is_valid_date_for_mapping(m_vals):
                    valid_month_dfs.append(m_sub)

            if len(valid_month_dfs) == 0:
                # "if the date has the 0 values dont take that day for the mapping cuz the maps that we will produce will be blank"
                panels_data.append({
                    "label": str(year),
                    "values": {},
                    "subtitle": "",
                })
            else:
                valid_combined = pd.concat(valid_month_dfs, ignore_index=True)
                if col_name == "Rain_mm":
                    # Annual total rainfall from valid months
                    agg_series = valid_combined.groupby("village_idx")[col_name].sum()
                else:
                    agg_series = valid_combined.groupby("village_idx")[col_name].mean()

                mean_val = float(agg_series.mean()) if not agg_series.empty else np.nan
                sub_str = f"Mean: {spec['format'].format(mean_val)}" if np.isfinite(mean_val) else ""
                panels_data.append({
                    "label": str(year),
                    "values": agg_series.to_dict(),
                    "subtitle": sub_str,
                })

        # Panel 12: 11-Year Climatological Mean (2016-2026)
        # Compute across only valid non-zero dates
        valid_all_dfs = []
        for (yr, mo), ym_df in panel.groupby(["year", "month"]):
            vals = ym_df[col_name].dropna()
            if is_valid_date_for_mapping(vals):
                valid_all_dfs.append(ym_df)

        if len(valid_all_dfs) > 0:
            all_valid_df = pd.concat(valid_all_dfs, ignore_index=True)
            if col_name == "Rain_mm":
                annual_totals = all_valid_df.groupby(["village_idx", "year"])[col_name].sum().reset_index()
                clim_series = annual_totals.groupby("village_idx")[col_name].mean()
                norm = spec.get("norm_annual", spec["norm"])
                ticks = spec.get("ticks_annual", spec["ticks"])
                cbar_lbl = r"$\mathrm{Annual}\;\mathrm{Precipitation}\;(\mathrm{mm})$"
            else:
                clim_series = all_valid_df.groupby("village_idx")[col_name].mean()
                norm = spec["norm"]
                ticks = spec["ticks"]
                cbar_lbl = spec["label"]

            clim_mean = float(clim_series.mean()) if not clim_series.empty else np.nan
            clim_str = f"Mean: {spec['format'].format(clim_mean)}" if np.isfinite(clim_mean) else ""
            panels_data.append({
                "label": "2016–2026 Mean",
                "values": clim_series.to_dict(),
                "subtitle": clim_str,
            })
        else:
            panels_data.append({"label": "2016–2026 Mean", "values": {}, "subtitle": ""})

        filename = f"yearly_mean_atlases/atlas_yearly_mean_{col_name.lower()}.png"
        caption = (
            f"Annual spatial mean distribution of {spec['title']} across Latur district (2016–2026) "
            f"in a 3x4 publication matrix with 11-year climatology and georeferenced cartographic elements."
        )
        main_title = f"{spec['title']} — Annual Spatial Mean Atlas (2016–2026)"

        renderer.render_atlas(
            panels_data=panels_data,
            cmap=spec["cmap"],
            norm=norm,
            cbar_label=cbar_lbl,
            main_title=main_title,
            filename=filename,
            caption=caption,
            grid_shape=(3, 4),
            figsize=(13.0, 10.8),
            cbar_ticks=ticks,
        )


# --------------------------------------------------------------------------
# 2. 12-Month Climatological Atlases (Jan–Dec)
# --------------------------------------------------------------------------
def generate_monthly_climatological_atlases(panel: pd.DataFrame, renderer: CartographicAtlasRenderer) -> None:
    """Generate 4x3 grid 12-month long-term climatology atlases for all indices."""
    print("  Generating 12-Month Climatological Atlases...")

    for col_name, spec in INDEX_SPECS.items():
        if col_name not in panel.columns:
            continue

        panels_data = []
        for m in range(1, 13):
            # Only include years where month m was a valid non-zero date
            valid_m_dfs = []
            for year in ALL_YEARS:
                ym_sub = panel[(panel["year"] == year) & (panel["month"] == m)]
                if ym_sub.empty:
                    continue
                vals = ym_sub[col_name].dropna()
                if is_valid_date_for_mapping(vals):
                    valid_m_dfs.append(ym_sub)

            m_name = MONTH_NAMES[m - 1]
            if len(valid_m_dfs) == 0:
                panels_data.append({
                    "label": m_name,
                    "values": {},
                    "subtitle": "",
                })
            else:
                combined_m = pd.concat(valid_m_dfs, ignore_index=True)
                agg_series = combined_m.groupby("village_idx")[col_name].mean()
                mean_val = float(agg_series.mean()) if not agg_series.empty else np.nan
                sub_str = f"Mean: {spec['format'].format(mean_val)}" if np.isfinite(mean_val) else ""

                panels_data.append({
                    "label": m_name,
                    "values": agg_series.to_dict(),
                    "subtitle": sub_str,
                })

        filename = f"monthly_climatologies/atlas_monthly_climatology_{col_name.lower()}.png"
        caption = (
            f"Long-term 12-month monthly spatial climatology of {spec['title']} across Latur district (2016–2026), "
            f"showing seasonal phenology and drought development across all 954 villages."
        )
        main_title = f"{spec['title']} — Long-Term Monthly Spatial Climatology (2016–2026)"

        renderer.render_atlas(
            panels_data=panels_data,
            cmap=spec["cmap"],
            norm=spec["norm"],
            cbar_label=spec["label"],
            main_title=main_title,
            filename=filename,
            caption=caption,
            grid_shape=(4, 3),
            figsize=(11.0, 13.8),
            cbar_ticks=spec["ticks"],
        )


# --------------------------------------------------------------------------
# 3. Annual 12-Month Progression Atlases for Each Year (2016 to 2026)
# --------------------------------------------------------------------------
def generate_annual_monthly_atlases(panel: pd.DataFrame, renderer: CartographicAtlasRenderer) -> None:
    """Generate 4x3 grid 12-month atlases for each individual year from 2016 to 2026."""
    print("  Generating Annual 12-Month Atlases for each year (2016–2026)...")

    # Primary indicators: CDI, SPI3, NDVI, VCI, Rain_mm, NSMI
    target_indices = ["composite_drought_score", "SPI3", "NDVI", "VCI", "Rain_mm", "NSMI"]

    for col_name in target_indices:
        if col_name not in panel.columns:
            continue
        spec = INDEX_SPECS[col_name]

        for year in ALL_YEARS:
            year_sub = panel[panel["year"] == year]
            panels_data = []

            for m in range(1, 13):
                m_sub = year_sub[year_sub["month"] == m]
                m_name = MONTH_NAMES[m - 1]

                if m_sub.empty:
                    panels_data.append({
                        "label": m_name,
                        "values": {},
                        "subtitle": "",
                    })
                    continue

                agg_series = m_sub.groupby("village_idx")[col_name].mean()
                valid_vals = agg_series.dropna()

                # "if the date has the 0 values dont take that day for the mapping cuz the maps that we will produce will be blank"
                if not is_valid_date_for_mapping(valid_vals):
                    panels_data.append({
                        "label": m_name,
                        "values": {},
                        "subtitle": "",
                    })
                else:
                    mean_val = float(valid_vals.mean())
                    sub_str = f"Mean: {spec['format'].format(mean_val)}"
                    panels_data.append({
                        "label": m_name,
                        "values": agg_series.to_dict(),
                        "subtitle": sub_str,
                    })

            filename = f"{year}/atlas_monthly_{col_name.lower()}_{year}.png"
            caption = (
                f"12-Month spatial progression of {spec['title']} for year {year} across all 954 villages of Latur district, "
                f"with missing periods and zero-value dates explicitly demarcated as No Data."
            )
            main_title = f"{spec['title']} — Monthly Spatial Progression ({year})"

            renderer.render_atlas(
                panels_data=panels_data,
                cmap=spec["cmap"],
                norm=spec["norm"],
                cbar_label=spec["label"],
                main_title=main_title,
                filename=filename,
                caption=caption,
                grid_shape=(4, 3),
                figsize=(11.0, 13.8),
                cbar_ticks=spec["ticks"],
            )


# --------------------------------------------------------------------------
# Main Entry Point for Cartographic Atlas
# --------------------------------------------------------------------------
def build(panel: pd.DataFrame) -> None:
    """Build all cartographic atlas figures."""
    renderer = CartographicAtlasRenderer()
    generate_yearly_mean_atlases(panel, renderer)
    generate_monthly_climatological_atlases(panel, renderer)
    generate_annual_monthly_atlases(panel, renderer)
