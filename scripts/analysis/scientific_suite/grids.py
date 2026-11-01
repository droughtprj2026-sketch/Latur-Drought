# -*- coding: utf-8 -*-
"""Reusable heatmap grid builders (month x year, tehsil x year, correlation)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

from . import config as C
from . import stats as S

MISSING_FACE = "#E4E4E4"


def norm_fmt(fmt: str) -> str:
    """Accept both ``"{:.2f}"`` and ``".2f"``; seaborn wants the bare spec."""
    if fmt.startswith("{") and fmt.endswith("}"):
        inner = fmt[1:-1]
        return inner[1:] if inner.startswith(":") else inner
    return fmt


def month_year_matrix(df: pd.DataFrame, column: str, agg: str = "mean") -> pd.DataFrame:
    """Calendar month (rows) x year (columns) aggregate of one index."""
    if column not in df.columns:
        return pd.DataFrame()
    sub = df.dropna(subset=[column])
    years = sorted(df["year"].unique())
    if sub.empty:
        return pd.DataFrame(index=C.MONTH_NUMBERS, columns=years, dtype=float)
    grouped = sub.groupby(["month", "year"])[column]
    series = grouped.mean() if agg == "mean" else grouped.size()
    return series.unstack("year").reindex(index=C.MONTH_NUMBERS, columns=years)


def tehsil_year_matrix(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame()
    grid = df.dropna(subset=[column]).pivot_table(
        index="tehsil", columns="year", values=column, aggfunc="mean"
    )
    order = grid.mean(axis=1).sort_values(ascending=False).index
    return grid.loc[order]


def village_year_matrix(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame()
    return df.dropna(subset=[column]).pivot_table(
        index="village_idx", columns="year", values=column, aggfunc="mean"
    )


def robust_limits(values: np.ndarray, lower: float = 2.0, upper: float = 98.0) -> tuple[float, float]:
    vals = values[np.isfinite(values)]
    if vals.size == 0:
        return (0.0, 1.0)
    lo, hi = np.nanpercentile(vals, [lower, upper])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo, hi = float(np.nanmin(vals)), float(np.nanmax(vals))
    if lo == hi:
        lo, hi = lo - 0.01, hi + 0.01
    return float(lo), float(hi)


def nice_norm(column: str, values: np.ndarray):
    """Pick a sensible colour norm for an index."""
    spec = C.COL.get(column)
    lo, hi = robust_limits(values)
    if spec is not None and spec.kind == "spi":
        limit = max(1.0, float(np.nanpercentile(np.abs(values[np.isfinite(values)]), 98)))
        limit = min(limit, 3.0)
        return TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)
    if spec is not None and spec.kind == "composite":
        return plt.Normalize(vmin=0.0, vmax=max(0.35, hi))
    if spec is not None and spec.kind == "percent":
        return plt.Normalize(vmin=max(0.0, lo), vmax=100.0)
    if spec is not None and spec.column == "NDVI":
        return plt.Normalize(vmin=max(0.0, lo), vmax=min(0.9, hi))
    if spec is not None and spec.column == "EVI":
        return plt.Normalize(vmin=max(0.0, lo), vmax=min(0.9, hi))
    if spec is not None and spec.column == "Rain_mm":
        return plt.Normalize(vmin=0.0, vmax=hi)
    return plt.Normalize(vmin=lo, vmax=hi)


def draw_month_year(ax, grid: pd.DataFrame, cmap=None, norm=None, annot: bool = True,
                    fmt: str = "{:.2f}", annot_size: float = 6.2, cbar: bool = False,
                    cbar_kws: dict | None = None, linewidths: float = 0.4) -> None:
    """Month x year heatmap with grey cells where a month has no observation."""
    if grid is None or grid.empty:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        return

    values = grid.to_numpy(dtype=float)
    mask = ~np.isfinite(values)
    index = list(grid.index)
    if all(isinstance(i, (int, np.integer)) and 1 <= int(i) <= 12 for i in index):
        ylabels = [C.MONTHS[int(m) - 1] for m in index]
    else:
        ylabels = [str(i) for i in index]

    ax.set_facecolor(MISSING_FACE)
    sns.heatmap(
        grid,
        ax=ax,
        cmap=cmap,
        norm=norm,
        mask=mask,
        annot=annot,
        fmt=norm_fmt(fmt),
        annot_kws={"size": max(annot_size, 7.5), "weight": "bold"},
        linewidths=linewidths,
        linecolor="white",
        cbar=cbar,
        cbar_kws=cbar_kws or {},
        xticklabels=[str(y) for y in grid.columns],
        yticklabels=ylabels,
    )
    ax.tick_params(axis="x", rotation=40, labelsize=9.0)
    ax.tick_params(axis="y", rotation=0, labelsize=7.5)
    ax.set_xlabel("")
    ax.set_ylabel("")


def draw_corr(ax, corr: pd.DataFrame, annot: bool = True, fmt: str = "{:.2f}",
              cmap: str = "RdBu_r", mask_upper: bool = True, cbar: bool = True,
              annot_size: float = 8.5, cbar_kws: dict | None = None,
              vmin: float = -1.0, vmax: float = 1.0) -> None:
    mask = np.triu(np.ones_like(corr.to_numpy(dtype=float), dtype=bool)) if mask_upper else None
    sns.heatmap(
        corr,
        ax=ax,
        mask=mask,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        center=0.0,
        annot=annot,
        fmt=norm_fmt(fmt),
        square=True,
        linewidths=0.6,
        linecolor="white",
        cbar=cbar,
        cbar_kws=cbar_kws or {"shrink": 0.75, "label": "correlation coefficient"},
        annot_kws={"size": annot_size, "weight": "bold"},
    )
    ax.tick_params(axis="x", rotation=45, labelsize=8.5)
    ax.tick_params(axis="y", rotation=0, labelsize=8.5)
    for label in ax.get_xticklabels():
        label.set_ha("right")


def draw_signed_heatmap(ax, matrix: pd.DataFrame, cbar_label: str, annot: bool = True,
                        fmt: str = "{:.3f}", annot_size: float = 6.5, cmap: str = "RdBu_r",
                        limit: float | None = None, cbar: bool = True) -> None:
    values = matrix.to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if limit is None:
        limit = float(np.nanmax(np.abs(finite))) if finite.size else 1.0
    limit = max(limit, 1e-6)
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit) if limit > 0 else None
    ax.set_facecolor(MISSING_FACE)
    sns.heatmap(
        matrix,
        ax=ax,
        cmap=cmap,
        norm=norm,
        mask=~np.isfinite(values),
        annot=annot,
        fmt=norm_fmt(fmt),
        annot_kws={"size": max(annot_size, 7.5), "weight": "bold"},
        linewidths=0.4,
        linecolor="white",
        cbar=cbar,
        cbar_kws={"shrink": 0.8, "label": cbar_label} if cbar else None,
    )
    ax.tick_params(axis="x", rotation=90, labelsize=8)
    ax.tick_params(axis="y", rotation=0, labelsize=8)


# --------------------------------------------------------------------------
# A labelled pair correlation matrix used by the tehsil section
# --------------------------------------------------------------------------
def pair_matrix(df: pd.DataFrame, pairs: list[tuple[str, str]], method: str = "pearson",
                group: str | None = None) -> pd.DataFrame:
    """Pearson/Spearman table of index pairs, optionally computed per group."""
    from . import stats as ST

    func = ST.pearson if method == "pearson" else ST.spearman
    rows: dict[str, dict] = {}
    labels = [f"{C.COL[a].short}~{C.COL[b].short}" if a in C.COL and b in C.COL else f"{a}~{b}"
              for a, b in pairs]

    if group is None:
        values = {}
        for (a, b), label in zip(pairs, labels):
            r, _, _ = func(df[a], df[b]) if a in df.columns and b in df.columns else (np.nan, np.nan, 0)
            values[label] = r
        return pd.DataFrame([values], index=[method])

    for name, sub in df.groupby(group):
        values = {}
        for (a, b), label in zip(pairs, labels):
            r, _, _ = func(sub[a], sub[b]) if a in sub.columns and b in sub.columns else (np.nan, np.nan, 0)
            values[label] = r
        rows[str(name)] = values
    return pd.DataFrame(rows).T
