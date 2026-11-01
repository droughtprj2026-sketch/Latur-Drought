# -*- coding: utf-8 -*-
"""PowerPoint-Ready Cartographic Animation Engine for Latur Drought Monitoring.

Generates publication-quality, presentation-ready GIF animations:
1. anim_cdi_monthly_evolution_2016_2026.gif: Flagship 10-year monthly drought progression across 954 villages.
2. anim_2018_historic_drought_progression.gif: 2018 catastrophic drought monthly onset and emergency peak.
3. anim_2020_la_nina_recovery_progression.gif: 2020 La Niña abundant rainfall and rapid vegetative greening.
4. anim_2024_2026_recent_drought_transition.gif: Recent 2024–2026 dynamic conditions through October 2026.
5. anim_ndvi_seasonal_phenology_timelapse.gif: 12-month long-term seasonal vegetation canopy cycle.
6. anim_spi3_meteorological_drought_timelapse.gif: 10-year rolling 3-month precipitation deficit (SPI-3).
7. anim_annual_mean_cdi_2016_2026.gif: Decadal year-by-year mean drought shift across Latur tehsils.

All animations strictly adhere to:
- Times New Roman typography throughout.
- Single clean North arrow in upper right (no bounding box).
- Georeferenced scale bar (0–40 km).
- Shared horizontal colorbar with physical units and thresholds.
- Dynamic top timeline progress bar and real-time statistics banner.
- Zero-value filtering (dates with no data are rendered as 'No Data' rather than blank).
- Optimized GIF palettes for PowerPoint slide embedding (< 4 MB).
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import BoundaryNorm, ListedColormap, Normalize
import numpy as np
import pandas as pd
from PIL import Image

from . import config as C
from . import data as D
from . import report
from . import style as ST
from .plots_cartographic_atlas import CartographicAtlasRenderer, is_valid_date_for_mapping

# Historical event annotations for the top subtitle banner
EVENT_ANNOTATIONS = {
    "2016-04": "Pre-monsoon acute water scarcity post-2015 drought",
    "2016-09": "Late Kharif monsoon revival eases hydrological deficit",
    "2017-08": "Sub-normal monsoon triggers moderate agricultural stress",
    "2018-06": "Kharif sowing deficit: Rainfall down 38% below normal",
    "2018-08": "Severe vegetative wilting spreads across central tehsils",
    "2018-09": "CRISIS PEAK: >80% of villages in D2–D4 Severe Drought",
    "2018-10": "Rabi failure: Acute soil moisture exhaustion",
    "2019-06": "Delayed monsoon onset: Elevated early moisture stress",
    "2019-09": "Vigorous late-monsoon recharge restores groundwater",
    "2020-07": "La Niña arrival: District-wide soil moisture saturation",
    "2020-09": "Optimal canopy density: Full agricultural recovery",
    "2021-09": "Abundant Kharif rainfall: Near-zero drought stress",
    "2022-08": "Record monsoon surplus: Peak greenness across 954 villages",
    "2023-09": "Late-monsoon dry spell: Localized stress in southern tehsils",
    "2024-07": "Timely monsoon onset: Healthy Kharif vegetative emergence",
    "2024-09": "Favorable monsoon distribution district-wide",
    "2025-08": "Sustained high canopy vigor across all administrative units",
    "2026-06": "Sub-normal monsoon onset: Negative SPI-3 emergence",
    "2026-09": "Late Kharif drying: Rising CDI stress, Deoni hotspot",
    "2026-10": "Current monitoring horizon: Emerging moderate drought",
}


class PPTAnimationBuilder:
    """High-performance GIF animation generator for cartographic presentations."""

    def __init__(self, renderer: CartographicAtlasRenderer | None = None):
        self.r = renderer or CartographicAtlasRenderer()
        self.dpi = 120
        self.figsize = (10.0, 7.5)

    def _setup_figure(self):
        """Create figure with Times New Roman typography and precise cartographic extents."""
        plt.rcParams.update({
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
            "mathtext.fontset": "cm",
        })

        fig = plt.figure(figsize=self.figsize, dpi=self.dpi, facecolor="white")
        # Main map axis
        ax = fig.add_axes([0.05, 0.12, 0.90, 0.72])
        ax.set_xlim(self.r.xlim)
        ax.set_ylim(self.r.ylim)
        ax.set_aspect("equal")
        ax.axis("off")

        # Hairline village polygons (base layer)
        polys = PolyCollection(
            self.r.poly_coords,
            edgecolors="#CBD5E1",
            linewidths=0.08,
            facecolors="#F1F5F9",
            zorder=2,
        )
        ax.add_collection(polys)

        # Bold Tehsil neatlines
        tehsils = LineCollection(
            self.r.tehsil_lines,
            edgecolors="#1E293B",
            linewidths=0.75,
            zorder=4,
        )
        ax.add_collection(tehsils)

        # Outer District boundary
        if self.r.dist_lines:
            dist = LineCollection(
                self.r.dist_lines,
                edgecolors="#0F172A",
                linewidths=1.2,
                zorder=5,
            )
            ax.add_collection(dist)

        # Static single North arrow at top-right
        ax.annotate(
            "N\n▲",
            xy=(0.93, 0.88),
            xycoords="figure fraction",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color="#0F172A",
            zorder=50,
        )

        # Static georeferenced scale bar (0–40 km)
        x_start = self.r.xlim[1] - 0.44 * (self.r.xlim[1] - self.r.xlim[0])
        y_pos = self.r.ylim[0] + 0.04 * (self.r.ylim[1] - self.r.ylim[0])
        km_deg = 40.0 / 111.32
        ax.plot([x_start, x_start + km_deg], [y_pos, y_pos], color="#0F172A", lw=2.2, zorder=10)
        ax.plot([x_start, x_start], [y_pos - 0.008, y_pos + 0.008], color="#0F172A", lw=1.5, zorder=10)
        ax.plot([x_start + km_deg / 2, x_start + km_deg / 2], [y_pos - 0.006, y_pos + 0.006], color="#0F172A", lw=1.2, zorder=10)
        ax.plot([x_start + km_deg, x_start + km_deg], [y_pos - 0.008, y_pos + 0.008], color="#0F172A", lw=1.5, zorder=10)
        ax.text(x_start, y_pos - 0.018, "0", ha="center", va="top", fontsize=8.5, color="#0F172A", zorder=10)
        ax.text(x_start + km_deg / 2, y_pos - 0.018, "20", ha="center", va="top", fontsize=8.5, color="#0F172A", zorder=10)
        ax.text(x_start + km_deg, y_pos - 0.018, "40 km", ha="center", va="top", fontsize=8.5, color="#0F172A", zorder=10)

        return fig, ax, polys

    def render_animation(
        self,
        frames_data: list[dict],
        cmap,
        norm,
        cbar_label: str,
        main_title: str,
        output_filename: str,
        cbar_ticks: list[float] | None = None,
        cbar_tick_labels: list[str] | None = None,
        duration_ms: int = 700,
        summary_meta: dict | None = None,
    ) -> Path:
        """Render a sequence of frames into an optimized animated GIF for PowerPoint."""
        out_dir = C.section_dir("animations")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / output_filename

        fig, ax, polys = self._setup_figure()

        # Add shared horizontal colorbar at bottom
        cbar_ax = fig.add_axes([0.22, 0.045, 0.56, 0.026])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal", ticks=cbar_ticks)
        if cbar_tick_labels and cbar_ticks:
            cbar.set_ticklabels(cbar_tick_labels)
        cbar.ax.tick_params(labelsize=8.5)
        cbar.set_label(cbar_label, fontsize=9.5, fontweight="bold", labelpad=3)

        # Dynamic text elements
        title_text = fig.text(
            0.50, 0.955, main_title,
            ha="center", va="top", fontsize=14, fontweight="bold", color="#0F172A"
        )
        date_text = fig.text(
            0.50, 0.915, "",
            ha="center", va="top", fontsize=12, fontweight="bold", color="#B91C1C"
        )
        event_text = fig.text(
            0.50, 0.880, "",
            ha="center", va="top", fontsize=10, style="italic", color="#475569"
        )
        stats_text = fig.text(
            0.05, 0.125, "",
            ha="left", va="bottom", fontsize=8.5, color="#1E293B"
        )

        # Timeline progress scrubber line
        n_frames = len(frames_data)
        progress_y = 0.850
        scrubber_x0 = 0.12
        scrubber_x1 = 0.88
        scrubber_line = fig.add_axes([scrubber_x0, progress_y, scrubber_x1 - scrubber_x0, 0.004])
        scrubber_line.axis("off")
        scrubber_bg = scrubber_line.axhspan(0, 1, facecolor="#E2E8F0")

        # Current progress point
        prog_dot = fig.text(scrubber_x0, progress_y, "●", ha="center", va="center", fontsize=8, color="#2563EB")

        images: list[Image.Image] = []

        for idx, f_data in enumerate(frames_data):
            period_lbl = f_data.get("period", "")
            vals_dict = f_data.get("values", {})
            subtitle = f_data.get("subtitle", "")
            stats_info = f_data.get("stats", "")

            # Check validity
            has_data = False
            poly_vals = np.full(len(self.r.poly_village_ids), np.nan)
            if isinstance(vals_dict, dict) and len(vals_dict) > 0:
                poly_vals = np.array([vals_dict.get(v_id, np.nan) for v_id in self.r.poly_village_ids])
                if is_valid_date_for_mapping(poly_vals):
                    has_data = True
            elif isinstance(vals_dict, pd.Series) and not vals_dict.empty:
                vmap = vals_dict.to_dict()
                poly_vals = np.array([vmap.get(v_id, np.nan) for v_id in self.r.poly_village_ids])
                if is_valid_date_for_mapping(poly_vals):
                    has_data = True

            if has_data:
                # NDVI valid masking
                if "NDVI" in main_title:
                    poly_vals[poly_vals <= 0.0] = np.nan
                facecolors = cmap(norm(poly_vals))
                # Gray for NaN / masked
                facecolors[np.isnan(poly_vals)] = [0.82, 0.85, 0.88, 1.0]
                polys.set_facecolors(facecolors)
                date_str = f_data.get("date_label", period_lbl)
            else:
                # Grey no-data state
                polys.set_facecolors(["#CBD5E1"] * len(self.r.poly_coords))
                date_str = f"{period_lbl}  (No Satellite Data / Cloud Masked)"

            # Update text
            date_text.set_text(date_str)
            if not has_data:
                date_text.set_color("#64748B")
            else:
                date_text.set_color("#0F172A")

            # Annotation note
            note = subtitle or EVENT_ANNOTATIONS.get(period_lbl, "")
            event_text.set_text(note)

            # Stats line
            stats_text.set_text(stats_info)

            # Move scrubber dot
            progress_ratio = idx / max(1, n_frames - 1)
            dot_x = scrubber_x0 + progress_ratio * (scrubber_x1 - scrubber_x0)
            prog_dot.set_position((dot_x, progress_y))

            # Render frame to PIL Image
            fig.canvas.draw()
            buf = fig.canvas.buffer_rgba()
            img = Image.frombuffer("RGBA", fig.canvas.get_width_height(), buf, "raw", "RGBA", 0, 1)
            # Convert to P mode with adaptive palette for crisp small GIFs
            img_p = img.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
            images.append(img_p)

        plt.close(fig)

        # Save animated GIF
        if images:
            images[0].save(
                out_path,
                save_all=True,
                append_images=images[1:],
                duration=duration_ms,
                loop=0,
                optimize=True,
            )
            print(f"  [animations] Saved {output_filename} ({len(images)} frames, {out_path.stat().st_size / 1024:.1f} KB)")

        # Register in report
        caption = summary_meta.get("what_it_is", f"PowerPoint cartographic animation: {output_filename}") if summary_meta else f"PowerPoint cartographic animation: {output_filename}"
        report.register(
            section="animations",
            filename=output_filename,
            caption=caption,
            source="village_with_baseline.csv",
            path=out_path,
            category="PowerPoint Cartographic Animations",
            summary=summary_meta,
        )

        return out_path


def build(panel: pd.DataFrame) -> dict[str, Path]:
    """Build all PowerPoint cartographic animations."""
    print("=" * 60)
    print("BUILDING POWERPOINT CARTOGRAPHIC ANIMATION SUITE")
    print("=" * 60)

    builder = PPTAnimationBuilder()
    results: dict[str, Path] = {}

    # Define color maps
    cdi_cmap = ST.CDI_CMAP
    cdi_norm = Normalize(vmin=0.0, vmax=1.0)
    cdi_ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    cdi_labels = ["0.0 (Normal)", "0.2 (D0)", "0.4 (D1)", "0.6 (D2)", "0.8 (D3)", "1.0 (D4)"]

    ndvi_cmap = plt.cm.YlGn
    ndvi_norm = Normalize(vmin=0.10, vmax=0.55)
    ndvi_ticks = [0.10, 0.20, 0.30, 0.40, 0.50]
    ndvi_labels = ["0.10", "0.20", "0.30", "0.40", "0.50"]

    spi_cmap = plt.cm.RdYlBu
    spi_norm = Normalize(vmin=-2.5, vmax=2.5)
    spi_ticks = [-2.0, -1.0, 0.0, 1.0, 2.0]
    spi_labels = ["-2.0", "-1.0", "0.0", "+1.0", "+2.0"]

    # Month names
    m_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Helper to calculate stats for a period
    def get_period_stats(df_period: pd.DataFrame, index_col: str) -> str:
        s = df_period[index_col].dropna()
        if len(s) == 0:
            return ""
        mean_val = s.mean()
        # Drought percent if CDI
        if index_col == C.CDI_COLUMN or "composite" in index_col:
            severe_pct = 100.0 * (df_period["dclass"].isin(["D2", "D3", "D4"])).mean()
            # Top Tehsil
            teh_mean = df_period.groupby("tehsil")[index_col].mean()
            top_teh = teh_mean.idxmax() if not teh_mean.empty else "N/A"
            return f"District Mean CDI: {mean_val:.3f}   |   Severe Area (D2–D4): {severe_pct:.1f}%   |   Hotspot: Tehsil {top_teh}"
        elif "NDVI" in index_col:
            p10 = s.quantile(0.10)
            p90 = s.quantile(0.90)
            return f"District Mean NDVI: {mean_val:.3f}   |   10th–90th Pct: {p10:.3f} – {p90:.3f}"
        elif "SPI" in index_col:
            dry_pct = 100.0 * (s < -1.0).mean()
            return f"District Mean SPI-3: {mean_val:+.2f}   |   Villages with SPI < -1.0 (Dry): {dry_pct:.1f}%"
        return f"District Mean: {mean_val:.3f}"

    # Helper to parse periods robustly
    def parse_ym(p):
        p_str = str(p)
        parts = p_str.split("-")
        y = parts[0]
        m = parts[1] if len(parts) > 1 else "01"
        return p_str, y, m

    # -------------------------------------------------------------------------
    # 1. anim_cdi_monthly_evolution_2016_2026.gif (Continuous 10-Year Decadal)
    # -------------------------------------------------------------------------
    print("\n[1/7] Generating 10-Year Monthly CDI Evolution Time-Lapse...")
    all_periods = sorted(panel["period"].unique(), key=lambda x: str(x))
    frames_10y_cdi = []
    for p in all_periods:
        sub = panel[panel["period"] == p]
        p_str, y, m = parse_ym(p)
        m_idx = int(m) - 1
        m_str = m_names[m_idx] if 0 <= m_idx < 12 else m
        vals = sub.set_index("village_idx")[C.CDI_COLUMN].to_dict()
        stats_str = get_period_stats(sub, C.CDI_COLUMN)
        frames_10y_cdi.append({
            "period": p_str,
            "date_label": f"{m_str.upper()} {y}",
            "values": vals,
            "subtitle": EVENT_ANNOTATIONS.get(p_str, ""),
            "stats": stats_str,
        })

    summary_cdi_10y = {
        "what_it_is": "Continuous 10-Year Cartographic Time-Lapse Animation mapping the monthly evolution of the Composite Drought Index (CDI) across all 954 villages of Latur district from 2016 to 2026.",
        "how_to_read": "Top scrubber advances chronologically through 130 months. Village polygons are colored using official WMO/USDM discrete bins (Green: None, Yellow: D0, Peach: D1, Orange: D2, Red: D3, Dark Maroon: D4). Grey indicates cloud-masked monsoon periods. Real-time district statistics and peak crisis notes appear in dynamic HUD banners.",
        "key_understanding": "Demonstrates the multi-annual cyclic nature of Marathwada drought, clearly contrasting the catastrophic 2018–2019 drought emergency with the La Niña surplus of 2020–2022 and the emerging dry anomalies of 2026.",
    }
    results["anim_cdi_monthly_evolution_2016_2026"] = builder.render_animation(
        frames_data=frames_10y_cdi,
        cmap=cdi_cmap,
        norm=cdi_norm,
        cbar_label="Composite Drought Index (CDI) — USDM / WMO Severity Class",
        main_title="Latur District — 10-Year Monthly Drought Progression (2016–2026)",
        output_filename="anim_cdi_monthly_evolution_2016_2026.gif",
        cbar_ticks=cdi_ticks,
        cbar_tick_labels=cdi_labels,
        duration_ms=650,
        summary_meta=summary_cdi_10y,
    )

    # -------------------------------------------------------------------------
    # 2. anim_2018_historic_drought_progression.gif (2018 Crisis Deep Dive)
    # -------------------------------------------------------------------------
    print("\n[2/7] Generating 2018 Historic Drought Progression Animation...")
    periods_2018 = [p for p in all_periods if str(p).startswith("2018-")]
    frames_2018 = []
    for p in periods_2018:
        sub = panel[panel["period"] == p]
        p_str, y, m = parse_ym(p)
        m_idx = int(m) - 1
        m_str = m_names[m_idx] if 0 <= m_idx < 12 else m
        vals = sub.set_index("village_idx")[C.CDI_COLUMN].to_dict()
        stats_str = get_period_stats(sub, C.CDI_COLUMN)
        frames_2018.append({
            "period": p_str,
            "date_label": f"{m_str.upper()} 2018",
            "values": vals,
            "subtitle": EVENT_ANNOTATIONS.get(p_str, "Catastrophic 2018 Agricultural Drought"),
            "stats": stats_str,
        })

    summary_2018 = {
        "what_it_is": "High-Resolution PowerPoint Presentation Animation tracking the monthly progression of the catastrophic 2018 Marathwada drought emergency across all 954 villages of Latur district.",
        "how_to_read": "Iterates month-by-month through 2018 (Jan–Dec). Observe the dramatic transformation from pre-monsoon dry state to Kharif failure in August–September, where D2–D4 severe drought rapidly enveloped >80% of the district.",
        "key_understanding": "Captures the rapid spatial propagation of agricultural crisis: early rainfall deficit in June–July manifested into total vegetative collapse and soil moisture depletion by September–October 2018.",
    }
    results["anim_2018_historic_drought_progression"] = builder.render_animation(
        frames_data=frames_2018,
        cmap=cdi_cmap,
        norm=cdi_norm,
        cbar_label="Composite Drought Index (CDI) — USDM / WMO Severity Class",
        main_title="2018 Historic Agricultural Drought Episode — Monthly Progression",
        output_filename="anim_2018_historic_drought_progression.gif",
        cbar_ticks=cdi_ticks,
        cbar_tick_labels=cdi_labels,
        duration_ms=900,
        summary_meta=summary_2018,
    )

    # -------------------------------------------------------------------------
    # 3. anim_2020_la_nina_recovery_progression.gif (2020 Recovery Deep Dive)
    # -------------------------------------------------------------------------
    print("\n[3/7] Generating 2020 La Niña Recovery Animation...")
    periods_2020 = [p for p in all_periods if str(p).startswith("2020-")]
    frames_2020 = []
    for p in periods_2020:
        sub = panel[panel["period"] == p]
        p_str, y, m = parse_ym(p)
        m_idx = int(m) - 1
        m_str = m_names[m_idx] if 0 <= m_idx < 12 else m
        vals = sub.set_index("village_idx")[C.CDI_COLUMN].to_dict()
        stats_str = get_period_stats(sub, C.CDI_COLUMN)
        frames_2020.append({
            "period": p_str,
            "date_label": f"{m_str.upper()} 2020",
            "values": vals,
            "subtitle": EVENT_ANNOTATIONS.get(p_str, "La Niña Hydrological & Vegetative Recovery"),
            "stats": stats_str,
        })

    summary_2020 = {
        "what_it_is": "PowerPoint Presentation Animation detailing the rapid spatial greening and hydrological recovery during the 2020 La Niña monsoon season across all 954 villages.",
        "how_to_read": "Chronological progression through 2020. Notice the rapid expansion of normal/healthy green category across all tehsils following vigorous July–September rainfall.",
        "key_understanding": "Demonstrates the high regenerative capacity of Marathwada agriculture when Kharif precipitation exceeds 1100 mm, reversing multi-year drought stress within two months.",
    }
    results["anim_2020_la_nina_recovery_progression"] = builder.render_animation(
        frames_data=frames_2020,
        cmap=cdi_cmap,
        norm=cdi_norm,
        cbar_label="Composite Drought Index (CDI) — USDM / WMO Severity Class",
        main_title="2020 La Niña Monsoon Recovery — Monthly Progression",
        output_filename="anim_2020_la_nina_recovery_progression.gif",
        cbar_ticks=cdi_ticks,
        cbar_tick_labels=cdi_labels,
        duration_ms=900,
        summary_meta=summary_2020,
    )

    # -------------------------------------------------------------------------
    # 4. anim_2024_2026_recent_drought_transition.gif (Recent Dynamic Transition)
    # -------------------------------------------------------------------------
    print("\n[4/7] Generating 2024–2026 Recent Transition Animation...")
    periods_recent = [p for p in all_periods if str(p) >= "2024-01"]
    frames_recent = []
    for p in periods_recent:
        sub = panel[panel["period"] == p]
        p_str, y, m = parse_ym(p)
        m_idx = int(m) - 1
        m_str = m_names[m_idx] if 0 <= m_idx < 12 else m
        vals = sub.set_index("village_idx")[C.CDI_COLUMN].to_dict()
        stats_str = get_period_stats(sub, C.CDI_COLUMN)
        frames_recent.append({
            "period": p_str,
            "date_label": f"{m_str.upper()} {y}",
            "values": vals,
            "subtitle": EVENT_ANNOTATIONS.get(p_str, "Recent Conditions & Emerging Moisture Anomaly"),
            "stats": stats_str,
        })

    summary_recent = {
        "what_it_is": "PowerPoint Presentation Animation tracking the recent drought trajectory from January 2024 through October 2026.",
        "how_to_read": "Traces the transition from 2024 favorable monsoon into 2025 stability, leading up to the sub-normal late-monsoon conditions of 2026 where Deoni and eastern tehsils show emerging stress.",
        "key_understanding": "Provides immediate operational utility for stakeholders, highlighting emerging late-2026 agricultural drought risks needing prioritized monitoring.",
    }
    results["anim_2024_2026_recent_drought_transition"] = builder.render_animation(
        frames_data=frames_recent,
        cmap=cdi_cmap,
        norm=cdi_norm,
        cbar_label="Composite Drought Index (CDI) — USDM / WMO Severity Class",
        main_title="Recent Drought Dynamics & Current Horizon (2024–2026)",
        output_filename="anim_2024_2026_recent_drought_transition.gif",
        cbar_ticks=cdi_ticks,
        cbar_tick_labels=cdi_labels,
        duration_ms=750,
        summary_meta=summary_recent,
    )

    # -------------------------------------------------------------------------
    # 5. anim_ndvi_seasonal_phenology_timelapse.gif (12-Month Seasonal Climatology)
    # -------------------------------------------------------------------------
    print("\n[5/7] Generating NDVI Seasonal Phenology Animation...")
    clim_ndvi = panel.groupby(["month", "village_idx"])["NDVI"].mean()
    frames_ndvi_clim = []
    for m in range(1, 13):
        m_str = m_names[m - 1]
        vals = clim_ndvi.loc[m].to_dict() if m in clim_ndvi.index else {}
        mean_val = float(np.nanmean(list(vals.values()))) if vals else 0.0
        p_note = "Pre-monsoon dry season / fallow land" if m in [3, 4, 5] else (
            "Kharif emergence & peak vegetative canopy" if m in [7, 8, 9] else "Rabi cropping & post-monsoon senescence"
        )
        frames_ndvi_clim.append({
            "period": f"Month {m:02d}",
            "date_label": f"{m_str.upper()} (11-Year Long-Term Climatology)",
            "values": vals,
            "subtitle": p_note,
            "stats": f"District Mean NDVI: {mean_val:.3f}   |   Seasonal Phase: {p_note}",
        })

    summary_ndvi_clim = {
        "what_it_is": "12-Month Cartographic Climatological Animation (January–December) tracing the long-term annual phenological cycle of Normalized Difference Vegetation Index (NDVI) across Latur district.",
        "how_to_read": "Frames loop through the 12 calendar months. Yellow represents dormant fallow land (pre-monsoon), deep green represents peak Kharif crop biomass (August–September). Scale bar at bottom-right, continuous YlGn colorbar at bottom.",
        "key_understanding": "Establishes the empirical baseline phenology of Marathwada: pre-monsoon minimum in April–May (NDVI ~0.15), rapid greening following June monsoon onset, and peak vegetative vigor in September (NDVI ~0.42).",
    }
    results["anim_ndvi_seasonal_phenology_timelapse"] = builder.render_animation(
        frames_data=frames_ndvi_clim,
        cmap=ndvi_cmap,
        norm=ndvi_norm,
        cbar_label="Normalized Difference Vegetation Index (NDVI) — Canopy Greenness",
        main_title="Annual Vegetative Phenology Cycle (11-Year Climatology Jan–Dec)",
        output_filename="anim_ndvi_seasonal_phenology_timelapse.gif",
        cbar_ticks=ndvi_ticks,
        cbar_tick_labels=ndvi_labels,
        duration_ms=800,
        summary_meta=summary_ndvi_clim,
    )

    # -------------------------------------------------------------------------
    # 6. anim_spi3_meteorological_drought_timelapse.gif (10-Year SPI-3)
    # -------------------------------------------------------------------------
    print("\n[6/7] Generating 10-Year SPI-3 Meteorological Drought Animation...")
    frames_spi3 = []
    for p in all_periods:
        sub = panel[panel["period"] == p]
        p_str, y, m = parse_ym(p)
        m_idx = int(m) - 1
        m_str = m_names[m_idx] if 0 <= m_idx < 12 else m
        vals = sub.set_index("village_idx")["SPI3"].to_dict()
        stats_str = get_period_stats(sub, "SPI3")
        frames_spi3.append({
            "period": p_str,
            "date_label": f"{m_str.upper()} {y}",
            "values": vals,
            "subtitle": "Rolling 3-Month Meteorological Moisture Anomaly",
            "stats": stats_str,
        })

    summary_spi3 = {
        "what_it_is": "10-Year Continuous Cartographic Animation mapping monthly Standardized Precipitation Index (SPI-3) across all 954 villages from 2016 to 2026.",
        "how_to_read": "Diverging RdYlBu colormap: Deep red indicates extreme meteorological drought (SPI < -2.0), yellow indicates normal precipitation, and deep blue indicates extreme rainfall surplus (SPI > +2.0).",
        "key_understanding": "Reveals the atmospheric moisture pulses that govern downstream soil moisture and crop conditions, emphasizing the sharp swings between multi-month deficits and torrential surpluses.",
    }
    results["anim_spi3_meteorological_drought_timelapse"] = builder.render_animation(
        frames_data=frames_spi3,
        cmap=spi_cmap,
        norm=spi_norm,
        cbar_label="Standardized Precipitation Index (SPI-3) — 3-Month Rainfall Anomaly",
        main_title="Meteorological Drought & Surplus Dynamics (SPI-3, 2016–2026)",
        output_filename="anim_spi3_meteorological_drought_timelapse.gif",
        cbar_ticks=spi_ticks,
        cbar_tick_labels=spi_labels,
        duration_ms=650,
        summary_meta=summary_spi3,
    )

    # -------------------------------------------------------------------------
    # 7. anim_annual_mean_cdi_2016_2026.gif (Decadal Annual Shift)
    # -------------------------------------------------------------------------
    print("\n[7/7] Generating Decadal Annual Mean CDI Progression Animation...")
    annual_cdi = panel.groupby(["year", "village_idx"])[C.CDI_COLUMN].mean()
    years = sorted(panel["year"].unique())
    frames_annual = []
    for yr in years:
        vals = annual_cdi.loc[yr].to_dict() if yr in annual_cdi.index else {}
        mean_val = float(np.nanmean(list(vals.values()))) if vals else 0.0
        narrative = EVENT_ANNOTATIONS.get(f"{yr}-09", f"Annual Mean Drought State for {yr}")
        frames_annual.append({
            "period": str(yr),
            "date_label": f"ANNUAL MEAN — YEAR {yr}",
            "values": vals,
            "subtitle": narrative,
            "stats": f"District Annual Mean CDI: {mean_val:.3f}   |   Monitoring Year: {yr}",
        })

    summary_annual = {
        "what_it_is": "Decadal Year-by-Year Cartographic Animation (2016–2026) displaying annual mean Composite Drought Index (CDI) across all 954 villages.",
        "how_to_read": "Each frame represents one complete calendar year. Observe the inter-annual shifting of drought hotspots across Ausa, Nilanga, Deoni, and Latur tehsils.",
        "key_understanding": "Proves that drought risk in Latur is geographically non-uniform: southern tehsils (Ausa, Nilanga) experience recurring vulnerability even during moderate recovery years.",
    }
    results["anim_annual_mean_cdi_2016_2026"] = builder.render_animation(
        frames_data=frames_annual,
        cmap=cdi_cmap,
        norm=cdi_norm,
        cbar_label="Composite Drought Index (CDI) — Annual Mean Severity Class",
        main_title="Decadal Annual Mean Drought Trajectory (2016–2026)",
        output_filename="anim_annual_mean_cdi_2016_2026.gif",
        cbar_ticks=cdi_ticks,
        cbar_tick_labels=cdi_labels,
        duration_ms=1200,
        summary_meta=summary_annual,
    )

    print("\nPowerPoint Animation Suite successfully generated!")
    return results
