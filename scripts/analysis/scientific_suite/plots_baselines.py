# -*- coding: utf-8 -*-
"""Climatological Baselines Cartographic Generator: Publication-Grade Spatial Maps.

Generates:
1. Individual high-resolution choropleth maps for the 8 core drought baselines:
   - Baseline NDVI (Normalized Difference Vegetation Index)
   - Baseline CDI (Composite Drought Index severity)
   - Baseline EVI (Enhanced Vegetation Index)
   - Baseline NSMI (Normalized Soil Moisture Index, SAR)
   - Baseline SPI-1 (1-Month Standardized Precipitation Index)
   - Baseline VHI (Vegetation Health Index)
   - Baseline VCI (Vegetation Condition Index)
   - Baseline Rainfall (CHIRPS precipitation depth, mm/month)
2. Master 8-Panel Climatological Baseline Atlas (2x4 comparison sheet)
3. Kharif Crop Season Baseline Atlas (July-October active agricultural baseline)
4. Comprehensive village-level research data table:
   output/figures/scientific_suite/08_statistics_tables/village_climatological_baselines.csv

Cartographic Standards:
- Strict Times New Roman serif typography throughout.
- Single authoritative North arrow in the upper right.
- Georeferenced scale bar (0-20 km).
- Georeferenced coordinate degree ticks (Lat/Lon).
- Bold tehsil boundaries with high-contrast white-halo labels and district border.
- Clean typography without text collisions or overlapping titles.
"""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize, TwoSlopeNorm

from . import config as C
from . import data as D
from . import style as ST


def lon_formatter(x, pos):
    return f"{x:.1f}°E"


def lat_formatter(y, pos):
    return f"{y:.1f}°N"


INDICATOR_SPECS = {
    "NDVI": {
        "col": "NDVI",
        "name": "NDVI",
        "full_name": "Normalized Difference Vegetation Index (NDVI)",
        "unit": "Canopy Greenness Normal",
        "cmap": ST.VEG_CMAP,
        "vmin": 0.12,
        "vmax": 0.34,
        "norm_type": "linear",
        "description": "Ten-year climatological mean NDVI baseline representing reference vegetative biomass and canopy greenness across 954 villages.",
        "high_is_drought": False,
    },
    "CDI": {
        "col": "composite_drought_score",
        "name": "CDI",
        "full_name": "Composite Drought Index (CDI)",
        "unit": "Severity Score Normal (0.0 = Normal, 1.0 = Extreme)",
        "cmap": ST.CDI_CMAP,
        "vmin": 0.10,
        "vmax": 0.22,
        "norm_type": "linear",
        "description": "Ten-year baseline Composite Drought Index (CDI) severity score, establishing the long-term climatological vulnerability baseline across 954 villages.",
        "high_is_drought": True,
    },
    "EVI": {
        "col": "EVI",
        "name": "EVI",
        "full_name": "Enhanced Vegetation Index (EVI)",
        "unit": "Canopy Vigor Normal",
        "cmap": ST.VEG_CMAP,
        "vmin": 0.12,
        "vmax": 0.32,
        "norm_type": "linear",
        "description": "Ten-year baseline Enhanced Vegetation Index (EVI) adjusting for soil background reflectance and atmospheric aerosol scattering.",
        "high_is_drought": False,
    },
    "NSMI": {
        "col": "NSMI",
        "name": "NSMI",
        "full_name": "Normalized Soil Moisture Index (NSMI)",
        "unit": "Relative Permittivity Normal (0.0 to 1.0)",
        "cmap": ST.SOIL_CMAP,
        "vmin": 0.15,
        "vmax": 0.25,
        "norm_type": "linear",
        "description": "Sentinel-1 C-band Synthetic Aperture Radar (SAR) root-zone soil moisture baseline, capturing all-weather dielectric permittivity normal.",
        "high_is_drought": False,
    },
    "SPI1": {
        "col": "SPI1",
        "name": "SPI-1",
        "full_name": "1-Month Standardized Precipitation Index (SPI-1)",
        "unit": "Standardized Anomaly Baseline",
        "cmap": "RdYlBu",
        "vmin": -0.0045,
        "vmax": -0.0015,
        "vcenter": -0.0030,
        "norm_type": "twoslope",
        "description": "Long-term reference 1-month Standardized Precipitation Index baseline, establishing meteorological equilibrium and drought departure threshold.",
        "high_is_drought": False,
    },
    "VHI": {
        "col": "VHI",
        "name": "VHI",
        "full_name": "Vegetation Health Index (VHI)",
        "unit": "Health Index Normal (%)",
        "cmap": "RdYlGn",
        "vmin": 40.0,
        "vmax": 60.0,
        "norm_type": "linear",
        "description": "Joint vegetative condition (VCI) and thermal evaporative stress (TCI) baseline, reflecting composite plant stress normal.",
        "high_is_drought": False,
    },
    "VCI": {
        "col": "VCI",
        "name": "VCI",
        "full_name": "Vegetation Condition Index (VCI)",
        "unit": "Condition Index Normal (%)",
        "cmap": "RdYlGn",
        "vmin": 40.0,
        "vmax": 60.0,
        "norm_type": "linear",
        "description": "Phenological expectation baseline scaling long-term vegetation condition relative to historical extremes across 954 villages.",
        "high_is_drought": False,
    },
    "Rain_mm": {
        "col": "Rain_mm",
        "name": "Rainfall",
        "full_name": "Monthly Precipitation Depth (CHIRPS v2.0)",
        "unit": "Precipitation Normal (mm / month)",
        "cmap": ST.RAIN_CMAP,
        "vmin": 75.0,
        "vmax": 95.0,
        "norm_type": "linear",
        "description": "CHIRPS v2.0 long-term mean monthly precipitation depth baseline, providing the climatological water input reference.",
        "high_is_drought": False,
    },
}


def _draw_baseline_map(
    ax,
    gdf,
    col_name: str,
    spec: dict,
    district,
    tehsils,
    title: str,
    cbar_label: str = "",
    panel_tag: str | None = None,
    is_standalone: bool = True,
):
    """Draw a publication-grade cartographic choropleth with zero text overlap."""
    norm = None
    if spec["norm_type"] == "twoslope":
        norm = TwoSlopeNorm(
            vcenter=spec.get("vcenter", 0.0),
            vmin=spec["vmin"],
            vmax=spec["vmax"],
        )
    else:
        norm = Normalize(vmin=spec["vmin"], vmax=spec["vmax"])

    gdf.plot(
        column=col_name,
        ax=ax,
        cmap=spec["cmap"],
        norm=norm,
        edgecolor="#CBD5E1",
        linewidth=0.15 if is_standalone else 0.08,
        missing_kwds={
            "color": "#F1F5F9",
            "edgecolor": "#CBD5E1",
            "linewidth": 0.1,
            "label": "No data",
        },
        legend=is_standalone,
        legend_kwds={
            "label": cbar_label or spec["unit"],
            "orientation": "horizontal",
            "shrink": 0.50 if is_standalone else 0.70,
            "pad": 0.05 if is_standalone else 0.04,
            "aspect": 30,
        }
        if is_standalone
        else None,
    )

    # Plot administrative tehsil boundaries
    if tehsils is not None:
        tehsils.boundary.plot(ax=ax, color="#0F172A", linewidth=0.85 if is_standalone else 0.65, zorder=5)
        if is_standalone:
            for _, row in tehsils.iterrows():
                if row.geometry is None or row.geometry.is_empty:
                    continue
                pt = row.geometry.representative_point()
                name = str(row.get("TEHSIL", "")).upper()
                ax.text(
                    pt.x,
                    pt.y,
                    name,
                    fontsize=7.5,
                    weight="bold",
                    color="#0F172A",
                    ha="center",
                    va="center",
                    zorder=8,
                    fontfamily="serif",
                    path_effects=[pe.withStroke(linewidth=3.0, foreground="white")],
                )

    # Plot district perimeter
    if district is not None:
        district.boundary.plot(ax=ax, color="#000000", linewidth=1.5 if is_standalone else 1.0, zorder=7)

    # Coordinate ticks and neatlines
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lon_formatter))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lat_formatter))
    ax.tick_params(labelsize=8.0 if is_standalone else 6.5, colors="#334155")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#334155")
        spine.set_linewidth(0.85)

    # Cartographic ornaments
    if is_standalone:
        ST.add_scale_bar(ax, length_km=20.0, x=0.06, y=0.06)
        ST.add_north_arrow(ax, x=0.92, y=0.88, length=0.07)
    if panel_tag:
        ST.add_panel_label(ax, label=panel_tag, x=-0.04, y=1.03, fontsize=11.0)

    # Clean title placement without collisions
    if title:
        ax.set_title(
            title,
            fontsize=12.0 if is_standalone else 9.5,
            weight="bold",
            pad=14 if is_standalone else 6,
            color="#0F172A",
            fontfamily="serif",
            linespacing=1.25,
        )


def build_baselines(panel: pd.DataFrame | None = None) -> list[Path]:
    """Compute and render all baseline maps and master atlases."""
    ST.apply_style()
    if panel is None:
        panel = D.load_panel()

    gdf_villages = D.load_villages()
    gdf_tehsils = D.load_tehsils()
    gdf_district = D.load_district()

    # 1. Compute multi-year decadal baselines per village
    agg_dict = {spec["col"]: "mean" for spec in INDICATOR_SPECS.values()}
    village_means = panel.groupby("village_idx")[list(agg_dict.keys())].mean().reset_index()

    # Rename to clean baseline column names
    rename_map = {spec["col"]: f"baseline_{key}" for key, spec in INDICATOR_SPECS.items()}
    village_baselines = village_means.rename(columns=rename_map)

    # 2. Compute Kharif seasonal baselines (July to October - peak monsoon crop season)
    kharif_panel = panel[panel["month"].isin([7, 8, 9, 10])]
    kharif_means = kharif_panel.groupby("village_idx")[list(agg_dict.keys())].mean().reset_index()
    kharif_rename = {spec["col"]: f"kharif_baseline_{key}" for key, spec in INDICATOR_SPECS.items()}
    kharif_baselines = kharif_means.rename(columns=kharif_rename)

    # Merge decadal and Kharif baselines
    combined_baselines = village_baselines.merge(kharif_baselines, on="village_idx", how="left")

    # Merge with village shapefile
    merged = gdf_villages.merge(combined_baselines, left_on="id", right_on="village_idx", how="left")

    # Export machine-readable research CSV table
    out_table_dir = C.section_dir("tables")
    out_table_dir.mkdir(parents=True, exist_ok=True)
    table_path = out_table_dir / "village_climatological_baselines.csv"

    export_df = pd.DataFrame({
        "village_idx": merged["id"],
        "village_name": merged.get("village_name", merged.get("village", "")),
        "tehsil": merged.get("tehsil", ""),
        "baseline_NDVI": merged["baseline_NDVI"].round(4),
        "baseline_CDI": merged["baseline_CDI"].round(4),
        "baseline_EVI": merged["baseline_EVI"].round(4),
        "baseline_NSMI": merged["baseline_NSMI"].round(4),
        "baseline_SPI1": merged["baseline_SPI1"].round(4),
        "baseline_VHI": merged["baseline_VHI"].round(2),
        "baseline_VCI": merged["baseline_VCI"].round(2),
        "baseline_Rain_mm": merged["baseline_Rain_mm"].round(2),
        "kharif_baseline_NDVI": merged["kharif_baseline_NDVI"].round(4),
        "kharif_baseline_CDI": merged["kharif_baseline_CDI"].round(4),
        "kharif_baseline_Rain_mm": merged["kharif_baseline_Rain_mm"].round(2),
    })
    export_df.to_csv(table_path, index=False, encoding="utf-8-sig")
    print(f"  [tables] village_climatological_baselines.csv (rows={len(export_df)})")

    generated_paths = []

    # ----------------------------------------------------------------------
    # 3. Generate Individual High-Resolution Baseline Maps
    # ----------------------------------------------------------------------
    for key, spec in INDICATOR_SPECS.items():
        base_col = f"baseline_{key}"
        fig, ax = plt.subplots(figsize=(11.0, 9.8), layout="constrained")

        title = (
            f"Decadal Climatological Baseline: {spec['full_name']}\n"
            f"11-Year Reference Standard Across 954 Villages (2016–2026)"
        )

        _draw_baseline_map(
            ax=ax,
            gdf=merged,
            col_name=base_col,
            spec=spec,
            district=gdf_district,
            tehsils=gdf_tehsils,
            title=title,
            cbar_label=f"Baseline {spec['name']} ({spec['unit']})",
            is_standalone=True,
        )

        filename = f"baselines/map_baseline_{key.lower()}.png"
        saved = ST.save(
            fig,
            "spatial",
            filename,
            caption=f"Cadastral choropleth map of the 11-year reference baseline for {spec['full_name']} across all 954 revenue villages in Latur District.",
            source="village_with_baseline.csv + latur_villages.geojson (2016-2026 climatological normal)",
        )
        generated_paths.append(saved)

    # ----------------------------------------------------------------------
    # 4. Generate Master 8-Panel Climatological Baseline Comparison Atlas
    # ----------------------------------------------------------------------
    fig, axes = plt.subplots(2, 4, figsize=(22.0, 12.0), layout="constrained")
    axes_flat = axes.flatten()

    indicator_keys = ["NDVI", "CDI", "EVI", "NSMI", "SPI1", "VHI", "VCI", "Rain_mm"]
    panel_tags = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)", "(h)"]

    for idx, key in enumerate(indicator_keys):
        ax = axes_flat[idx]
        spec = INDICATOR_SPECS[key]
        base_col = f"baseline_{key}"

        _draw_baseline_map(
            ax=ax,
            gdf=merged,
            col_name=base_col,
            spec=spec,
            district=gdf_district,
            tehsils=gdf_tehsils,
            title=f"{panel_tags[idx]} Baseline {spec['name']}",
            cbar_label="",
            panel_tag=None,
            is_standalone=False,
        )

        # Individual colorbar below each panel in the grid
        norm = None
        if spec["norm_type"] == "twoslope":
            norm = TwoSlopeNorm(vcenter=spec.get("vcenter", 0.0), vmin=spec["vmin"], vmax=spec["vmax"])
        else:
            norm = Normalize(vmin=spec["vmin"], vmax=spec["vmax"])

        sm = plt.cm.ScalarMappable(cmap=spec["cmap"], norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", shrink=0.72, pad=0.03, aspect=24)
        cbar.ax.tick_params(labelsize=7.0)
        cbar.set_label(spec["unit"], fontsize=7.5, fontfamily="serif")

    # Master title and top-level North arrow and scale bar on panel (d)
    ST.add_north_arrow(axes_flat[3], x=0.90, y=0.86, length=0.08)
    ST.add_scale_bar(axes_flat[3], length_km=20.0, x=0.06, y=0.06)

    fig.suptitle(
        "Decadal Climatological Baselines for All Multi-Index Indicators — Latur District (954 Villages, 2016–2026)\n"
        "Reference normals from which positive/negative departures establish hydrological, agricultural, and vegetative drought severity",
        fontsize=14.0,
        fontfamily="serif",
        weight="bold",
    )

    saved_master = ST.save(
        fig,
        "spatial",
        "baselines/atlas_all_indices_baseline_comparison.png",
        caption="Master 8-panel cartographic atlas comparing decadal climatological baselines across all biophysical, meteorological, and composite indices for 954 revenue villages.",
        source="Multi-sensor baseline synthesis (Sentinel-2, Sentinel-1 SAR, Landsat TIRS, CHIRPS v2.0)",
    )
    generated_paths.append(saved_master)

    # ----------------------------------------------------------------------
    # 5. Generate Kharif Crop Season Baseline Atlas (July–October)
    # ----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 4, figsize=(22.0, 6.4), layout="constrained")
    kharif_keys = ["NDVI", "CDI", "NSMI", "Rain_mm"]
    kharif_tags = ["(a)", "(b)", "(c)", "(d)"]

    for idx, key in enumerate(kharif_keys):
        ax = axes[idx]
        spec = INDICATOR_SPECS[key]
        base_col = f"kharif_baseline_{key}"

        # Adjust range for active Kharif growing season
        spec_kharif = spec.copy()
        if key == "NDVI":
            spec_kharif["vmin"] = 0.22
            spec_kharif["vmax"] = 0.48
        elif key == "Rain_mm":
            spec_kharif["vmin"] = 120.0
            spec_kharif["vmax"] = 240.0
            spec_kharif["unit"] = "Kharif Rain (mm / month)"
        elif key == "CDI":
            spec_kharif["vmin"] = 0.08
            spec_kharif["vmax"] = 0.24

        _draw_baseline_map(
            ax=ax,
            gdf=merged,
            col_name=base_col,
            spec=spec_kharif,
            district=gdf_district,
            tehsils=gdf_tehsils,
            title=f"{kharif_tags[idx]} Kharif Season Baseline {spec['name']}",
            cbar_label="",
            is_standalone=False,
        )

        norm = Normalize(vmin=spec_kharif["vmin"], vmax=spec_kharif["vmax"])
        sm = plt.cm.ScalarMappable(cmap=spec_kharif["cmap"], norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", shrink=0.72, pad=0.03, aspect=24)
        cbar.ax.tick_params(labelsize=7.0)
        cbar.set_label(spec_kharif["unit"], fontsize=8.0, fontfamily="serif")

    ST.add_north_arrow(axes[3], x=0.90, y=0.86, length=0.08)
    ST.add_scale_bar(axes[3], length_km=20.0, x=0.06, y=0.06)

    fig.suptitle(
        "Kharif Agricultural Season Baseline Normals (July–October, 2016–2026)\n"
        "Reference standards during peak crop phenology against which statutory drought declarations are evaluated",
        fontsize=13.0,
        fontfamily="serif",
        weight="bold",
    )

    saved_kharif = ST.save(
        fig,
        "spatial",
        "baselines/atlas_kharif_crop_season_baselines.png",
        caption="Kharif agricultural season baseline atlas (July–October) establishing the statutory crop-growing normals across 954 villages.",
        source="Kharif seasonal subset of 11-year empirical record",
    )
    generated_paths.append(saved_kharif)

    return generated_paths


if __name__ == "__main__":
    build_baselines()
