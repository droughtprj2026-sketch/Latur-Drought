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

    fig, axes = plt.subplots(2, 3, figsize=(15.4, 9.0))
    rows = []
    for ax, (column, label, color) in zip(axes.ravel(), series):
        y = annual[column].dropna()
        if y.empty:
            ax.axis("off")
            continue
        mk = S.mann_kendall(y.to_numpy())
        ss = S.sens_slope(y.to_numpy(), index=y.index.to_numpy())

        ax.plot(y.index, y, marker="o", ms=5, lw=1.9, color=color)
        ax.fill_between(y.index, y.mean(), y, color=color, alpha=0.12)
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
        arrow = {"increasing": "up", "decreasing": "down"}.get(mk["trend"], "flat")
        ax.text(0.02, 0.96, f"Mann-Kendall tau={mk['tau']:+.2f}\n{ST.p_text(mk['p'])}\n{arrow}",
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

    extent = scored.groupby("period")[["is_drought", "is_severe"]].mean() * 100.0
    extent = extent.sort_index()
    smooth = extent.rolling(3, min_periods=1).mean()
    dates = extent.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(14.2, 5.8))
    ax.fill_between(dates, extent["is_drought"], color="#F6BC63", alpha=0.35,
                    label="any drought (D0-D4), monthly")
    ax.plot(dates, smooth["is_drought"], color="#C23B22", lw=2.0, label="3-month running mean")
    ax.plot(dates, extent["is_severe"], color="#6E1423", lw=1.2, ls="--",
            label="severe or worse (D2-D4)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of scored villages (%)")
    ax.set_xlabel("Year")
    ax.grid(alpha=0.35)
    ax.legend(loc="upper left", ncol=3)

    peak_period = extent["is_drought"].idxmax()
    ax.annotate(
        f"peak {extent['is_drought'].max():.0f}% ({peak_period})",
        xy=(peak_period.to_timestamp(), extent["is_drought"].max()),
        xytext=(12, -18), textcoords="offset points", fontsize=8.5,
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
        "Averaged over scored villages only; months that are entirely cloud-covered carry no villages "
        "and are absent from the line.",
    )
    ST.save(
        fig, "temporal", "t4_drought_extent.png",
        "Monthly share of villages in any drought and in severe-or-worse drought, with a 3-month running mean.",
        source="village_with_baseline.csv",
    )
    return extent.reset_index()


def fig_spi12_episodes(panel: pd.DataFrame) -> pd.DataFrame:
    series = panel.groupby("period")["SPI12"].mean().dropna().sort_index()
    if series.empty:
        return pd.DataFrame()
    dates = series.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(14.2, 6.0))
    ax.axhspan(0.0, 0.5, color="#E2DED2", alpha=0.45)
    ax.axhspan(-0.8, 0.0, color="#F2E26B", alpha=0.25)
    ax.axhspan(-1.3, -0.8, color="#F6BC63", alpha=0.35)
    ax.axhspan(-1.6, -1.3, color="#E9822F", alpha=0.40)
    ax.axhspan(-2.0, -1.6, color="#C23B22", alpha=0.35)
    ax.axhspan(series.min() - 0.3, -2.0, color="#6E1423", alpha=0.35)

    ax.plot(dates, series, color="#111111", lw=2.0)
    ax.scatter(dates, series, s=10, color="#111111", zorder=3)
    ax.axhline(0, color="#444444", lw=0.8)
    for level in (-0.8, -1.3, -1.6, -2.0):
        ax.axhline(level, color="#7A7A7A", lw=0.6, ls=":")

    # Drought episodes: contiguous runs below -1.0.
    mask = series <= -1.0
    groups = (mask != mask.shift()).cumsum()
    episodes = []
    for _, block in series[mask].groupby(groups[mask]):
        if len(block) >= 2:
            episodes.append((block.index.min(), block.index.max(), block.min(), len(block)))
            ax.axvspan(block.index.min().to_timestamp(), block.index.max().to_timestamp(),
                       color="#6E1423", alpha=0.10)
            ax.text(block.index.min().to_timestamp(), series.min() - 0.15,
                    f"{block.min():.1f}", fontsize=7.5, color="#6E1423", rotation=90,
                    va="bottom", ha="center")

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylabel("District mean SPI-12")
    ax.set_xlabel("Year")
    ax.set_title(
        "SPI-12 drought episodes and their severity\n"
        "Bands are the McKee / US-DM SPI classes; shaded spans are runs of two months or more below -1.0",
        fontsize=12,
    )
    ax.grid(axis="x", alpha=0.25)

    for label, y in zip(("D0", "D1", "D2", "D3", "D4"), (-0.35, -1.05, -1.45, -1.8, -2.3)):
        ax.text(dates[-1], y, label, fontsize=8, va="center", ha="left", color="#333333",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))

    fig.tight_layout()
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
