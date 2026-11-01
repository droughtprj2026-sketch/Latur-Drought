# -*- coding: utf-8 -*-
"""Section 06 - temporal evolution, drought episodes and trend tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

from . import config as C
from . import data as D
from . import grids as G
from . import stats as S
from . import style as ST


def _period_dates(index: pd.PeriodIndex) -> np.ndarray:
    return index.to_timestamp().to_numpy()


def get_tehsils_west_to_east(panel: pd.DataFrame) -> list[tuple[str, float]]:
    """Return list of (tehsil_name, centroid_longitude) ordered West to East."""
    import json
    if C.TEHSIL_GEOJSON.exists():
        try:
            with open(C.TEHSIL_GEOJSON, "r", encoding="utf-8") as f:
                gj = json.load(f)
            tehsil_lons = {}
            for feat in gj.get("features", []):
                name = feat["properties"].get("TEHSIL", feat["properties"].get("tehsil_name"))
                coords = feat["geometry"]["coordinates"]

                def get_lons(c):
                    if isinstance(c[0], (int, float)):
                        return [c[0]]
                    l = []
                    for sub in c:
                        l.extend(get_lons(sub))
                    return l

                lons = get_lons(coords)
                if name and lons:
                    tehsil_lons[name] = sum(lons) / len(lons)
            present = set(panel["tehsil"].unique())
            res = [(t, tehsil_lons[t]) for t in tehsil_lons if t in present]
            if res:
                return sorted(res, key=lambda x: x[1])
        except Exception:
            pass
    return [(t, float("nan")) for t in sorted(panel["tehsil"].unique())]


def fig_hovmoller(panel: pd.DataFrame) -> None:
    ordered_tehsils = get_tehsils_west_to_east(panel)
    tehsil_names = [t[0] for t in ordered_tehsils]
    tehsil_labels = [f"{t[0]} ({t[1]:.2f}°E)" if np.isfinite(t[1]) else t[0] for t in ordered_tehsils]

    study_periods = D.study_periods(panel)
    dates = [p.to_timestamp() for p in study_periods]
    next_date = study_periods[-1].to_timestamp() + pd.DateOffset(months=1)
    date_edges = dates + [next_date]
    y_edges = np.arange(len(tehsil_names) + 1)

    # 1. CDI matrix: detect valid observed periods
    cdi_period_valid = panel.groupby("period")[C.CDI_COLUMN].apply(
        lambda s: s.notna().any() and not (s == 0.0).all() and (s == 0.0).mean() < 0.90
    )
    piv_cdi = panel.groupby(["tehsil", "period"])[C.CDI_COLUMN].mean().unstack(level="period")
    piv_cdi = piv_cdi.reindex(index=tehsil_names, columns=study_periods)
    for col in piv_cdi.columns:
        if not cdi_period_valid.get(col, False):
            piv_cdi[col] = np.nan
    matrix_cdi = piv_cdi.to_numpy()

    # 2. SPI-3 matrix
    piv_spi = panel.groupby(["tehsil", "period"])["SPI3"].mean().unstack(level="period")
    piv_spi = piv_spi.reindex(index=tehsil_names, columns=study_periods)
    matrix_spi = piv_spi.to_numpy()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15.5, 9.8), sharex=True, layout="constrained")
    for ax in (ax1, ax2):
        ax.set_facecolor("#F1F5F9")

    # Plot CDI Hovmoller
    pm1 = ax1.pcolormesh(date_edges, y_edges, matrix_cdi, cmap=ST.CDI_CMAP, vmin=0.0, vmax=0.75, shading="flat")
    ax1.set_yticks(np.arange(len(tehsil_names)) + 0.5)
    ax1.set_yticklabels(tehsil_labels, fontsize=9.5)
    ax1.set_ylabel("← West       Longitudinal Transect       East →\nTehsil", fontsize=10.5, weight="bold")
    ax1.set_title("A. Composite Drought Index (CDI) Hovmöller (0.0 = Normal, >0.50 = Extreme/Exceptional Drought)", fontsize=11.5, weight="bold")

    cbar1 = fig.colorbar(pm1, ax=ax1, shrink=0.75, pad=0.015, aspect=20)
    cbar1.set_label("Composite Drought Index (CDI)", fontsize=9.5)
    cbar1.set_ticks([0.0, 0.20, 0.30, 0.40, 0.50, 0.65])
    cbar1.set_ticklabels(["Normal", "D0", "D1", "D2", "D3", "D4"])

    # Plot SPI-3 Hovmoller
    import matplotlib.cm as mcm
    spi_cmap = mcm.get_cmap("RdBu")
    pm2 = ax2.pcolormesh(date_edges, y_edges, matrix_spi, cmap=spi_cmap, vmin=-2.5, vmax=2.5, shading="flat")
    ax2.set_yticks(np.arange(len(tehsil_names)) + 0.5)
    ax2.set_yticklabels(tehsil_labels, fontsize=9.5)
    ax2.set_ylabel("← West       Longitudinal Transect       East →\nTehsil", fontsize=10.5, weight="bold")
    ax2.set_title("B. Standardized Precipitation Index (SPI-3) Hovmöller (Diverging Meteorological Moisture)", fontsize=11.5, weight="bold")

    cbar2 = fig.colorbar(pm2, ax=ax2, shrink=0.75, pad=0.015, aspect=20)
    cbar2.set_label("SPI-3 (Precipitation Anomaly)", fontsize=9.5)

    # Highlight major historical episodes across both panels
    episodes = [
        (pd.Timestamp("2018-06-01"), pd.Timestamp("2019-06-01"), "2018–19 Severe Drought", "#DC2626"),
        (pd.Timestamp("2020-06-01"), pd.Timestamp("2021-10-01"), "2020–21 Wet Surplus", "#2563EB"),
        (pd.Timestamp("2023-08-01"), pd.Timestamp("2024-04-01"), "2023–24 Late Deficit", "#D97706"),
    ]
    for start, end, label, color in episodes:
        for ax in (ax1, ax2):
            ax.axvspan(start, end, color=color, alpha=0.07, zorder=3)
            ax.axvline(start, color=color, ls="--", lw=0.9, alpha=0.6, zorder=3)
            ax.axvline(end, color=color, ls="--", lw=0.9, alpha=0.6, zorder=3)
        ax1.text(
            start + (end - start) / 2, len(tehsil_names) + 0.15, label,
            ha="center", va="bottom", fontsize=8.5, color=color, weight="bold", fontfamily="serif"
        )

    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
    ax2.set_xlabel("Observation Month (2016–2026 Continuous Record)", fontsize=11, weight="bold")

    fig.suptitle(
        "Spatio-Temporal Hovmöller Diagram: West-to-East Drought Transect Across Latur (2016–2026)\n"
        "Tracking meteorological deficit (SPI-3) and composite drought impact (CDI) propagation along longitude (76.50°E → 77.16°E)",
        fontsize=13.0, weight="bold",
    )
    ST.figure_note(
        fig,
        "Subtle grey cells in the CDI panel represent cloud-masked or unobserved monsoon months, never zero drought. "
        "Tehsils are strictly ordered from West to East based on geographic polygon centroids.",
    )
    ST.save(
        fig, "temporal", "t1_hovmoller_cdi_spi.png",
        "True spatio-temporal Hovmöller diagram showing West-to-East drought propagation across 10 tehsils and 129 continuous months.",
        source="village_with_baseline.csv",
    )


def fig_annual_series(panel: pd.DataFrame) -> pd.DataFrame:
    annual = panel.groupby("year").agg(
        cdi=(C.CDI_COLUMN, "mean"),
        spI3=("SPI3", "mean"),
        spi12=("SPI12", "mean"),
        rain=("Rain_mm", "mean"),
        ndvi=("NDVI", "mean"),
        nsmi=("NSMI", "mean"),
    )
    scored = panel[panel["dclass"].isin(C.DROUGHT_CODES)]
    annual["drought_share"] = (
        scored.groupby("year").size() / panel.groupby("year").size() * 100.0
    )
    annual = annual.round(4)

    series = [
        ("cdi", "Annual mean CDI", "#6E1423"),
        ("drought_share", "Village-months in drought (%)", "#C23B22"),
        ("spI3", "Annual mean SPI-3", "#1F6FB2"),
        ("spi12", "Annual mean SPI-12", "#0B3C5D"),
        ("rain", "Annual mean monthly rainfall (mm)", "#2E86AB"),
        ("ndvi", "Annual mean NDVI", "#2E7D32"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(15.4, 9.2), layout="constrained")
    rows = []
    for ax, (column, label, color) in zip(axes.ravel(), series):
        y = annual[column].dropna()
        if y.empty:
            ax.axis("off")
            continue
        mk = S.mann_kendall(y.to_numpy())
        ss = S.sens_slope(y.to_numpy(), index=y.index.to_numpy())

        ax.plot(y.index, y, marker="o", ms=5, lw=1.9, color=color)
        ax.fill_between(y.index, y.mean(), y, color=color, alpha=0.10)
        ax.axhline(y.mean(), color="#666666", ls=":", lw=1.0)
        if np.isfinite(ss["slope"]):
            xs = np.array([y.index.min(), y.index.max()], dtype=float)
            ax.plot(xs, ss["intercept"] + ss["slope"] * xs, color="#111111", lw=1.4, ls="--",
                    label=f"Sen slope {ss['slope']:+.4f}/yr")
            ax.legend(loc="best", fontsize=7.5)

        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Year")
        ax.set_xticks(sorted(y.index))
        ax.tick_params(axis="x", rotation=90, labelsize=7.5)
        ax.grid(alpha=0.35)
        ax.text(0.02, 0.96, f"Mann-Kendall tau={mk['tau']:+.2f}\n{ST.p_text(mk['p'])}\n{mk['trend']}",
                transform=ax.transAxes, va="top", fontsize=8.0, fontfamily="serif")

        rows.append(S.trend_table(y, label))

    fig.suptitle(
        "Annual evolution of the drought signal with non-parametric trend tests\n"
        "Mann-Kendall for monotonic trend, Sen's slope for a robust rate of change",
        fontsize=13,
    )
    ST.save(
        fig, "temporal", "t2_annual_series_trends.png",
        "Annual series of CDI, drought share, SPI-3, SPI-12, rainfall and NDVI with Mann-Kendall and Sen's slope.",
        source="village_with_baseline.csv",
    )
    return pd.DataFrame(rows).assign(scope="district")


def fig_class_composition(panel: pd.DataFrame) -> None:
    scored = panel[panel["dclass"].isin(C.CLASS_ORDER)]
    if scored.empty:
        return
    monthly = (
        pd.crosstab(scored["period"], scored["dclass"], normalize="index")
        .reindex(columns=C.CLASS_ORDER)
        .fillna(0.0)
        * 100.0
    )
    annual = (
        pd.crosstab(scored["year"], scored["dclass"], normalize="index")
        .reindex(columns=C.CLASS_ORDER)
        .fillna(0.0)
        * 100.0
    )

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(14.2, 9.6),
                                  gridspec_kw={"height_ratios": [1, 1]})
    months = monthly.index.to_timestamp()
    ax.stackplot(months, [monthly[c].to_numpy() for c in C.CLASS_ORDER],
                 labels=[C.D_CLASS_LABELS[c] for c in C.CLASS_ORDER],
                 colors=[C.DROUGHT_COLORS[c] for c in C.CLASS_ORDER], alpha=0.92,
                 edgecolor="white", linewidth=0.25)
    ax.set_ylim(0, 100)
    ax.set_xlim(months.min(), months.max())
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylabel("Share of scored village-months (%)")
    ax.set_title("A. Monthly class composition across the full record", fontsize=11)
    ax.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    bottom = np.zeros(len(annual))
    for code in C.CLASS_ORDER:
        values = annual[code].to_numpy()
        ax2.bar(annual.index.astype(str), values, bottom=bottom,
                color=C.DROUGHT_COLORS[code], edgecolor="white", linewidth=0.4,
                label=C.D_CLASS_LABELS[code])
        bottom += values
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("Share (%)")
    ax2.set_xlabel("Year")
    ax2.set_title("B. Annual class composition, side by side", fontsize=11)
    ax2.tick_params(axis="x", rotation=45)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle(
        "Composition of drought severity over time\n"
        "The worst years are visible as a shift of mass from pale to dark bands",
        fontsize=13,
    )
    ST.save(
        fig, "temporal", "t3_class_composition.png",
        "Stacked area and stacked bars of the monthly and annual drought-class composition.",
        source="village_with_baseline.csv",
    )


def fig_drought_extent(panel: pd.DataFrame) -> pd.DataFrame:
    scored = panel[panel["dclass"].isin(C.CLASS_ORDER)].copy()
    scored["is_drought"] = scored["dclass"].isin(C.DROUGHT_CODES)
    scored["is_severe"] = scored["dclass"].isin(["D2", "D3", "D4"])

    extent = (scored.groupby("period")[["is_drought", "is_severe"]].mean() * 100.0).sort_index()
    # Reindex onto the full monthly grid so months with no observation break the
    # line instead of being bridged by a straight segment.
    extent = extent.reindex(D.study_periods(panel))
    smooth = extent["is_drought"].rolling(3, min_periods=2).mean()

    dates = extent.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(14.4, 6.0), layout="constrained")
    ax.fill_between(dates, smooth.to_numpy(), color="#F6BC63", alpha=0.35,
                    label="any drought (D0-D4), 3-month running mean")
    ax.plot(dates, smooth.to_numpy(), color="#C23B22", lw=2.1,
            label="3-month running mean")
    ax.plot(dates, extent["is_drought"].to_numpy(), color="#E09F3E", lw=0.9, alpha=0.85,
            label="monthly extent")
    ax.plot(dates, extent["is_severe"].to_numpy(), color="#6E1423", lw=1.1, ls="--",
            label="severe or worse (D2-D4)")

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of scored villages (%)")
    ax.set_xlabel("Year")
    ax.grid(alpha=0.35)
    ax.legend(loc="upper left", ncol=2, fontsize=8)

    peak_period = extent["is_drought"].idxmax()
    ax.annotate(
        f"peak {extent['is_drought'].max():.0f}% ({peak_period})",
        xy=(peak_period.to_timestamp(), extent["is_drought"].max()),
        xytext=(14, -26), textcoords="offset points", fontsize=8.5, fontfamily="serif", weight="bold",
        arrowprops=dict(arrowstyle="->", color="#C23B22", lw=0.9),
    )

    fig.suptitle(
        "Drought extent through time: the share of villages actually affected\n"
        "Extent is a population measure, so it is not inflated by a single extreme village",
        fontsize=12.5,
    )
    ST.figure_note(
        fig,
        "Averaged over scored villages only. Months with no observation are absent from the line, "
        "so a break is a data gap and not a return to normal conditions.",
    )
    ST.save(
        fig, "temporal", "t4_drought_extent.png",
        "Monthly share of villages in any drought and in severe-or-worse drought, with a 3-month running mean.",
        source="village_with_baseline.csv",
    )
    return extent.reset_index()


def fig_spi12_episodes(panel: pd.DataFrame) -> pd.DataFrame:
    series = panel.groupby("period")["SPI12"].mean().sort_index()
    if series.empty:
        return pd.DataFrame()
    series = series.reindex(D.study_periods(panel))
    dates = series.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(14.6, 6.2), layout="constrained")
    ax.axhspan(0.0, 1.0, color="#E2DED2", alpha=0.45)
    ax.axhspan(-0.8, 0.0, color="#F2E26B", alpha=0.28)
    ax.axhspan(-1.3, -0.8, color="#F6BC63", alpha=0.35)
    ax.axhspan(-1.6, -1.3, color="#E9822F", alpha=0.38)
    ax.axhspan(-2.0, -1.6, color="#C23B22", alpha=0.33)
    ax.axhspan(float(np.nanmin(series)) - 0.4, -2.0, color="#6E1423", alpha=0.30)

    ax.plot(dates, series.to_numpy(), color="#111111", lw=1.9)
    ax.scatter(dates, series.to_numpy(), s=12, color="#111111", zorder=3)
    ax.axhline(0, color="#444444", lw=0.8)
    for level in (-0.8, -1.3, -1.6, -2.0):
        ax.axhline(level, color="#6E6E6E", lw=0.6, ls=":")

    # Episodes: contiguous runs at or below -1.0, using only observed months.
    observed = series.dropna()
    mask = observed <= -1.0
    groups = (mask != mask.shift()).cumsum()
    episodes = []
    top = float(np.nanmax(series)) + 0.35
    for _, block in observed[mask].groupby(groups[mask]):
        if len(block) < 2:
            continue
        start, end = block.index.min(), block.index.max()
        episodes.append((start, end, float(block.min()), len(block)))
        ax.axvspan(start.to_timestamp(), end.to_timestamp(), color="#6E1423", alpha=0.09,
                   linewidth=0, zorder=0)
        for edge in (start, end):
            ax.axvline(edge.to_timestamp(), color="#6E1423", lw=0.8, alpha=0.55, ls="-")
        ax.text(
            start.to_timestamp() + (end.to_timestamp() - start.to_timestamp()) / 2, top,
            f"{len(block)} mo\nmin {block.min():.1f}",
            ha="center", va="top", fontsize=8.0, color="#4A0E14", fontfamily="serif", weight="bold"
        )

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(float(np.nanmin(series)) - 0.4, top + 0.45)
    ax.set_ylabel("District mean SPI-12")
    ax.set_xlabel("Year")
    ax.set_title(
        "SPI-12 drought episodes and their severity\n"
        "Bands are the McKee / US-DM SPI classes; boxes mark runs of two months or more below -1.0",
        fontsize=12,
    )
    ax.grid(axis="x", alpha=0.25)

    for code, y in (("D0", -0.35), ("D1", -1.05), ("D2", -1.45), ("D3", -1.8), ("D4", -2.3)):
        ax.annotate(
            code, xy=(1.0, y), xycoords=("axes fraction", "data"), xytext=(5, 0),
            textcoords="offset points", fontsize=8, va="center", ha="left", color="#333333",
            annotation_clip=False,
        )

    ST.figure_note(
        fig,
        "D9-style breaks in the black line are months with no SPI-12 observation, not a return to normal.",
    )
    ST.save(
        fig, "temporal", "t5_spi12_episodes.png",
        "District mean SPI-12 with SPI class bands and detected multi-month drought episodes.",
        source="village_with_baseline.csv",
    )
    return pd.DataFrame(episodes, columns=["episode_start", "episode_end", "min_spi12", "months"])


def fig_tehsil_trends(panel: pd.DataFrame) -> pd.DataFrame:
    tehsils = sorted(panel["tehsil"].unique())
    annual = (
        panel.dropna(subset=[C.CDI_COLUMN])
        .pivot_table(index="year", columns="tehsil", values=C.CDI_COLUMN, aggfunc="mean")
        .sort_index()
    )
    if annual.empty:
        return pd.DataFrame()

    ncols = 5
    nrows = int(np.ceil(len(tehsils) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.9 * ncols, 3.3 * nrows), sharex=True, sharey=True)
    axes = np.atleast_1d(axes).ravel()
    rows = []

    y_max = float(np.nanmax(annual.to_numpy())) * 1.15
    for ax, tehsil in zip(axes, tehsils):
        if tehsil not in annual.columns:
            ax.axis("off")
            continue
        y = annual[tehsil].dropna()
        mk = S.mann_kendall(y.to_numpy())
        ss = S.sens_slope(y.to_numpy(), index=y.index.to_numpy())
        color = ST.CDI_CMAP(min(0.95, 0.15 + y.mean()))
        ax.plot(y.index, y, marker="o", ms=4, lw=1.7, color=color)
        ax.fill_between(y.index, y.mean(), y, color=color, alpha=0.15)
        if np.isfinite(ss["slope"]):
            xs = np.array([y.index.min(), y.index.max()], dtype=float)
            ax.plot(xs, ss["intercept"] + ss["slope"] * xs, color="#111111", lw=1.2, ls="--")
        ax.set_title(tehsil, fontsize=9.5)
        ax.set_ylim(0, y_max)
        ax.grid(alpha=0.3)
        ax.text(0.04, 0.94,
                f"slope {ss['slope']:+.4f}/yr\n{ST.p_text(mk['p'])}",
                transform=ax.transAxes, va="top", fontsize=7.5, fontfamily="serif")
        rows.append({**S.trend_table(y, C.COL[C.CDI_COLUMN].short), "scope": tehsil})

    for ax in axes[len(tehsils):]:
        ax.axis("off")

    fig.suptitle(
        "Annual mean CDI per tehsil with Sen's slope and Mann-Kendall test\n"
        "Shared vertical scale, so the height of a tehsil is comparable across panels",
        fontsize=13,
    )
    ST.figure_note(fig, "A dashed line with a positive slope means the tehsil is drying. "
                        "Small n (eleven years) limits power, so p-values are indicative.", y=0.0)
    ST.save(
        fig, "temporal", "t6_tehsil_trends.png",
        "Small-multiple annual CDI series for every tehsil with Sen's slope and Mann-Kendall p-value.",
        source="village_with_baseline.csv",
    )
    return pd.DataFrame(rows)


def fig_drought_area_percentage(panel: pd.DataFrame) -> pd.DataFrame:
    """10-Year Drought Area Percentage (DAP) Evolution (2016-2026)."""
    # Exclude unobserved/all-zero periods for CDI
    cdi_valid = panel.groupby("period")[C.CDI_COLUMN].apply(
        lambda s: s.notna().any() and not (s == 0.0).all() and (s == 0.0).mean() < 0.90
    )
    valid_periods = cdi_valid[cdi_valid].index

    scored = panel[panel["period"].isin(valid_periods) & panel["dclass"].isin(C.CLASS_ORDER)].copy()
    if scored.empty:
        return pd.DataFrame()

    monthly = (
        pd.crosstab(scored["period"], scored["dclass"], normalize="index")
        .reindex(columns=C.CLASS_ORDER)
        .fillna(0.0)
        * 100.0
    )
    # Reindex to full study periods to preserve gaps
    full_periods = D.study_periods(panel)
    monthly = monthly.reindex(full_periods)

    dates = [p.to_timestamp() for p in monthly.index]

    fig, (ax_stack, ax_severe) = plt.subplots(2, 1, figsize=(15.2, 9.8), sharex=True,
                                             gridspec_kw={"height_ratios": [2.2, 1.0]},
                                             layout="constrained")

    # Palette matching USDM / WMO standards
    colors = [C.DROUGHT_COLORS.get(c, "#E2E8F0") for c in C.CLASS_ORDER]
    labels = [C.D_CLASS_LABELS.get(c, c) for c in C.CLASS_ORDER]

    # Stackplot
    stack_data = [monthly[c].to_numpy() for c in C.CLASS_ORDER]
    ax_stack.stackplot(dates, stack_data, labels=labels, colors=colors, alpha=0.92,
                       edgecolor="white", linewidth=0.3)
    ax_stack.set_ylim(0, 100)
    ax_stack.set_ylabel("Share of District Villages (% Area)", fontsize=11, weight="bold")
    ax_stack.set_title("A. 10-Year Drought Area Percentage (DAP) Stacked Composition", fontsize=11.5, weight="bold")
    ax_stack.legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=6, fontsize=9.0, frameon=True)
    ax_stack.grid(axis="y", linestyle=":", alpha=0.5)

    # Severe Drought Line (D2 + D3 + D4)
    severe_pct = monthly[["D2", "D3", "D4"]].sum(axis=1)
    ax_severe.fill_between(dates, severe_pct.to_numpy(), color="#DC2626", alpha=0.25, label="Severe-to-Exceptional (D2–D4)")
    ax_severe.plot(dates, severe_pct.to_numpy(), color="#991B1B", lw=2.0)
    ax_severe.scatter(dates, severe_pct.to_numpy(), s=14, color="#991B1B", zorder=3)
    ax_severe.set_ylim(0, 100)
    ax_severe.set_ylabel("Severe (D2–D4) %", fontsize=10.5, weight="bold")
    ax_severe.set_title("B. High-Impact Drought Area (D2–D4 Cumulative)", fontsize=11.0, weight="bold")
    ax_severe.grid(axis="y", linestyle=":", alpha=0.5)

    # Highlight peak severe drought
    peak_date = severe_pct.idxmax()
    peak_val = severe_pct.max()
    if np.isfinite(peak_val) and peak_val > 10.0:
        ax_severe.annotate(
            f"Peak: {peak_val:.1f}% ({peak_date})",
            xy=(peak_date.to_timestamp(), peak_val),
            xytext=(15, -20), textcoords="offset points", fontsize=8.5, weight="bold", fontfamily="serif",
            arrowprops=dict(arrowstyle="->", color="#991B1B", lw=1.0)
        )

    ax_severe.xaxis.set_major_locator(mdates.YearLocator())
    ax_severe.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_severe.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
    ax_severe.set_xlabel("Year", fontsize=11, weight="bold")

    fig.suptitle(
        "10-Year Drought Area Percentage (DAP) Evolution across Latur District (2016–2026)\n"
        "Categorical USDM/WMO severity hierarchy aggregated over 954 villages",
        fontsize=13.0, weight="bold"
    )
    ST.figure_note(
        fig,
        "Evaluated over observed village-months. Breaks in the stack represent cloud-masked monsoon periods. "
        "D2–D4 indicates villages requiring immediate agricultural drought relief interventions.",
    )
    ST.save(
        fig, "temporal", "t7_drought_area_percentage_stacked.png",
        "10-Year Drought Area Percentage (DAP) stacked area chart showing monthly evolution of USDM drought classes D0-D4.",
        source="village_with_baseline.csv",
    )
    return monthly.reset_index()


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    fig_hovmoller(panel)
    annual = fig_annual_series(panel)
    fig_class_composition(panel)
    extent = fig_drought_extent(panel)
    episodes = fig_spi12_episodes(panel)
    trends = fig_tehsil_trends(panel)
    dap = fig_drought_area_percentage(panel)
    return {
        "annual_trends_district": annual,
        "drought_extent": extent,
        "spi12_episodes": episodes,
        "annual_trends_tehsil": trends,
        "drought_area_percentage": dap,
    }
