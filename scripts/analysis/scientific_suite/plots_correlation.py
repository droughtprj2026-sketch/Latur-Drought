# -*- coding: utf-8 -*-
"""Section 02 - correlation structure, reported for Pearson and Spearman together."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from . import config as C
from . import data as D
from . import grids as G
from . import stats as S
from . import style as ST

# Index pairs with a defensible physical meaning, used in the tehsil matrices and
# the forest plot. The order runs meteorological -> soil -> vegetation -> composite.
PAIRS: list[tuple[str, str]] = [
    ("Rain_mm", "SPI1"),
    ("Rain_mm", "SPI3"),
    ("SPI3", "SPI6"),
    ("SPI6", "SPI12"),
    ("SPI3", "NSMI"),
    ("NSMI", "VCI"),
    ("SPI3", "NDVI"),
    ("SPI3", "VCI"),
    ("NDVI", "VCI"),
    ("NDVI", "VHI"),
    ("VCI", "VHI"),
    ("SPI3", "composite_drought_score"),
    ("NDVI", "composite_drought_score"),
    ("VCI", "composite_drought_score"),
]


def short_labels(columns: list[str]) -> list[str]:
    return [C.COL[c].short if c in C.COL else c for c in columns]


def pair_label(a: str, b: str) -> str:
    return f"{C.COL[a].short}~{C.COL[b].short}"


def _corr_frame(panel: pd.DataFrame, columns: list[str], method: str):
    corr = S.corr_matrix(panel, columns, method=method)
    corr.index = short_labels(list(corr.index))
    corr.columns = short_labels(list(corr.columns))
    return corr


# --------------------------------------------------------------------------
# 1-2. The two headline matrices
# --------------------------------------------------------------------------
def fig_pearson_matrix(panel: pd.DataFrame) -> None:
    corr = _corr_frame(panel, C.CORE_COLUMNS, "pearson")
    fig, ax = plt.subplots(figsize=(11.4, 9.4))
    G.draw_corr(
        ax, corr, annot=True, fmt="{:.2f}", cbar=True,
        cbar_kws={"shrink": 0.78, "label": "Pearson r (linear association)"},
    )
    ax.set_title(
        "Pearson correlation matrix, full study period\n"
        "Linear association between meteorological, soil-moisture, vegetation and composite indices",
        fontsize=12.5, pad=14,
    )
    ST.figure_note(
        fig,
        "Pairwise-complete observations. SPI increases with wetness, so SPI-NDVI is expected to be positive; "
        "CDI increases with drought, so CDI-NDVI is expected to be negative.",
    )
    ST.save(
        fig, "correlation", "c1_pearson_matrix.png",
        "Pearson correlation matrix for all eleven indices over the full study period.",
        source="village_with_baseline.csv",
    )


def fig_spearman_matrix(panel: pd.DataFrame) -> None:
    corr = _corr_frame(panel, C.CORE_COLUMNS, "spearman")
    fig, ax = plt.subplots(figsize=(11.4, 9.4))
    G.draw_corr(
        ax, corr, annot=True, fmt="{:.2f}", cbar=True,
        cbar_kws={"shrink": 0.78, "label": "Spearman rho (rank association)"},
    )
    ax.set_title(
        "Spearman rank correlation matrix, full study period\n"
        "Monotonic association, robust to the skewed tails of rainfall and NDVI",
        fontsize=12.5, pad=14,
    )
    ST.figure_note(
        fig,
        "Compare with the Pearson matrix: a large gap between r and rho marks a relationship that is "
        "monotonic but not linear, or one driven by a handful of extreme months.",
    )
    ST.save(
        fig, "correlation", "c2_spearman_matrix.png",
        "Spearman rank correlation matrix for the same eleven indices.",
        source="village_with_baseline.csv",
    )


def fig_method_agreement(panel: pd.DataFrame) -> pd.DataFrame:
    pear = _corr_frame(panel, C.CORE_COLUMNS, "pearson")
    spear = _corr_frame(panel, C.CORE_COLUMNS, "spearman")
    labels = list(pear.columns)
    n = len(labels)
    upper = [(i, j) for i in range(n) for j in range(i + 1, n)]
    r_pear = np.array([pear.iloc[i, j] for i, j in upper])
    r_spear = np.array([spear.iloc[i, j] for i, j in upper])
    pair_names = [f"{labels[i]}~{labels[j]}" for i, j in upper]

    diff = (spear - pear)

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(15.5, 7.0), gridspec_kw={"width_ratios": [1, 1.1]}
    )
    ax.scatter(r_pear, r_spear, s=42, c="#17405F", alpha=0.75, edgecolor="white", linewidth=0.7)
    lim = (-0.05, 1.0)
    ax.plot(lim, lim, color="#B71C1C", ls="--", lw=1.1, label="1:1 (identical methods)")
    ax.axhline(0, color="#999999", lw=0.7)
    ax.axvline(0, color="#999999", lw=0.7)
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel("Pearson r")
    ax.set_ylabel("Spearman rho")
    ax.set_title("How far the two estimators disagree, pair by pair")
    ax.grid(alpha=0.4)
    ax.legend(loc="lower right")

    for name, xv, yv in zip(pair_names, r_pear, r_spear):
        if abs(yv - xv) > 0.14:
            ax.annotate(name, (xv, yv), xytext=(5, 4), textcoords="offset points",
                        fontsize=7.5, color="#333333")

    diff.index = labels
    diff.columns = labels
    G.draw_corr(
        ax2, diff, annot=True, fmt="{:+.2f}", cbar=True,
        cbar_kws={"shrink": 0.78, "label": "Spearman rho minus Pearson r"},
        vmin=-0.5, vmax=0.5, annot_size=6.4,
    )
    ax2.set_title("Signed difference between the estimators")

    fig.suptitle(
        "Pearson versus Spearman agreement across every index pair\n"
        "Points off the 1:1 line are the pairs where the choice of estimator changes the conclusion",
        fontsize=13,
    )
    ST.save(
        fig, "correlation", "c3_pearson_vs_spearman_agreement.png",
        "Per-pair comparison of Pearson and Spearman coefficients and their signed difference matrix.",
        source="village_with_baseline.csv",
    )
    return pd.DataFrame({"pair": pair_names, "pearson_r": r_pear, "spearman_rho": r_spear,
                         "difference": r_spear - r_pear})


# --------------------------------------------------------------------------
# Significance
# --------------------------------------------------------------------------
def fig_significance_matrix(panel: pd.DataFrame) -> pd.DataFrame:
    cols = C.CORE_COLUMNS
    p_pear = S.corr_pvalues(panel, cols, "pearson")
    p_spear = S.corr_pvalues(panel, cols, "spearman")

    def _stars_matrix(pframe: pd.DataFrame) -> pd.DataFrame:
        out = pframe.copy().astype(object)
        for i in range(out.shape[0]):
            for j in range(out.shape[1]):
                out.iloc[i, j] = ST.significance_stars(float(pframe.iloc[i, j]))
        return out

    stars_pear = _stars_matrix(p_pear)
    stars_spear = _stars_matrix(p_spear)
    neglog_pear = -np.log10(p_pear.clip(lower=1e-300))
    neglog_spear = -np.log10(p_spear.clip(lower=1e-300))

    fig, axes = plt.subplots(1, 2, figsize=(16.5, 7.6))
    for ax, neglog, stars, title in (
        (axes[0], neglog_pear, stars_pear, "Pearson"),
        (axes[1], neglog_spear, stars_spear, "Spearman"),
    ):
        neglog.index = short_labels(list(neglog.index))
        neglog.columns = short_labels(list(neglog.columns))
        stars.index = neglog.index
        stars.columns = neglog.columns
        sns.heatmap(
            neglog, ax=ax, cmap="magma_r", annot=stars.to_numpy(), fmt="",
            annot_kws={"size": 7}, linewidths=0.5, linecolor="white",
            cbar_kws={"label": "-log10(p)"}, square=True,
            mask=np.triu(np.ones_like(neglog.to_numpy(), dtype=bool)),
        )
        ax.set_title(f"{title}: significance of each pair")
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        ax.tick_params(axis="y", rotation=0, labelsize=8)
        for label in ax.get_xticklabels():
            label.set_ha("right")

    fig.suptitle(
        "Statistical significance of every index pair\n"
        "* p < 0.05    ** p < 0.01    *** p < 0.001    (colour = -log10 p)",
        fontsize=13,
    )
    ST.save(
        fig, "correlation", "c4_significance_matrices.png",
        "Significance stars over -log10(p) for Pearson and Spearman correlation.",
        source="village_with_baseline.csv",
    )

    rows = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            rows.append({
                "pair": pair_label(a, b),
                "pearson_r": round(float(p_pear.loc[a, b]), 4) if np.isfinite(p_pear.loc[a, b]) else np.nan,
                "pearson_p": p_pear.loc[a, b],
                "spearman_rho": round(float(p_spear.loc[a, b]), 4) if np.isfinite(p_spear.loc[a, b]) else np.nan,
                "spearman_p": p_spear.loc[a, b],
                "n": int(panel[[a, b]].dropna().shape[0]),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Year by year, both estimators
# --------------------------------------------------------------------------
def _annual_grid(panel: pd.DataFrame, method: str, filename: str, caption: str) -> None:
    years = sorted(panel["year"].unique())
    ncols = 4
    nrows = int(np.ceil(len(years) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.15 * ncols, 3.65 * nrows))
    axes = np.atleast_1d(axes).ravel()

    vmax_global = 0
    grids = {}
    for year in years:
        sub = panel[panel["year"] == year]
        corr = S.corr_matrix(sub, C.ANNUAL_COLUMNS, method=method)
        if corr.empty:
            continue
        corr.index = short_labels(list(corr.index))
        corr.columns = short_labels(list(corr.columns))
        grids[year] = corr
        vmax_global = max(vmax_global, float(np.nanmax(np.abs(corr.to_numpy()))))

    for ax, year in zip(axes, years):
        corr = grids.get(year)
        if corr is None or corr.shape[0] < 2:
            ax.axis("off")
            continue
        G.draw_corr(ax, corr, annot=True, fmt="{:.2f}", cbar=False, annot_size=6.6,
                    vmin=-1.0, vmax=1.0)
        n_obs = int(panel[panel["year"] == year].dropna(subset=["SPI3", "NDVI"]).shape[0])
        ax.set_title(f"{year}  (n = {n_obs:,})", fontsize=9.5)

    for ax in axes[len(years):]:
        ax.axis("off")

    estimator = "Pearson" if method == "pearson" else "Spearman"
    fig.suptitle(
        f"{estimator} correlation, recomputed inside each hydrological year\n"
        "Stability of the coupling from year to year, not just across the pooled record",
        fontsize=13.5, y=1.005,
    )
    ST.figure_note(
        fig,
        f"Each panel uses only that year's village-months. n is the count of village-months with both "
        f"SPI-3 and NDVI, which is the limiting pair outside the monsoon.",
    )
    ST.save(fig, "correlation", filename,
            f"Year-by-year {estimator} correlation grid for the six core indices.", source="village_with_baseline.csv")


def fig_annual_pearson(panel: pd.DataFrame) -> None:
    _annual_grid(panel, "pearson", "c5_annual_pearson_grid.png",
                 "Year-by-year Pearson correlation grid.")


def fig_annual_spearman(panel: pd.DataFrame) -> None:
    _annual_grid(panel, "spearman", "c6_annual_spearman_grid.png",
                 "Year-by-year Spearman correlation grid.")


# --------------------------------------------------------------------------
# Seasonal contrast
# --------------------------------------------------------------------------
def fig_seasonal(panel: pd.DataFrame) -> None:
    wet, dry = D.season_months(panel)
    wet_panel = panel[panel["month"].isin(wet)]
    dry_panel = panel[panel["month"].isin(dry)]

    fig, axes = plt.subplots(2, 2, figsize=(13.6, 11.8))
    for row, (method, label) in enumerate((("pearson", "Pearson r"), ("spearman", "Spearman rho"))):
        for col, (sub, season_name) in enumerate(
            ((wet_panel, f"Wet season {D.season_label(wet)}"), (dry_panel, f"Dry season {D.season_label(dry)}"))
        ):
            ax = axes[row, col]
            corr = _corr_frame(sub, C.ANNUAL_COLUMNS, method)
            G.draw_corr(ax, corr, annot=True, fmt="{:.2f}", cbar=(col == 1),
                        annot_size=7.2,
                        cbar_kws={"shrink": 0.8, "label": label})
            ax.set_title(f"{label} - {season_name}", fontsize=10)
            n_obs = int(sub.dropna(subset=["SPI3", "NDVI"]).shape[0])
            ax.text(0.01, -0.13, f"n = {n_obs:,} village-months", transform=ax.transAxes,
                    fontsize=7.5, color="#555555")

    fig.suptitle(
        "Seasonal contrast: the same coupling measured in the wet and dry halves of the year\n"
        "Seasons are defined from the district rainfall climatology, not fixed calendar assumptions",
        fontsize=13,
    )
    ST.save(
        fig, "correlation", "c7_seasonal_pearson_spearman.png",
        "Wet-season and dry-season correlation matrices, computed with both Pearson and Spearman.",
        source="village_with_baseline.csv",
    )


# --------------------------------------------------------------------------
# Tehsil-level matrices
# --------------------------------------------------------------------------
def _tehsil_matrix(panel: pd.DataFrame, method: str, filename: str, caption: str) -> pd.DataFrame:
    matrix = G.pair_matrix(panel, PAIRS, method=method, group="tehsil")
    if matrix.empty:
        return matrix
    matrix = matrix.loc[matrix.mean(axis=1).sort_values(ascending=False).index]

    estimator = "Pearson r" if method == "pearson" else "Spearman rho"
    fig, ax = plt.subplots(figsize=(12.8, 6.2))
    G.draw_signed_heatmap(
        ax, matrix, cbar_label=estimator, annot=True, fmt="{:.2f}", annot_size=7.2,
        limit=1.0,
    )
    ax.set_title(
        f"Per-tehsil {estimator} for physically meaningful index pairs\n"
        "Rows ordered by mean correlation strength; grey cells have too few overlapping observations",
        fontsize=12.5, pad=12,
    )
    ax.set_xlabel("Index pair")
    ax.set_ylabel("Tehsil")
    ST.figure_note(
        fig,
        "A negative SPI-NDVI cell means vegetation in that tehsil does not track rainfall within the "
        "available months - usually irrigated or double-cropped pockets.",
    )
    ST.save(fig, "correlation", filename, caption, source="village_with_baseline.csv")
    return matrix


def fig_tehsil_pearson(panel: pd.DataFrame) -> pd.DataFrame:
    return _tehsil_matrix(panel, "pearson", "c8_tehsil_pearson_heatmap.png",
                          "Per-tehsil Pearson correlation for fourteen index pairs.")


def fig_tehsil_spearman(panel: pd.DataFrame) -> pd.DataFrame:
    return _tehsil_matrix(panel, "spearman", "c9_tehsil_spearman_heatmap.png",
                          "Per-tehsil Spearman correlation for the same fourteen index pairs.")


# --------------------------------------------------------------------------
# Forest plot: the presentation summary
# --------------------------------------------------------------------------
def fig_key_correlations(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for a, b in PAIRS:
        if a not in panel.columns or b not in panel.columns:
            continue
        r, p, n = S.pearson(panel[a], panel[b])
        rho, p_s, _ = S.spearman(panel[a], panel[b])
        lo, hi = S.fisher_ci(r, n)
        rows.append({"pair": pair_label(a, b), "pearson_r": r, "pearson_p": p,
                     "ci_low": lo, "ci_high": hi, "spearman_rho": rho, "spearman_p": p_s, "n": n})
    frame = pd.DataFrame(rows).dropna(subset=["pearson_r"])
    frame = frame.sort_values("pearson_r")
    frame["pair"] = pd.Categorical(frame["pair"], categories=frame["pair"], ordered=True)

    fig, ax = plt.subplots(figsize=(11.6, 7.6))
    y = np.arange(len(frame))
    ax.hlines(y, frame["ci_low"], frame["ci_high"], color="#B0BEC5", lw=3.0, alpha=0.9,
              label="95% CI (Fisher z)")
    ax.scatter(frame["pearson_r"], y, s=68, color="#17405F", zorder=3, label="Pearson r")
    ax.scatter(frame["spearman_rho"], y, s=52, marker="D", color="#C23B22", zorder=3,
               label="Spearman rho")
    ax.axvline(0, color="#444444", lw=0.9)

    for yi, (_, row) in enumerate(frame.iterrows()):
        star = ST.significance_stars(row["pearson_p"])
        if star:
            ax.text(row["ci_high"] + 0.02, yi, star, va="center", fontsize=9, weight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(frame["pair"])
    ax.set_xlim(-1.05, 1.05)
    ax.set_xlabel("Correlation coefficient")
    ax.set_title(
        "Headline correlation results with confidence intervals\n"
        "Pearson and Spearman shown together; stars mark |r| significantly different from zero",
        fontsize=12.5,
    )
    ax.grid(axis="x", alpha=0.45)
    ax.legend(loc="lower right")
    ST.figure_note(
        fig,
        "Wide intervals indicate a pair observed only in a narrow season. Overlapping r and rho means the "
        "relationship is close to linear.",
    )
    ST.save(
        fig, "correlation", "c10_key_correlation_forest.png",
        "Forest plot of the headline index correlations with 95% confidence intervals, Pearson and Spearman.",
        source="village_with_baseline.csv",
    )
    return frame.drop(columns=["pair"]).assign(pair=frame["pair"].astype(str))


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    fig_pearson_matrix(panel)
    fig_spearman_matrix(panel)
    agreement = fig_method_agreement(panel)
    significance = fig_significance_matrix(panel)
    fig_annual_pearson(panel)
    fig_annual_spearman(panel)
    fig_seasonal(panel)
    fig_tehsil_pearson(panel)
    fig_tehsil_spearman(panel)
    forest = fig_key_correlations(panel)
    return {
        "pearson_vs_spearman": agreement,
        "significance": significance,
        "key_correlations": forest,
    }
