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


def fig_hovmoller(panel: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14.0, 11.5), sharex=True)
    panels = [(C.CDI_COLUMN, "A. Composite Drought Index (higher = more stressed)"),
              ("SPI3", "B. SPI-3 (negative = rainfall deficit)")]

    for ax, (column, title) in zip(axes, panels):
        grid = G.month_year_matrix(panel, column)
        norm = G.nice_norm(column, panel[column].to_numpy(dtype=float))
        G.draw_month_year(
            ax, grid, cmap=ST.cmap_for(column), norm=norm,
            annot=True, fmt="{:.2f}", annot_size=5.8, cbar=True,
            cbar_kws={"label": C.COL[column].label, "shrink": 0.7},
        )
        ax.set_title(title, fontsize=11)
        ax.set_ylabel("Calendar month")

    axes[-1].set_xlabel("Year")
    fig.suptitle(
        "Hovmoller diagram of drought evolution, month by month for the whole record\n"
        "Grey cells are months without an observation, so a blank band is a data gap, never zero drought",
        fontsize=13,
    )
    ST.save(
        fig, "temporal", "t1_hovmoller_cdi_spi.png",
        "Month x year Hovmoller heatmaps of the CDI and SPI-3.",
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
                transform=ax.transAxes, va="top", fontsize=7.4, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#CCCCCC", lw=0.5, alpha=0.92))

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
        xytext=(14, -26), textcoords="offset points", fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#C23B22", lw=0.8),
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
            ha="center", va="top", fontsize=7.4, color="#4A0E14", family="monospace",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#6E1423", lw=0.6, alpha=0.9),
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
                transform=ax.transAxes, va="top", fontsize=7.0, family="monospace",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#CCCCCC", lw=0.5, alpha=0.9))
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


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    fig_hovmoller(panel)
    annual = fig_annual_series(panel)
    fig_class_composition(panel)
    extent = fig_drought_extent(panel)
    episodes = fig_spi12_episodes(panel)
    trends = fig_tehsil_trends(panel)
    return {
        "annual_trends_district": annual,
        "drought_extent": extent,
        "spi12_episodes": episodes,
        "annual_trends_tehsil": trends,
    }
