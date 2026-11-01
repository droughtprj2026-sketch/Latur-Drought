# -*- coding: utf-8 -*-
"""Section 01 - image availability and sampling completeness."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from . import config as C
from . import data as D
from . import grids as G
from . import style as ST

SOURCES: dict[str, str] = {
    "Sentinel-2 optical (NDVI)": "NDVI",
    "Sentinel-1 soil moisture (NSMI)": "NSMI",
    "CHIRPS rainfall": "Rain_mm",
}
SOURCE_COLORS = {
    "Sentinel-2 optical (NDVI)": C.GROUP_COLORS["vegetation"],
    "Sentinel-1 soil moisture (NSMI)": C.GROUP_COLORS["soil"],
    "CHIRPS rainfall": C.GROUP_COLORS["meteorological"],
}


def fig_tehsil_year_availability(panel: pd.DataFrame) -> None:
    grids = {label: D.availability_matrix(panel, column) for label, column in SOURCES.items()}
    grids = {k: v for k, v in grids.items() if not v.empty}
    if not grids:
        return

    # One shared tehsil order for all three panels, ranked by the first source.
    first = next(iter(grids.values()))
    order = first.mean(axis=1).sort_values(ascending=False).index
    grids = {k: v.reindex(order) for k, v in grids.items()}

    fig, axes = plt.subplots(1, len(grids), figsize=(16.5, 6.0), layout="constrained")
    axes = np.atleast_1d(axes)
    for i, (ax, (label, grid)) in enumerate(zip(axes, grids.items())):
        sns.heatmap(
            grid, ax=ax, cmap=ST.COVERAGE_CMAP, vmin=0, vmax=100,
            annot=True, fmt=".0f", annot_kws={"size": 7},
            linewidths=0.5, linecolor="white",
            cbar=(i == len(grids) - 1),
            cbar_kws={"label": "coverage (%)", "shrink": 0.8} if i == len(grids) - 1 else None,
        )
        ax.set_title(label, fontsize=10, pad=8)
        ax.set_xlabel("Year")
        ax.set_ylabel("Tehsil (ranked by coverage)" if i == 0 else "")
        ax.tick_params(axis="x", rotation=90, labelsize=8)
        ax.tick_params(axis="y", rotation=0, labelsize=8)
        for text in ax.texts:
            try:
                value = float(text.get_text())
            except (TypeError, ValueError):
                continue
            text.set_color("white" if value >= 62 else "#1A1A1A")
            text.set_fontweight("bold" if value >= 90 else "normal")

    fig.suptitle(
        "Source availability by tehsil and year\n"
        "Coverage = observed village-months with a valid value / (villages x months in the study window)",
        fontsize=13,
    )
    ST.figure_note(
        fig,
        "100 means every village was observed in every month of that year. A value of 33 in 2018 is the "
        "shared gap in all three sources, so it is a pipeline gap rather than cloud cover.",
    )
    ST.save(
        fig, "availability", "a1_tehsil_year_availability.png",
        "Sentinel-2, Sentinel-1 and CHIRPS coverage (%) for every tehsil and year.",
        source="village_with_baseline.csv",
    )


def fig_month_year_availability(panel: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(13.5, 12.4), sharex=True)
    for ax, (label, column) in zip(axes, SOURCES.items()):
        grid = D.availability_by_month(panel, column)
        if grid.empty:
            ax.axis("off")
            continue
        G.draw_month_year(
            ax, grid, cmap=ST.COVERAGE_CMAP,
            norm=plt.Normalize(vmin=0, vmax=100),
            annot=True, fmt="{:.0f}", annot_size=6.2, cbar=(ax is axes[-1]),
            cbar_kws={"label": "village coverage (%)", "shrink": 0.7},
        )
        ax.set_title(f"{label}", fontsize=10.5)
        ax.set_ylabel("Calendar month")

    axes[-1].set_xlabel("Year")
    fig.suptitle(
        "Monthly acquisition record across the whole extent\n"
        "Share of all villages with a valid observation in each month (grey = month absent from the panel)",
        fontsize=13,
    )
    ST.save(
        fig, "availability", "a2_month_year_availability.png",
        "Month x year availability grid for all three sources; grey cells are months with no observation at all.",
        source="village_with_baseline.csv",
    )


def fig_tehsil_availability_bars(panel: pd.DataFrame) -> None:
    summary = D.source_availability_summary(panel, SOURCES)
    if summary.empty:
        return
    per_tehsil = {}
    for label, column in SOURCES.items():
        table = D.availability_table(panel, column)
        if table.empty:
            continue
        per_tehsil[label] = table.groupby("tehsil")["pct"].mean()
    frame = pd.DataFrame(per_tehsil)
    frame = frame.sort_values(frame.columns[0], ascending=True)

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(14.5, 6.2), gridspec_kw={"width_ratios": [1.55, 1]}
    )
    y = np.arange(len(frame))
    height = 0.26
    for i, label in enumerate(frame.columns):
        ax.barh(
            y + (i - 1) * height, frame[label], height=height, label=label,
            color=SOURCE_COLORS.get(label, "#777777"), edgecolor="white", linewidth=0.5,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(frame.index)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Mean coverage over the study period (%)")
    ax.set_title("Sampling completeness by tehsil")
    ax.grid(axis="x", alpha=0.5)
    ax.axvline(100, color="#999999", lw=0.8, ls=":")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=8)

    bars = ax2.barh(
        np.arange(len(summary)), summary["coverage_pct"], height=0.55,
        color=[SOURCE_COLORS.get(s, "#777777") for s in summary["source"]],
        edgecolor="white",
    )
    ax2.set_yticks(np.arange(len(summary)))
    ax2.set_yticklabels(summary["source"])
    ax2.set_xlim(0, 105)
    ax2.set_xlabel("District-wide coverage (%)")
    ax2.set_title("Whole-extent coverage")
    ax2.grid(axis="x", alpha=0.5)
    for bar, value, lo, hi in zip(bars, summary["coverage_pct"], summary["tehsil_min_pct"],
                                  summary["tehsil_max_pct"]):
        ax2.text(value + 1.2, bar.get_y() + bar.get_height() / 2,
                 f"{value:.1f}%  ({lo:.0f}-{hi:.0f})", va="center", fontsize=8)

    fig.suptitle(
        "Image availability across every tehsil, and the spread between the best and worst observed tehsil",
        fontsize=13,
    )
    ST.save(
        fig, "availability", "a3_tehsil_availability_ranking.png",
        "Tehsil-level coverage bars for each source, plus the district-wide figure with the min-max tehsil range.",
        source="village_with_baseline.csv",
    )


def fig_annual_availability_trend(panel: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.4, 5.6), layout="constrained")

    # Left: how many calendar months of each year exist in the panel at all.
    observed = panel.groupby("year")["period"].nunique()
    expected = D.months_per_year(panel)
    axes[0].bar(observed.index.astype(str), observed.to_numpy(), color="#3C7FB3",
                edgecolor="#1B3A52", linewidth=0.6, label="months in the panel")
    axes[0].plot(expected.index.astype(str), expected.to_numpy(), color="#C23B22", marker="o",
                 ms=5, lw=1.8, label="months in the study window")
    for x, (year, value) in enumerate(observed.items()):
        gap = int(expected.get(year, 0)) - int(value)
        axes[0].text(x, value + 0.25, f"{value}", ha="center", va="bottom", fontsize=8)
        if gap > 0:
            axes[0].text(x, value - 1.1, f"-{gap}", ha="center", va="top", fontsize=7.5,
                         color="#C23B22", weight="bold")
    axes[0].set_title("Months present in the panel, against the study window")
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Calendar months")
    axes[0].set_ylim(0, 13.4)
    axes[0].grid(axis="y", alpha=0.45)
    axes[0].legend(loc="lower left")
    axes[0].tick_params(axis="x", rotation=45)

    # Right: spatial completeness once a month exists, per source.
    for label, column in SOURCES.items():
        annual = D.annual_availability(panel, column)
        if annual.empty:
            continue
        axes[1].plot(annual["year"], annual["village_month_pct"], marker="s", ms=5, lw=1.9,
                     color=SOURCE_COLORS.get(label, "#777777"), label=label)
    axes[1].axhline(90, color="#B71C1C", lw=0.9, ls="--")
    axes[1].set_title("Share of village-months covered in each year")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("Coverage (%)")
    axes[1].set_ylim(0, 105)
    axes[1].grid(alpha=0.45)
    axes[1].legend(loc="lower left")
    axes[1].text(0.99, 0.02, "90% target", transform=axes[1].transAxes,
                 ha="right", va="bottom", fontsize=8, color="#B71C1C")

    fig.suptitle(
        "Annual sampling record: temporal completeness versus spatial completeness\n"
        "A month either exists for every village or for none, so the two panels answer different questions",
        fontsize=12.5,
    )
    ST.save(
        fig, "availability", "a4_annual_availability_trend.png",
        "Per-year count of months present and the spatial coverage of each source within those months.",
        source="village_with_baseline.csv",
    )


def fig_component_completeness(panel: pd.DataFrame) -> None:
    counts = D.component_count(panel)
    frame = pd.DataFrame({"n_inputs": counts, "dclass": panel["dclass"]})
    totals = frame["n_inputs"].value_counts().sort_index()
    composition = (
        pd.crosstab(frame["n_inputs"], frame["dclass"], normalize="index")
        .reindex(columns=C.CLASS_ORDER + ["ND"])
        .fillna(0.0)
        * 100.0
    )

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(14.5, 5.6), gridspec_kw={"width_ratios": [1, 1.35]}
    )
    bar_colors = [ST.COVERAGE_CMAP(0.25 + 0.15 * i) for i in range(len(totals))]
    bars = ax.bar(totals.index.astype(str), totals.to_numpy(), color=bar_colors,
                  edgecolor="#444444", linewidth=0.5)
    for bar, value in zip(bars, totals.to_numpy()):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.01, f"{value:,}",
                ha="center", va="bottom", fontsize=8.5)
    ax.set_xlabel("Number of available CDI components (SPI-3, NDVI, VCI, NSMI)")
    ax.set_ylabel("Village-months")
    ax.set_title("How many indices actually back each score")
    ax.grid(axis="y", alpha=0.45)

    bottom = np.zeros(len(composition))
    x = np.arange(len(composition))
    for code in composition.columns:
        values = composition[code].to_numpy()
        ax2.bar(x, values, bottom=bottom, color=C.DROUGHT_COLORS.get(code, "#BDBDBD"),
                edgecolor="white", linewidth=0.5,
                hatch="///" if code == "ND" else None,
                label=C.D_CLASS_LABELS.get(code, code))
        bottom += values
    ax2.set_xticks(x)
    ax2.set_xticklabels(composition.index.astype(str))
    ax2.set_ylim(0, 100)
    ax2.set_xlabel("Number of available CDI components")
    ax2.set_ylabel("Share of village-months (%)")
    ax2.set_title("Drought class reached at each completeness level")
    ax2.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8)

    fig.suptitle(
        "Completeness of the composite: rainfall-only monsoon months versus fully observed months",
        fontsize=13,
    )
    ST.save(
        fig, "availability", "a5_component_completeness.png",
        "Distribution of available CDI components per village-month and the drought class reached at each level.",
        source="village_with_baseline.csv",
    )


def build(panel: pd.DataFrame) -> None:
    fig_tehsil_year_availability(panel)
    fig_month_year_availability(panel)
    fig_tehsil_availability_bars(panel)
    fig_annual_availability_trend(panel)
    fig_component_completeness(panel)
