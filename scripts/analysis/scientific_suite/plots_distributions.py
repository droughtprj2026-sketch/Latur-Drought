# -*- coding: utf-8 -*-
"""Section 05 - distributions and drought-class separation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from . import config as C
from . import data as D
from . import stats as S
from . import style as ST


def fig_index_distributions(panel: pd.DataFrame) -> None:
    specs = [s for s in C.INDEXES if s.column in panel.columns and panel[s.column].notna().any()]
    ncols = 4
    nrows = int(np.ceil(len(specs) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.1 * ncols, 3.2 * nrows))
    axes = np.atleast_1d(axes).ravel()

    for ax, spec in zip(axes, specs):
        values = panel[spec.column].dropna()
        if values.empty:
            ax.axis("off")
            continue
        ax.hist(values, bins=60, density=True, color=ST.cmap_for(spec.column)(0.55),
                edgecolor="white", linewidth=0.3)
        try:
            sns.kdeplot(values, ax=ax, color="#111111", lw=1.4)
        except Exception:
            pass
        mean, median = values.mean(), values.median()
        ax.axvline(mean, color="#C23B22", ls="--", lw=1.3, label=f"mean {mean:.2f}")
        ax.axvline(median, color="#17405F", ls=":", lw=1.3, label=f"median {median:.2f}")
        ax.set_title(f"{spec.short}", fontsize=10)
        ax.set_xlabel(f"{spec.unit}" if spec.unit != "-" else "value")
        ax.set_ylabel("density")
        ax.legend(fontsize=6.8, loc="upper right")
        ax.grid(axis="y", alpha=0.3)
        skew = float(values.skew())
        ax.text(0.02, 0.96, f"n={len(values):,}\nskew={skew:+.2f}", transform=ax.transAxes,
                va="top", fontsize=6.8, family="monospace", color="#444444")

    for ax in axes[len(specs):]:
        ax.axis("off")

    fig.suptitle(
        "Marginal distribution of every index over the full record\n"
        "Skew and multi-modality decide whether a mean is a fair summary",
        fontsize=13.5,
    )
    ST.save(
        fig, "distribution", "d1_index_distributions.png",
        "Histogram plus KDE for every index, with mean, median, n and skewness.",
        source="village_with_baseline.csv",
    )


def fig_monthly_climatology(panel: pd.DataFrame) -> None:
    columns = [("Rain_mm", "Monthly rainfall [mm]"), ("NDVI", "NDVI"),
               ("NSMI", "NSMI"), (C.CDI_COLUMN, "Composite Drought Index")]
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 10.0))
    for ax, (column, label) in zip(axes.ravel(), columns):
        if column not in panel.columns:
            ax.axis("off")
            continue
        sub = panel.dropna(subset=[column])
        sns.boxplot(
            data=sub, x="month", y=column, ax=ax, color=ST.cmap_for(column)(0.55),
            fliersize=1.2, linewidth=0.8, whis=1.5,
        )
        ax.set_xticks(range(12))
        ax.set_xticklabels(C.MONTHS, rotation=45, ha="right")
        ax.set_xlabel("")
        ax.set_ylabel(label)
        ax.set_title(f"{C.COL[column].label} by calendar month", fontsize=10)
        ax.grid(axis="y", alpha=0.35)

    wet, dry = D.season_months(panel)
    fig.suptitle(
        "Seasonal climatology and its dispersion\n"
        f"Wet season resolved from the rainfall record: {D.season_label(wet)}",
        fontsize=13,
    )
    ST.figure_note(
        fig,
        "Boxes are the interquartile range, whiskers 1.5 IQR. Wide boxes in the monsoon are cloud gaps, "
        "not real variability in every village.",
    )
    ST.save(
        fig, "distribution", "d2_monthly_climatology.png",
        "Monthly boxplots for rainfall, NDVI, NSMI and CDI showing the seasonal cycle and its spread.",
        source="village_with_baseline.csv",
    )


def fig_class_separation(panel: pd.DataFrame) -> pd.DataFrame:
    columns = [c for c in ("SPI3", "NSMI", "NDVI", "VCI", C.CDI_COLUMN) if c in panel.columns]
    scored = panel[panel["dclass"].isin(C.CLASS_ORDER)]

    fig, axes = plt.subplots(2, 3, figsize=(15.2, 9.4))
    axes = axes.ravel()
    rows = []

    for ax, column in zip(axes, columns):
        sub = scored.dropna(subset=[column])
        if sub.empty:
            ax.axis("off")
            continue
        sns.violinplot(
            data=sub, x="dclass", y=column, order=C.CLASS_ORDER,
            hue="dclass", hue_order=C.CLASS_ORDER, palette=C.DROUGHT_COLORS,
            cut=0, inner="quartile", linewidth=0.7, ax=ax, legend=False,
        )
        ax.set_xticks(range(len(C.CLASS_ORDER)))
        ax.set_xticklabels(C.CLASS_ORDER)
        ax.set_xlabel("")
        ax.set_ylabel(C.COL[column].label)
        ax.set_title(f"{C.COL[column].short} by drought class", fontsize=10)

        test = S.kruskal_by(sub, column, "dclass")
        ax.text(0.02, 0.97,
                f"Kruskal-Wallis\nH = {test['h']:.1f}\n{ST.p_text(test['p'])}",
                transform=ax.transAxes, va="top", fontsize=7.4, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#CCCCCC", lw=0.5, alpha=0.9))

        for code in C.CLASS_ORDER:
            values = sub.loc[sub["dclass"] == code, column]
            if len(values):
                rows.append({
                    "index": C.COL[column].short,
                    "class": code,
                    "n": int(len(values)),
                    "mean": round(float(values.mean()), 4),
                    "median": round(float(values.median()), 4),
                    "sd": round(float(values.std()), 4),
                    "p25": round(float(values.quantile(0.25)), 4),
                    "p75": round(float(values.quantile(0.75)), 4),
                    "kruskal_H": round(test["h"], 3),
                    "kruskal_p": test["p"],
                })

    # Sixth panel: class frequency, so the reader can see the sample behind each violin.
    ax = axes[len(columns)]
    counts = scored["dclass"].value_counts().reindex(C.CLASS_ORDER).fillna(0)
    bars = ax.bar(counts.index, counts.to_numpy(),
                  color=[C.DROUGHT_COLORS[c] for c in counts.index], edgecolor="#333333", linewidth=0.6)
    for bar, value in zip(bars, counts.to_numpy()):
        share = 100.0 * value / max(counts.sum(), 1)
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{int(value):,}\n{share:.1f}%",
                ha="center", va="bottom", fontsize=8)
    ax.set_title("Class frequency behind the violins", fontsize=10)
    ax.set_xlabel("Drought class")
    ax.set_ylabel("Village-months")
    ax.grid(axis="y", alpha=0.35)
    ax.set_ylim(0, counts.max() * 1.22 if counts.max() else 1)

    for ax in axes[len(columns) + 1:]:
        ax.axis("off")

    fig.suptitle(
        "Do the indices actually separate the drought classes\n"
        "Each violin is the distribution of one index inside a class; overlap is the residual uncertainty",
        fontsize=13,
    )
    ST.save(
        fig, "distribution", "d3_class_separation.png",
        "Violin plots of each index by drought class with Kruskal-Wallis tests, plus class frequencies.",
        source="village_with_baseline.csv",
    )
    return pd.DataFrame(rows)


def fig_village_variability(panel: pd.DataFrame) -> pd.DataFrame:
    scored = panel.dropna(subset=[C.CDI_COLUMN])
    stats_v = scored.groupby(["village_idx", "tehsil"])[C.CDI_COLUMN].agg(
        mean="mean", p25=lambda s: s.quantile(0.25), p75=lambda s: s.quantile(0.75),
        count="size",
    ).reset_index()
    stats_v = stats_v[stats_v["count"] >= 12]
    stats_v = stats_v.sort_values("mean").reset_index(drop=True)

    names = panel.drop_duplicates("village_idx").set_index("village_idx")["village"]
    stats_v["label"] = stats_v["village_idx"].map(names).fillna("").astype(str)
    stats_v["label"] = stats_v["label"] + " (" + stats_v["tehsil"].astype(str) + ")"

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(15.4, 7.4), gridspec_kw={"width_ratios": [1.35, 1]}
    )
    x = np.arange(len(stats_v))
    ax.fill_between(x, stats_v["p25"], stats_v["p75"], color="#90A4AE", alpha=0.55,
                    label="interquartile range")
    ax.plot(x, stats_v["mean"], color="#6E1423", lw=1.6, label="village mean CDI")
    ax.axhline(0.35, color="#F6BC63", ls="--", lw=1.1)
    ax.axhline(0.50, color="#E9822F", ls="--", lw=1.1)
    ax.text(0, 0.36, "D1", fontsize=7.5, color="#8D6E00")
    ax.text(0, 0.51, "D2", fontsize=7.5, color="#A0522D")
    ax.set_xlabel(f"Villages ranked by mean CDI (n = {len(stats_v)})")
    ax.set_ylabel("Composite Drought Index")
    ax.set_title("Ten-year mean CDI by village with its own interquartile band", fontsize=10.5)
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.35)

    top = stats_v.tail(14).iloc[::-1]
    bars = ax2.barh(np.arange(len(top)), top["mean"], color="#6E1423", alpha=0.9, edgecolor="white")
    ax2.set_yticks(np.arange(len(top)))
    ax2.set_yticklabels(top["label"], fontsize=8)
    ax2.set_xlabel("Mean CDI")
    ax2.set_title("The fourteen most drought-exposed villages", fontsize=10.5)
    ax2.grid(axis="x", alpha=0.35)
    for bar, value in zip(bars, top["mean"]):
        ax2.text(value + 0.005, bar.get_y() + bar.get_height() / 2, f"{value:.2f}",
                 va="center", fontsize=7.5)

    fig.suptitle(
        "Between-village inequality of drought exposure\n"
        "A district mean hides the range that decides where relief is targeted",
        fontsize=13,
    )
    ST.save(
        fig, "distribution", "d4_village_variability.png",
        "Village-level mean CDI ranked with its interquartile band, plus the fourteen worst-exposed villages.",
        source="village_with_baseline.csv",
    )
    return stats_v.drop(columns=["label"])


def fig_component_contributions(panel: pd.DataFrame) -> None:
    parsed = panel["component_contributions"].map(D.parse_contributions) if "component_contributions" in panel.columns else None
    if parsed is None:
        return
    components = ["SPI", "VCI", "NDVI", "NSMI"]
    frame = pd.DataFrame({c: parsed.map(lambda d, c=c: d.get(c, np.nan)) for c in components})
    frame = frame.dropna(how="all")
    if frame.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14.6, 5.4), gridspec_kw={"width_ratios": [1.3, 1]})

    ax = axes[0]
    data = [frame[c].dropna().to_numpy() for c in components]
    parts = ax.violinplot(data, showmedians=True, widths=0.85, showextrema=False)
    colors = ["#1F6FB2", "#2E7D32", "#66BB6A", "#8C6D31"]
    for body, color in zip(parts["bodies"], colors):
        body.set_facecolor(color)
        body.set_alpha(0.7)
        body.set_edgecolor("#333333")
    parts["cmedians"].set_color("#111111")
    ax.set_xticks(range(1, len(components) + 1))
    ax.set_xticklabels(components)
    ax.set_ylabel("Contribution to the composite score")
    ax.set_title("How much each component contributes when it is present", fontsize=10.5)
    ax.grid(axis="y", alpha=0.35)

    ax = axes[1]
    presence = frame.notna().mean() * 100.0
    bars = ax.barh(presence.index, presence.to_numpy(),
                   color=["#1F6FB2", "#2E7D32", "#66BB6A", "#8C6D31"], edgecolor="white")
    ax.set_xlim(0, 105)
    ax.set_xlabel("Village-months where the component contributed (%)")
    ax.set_title("Presence of each component", fontsize=10.5)
    ax.grid(axis="x", alpha=0.35)
    for bar, value in zip(bars, presence.to_numpy()):
        ax.text(value + 1, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", fontsize=8)

    fig.suptitle(
        "Decomposition of the composite drought index\n"
        "A component that is present less often is not a component that matters less when it is there",
        fontsize=13,
    )
    ST.figure_note(
        fig,
        "Contributions are the weighted, normalised signals recorded in component_contributions; "
        "weights come from config/composite.yaml.",
    )
    ST.save(
        fig, "distribution", "d5_component_contributions.png",
        "Distribution of each component's contribution to the CDI and its presence across village-months.",
        source="village_with_baseline.csv",
    )


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    fig_index_distributions(panel)
    fig_monthly_climatology(panel)
    separation = fig_class_separation(panel)
    variability = fig_village_variability(panel)
    fig_component_contributions(panel)
    return {"class_separation": separation, "village_variability": variability}
