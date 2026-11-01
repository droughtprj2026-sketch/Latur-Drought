# -*- coding: utf-8 -*-
"""Section 04 - scatter relationships, regressions and response lags."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from . import config as C
from . import data as D
from . import stats as S
from . import style as ST


def _scatter_with_fit(ax, df: pd.DataFrame, xcol: str, ycol: str, color: str,
                      panel_tag: str | None = None) -> dict:
    sub = df[[xcol, ycol]].dropna()
    res = S.ols(sub[xcol], sub[ycol])
    spearman_res = S.spearman(sub[xcol], sub[ycol])

    # Hexagonal 2D density binning with logarithmic scale for high-density remote sensing clouds
    hb = ax.hexbin(
        sub[xcol], sub[ycol],
        gridsize=55, bins="log", mincnt=1,
        cmap="cividis" if "SPI" in xcol else "viridis",
        linewidths=0.15, edgecolors="none", rasterized=True, zorder=2
    )

    x_lo = float(sub[xcol].quantile(0.005))
    x_hi = float(sub[xcol].quantile(0.995))
    if np.isfinite(res["slope"]):
        xs = np.linspace(x_lo, x_hi, 150)
        ax.plot(xs, res["intercept"] + res["slope"] * xs, color="#DC2626", lw=2.2, ls="-", zorder=5, label="OLS Regression")
        # 95% confidence band for the mean response
        n = res["n"]
        if n > 3 and np.isfinite(res["stderr"]):
            xbar = sub[xcol].mean()
            ssx = ((sub[xcol] - xbar) ** 2).sum()
            if ssx > 0:
                resid = sub[ycol] - (res["intercept"] + res["slope"] * sub[xcol])
                s_err = np.sqrt((resid ** 2).sum() / (n - 2))
                se_mean = s_err * np.sqrt(1.0 / n + (xs - xbar) ** 2 / ssx)
                ax.fill_between(xs, res["intercept"] + res["slope"] * xs - 1.96 * se_mean,
                                res["intercept"] + res["slope"] * xs + 1.96 * se_mean,
                                color="#DC2626", alpha=0.25, linewidth=0, zorder=4, label="95% CI")

    ax.set_xlabel(ST.label_of(xcol), fontsize=11, weight="bold")
    ax.set_ylabel(ST.label_of(ycol), fontsize=11, weight="bold")
    ax.grid(True, linestyle=":", color="#94A3B8", alpha=0.5)

    if panel_tag:
        ST.add_panel_label(ax, label=panel_tag, x=-0.08, y=1.04)

    # Fisher 95% CI for Pearson r
    ci_lo, ci_hi = S.fisher_ci(res["r"], res["n"])

    ST.stats_box(
        ax,
        [
            f"N          = {res['n']:,}",
            f"Pearson r  = {res['r']:+.3f} [{ci_lo:+.3f}, {ci_hi:+.3f}]",
            f"Spearman ρ = {spearman_res[0]:+.3f}",
            f"R²         = {res['r2']:.3f}",
            f"Fit: y     = {res['intercept']:+.3f} + {res['slope']:+.3f}x",
            ST.p_text(res["p"]),
        ],
        loc="upper left" if res["slope"] < 0 else "lower right",
        fontsize=8.2,
    )
    return res


def fig_core_scatter(panel: pd.DataFrame) -> pd.DataFrame:
    layout = [
        ("SPI3", "NDVI", "#1B5E20", "Meteorological driver vs Vegetation state", "(a)"),
        ("SPI3", "NSMI", "#4E342E", "Meteorological driver vs Soil moisture", "(b)"),
        ("NSMI", "VCI", "#00695C", "Soil moisture vs Vegetation condition", "(c)"),
        ("SPI3", C.CDI_COLUMN, "#6E1423", "Rainfall anomaly vs Composite drought score", "(d)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(15.2, 12.6))
    results = []
    for ax, (xcol, ycol, color, title, tag) in zip(axes.ravel(), layout):
        if xcol not in panel.columns or ycol not in panel.columns:
            ax.axis("off")
            continue
        res = _scatter_with_fit(ax, panel, xcol, ycol, color, panel_tag=tag)
        ax.set_title(f"{title}\n{ST.label_of(xcol)} vs {ST.label_of(ycol)}", fontsize=11.5, weight="bold", pad=10)
        results.append({"predictor": xcol, "response": ycol, **res})

        if ycol == C.CDI_COLUMN:
            for band in __import__("common.classify", fromlist=["composite_thresholds"]).composite_thresholds():
                if band["code"] != "D4":
                    ax.axhline(band["max"], color="#616161", ls=":", lw=0.8, alpha=0.8)
            ax.text(0.99, 0.02, "dotted = CDI class thresholds (config/composite.yaml)",
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, color="#444444")

    fig.suptitle(
        "Core index relationships with ordinary least squares fit and 95% confidence band\n"
        "The four couplings the composite is built on, tested over every observed village-month",
        fontsize=13.5,
    )
    ST.save(
        fig, "relationships", "r1_core_scatter_regressions.png",
        "Four core scatter regressions with OLS fit, 95% confidence band and full diagnostics.",
        source="village_with_baseline.csv",
    )
    return pd.DataFrame(results)


def fig_pairplot(panel: pd.DataFrame) -> None:
    columns = ["SPI3", "NSMI", "NDVI", "VCI", C.CDI_COLUMN]
    columns = [c for c in columns if c in panel.columns]
    sub = panel.dropna(subset=columns + ["dclass"])
    sub = sub[sub["dclass"].isin(C.CLASS_ORDER)]
    if sub.empty:
        return
    sub = sub.sample(n=min(4500, len(sub)), random_state=11)

    present = [c for c in C.CLASS_ORDER if c in set(sub["dclass"])]
    grid = sns.pairplot(
        sub,
        vars=columns,
        hue="dclass",
        hue_order=present,
        palette={k: v for k, v in C.DROUGHT_COLORS.items()},
        corner=True,
        diag_kind="kde",
        plot_kws={"s": 9, "alpha": 0.45, "linewidth": 0},
        diag_kws={"linewidth": 1.2, "common_norm": False},
    )
    grid.fig.set_size_inches(12.6, 11.4)

    # Readable axis labels instead of the raw column names.
    for ax in grid.axes.flatten():
        if ax is None:
            continue
        xlabel, ylabel = ax.get_xlabel(), ax.get_ylabel()
        if xlabel:
            ax.set_xlabel(C.COL[xlabel].short if xlabel in C.COL else xlabel, fontsize=9)
        if ylabel:
            ax.set_ylabel(C.COL[ylabel].short if ylabel in C.COL else ylabel, fontsize=9)

    # Replace the auto legend with a labelled one, placed in the empty corner half.
    if grid._legend is not None:
        grid._legend.remove()

    from matplotlib.patches import Patch

    handles = [Patch(facecolor=C.DROUGHT_COLORS[c], label=C.D_CLASS_LABELS[c]) for c in present]
    grid.fig.legend(
        handles=handles, title="Drought class", loc="upper right",
        bbox_to_anchor=(0.99, 0.97), frameon=True, fontsize=8.5, title_fontsize=9,
    )

    grid.fig.suptitle(
        "Pairwise scatter matrix of the five CDI inputs and the composite, coloured by drought class\n"
        f"Random sample of {len(sub):,} village-months for legibility",
        fontsize=13, y=0.985,
    )
    grid.fig.subplots_adjust(top=0.90, right=0.84, wspace=0.10, hspace=0.10)
    ST.save(
        grid.fig, "relationships", "r2_pairplot_matrix.png",
        "Seaborn pairplot of the five core indices coloured by drought class, with KDE margins.",
        source="village_with_baseline.csv",
    )


def fig_hexbin_density(panel: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.6, 6.2))
    panels = [("SPI3", "NDVI", "Meteorological to vegetation"), ("NSMI", "VCI", "Soil moisture to vegetation condition")]
    for ax, (xcol, ycol, title) in zip(axes, panels):
        sub = panel[[xcol, ycol]].dropna()
        if sub.empty:
            ax.axis("off")
            continue
        hb = ax.hexbin(sub[xcol], sub[ycol], gridsize=52, cmap="magma_r", bins="log", mincnt=1,
                       linewidths=0)
        cb = fig.colorbar(hb, ax=ax, shrink=0.85, pad=0.02)
        cb.set_label("village-months per hexagon (log)")

        res = S.ols(sub[xcol], sub[ycol])
        if np.isfinite(res["slope"]):
            xs = np.linspace(sub[xcol].min(), sub[xcol].max(), 100)
            ax.plot(xs, res["intercept"] + res["slope"] * xs, color="#00E5FF", lw=2.2)
        r_s, _, _ = S.spearman(sub[xcol], sub[ycol])
        ax.set_title(f"{title}\nPearson r = {res['r']:+.3f}   Spearman rho = {r_s:+.3f}   n = {res['n']:,}",
                     fontsize=10.5)
        ax.set_xlabel(C.COL[xcol].label)
        ax.set_ylabel(C.COL[ycol].label)

    fig.suptitle(
        "Point density instead of overplotting\n"
        "101,124 village-months compressed into hexagons; cyan line is the OLS fit",
        fontsize=13,
    )
    ST.save(
        fig, "relationships", "r3_hexbin_density.png",
        "Hexbin density plots of the two central couplings with both correlation coefficients.",
        source="village_with_baseline.csv",
    )


def fig_regression_by_tehsil(panel: pd.DataFrame) -> pd.DataFrame:
    tehsils = sorted(panel["tehsil"].unique())
    ncols = 5
    nrows = int(np.ceil(len(tehsils) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.9 * ncols, 3.5 * nrows), sharex=True, sharey=True)
    axes = np.atleast_1d(axes).ravel()

    rows = []
    for ax, tehsil in zip(axes, tehsils):
        sub = panel[panel["tehsil"] == tehsil][["SPI3", "NDVI"]].dropna()
        if sub.empty:
            ax.axis("off")
            continue
        ax.scatter(sub["SPI3"], sub["NDVI"], s=4, color="#2E7D32", alpha=0.28, linewidths=0,
                   rasterized=True)
        res = S.ols(sub["SPI3"], sub["NDVI"])
        if np.isfinite(res["slope"]):
            xs = np.linspace(sub["SPI3"].min(), sub["SPI3"].max(), 50)
            ax.plot(xs, res["intercept"] + res["slope"] * xs, color="#6E1423", lw=1.9)
        ax.set_title(f"{tehsil}", fontsize=9.5)
        ax.text(0.04, 0.06, f"r = {res['r']:+.2f}\nn = {res['n']:,}", transform=ax.transAxes,
                fontsize=7.4, va="bottom", family="monospace",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#CCCCCC", lw=0.5, alpha=0.9))
        ax.grid(alpha=0.3)
        rows.append({"tehsil": tehsil, **res})

    for ax in axes[len(tehsils):]:
        ax.axis("off")

    fig.suptitle(
        "SPI-3 vs NDVI inside every tehsil\n"
        "Does the district-level coupling survive at tehsil scale, or is it carried by a few pockets",
        fontsize=13,
    )
    ST.figure_note(fig, "Shared axes. A flat line means vegetation in that tehsil is decoupled from rainfall "
                        "within the observed months.", y=0.0)
    ST.save(
        fig, "relationships", "r4_regression_by_tehsil.png",
        "Per-tehsil SPI-3 vs NDVI scatter regressions with r and n annotated.",
        source="village_with_baseline.csv",
    )
    return pd.DataFrame(rows)


def fig_lag_response(panel: pd.DataFrame) -> pd.DataFrame:
    drivers = [c for c in ("SPI1", "SPI3", "SPI6", "SPI12") if c in panel.columns]
    responses = [c for c in ("NDVI", "VCI", "NSMI") if c in panel.columns]
    max_lag = 6

    tables = []
    fig, axes = plt.subplots(1, len(responses), figsize=(5.8 * len(responses), 5.6),
                             layout="constrained", sharey=True)
    axes = np.atleast_1d(axes)

    colors = {
        "SPI1": "#38BDF8",
        "SPI3": "#2563EB",
        "SPI6": "#1D4ED8",
        "SPI12": "#0F172A",
    }
    markers = {"SPI1": "o", "SPI3": "s", "SPI6": "^", "SPI12": "D"}
    tags = ["a", "b", "c", "d"]

    for i, (ax, response) in zip(range(len(responses)), zip(axes, responses)):
        peak_lines = []
        for driver in drivers:
            table = S.lag_correlation(panel, driver, response, max_lag=max_lag)
            if table.empty:
                continue
            table["response"] = response

            # Compute 95% Fisher CI for each lag
            ci_bounds = [S.fisher_ci(row["r"], int(row["n"])) for _, row in table.iterrows()]
            table["r_lo"] = [b[0] for b in ci_bounds]
            table["r_hi"] = [b[1] for b in ci_bounds]
            tables.append(table)

            c = colors.get(driver, "#555555")
            m = markers.get(driver, "o")

            # Shaded 95% CI envelope
            ax.fill_between(table["lag_months"], table["r_lo"], table["r_hi"], color=c, alpha=0.12)
            # Line and markers
            ax.plot(table["lag_months"], table["r"], marker=m, ms=5.5, lw=2.0, color=c, label=driver)

            # Significant points (p < 0.05)
            sig = table[table["p"] < 0.05]
            ax.scatter(sig["lag_months"], sig["r"], s=45, facecolor="white",
                       edgecolor=c, linewidth=1.8, zorder=5)

            peak = table.loc[table["r"].abs().idxmax()]
            peak_lines.append(f"{driver}: peak lag {int(peak['lag_months'])} mo (r={peak['r']:+.3f})")

        ax.axhline(0, color="#64748B", lw=0.9, ls="--")
        ax.set_xlabel("Lag (Months) from Driver to Response", fontsize=10.5, weight="bold")
        if i == 0:
            ax.set_ylabel("Pooled Pearson Correlation (r)", fontsize=11.0, weight="bold")
        ax.set_title(f"({tags[i]}) Response: {C.COL[response].short} ({C.COL[response].label})", fontsize=11.0, weight="bold")
        ax.set_xticks(range(0, max_lag + 1))
        ax.grid(True, linestyle=":", color="#CBD5E1", alpha=0.6)
        ax.legend(title="Precipitation Driver", loc="lower left", fontsize=8.0, framealpha=0.92)
        ST.stats_box(ax, ["Peak Response Timing:"] + peak_lines, loc="upper right", fontsize=7.2)

    fig.suptitle(
        "Multi-Scale Lag-Response Analysis: Soil Moisture and Canopy Memory of Rainfall\n"
        "Pooled cross-correlations across 954 villages with 95% Fisher-z confidence intervals (shaded)",
        fontsize=13.0, weight="bold",
    )
    ST.figure_note(
        fig,
        "Lags range from zero (concurrent) to six months. Hollow circles indicate statistical significance at p < 0.05. "
        "Notice that short-term soil moisture (NSMI) peaks at lag 0-1 month with SPI-1/3, while vegetation greenness (NDVI) "
        "accumulates moisture over 1-2 months.",
    )
    ST.save(
        fig, "relationships", "r5_response_lag.png",
        "Multi-scale lag-response curves for SPI-1/3/6/12 against NDVI, VCI and NSMI with 95% confidence intervals.",
        source="village_with_baseline.csv",
    )
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def fig_index_agreement(panel: pd.DataFrame) -> pd.DataFrame:
    fig, axes = plt.subplots(1, 3, figsize=(16.0, 5.1))

    ax = axes[0]
    sub = panel[["NDVI", "EVI"]].dropna()
    if not sub.empty:
        plot = sub.sample(n=min(24000, len(sub)), random_state=3)
        ax.scatter(plot["NDVI"], plot["EVI"], s=5, color="#2E7D32", alpha=0.3, linewidths=0,
                   rasterized=True)
        lim = [min(plot["NDVI"].min(), plot["EVI"].min()), max(plot["NDVI"].max(), plot["EVI"].max())]
        ax.plot(lim, lim, color="#C23B22", ls="--", lw=1.2, label="1:1")
        res = S.ols(sub["NDVI"], sub["EVI"])
        xs = np.linspace(lim[0], lim[1], 50)
        ax.plot(xs, res["intercept"] + res["slope"] * xs, color="#111111", lw=1.8, label="OLS")
        ax.set_xlabel("NDVI")
        ax.set_ylabel("EVI")
        ax.set_title("NDVI and EVI measure the same canopy", fontsize=10)
        ax.legend(loc="upper left")
        ax.grid(alpha=0.35)
        ST.stats_box(ax, [f"n = {res['n']:,}", f"r = {res['r']:+.3f}", f"R2 = {res['r2']:.3f}"],
                     loc="lower right")

    ax = axes[1]
    sub_vegi = panel[["VCI", "VHI"]].dropna()
    if not sub_vegi.empty:
        plot = sub_vegi.sample(n=min(24000, len(sub_vegi)), random_state=5)
        ax.scatter(plot["VCI"], plot["VHI"], s=5, color="#00695C", alpha=0.3, linewidths=0,
                   rasterized=True)
        res = S.ols(sub_vegi["VCI"], sub_vegi["VHI"])
        xs = np.linspace(plot["VCI"].min(), plot["VCI"].max(), 50)
        ax.plot(xs, res["intercept"] + res["slope"] * xs, color="#C23B22", lw=1.8)
        ax.plot(xs, xs, color="#111111", ls=":", lw=1.0, label="1:1")
        identical = bool(np.allclose(sub_vegi["VCI"], sub_vegi["VHI"], atol=1e-6))
        ax.set_xlabel("VCI (%)")
        ax.set_ylabel("VHI (%)")
        ax.set_title(
            "VHI is an exact copy of VCI: no thermal input is ingested"
            if identical else "VCI and VHI diverge where thermal stress enters",
            fontsize=10,
        )
        ax.legend(loc="upper left")
        ax.grid(alpha=0.35)
        ST.stats_box(
            ax,
            [f"n = {res['n']:,}", f"r = {res['r']:+.3f}",
             f"max|VHI-VCI| = {float((sub_vegi['VHI'] - sub_vegi['VCI']).abs().max()):.6f}"],
            loc="lower right",
        )

    ax = axes[2]
    sub_agr = panel[["NDVI", "EVI"]].dropna()
    if not sub_agr.empty:
        res = S.ols(sub_agr["NDVI"], sub_agr["EVI"])
        resid = sub_agr["EVI"] - (res["intercept"] + res["slope"] * sub_agr["NDVI"])
        ax.hist(resid, bins=70, color="#8C6D31", alpha=0.85, edgecolor="white", linewidth=0.3)
        ax.axvline(0, color="#C23B22", lw=1.1, ls="--")
        ax.set_xlabel("EVI residual from the NDVI fit")
        ax.set_ylabel("Village-months")
        ax.set_title(f"Residual spread (sd = {resid.std():.4f})", fontsize=10)
        ax.grid(axis="y", alpha=0.35)

    fig.suptitle(
        "Internal consistency of the vegetation indices\n"
        "Where two indices disagree, the composite is carrying measurement noise rather than signal",
        fontsize=13,
    )
    ST.figure_note(
        fig,
        "The middle panel is the diagnostic that matters: VHI equals VCI to six decimals here, so the "
        "thermal component is absent and VHI must not be read as an independent stress index.",
    )
    ST.save(
        fig, "relationships", "r6_index_agreement.png",
        "NDVI/EVI agreement, VCI/VHI agreement and the NDVI-EVI residual distribution.",
        source="village_with_baseline.csv",
    )
    if sub_agr.empty:
        return pd.DataFrame()
    res = S.ols(panel["NDVI"], panel["EVI"])
    return pd.DataFrame([{"pair": "NDVI~EVI", **res}])


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    core = fig_core_scatter(panel)
    fig_pairplot(panel)
    fig_hexbin_density(panel)
    by_tehsil = fig_regression_by_tehsil(panel)
    lag = fig_lag_response(panel)
    agreement = fig_index_agreement(panel)
    return {
        "core_regressions": core,
        "tehsil_regressions": by_tehsil,
        "lag_correlations": lag,
        "agreement": agreement,
    }
