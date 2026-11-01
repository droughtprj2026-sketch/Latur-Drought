# -*- coding: utf-8 -*-
"""Section 03 - the full heatmap atlas.

Every index in the registry is rendered twice: month x year (time) and
tehsil x year (space), then the village x year block and the drought-class
frequency grids close the section. These are the figures that show the whole
ten-year record at once.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from . import config as C
from . import data as D
from . import grids as G
from . import style as ST


def _fmt_for(column: str) -> str:
    spec = C.COL[column]
    if spec.kind in ("spi",):
        return "{:.1f}"
    if spec.kind == "composite":
        return "{:.2f}"
    if spec.column in ("NDVI", "EVI", "NSMI"):
        return "{:.2f}"
    if spec.column == "Rain_mm":
        return "{:.0f}"
    return "{:.0f}"


def _atlas(panel: pd.DataFrame, builder, filename: str, suptitle: str, caption: str,
           ncols: int = 4, panel_w: float = 5.0, panel_h: float = 4.0,
           annot: bool = True, annot_size: float = 5.4) -> None:
    specs = [s for s in C.INDEXES if s.column in panel.columns and panel[s.column].notna().any()]
    nrows = int(np.ceil(len(specs) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(panel_w * ncols, panel_h * nrows))
    axes = np.atleast_1d(axes).ravel()

    for ax, spec in zip(axes, specs):
        grid = builder(panel, spec.column)
        if grid is None or grid.empty:
            ax.axis("off")
            continue
        values = panel[spec.column].to_numpy(dtype=float)
        norm = G.nice_norm(spec.column, values)
        G.draw_month_year(
            ax, grid, cmap=ST.cmap_for(spec.column), norm=norm,
            annot=annot, fmt=_fmt_for(spec.column), annot_size=annot_size, cbar=False,
        )
        unit = f" [{spec.unit}]" if spec.unit not in ("-",) else ""
        ax.set_title(f"{spec.short}{unit}", fontsize=9.5)
        ax.set_ylabel("")

    for ax in axes[len(specs):]:
        ax.axis("off")

    fig.suptitle(suptitle, fontsize=14, y=1.0)
    ST.figure_note(
        fig,
        "Grey cells are months with no observation. Each panel keeps its own colour scale so the seasonal "
        "shape of every index stays visible.",
        y=-0.005,
    )
    ST.save(fig, "heatmap", filename, caption, source="village_with_baseline.csv")


def fig_index_atlas_time(panel: pd.DataFrame) -> None:
    _atlas(
        panel,
        G.month_year_matrix,
        "h1_index_heatmap_atlas_month_year.png",
        "Heatmap atlas: every index as a calendar month x year matrix\n"
        "Vertical structure is the seasonal cycle, horizontal structure is the multi-year drought signal",
        "Month x year mean of every index in the registry, one panel per index.",
    )


def fig_index_atlas_space(panel: pd.DataFrame) -> None:
    _atlas(
        panel,
        G.tehsil_year_matrix,
        "h2_index_heatmap_atlas_tehsil_year.png",
        "Heatmap atlas: every index as a tehsil x year matrix\n"
        "Rows are ordered by the ten-year mean of that index, so the most stressed tehsil is always on top",
        "Tehsil x year mean of every index in the registry, rows ranked by ten-year mean.",
        panel_h=3.3,
        annot_size=5.0,
    )


def fig_village_year_clustermap(panel: pd.DataFrame) -> None:
    matrix = G.village_year_matrix(panel, C.CDI_COLUMN)
    if matrix.empty:
        return
    matrix = matrix.dropna(how="all")
    if matrix.shape[0] < 5:
        return

    grid = sns.clustermap(
        matrix,
        cmap=ST.CDI_CMAP,
        vmin=0.0, vmax=float(np.nanpercentile(matrix.to_numpy(), 95)),
        col_cluster=False,
        row_cluster=True,
        metric="euclidean",
        method="average",
        figsize=(10.6, 13.5),
        yticklabels=False,
        xticklabels=[str(c) for c in matrix.columns],
        cbar_kws={"label": "Annual mean CDI", "shrink": 0.45},
        linewidths=0.0,
    )
    grid.ax_heatmap.set_xlabel("Year")
    grid.ax_heatmap.set_ylabel(f"Villages ({matrix.shape[0]}) grouped by ten-year drought profile")
    grid.ax_heatmap.tick_params(axis="x", rotation=90, labelsize=8)
    grid.fig.suptitle(
        "Village x year drought exposure, hierarchically clustered\n"
        "Villages sharing a similar ten-year history fall into the same block",
        fontsize=13,
    )
    ST.figure_note(
        grid.fig,
        "Row clustering uses the annual-mean CDI vector, so blocks are exposure archetypes, not "
        "administrative units. White gaps are village-years with no score.",
        y=0.02,
    )
    ST.save(
        grid.fig, "heatmap", "h3_village_year_clustermap.png",
        "Clustered village x year matrix of annual mean CDI, revealing drought-exposure archetypes.",
        source="village_with_baseline.csv",
    )


def fig_drought_frequency_heatmaps(panel: pd.DataFrame) -> pd.DataFrame:
    scored = panel[panel["dclass"].isin(C.DROUGHT_CODES + ["None"])].copy()
    scored["is_drought"] = scored["dclass"].isin(C.DROUGHT_CODES)
    scored["is_moderate"] = scored["dclass"].isin(["D1", "D2", "D3", "D4"])

    tehsil_year = (
        scored.pivot_table(index="tehsil", columns="year", values="is_drought", aggfunc="mean") * 100.0
    )
    tehsil_year = tehsil_year.loc[tehsil_year.mean(axis=1).sort_values(ascending=False).index]

    month_year = (
        scored.pivot_table(index="month", columns="year", values="is_moderate", aggfunc="mean") * 100.0
    ).reindex(index=C.MONTH_NUMBERS, columns=sorted(scored["year"].unique()))

    fig, axes = plt.subplots(
        2, 1, figsize=(13.2, 11.4), gridspec_kw={"height_ratios": [1.0, 0.9]}
    )
    sns.heatmap(
        tehsil_year, ax=axes[0], cmap="YlOrRd", vmin=0,
        vmax=max(1.0, float(np.nanpercentile(tehsil_year.to_numpy(), 98))),
        annot=True, fmt=".0f", annot_kws={"size": 7}, linewidths=0.5, linecolor="white",
        cbar_kws={"label": "% village-months in drought (D0-D4)", "shrink": 0.8},
    )
    axes[0].set_title("A. Drought frequency by tehsil and year", fontsize=11)
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Tehsil")
    axes[0].tick_params(axis="x", rotation=90, labelsize=8)
    axes[0].tick_params(axis="y", rotation=0, labelsize=8)

    G.draw_month_year(
        axes[1], month_year, cmap="YlOrRd",
        norm=plt.Normalize(vmin=0, vmax=max(1.0, float(np.nanpercentile(month_year.to_numpy(), 98)))),
        annot=True, fmt="{:.0f}", annot_size=6.4, cbar=True,
        cbar_kws={"label": "% village-months at D1 or worse", "shrink": 0.75},
    )
    axes[1].set_title("B. Moderate-or-worse frequency by calendar month and year", fontsize=11)
    axes[1].set_ylabel("Calendar month")
    axes[1].set_xlabel("Year")

    fig.suptitle(
        "Where and when drought actually occurs, not just how strong it is\n"
        "Drought frequency counts village-months, so sparse months cannot masquerade as drought",
        fontsize=13,
    )
    ST.save(
        fig, "heatmap", "h4_drought_frequency_heatmaps.png",
        "Drought-occurrence frequency by tehsil x year and by month x year.",
        source="village_with_baseline.csv",
    )
    return tehsil_year


def fig_class_share_heatmap(panel: pd.DataFrame) -> None:
    """Share of each drought class per year, as a stacked heatmap (class x year)."""
    scored = panel[panel["dclass"].isin(C.CLASS_ORDER)]
    if scored.empty:
        return
    share = (
        pd.crosstab(scored["year"], scored["dclass"], normalize="index")
        .reindex(columns=C.CLASS_ORDER)
        .fillna(0.0)
        * 100.0
    ).T

    fig, ax = plt.subplots(figsize=(13.0, 4.6))
    sns.heatmap(
        share, ax=ax, cmap="YlOrRd", vmin=0, vmax=100,
        annot=True, fmt=".1f", annot_kws={"size": 7.5},
        linewidths=0.5, linecolor="white",
        cbar_kws={"label": "% of scored village-months", "shrink": 0.8},
        yticklabels=[C.D_CLASS_LABELS[c] for c in share.index],
    )
    ax.set_title(
        "Drought-class composition of every year\n"
        "Each column sums to 100% of the scored village-months in that year",
        fontsize=12.5, pad=12,
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("")
    ax.tick_params(axis="y", rotation=0, labelsize=9)
    ax.tick_params(axis="x", rotation=90, labelsize=8)
    ST.save(
        fig, "heatmap", "h5_class_share_by_year.png",
        "Percentage of scored village-months in each drought class, year by year.",
        source="village_with_baseline.csv",
    )


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    fig_index_atlas_time(panel)
    fig_index_atlas_space(panel)
    fig_village_year_clustermap(panel)
    frequency = fig_drought_frequency_heatmaps(panel)
    fig_class_share_heatmap(panel)
    return {"tehsil_drought_frequency": frequency.reset_index() if not frequency.empty else frequency}
