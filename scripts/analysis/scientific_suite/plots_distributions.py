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
    columns = [
        ("Rain_mm", "Monthly Rainfall [mm]", "#0284C7", "a"),
        ("NDVI", "Vegetation Condition [NDVI]", "#16A34A", "b"),
        ("NSMI", "Soil Moisture Index [NSMI]", "#D97706", "c"),
        (C.CDI_COLUMN, "Composite Drought Index [CDI]", "#DC2626", "d"),
    ]

    # Pre-filter CDI for unobserved / all-zero months
    cdi_valid = panel.groupby("period")[C.CDI_COLUMN].apply(
        lambda s: s.notna().any() and not (s == 0.0).all() and (s == 0.0).mean() < 0.90
    )
    valid_cdi_periods = set(cdi_valid[cdi_valid].index)

    fig, axes = plt.subplots(2, 2, figsize=(15.5, 11.2), layout="constrained")

    months = np.arange(1, 13)
    month_names = C.MONTHS

    for ax, (column, label, base_color, tag) in zip(axes.ravel(), columns):
        if column not in panel.columns:
            ax.axis("off")
            continue

        if column == C.CDI_COLUMN:
            sub = panel[panel["period"].isin(valid_cdi_periods) & panel[column].notna()]
        else:
            sub = panel[panel[column].notna()]

        # Compute monthly percentiles across all years
        monthly_stats = sub.groupby("month")[column].quantile([0.10, 0.25, 0.50, 0.75, 0.90]).unstack()
        monthly_stats = monthly_stats.reindex(months)

        # Plot climatological envelopes
        ax.fill_between(
            months, monthly_stats[0.10], monthly_stats[0.90],
            color=base_color, alpha=0.15, label="10th–90th percentile envelope"
        )
        ax.fill_between(
            months, monthly_stats[0.25], monthly_stats[0.75],
            color=base_color, alpha=0.28, label="Interquartile Range (IQR)"
        )
        ax.plot(
            months, monthly_stats[0.50],
            color="#0F172A", lw=2.2, marker="o", ms=4.5, zorder=4, label="Historical Median"
        )

        # Compute benchmark trajectories (district-wide mean per month)
        for yr, yr_color, yr_ls, yr_m, yr_name in [
            (2018, "#DC2626", "--", "s", "2018 (Severe Drought)"),
            (2020, "#2563EB", "-.", "^", "2020 (Wet Surplus)"),
            (2024, "#9333EA", ":", "D", "2024 (Recent Year)"),
        ]:
            yr_sub = sub[sub["year"] == yr]
            if not yr_sub.empty:
                yr_mean = yr_sub.groupby("month")[column].mean().reindex(months)
                ax.plot(
                    months, yr_mean,
                    color=yr_color, ls=yr_ls, lw=1.8, marker=yr_m, ms=4.5,
                    zorder=5, label=yr_name
                )

        ax.set_xticks(months)
        ax.set_xticklabels(month_names, fontsize=9.5)
        ax.set_ylabel(label, fontsize=10.5, weight="bold")
        ax.set_title(f"({tag}) {label} Climatology & Benchmark Trajectories", fontsize=11.0, weight="bold")
        ax.grid(True, linestyle=":", color="#94A3B8", alpha=0.5)

        # Legend on top right of each panel
        ax.legend(loc="upper right" if column != "Rain_mm" else "upper left", fontsize=7.8, framealpha=0.92)

    fig.suptitle(
        "Phenological Climatology Envelopes with Benchmark Drought Overlays (2016–2026)\n"
        "Shaded envelopes represent historical variability (10th–90th percentile, IQR) vs key benchmark years",
        fontsize=13.0, weight="bold",
    )
    ST.figure_note(
        fig,
        "Notice the acute departure in 2018 during peak Kharif (July–October): rainfall collapsed below the 10th percentile, "
        "causing subsequent vegetation (NDVI) and soil moisture (NSMI) deficits, spiking the CDI above 0.40.",
    )
    ST.save(
        fig, "distribution", "d2_monthly_climatology.png",
        "Phenological climatology envelopes (10th-90th percentile, IQR) with benchmark drought overlays for 2018, 2020, and 2024.",
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
                transform=ax.transAxes, va="top", fontsize=8.0, fontfamily="serif")

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
    ST.figure_note(
        fig,
        "NDVI is not monotonic across classes: the monsoon months with high NDVI are cloudy and mostly "
        "unclassified, while the dry-season months that reach D3-D4 still carry standing crop. Read NDVI "
        "together with the month x year atlas, not on its own.",
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
        mean="mean", median="median", count="size",
        p10=lambda s: s.quantile(0.10), p90=lambda s: s.quantile(0.90),
    ).reset_index()
    stats_v = stats_v[stats_v["count"] >= 12]
    stats_v = stats_v.sort_values("mean").reset_index(drop=True)

    names = panel.drop_duplicates("village_idx").set_index("village_idx")["village"]
    stats_v["label"] = stats_v["village_idx"].map(names).fillna("").astype(str)
    stats_v["label"] = stats_v["label"] + " (" + stats_v["tehsil"].astype(str) + ")"

    district_mean = float(scored[C.CDI_COLUMN].mean())
    p10, p90 = stats_v["mean"].quantile([0.10, 0.90])

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(15.6, 7.4), gridspec_kw={"width_ratios": [1.25, 1]}, layout="constrained"
    )

    x = np.arange(len(stats_v))
    ax.plot(x, stats_v["mean"], color="#6E1423", lw=1.8, label="village mean CDI")
    ax.fill_between(x, stats_v["p10"], stats_v["p90"], color="#B0BEC5", alpha=0.45,
                    label="village p10-p90 of monthly CDI")
    ax.axhline(district_mean, color="#17405F", ls="--", lw=1.3,
               label=f"district mean {district_mean:.3f}")
    ax.axhspan(p10, p90, color="#6E1423", alpha=0.06)
    ax.text(len(stats_v) * 0.005, p90, "villages between the 10th and 90th percentile of exposure",
            fontsize=7.4, color="#4A0E14", va="bottom")

    top = stats_v.tail(14)
    ax.scatter(x[-14:], top["mean"], s=26, color="#4A0E14", zorder=4, label="top 14 villages")

    ax.set_xlabel(f"Villages ranked by mean CDI (n = {len(stats_v)})")
    ax.set_ylabel("Composite Drought Index")
    ax.set_title("Village-level distribution of drought exposure", fontsize=10.5, loc="left")
    ax.set_xlim(-8, len(stats_v) + 8)
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.35)

    top = top.iloc[::-1]
    y = np.arange(len(top))
    bars = ax2.barh(y, top["mean"], color="#6E1423", alpha=0.92, edgecolor="white", height=0.72)
    ax2.set_yticks(y)
    ax2.set_yticklabels(top["label"], fontsize=8)
    ax2.set_xlim(float(top["mean"].min()) * 0.90, float(top["mean"].max()) * 1.06)
    ax2.set_xlabel("Mean CDI (axis starts near the top-14 minimum)")
    ax2.set_title("The fourteen most drought-exposed villages", fontsize=10.5, loc="left")
    ax2.grid(axis="x", alpha=0.35)
    for bar, value in zip(bars, top["mean"]):
        ax2.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                 f"  {value:.4f}", va="center", fontsize=7.6, color="#333333")

    fig.suptitle(
        "Between-village inequality of drought exposure\n"
        "A district mean hides the range that decides where relief is targeted",
        fontsize=13,
    )
    ST.save(
        fig, "distribution", "d4_village_variability.png",
        "Ranked village mean CDI with per-village p10-p90 band, plus the fourteen most exposed villages.",
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


def fig_index_distribution_context(panel: pd.DataFrame, focus: str, out_name: str) -> dict:
    """Distribution of ONE index set against every other index.

    Three panels: the raw distribution with its own reference spans, the same
    distribution standardised and overlaid on all the others, and an ECDF
    comparison against the CDI components. This is the figure that answers
    "show me the distribution of NDVI together with all the indices".
    """
    if focus not in panel.columns or panel[focus].notna().sum() < 10:
        return {}

    spec = C.COL[focus]
    values = panel[focus].dropna()
    others = [s for s in C.INDEXES if s.column != focus and s.column in panel.columns
              and panel[s.column].notna().sum() > 10]

    fig = plt.figure(figsize=(15.6, 10.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 0.95], hspace=0.34, wspace=0.22)
    ax_raw = fig.add_subplot(gs[0, :])
    ax_z = fig.add_subplot(gs[1, 0])
    ax_ecdf = fig.add_subplot(gs[1, 1])

    # ---- Panel A: the focus distribution, raw -----------------------------
    color = ST.cmap_for(focus)(0.72)

    if spec.kind == "composite":
        from common import classify as _clf

        prev = 0.0
        for band in _clf.composite_thresholds():
            lo, hi = prev, float(band["max"])
            code = band["code"]
            ax_raw.axvspan(lo, hi, color=C.DROUGHT_COLORS[code], alpha=0.22, linewidth=0)
            if lo < values.max():
                ax_raw.text(min((lo + hi) / 2.0, values.max()), 0.965, code,
                            transform=ax_raw.get_xaxis_transform(),
                            ha="center", va="top", fontsize=8.5, weight="bold", color="#333333")
            prev = hi
    elif spec.kind == "spi":
        bands = [(-10.0, -2.0, "D4"), (-2.0, -1.6, "D3"), (-1.6, -1.3, "D2"),
                 (-1.3, -0.8, "D1"), (-0.8, -0.5, "D0")]
        for lo, hi, code in bands:
            ax_raw.axvspan(lo, hi, color=C.DROUGHT_COLORS[code], alpha=0.22, linewidth=0)
        ax_raw.axvspan(-0.5, float(values.max()) + 0.2,
                       color=C.DROUGHT_COLORS["None"], alpha=0.18, linewidth=0)

    ax_raw.hist(values, bins=70, density=True, color=color, alpha=0.72,
                edgecolor="white", linewidth=0.3)
    sns.kdeplot(values, ax=ax_raw, color="#111111", lw=1.9)

    mean, median = float(values.mean()), float(values.median())
    p10, p90 = values.quantile([0.10, 0.90])
    ax_raw.axvline(mean, color="#C23B22", ls="--", lw=1.5, label=f"mean {mean:.3f}")
    ax_raw.axvline(median, color="#17405F", ls=":", lw=1.5, label=f"median {median:.3f}")
    for q, lab in ((p10, "p10"), (p90, "p90")):
        ax_raw.axvline(q, color="#777777", ls="-.", lw=0.9)
        ax_raw.text(q, ax_raw.get_ylim()[1] * 0.02, lab, rotation=90, fontsize=7,
                    ha="right", va="bottom", color="#555555")

    ax_raw.set_xlabel(f"{spec.label} [{spec.unit}]" if spec.unit != "-" else spec.label)
    ax_raw.set_ylabel("probability density")
    ax_raw.set_title(f"{spec.short}: distribution over all {len(values):,} observed village-months",
                     fontsize=11.5, loc="left")
    lo_x = float(values.quantile(0.0005))
    hi_x = float(values.quantile(0.9995))
    if lo_x == hi_x:
        lo_x, hi_x = lo_x - 1.0, hi_x + 1.0
    ax_raw.set_xlim(lo_x, hi_x)
    ax_raw.legend(loc="upper right", bbox_to_anchor=(1.0, 0.86))
    ax_raw.grid(axis="y", alpha=0.3)

    summary = {
        "index": spec.short,
        "n": int(len(values)),
        "mean": round(mean, 4),
        "median": round(median, 4),
        "sd": round(float(values.std()), 4),
        "cv": round(float(values.std() / mean), 4) if mean else np.nan,
        "skew": round(float(values.skew()), 4),
        "kurtosis": round(float(values.kurtosis()), 4),
        "p10": round(float(p10), 4),
        "p90": round(float(p90), 4),
        "min": round(float(values.min()), 4),
        "max": round(float(values.max()), 4),
        "share_below_zero": round(float(100.0 * (values < 0).mean()), 2),
    }
    ST.stats_box(
        ax_raw,
        [f"n      = {summary['n']:,}", f"mean   = {summary['mean']:.3f}",
         f"median = {summary['median']:.3f}", f"sd     = {summary['sd']:.3f}",
         f"skew   = {summary['skew']:+.2f}"],
        loc="upper left",
    )

    # ---- Panel B: standardised overlay of every index ---------------------
    for spec_o in others:
        z = (panel[spec_o.column] - panel[spec_o.column].mean()) / panel[spec_o.column].std()
        z = z.dropna()
        if len(z) < 20:
            continue
        sns.kdeplot(z, ax=ax_z, color="#9E9E9E", lw=0.85, alpha=0.65, zorder=1)

    focus_z = ((values - mean) / values.std()).dropna()
    sns.kdeplot(focus_z, ax=ax_z, color=color, lw=2.8, zorder=3, label=f"{spec.short} (focus)")
    ax_z.axvline(0, color="#333333", lw=0.9)
    ax_z.set_xlim(-4, 4)
    ax_z.set_xlabel("standardised value (z-score)")
    ax_z.set_ylabel("density")
    ax_z.set_title("Same distribution against every other index, standardised", fontsize=10.5, loc="left")
    ax_z.legend(loc="upper right")
    ax_z.grid(alpha=0.3)
    ax_z.text(0.015, 0.03, "grey = the other ten indices", transform=ax_z.transAxes,
              fontsize=7.6, color="#555555")

    # ---- Panel C: ECDF against the CDI components -------------------------
    components = [c for c in ("SPI3", "NDVI", "VCI", "NSMI") if c in panel.columns]
    ordered = list(dict.fromkeys(components + [focus]))
    palette = plt.cm.viridis(np.linspace(0.1, 0.85, len(ordered)))
    for col, colr in zip(ordered, palette):
        v = panel[col].dropna()
        if len(v) < 20:
            continue
        # ECDF on the index's own 0-1 min-max scale so the panels are comparable.
        span = v.max() - v.min()
        scaled = (v - v.min()) / span if span else v * 0.0
        xs = np.sort(scaled.to_numpy())
        ys = np.arange(1, xs.size + 1) / xs.size * 100.0
        ax_ecdf.plot(xs, ys, lw=2.2 if col == focus else 1.3, color=colr,
                     label=C.COL[col].short, alpha=1.0 if col == focus else 0.8)
    ax_ecdf.set_xlabel("value rescaled to each index's own 0-1 range")
    ax_ecdf.set_ylabel("cumulative share of observations (%)")
    ax_ecdf.set_title("Empirical CDF against the CDI components", fontsize=10.5, loc="left")
    ax_ecdf.grid(alpha=0.3)
    ax_ecdf.legend(loc="lower right", ncol=2, fontsize=7.8)
    ax_ecdf.set_xlim(0, 1)

    fig.suptitle(
        f"Distribution of {spec.short} in the context of every index\n"
        f"{spec.label}: shape, spread and position relative to the rest of the record",
        fontsize=13.5,
    )
    ST.save(
        fig, "distribution", out_name,
        f"Distribution of {spec.short} against all other indices: raw density, standardised overlay and ECDF.",
        source="village_with_baseline.csv",
    )
    return summary


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    fig_index_distributions(panel)
    fig_monthly_climatology(panel)
    separation = fig_class_separation(panel)
    variability = fig_village_variability(panel)
    fig_component_contributions(panel)

    # One full "this index against all the others" figure per index, with the
    # composite and NDVI written first because they are the headline products.
    priority = [C.CDI_COLUMN, "NDVI"]
    ordered = priority + [s.column for s in C.INDEXES if s.column not in priority]
    summaries = []
    for column in ordered:
        spec = C.COL.get(column)
        if spec is None:
            continue
        summary = fig_index_distribution_context(
            panel, column, f"per_index/d6_distribution_{spec.short}.png"
        )
        if summary:
            summaries.append(summary)

    return {
        "class_separation": separation,
        "village_variability": variability,
        "distribution_summary": pd.DataFrame(summaries),
    }
