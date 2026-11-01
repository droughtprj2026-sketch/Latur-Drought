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
                      sample: int = 26000, seed: int = 7) -> dict:
    sub = df[[xcol, ycol]].dropna()
    res = S.ols(sub[xcol], sub[ycol])
    plot = sub.sample(n=min(sample, len(sub)), random_state=seed) if len(sub) > sample else sub

    spec_x, spec_y = C.COL[xcol], C.COL[ycol]
    is_spi_x = spec_x.kind == "spi"
    cmap = ST.CDI_CMAP if not is_spi_x else ST.cmap_for(xcol)
    vals = plot[xcol]
    ax.scatter(plot[xcol], plot[ycol], s=5, c=vals, cmap=cmap, alpha=0.35,
               linewidths=0, rasterized=True)

    if np.isfinite(res["slope"]):
        xs = np.linspace(plot[xcol].min(), plot[xcol].max(), 100)
        ax.plot(xs, res["intercept"] + res["slope"] * xs, color=color, lw=2.0, ls="--")
        # 95% band for the mean response
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
                                color=color, alpha=0.16, linewidth=0)

    ax.set_xlabel(f"{spec_x.label} [{spec_x.unit}]" if spec_x.unit != "-" else spec_x.label)
    ax.set_ylabel(f"{spec_y.label} [{spec_y.unit}]" if spec_y.unit != "-" else spec_y.label)
    ax.grid(alpha=0.35)

    ST.stats_box(
        ax,
        [
            f"n     = {res['n']:,}",
            f"r     = {res['r']:+.3f}",
            f"R2    = {res['r2']:.3f}",
            f"slope = {res['slope']:+.4f}",
            ST.p_text(res["p"]),
        ],
        loc="upper left",
    )
    return res


def fig_core_scatter(panel: pd.DataFrame) -> pd.DataFrame:
    layout = [
        ("SPI3", "NDVI", "#1B5E20", "Meteorological driver to vegetation state"),
        ("SPI3", "NSMI", "#4E342E", "Meteorological driver to soil moisture"),
        ("NSMI", "VCI", "#00695C", "Soil moisture to vegetation condition"),
        ("SPI3", C.CDI_COLUMN, "#6E1423", "Rainfall anomaly to composite drought score"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14.6, 12.0))
    results = []
    for ax, (xcol, ycol, color, title) in zip(axes.ravel(), layout):
        if xcol not in panel.columns or ycol not in panel.columns:
            ax.axis("off")
            continue
        res = _scatter_with_fit(ax, panel, xcol, ycol, color)
        ax.set_title(f"{title}\n{C.COL[xcol].short} vs {C.COL[ycol].short}", fontsize=10.5)
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
    sub = sub.assign(**{c: sub[c] for c in columns})

    grid = sns.pairplot(
        sub,
        vars=columns,
        hue="dclass",
        hue_order=[c for c in C.CLASS_ORDER if c in sub["dclass"].unique()],
        palette={k: v for k, v in C.DROUGHT_COLORS.items()},
        corner=True,
        diag_kind="kde",
        plot_kws={"s": 9, "alpha": 0.45, "linewidth": 0},
        diag_kws={"linewidth": 1.2, "common_norm": False},
    )
    grid.fig.set_size_inches(13.5, 12.0)
    grid.fig.suptitle(
        "Pairwise scatter matrix of the five CDI inputs and the composite, coloured by drought class\n"
        f"Random sample of {len(sub):,} village-months for legibility",
        fontsize=13, y=1.01,
    )
    grid.add_legend(title="Drought class", bbox_to_anchor=(0.82, 0.62))
    if grid.legend is not None:
        for text in grid.legend.get_texts():
            text.set_text(C.D_CLASS_LABELS.get(text.get_text(), text.get_text()))
    grid.fig.tight_layout()
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
    drivers = [c for c in ("SPI1", "SPI3", "SPI6") if c in panel.columns]
    responses = [c for c in ("NDVI", "VCI", "NSMI") if c in panel.columns]
    max_lag = 6

    tables = []
    fig, axes = plt.subplots(1, len(responses), figsize=(5.2 * len(responses), 5.0))
    axes = np.atleast_1d(axes)
    colors = {"SPI1": "#7FB3D5", "SPI3": "#1F6FB2", "SPI6": "#0B3C5D"}

    for ax, response in zip(axes, responses):
        for driver in drivers:
            table = S.lag_correlation(panel, driver, response, max_lag=max_lag)
            table["response"] = response
            tables.append(table)
            ax.plot(table["lag_months"], table["r"], marker="o", ms=4.5, lw=1.9,
                    color=colors.get(driver, "#555555"), label=driver)
            sig = table[table["p"] < 0.05]
            ax.scatter(sig["lag_months"], sig["r"], s=52, facecolor="none",
                       edgecolor=colors.get(driver, "#555555"), linewidth=1.6)
            peak = table.loc[table["r"].abs().idxmax()]
            ST.annotate_max(ax, peak["lag_months"], peak["r"],
                            f"{driver} peak lag {int(peak['lag_months'])} mo",
                            color=colors.get(driver, "#555555"))

        ax.axhline(0, color="#555555", lw=0.8)
        ax.set_xlabel("Lag (months) from driver to response")
        ax.set_ylabel("Pooled correlation coefficient")
        ax.set_title(f"Response: {C.COL[response].short}", fontsize=10.5)
        ax.set_xticks(range(0, max_lag + 1))
        ax.grid(alpha=0.4)
        ax.legend(title="Driver", loc="lower left")

    fig.suptitle(
        "Response lag: how many months vegetation and soil moisture trail rainfall\n"
        "Hollow markers are significant at p < 0.05; the annotated point is each driver's peak",
        fontsize=13,
    )
    ST.save(
        fig, "relationships", "r5_response_lag.png",
        "Pooled lagged correlations of SPI-1/3/6 against NDVI, VCI and NSMI for lags of zero to six months.",
        source="village_with_baseline.csv",
    )
    return pd.concat(tables, ignore_index=True)


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
    sub = panel[["VCI", "VHI"]].dropna()
    if not sub.empty:
        plot = sub.sample(n=min(24000, len(sub)), random_state=5)
        ax.scatter(plot["VCI"], plot["VHI"], s=5, color="#00695C", alpha=0.3, linewidths=0,
                   rasterized=True)
        res = S.ols(sub["VCI"], sub["VHI"])
        xs = np.linspace(plot["VCI"].min(), plot["VCI"].max(), 50)
        ax.plot(xs, res["intercept"] + res["slope"] * xs, color="#C23B22", lw=1.8)
        ax.plot(xs, xs, color="#111111", ls=":", lw=1.0, label="1:1")
        ax.set_xlabel("VCI (%)")
        ax.set_ylabel("VHI (%)")
        ax.set_title("VCI and VHI diverge where thermal stress enters", fontsize=10)
        ax.legend(loc="upper left")
        ax.grid(alpha=0.35)
        ST.stats_box(ax, [f"n = {res['n']:,}", f"r = {res['r']:+.3f}", f"slope = {res['slope']:+.3f}"],
                     loc="lower right")

    ax = axes[2]
    sub = panel[["NDVI", "EVI"]].dropna()
    if not sub.empty:
        res = S.ols(sub["NDVI"], sub["EVI"])
        resid = sub["EVI"] - (res["intercept"] + res["slope"] * sub["NDVI"])
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
    ST.save(
        fig, "relationships", "r6_index_agreement.png",
        "NDVI/EVI agreement, VCI/VHI agreement and the NDVI-EVI residual distribution.",
        source="village_with_baseline.csv",
    )
    if sub.empty:
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
