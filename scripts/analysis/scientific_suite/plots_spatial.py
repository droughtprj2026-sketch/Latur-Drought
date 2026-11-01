# -*- coding: utf-8 -*-
"""Section 07 - spatial pattern across villages and tehsils."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import TwoSlopeNorm

from . import config as C
from . import data as D
from . import stats as S
from . import style as ST


def _draw_villages(ax, gdf, column: str, cmap, norm=None, vmin=None, vmax=None,
                   cbar_label: str = "", title: str = "", edge: str = "#8A8A8A",
                   linewidth: float = 0.12) -> None:
    district = D.load_district()
    tehsils = D.load_tehsils()

    gdf.plot(
        column=column, ax=ax, cmap=cmap,
        norm=norm, vmin=vmin if norm is None else None, vmax=vmax if norm is None else None,
        edgecolor=edge, linewidth=linewidth,
        missing_kwds={"color": "#E4E4E4", "edgecolor": "#CACACA", "linewidth": 0.1,
                      "label": "No data"},
        legend=True,
        legend_kwds={"label": cbar_label, "orientation": "horizontal", "shrink": 0.62,
                     "pad": 0.02, "aspect": 38},
    )

    if tehsils is not None:
        tehsils.boundary.plot(ax=ax, color="#263238", linewidth=0.85)
        for _, row in tehsils.iterrows():
            if row.geometry is None or row.geometry.is_empty:
                continue
            point = row.geometry.representative_point()
            name = str(row.get("TEHSIL", ""))
            ax.text(
                point.x, point.y, name.upper(), fontsize=6.4, weight="bold", color="#1A1A1A",
                ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.0, foreground="white")],
            )
    if district is not None:
        district.boundary.plot(ax=ax, color="#000000", linewidth=1.5)

    ax.set_title(title, fontsize=11)
    ax.set_axis_off()


def _merge(gdf, frame: pd.DataFrame, value: str) -> "pd.DataFrame":
    out = gdf.merge(frame, left_on="id", right_on="village_idx", how="left")
    if value not in out.columns:
        out[value] = np.nan
    return out


# --------------------------------------------------------------------------
# 1. Mean CDI
# --------------------------------------------------------------------------
def fig_village_mean_cdi(panel: pd.DataFrame) -> pd.DataFrame:
    gdf = D.load_villages()
    stats_v = (
        panel.dropna(subset=[C.CDI_COLUMN])
        .groupby("village_idx")[C.CDI_COLUMN]
        .agg(mean="mean", count="size", p90=lambda s: s.quantile(0.90))
        .reset_index()
    )
    stats_v = stats_v[stats_v["count"] >= 12]
    if stats_v.empty:
        return stats_v
    merged = _merge(gdf, stats_v, "mean")

    fig, ax = plt.subplots(figsize=(12.2, 10.2))
    _draw_villages(
        ax, merged, "mean", ST.CDI_CMAP,
        vmin=0.0, vmax=float(min(0.75, np.nanpercentile(stats_v["mean"], 98))),
        cbar_label="Ten-year mean CDI",
        title="Ten-year mean Composite Drought Index by village",
    )
    annotated = merged.dropna(subset=["mean"]).nlargest(5, "mean")
    for _, row in annotated.iterrows():
        point = row.geometry.representative_point()
        ax.annotate(
            f"{row.get('village_name', row.get('village', ''))}\n{row['mean']:.2f}",
            xy=(point.x, point.y), xytext=(8, 6), textcoords="offset points",
            fontsize=6.6, color="#4A0E14",
            arrowprops=dict(arrowstyle="-", color="#4A0E14", lw=0.7),
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#4A0E14", lw=0.5, alpha=0.9),
        )

    fig.suptitle(
        "Spatial distribution of drought exposure, 954 villages\n"
        "The five most exposed villages are labelled; grey polygons have too few observations",
        fontsize=13,
    )
    ST.figure_note(fig, "Villages with fewer than 12 scored months are treated as no data, not as zero.", y=0.06)
    ST.save(
        fig, "spatial", "s1_village_mean_cdi.png",
        "Choropleth of ten-year mean CDI per village with the most exposed villages labelled.",
        source="village_with_baseline.csv + latur_villages_latest.geojson",
    )
    return stats_v


# --------------------------------------------------------------------------
# 2. Village-level coupling
# --------------------------------------------------------------------------
def fig_village_correlation(panel: pd.DataFrame) -> pd.DataFrame:
    gdf = D.load_villages()
    rows = []
    for village, sub in panel.groupby("village_idx"):
        r, p, n = S.pearson(sub["SPI3"], sub["NDVI"])
        rows.append({"village_idx": village, "r_spi3_ndvi": r, "p": p, "n": n})
    frame = pd.DataFrame(rows)
    frame.loc[frame["n"] < C.MIN_PAIRS_VILLAGE, "r_spi3_ndvi"] = np.nan
    if frame["r_spi3_ndvi"].notna().sum() == 0:
        return frame

    merged = _merge(gdf, frame, "r_spi3_ndvi")
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(16.2, 8.4), gridspec_kw={"width_ratios": [1.45, 1]}
    )
    _draw_villages(
        ax, merged, "r_spi3_ndvi", "RdBu_r",
        norm=TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0),
        cbar_label="Pearson r (SPI-3 vs NDVI)",
        title="Village-level coupling of vegetation to rainfall",
    )

    values = frame["r_spi3_ndvi"].dropna()
    ax2.hist(values, bins=48, color="#17405F", alpha=0.85, edgecolor="white", linewidth=0.4)
    ax2.axvline(values.mean(), color="#C23B22", lw=1.6, ls="--",
                label=f"mean r = {values.mean():+.2f}")
    ax2.axvline(0, color="#333333", lw=0.9)
    ax2.set_xlabel("Pearson r (SPI-3 vs NDVI), one value per village")
    ax2.set_ylabel("Villages")
    ax2.set_title("Distribution of the coupling strength", fontsize=10.5)
    ax2.legend(loc="upper left")
    ax2.grid(axis="y", alpha=0.35)
    ax2.text(0.98, 0.96,
             f"villages = {len(values)}\npositive r = {100 * (values > 0).mean():.0f}%\n"
             f"negative r = {100 * (values < 0).mean():.0f}%",
             transform=ax2.transAxes, ha="right", va="top", fontsize=8, family="monospace",
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#CCCCCC", lw=0.6, alpha=0.92))

    fig.suptitle(
        "Where does vegetation actually follow rainfall\n"
        f"Per-village Pearson correlation, villages with at least {C.MIN_PAIRS_VILLAGE} overlapping months",
        fontsize=13,
    )
    ST.save(
        fig, "spatial", "s2_village_spi_ndvi_correlation.png",
        "Village choropleth and histogram of the SPI-3 vs NDVI Pearson correlation.",
        source="village_with_baseline.csv + latur_villages_latest.geojson",
    )
    return frame


# --------------------------------------------------------------------------
# 3. Village trend
# --------------------------------------------------------------------------
def fig_village_trend(panel: pd.DataFrame) -> pd.DataFrame:
    gdf = D.load_villages()
    annual = (
        panel.dropna(subset=[C.CDI_COLUMN])
        .pivot_table(index="village_idx", columns="year", values=C.CDI_COLUMN, aggfunc="mean")
    )
    rows = []
    for village, series in annual.iterrows():
        y = series.dropna()
        if len(y) < 5:
            rows.append({"village_idx": village, "slope": np.nan, "p": np.nan, "n_years": len(y)})
            continue
        ss = S.sens_slope(y.to_numpy(), index=y.index.to_numpy())
        mk = S.mann_kendall(y.to_numpy())
        rows.append({"village_idx": village, "slope": ss["slope"], "p": mk["p"], "n_years": len(y)})
    frame = pd.DataFrame(rows)
    if frame["slope"].notna().sum() == 0:
        return frame

    merged = _merge(gdf, frame, "slope")
    limit = float(np.nanpercentile(np.abs(frame["slope"].dropna()), 96))
    limit = max(limit, 1e-4)

    fig, ax = plt.subplots(figsize=(12.2, 10.2))
    _draw_villages(
        ax, merged, "slope", "RdBu_r",
        norm=TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit),
        cbar_label="Sen's slope of annual mean CDI (per year)",
        title="Direction of change in village drought stress",
    )
    fig.suptitle(
        "Is drought stress rising or falling, village by village\n"
        "Red is a drying trend (CDI rising), blue is recovery; values beyond the 96th percentile are clipped",
        fontsize=13,
    )
    ST.figure_note(fig, "Symmetric colour scale about zero so the sign is never implied by the ramp.", y=0.06)
    ST.save(
        fig, "spatial", "s3_village_trend.png",
        "Choropleth of Sen's slope of annual mean CDI per village.",
        source="village_with_baseline.csv + latur_villages_latest.geojson",
    )
    return frame


# --------------------------------------------------------------------------
# 4. Annual atlas
# --------------------------------------------------------------------------
def fig_annual_atlas(panel: pd.DataFrame) -> None:
    gdf = D.load_villages()
    annual = panel.dropna(subset=[C.CDI_COLUMN]).groupby(["village_idx", "year"])[C.CDI_COLUMN].mean().reset_index()
    years = sorted(panel["year"].unique())
    ncols = 4
    nrows = int(np.ceil(len(years) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(4.4 * ncols, 4.1 * nrows))
    axes = np.atleast_1d(axes).ravel()
    vmax = float(np.nanpercentile(annual[C.CDI_COLUMN], 97))

    for ax, year in zip(axes, years):
        subset = annual[annual["year"] == year]
        merged = _merge(gdf, subset.rename(columns={"village_idx": "village_idx"}), C.CDI_COLUMN)
        merged.plot(
            column=C.CDI_COLUMN, ax=ax, cmap=ST.CDI_CMAP, vmin=0.0, vmax=vmax,
            edgecolor="none", missing_kwds={"color": "#E4E4E4"},
        )
        tehsils = D.load_tehsils()
        if tehsils is not None:
            tehsils.boundary.plot(ax=ax, color="#37474F", linewidth=0.55)
        mean_value = float(subset[C.CDI_COLUMN].mean()) if not subset.empty else np.nan
        ax.set_title(f"{year}   mean CDI {mean_value:.2f}", fontsize=9.5)
        ax.set_axis_off()

    for ax in axes[len(years):]:
        ax.axis("off")

    sm = plt.cm.ScalarMappable(cmap=ST.CDI_CMAP, norm=plt.Normalize(0.0, vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes.tolist(), orientation="horizontal", fraction=0.025, pad=0.025, aspect=45)
    cbar.set_label("Annual mean CDI", weight="bold", fontsize=10)

    fig.suptitle(
        "Annual drought severity atlas, one panel per year\n"
        "Grey villages have no scored month in that year",
        fontsize=14, y=0.995,
    )
    ST.save(
        fig, "spatial", "s4_annual_drought_atlas.png",
        "Small-multiple annual choropleths of mean village CDI.",
        source="village_with_baseline.csv + latur_villages_latest.geojson",
    )


# --------------------------------------------------------------------------
# 5. Tehsil vulnerability ranking
# --------------------------------------------------------------------------
def fig_tehsil_vulnerability(panel: pd.DataFrame) -> pd.DataFrame:
    scored = panel[panel["dclass"].isin(C.CLASS_ORDER)].copy()
    scored["is_drought"] = scored["dclass"].isin(C.DROUGHT_CODES)

    tehsil_stats = scored.groupby("tehsil").agg(
        mean_cdi=(C.CDI_COLUMN, "mean"),
        drought_frequency=("is_drought", "mean"),
        mean_ndvi=("NDVI", "mean"),
        mean_spi3=("SPI3", "mean"),
    )
    tehsil_stats["drought_frequency"] *= 100.0

    annual = (
        panel.dropna(subset=[C.CDI_COLUMN])
        .pivot_table(index="year", columns="tehsil", values=C.CDI_COLUMN, aggfunc="mean")
    )
    slopes = {}
    for tehsil in annual.columns:
        y = annual[tehsil].dropna()
        slopes[tehsil] = S.sens_slope(y.to_numpy(), index=y.index.to_numpy())["slope"] if len(y) >= 5 else np.nan
    tehsil_stats["cdi_trend"] = pd.Series(slopes)

    def _z(series: pd.Series) -> pd.Series:
        sd = series.std(ddof=0)
        return (series - series.mean()) / sd if sd and np.isfinite(sd) else series * 0.0

    # Transparent composite: mean CDI, drought frequency and drying trend, equally weighted z-scores.
    tehsil_stats["vulnerability"] = (
        _z(tehsil_stats["mean_cdi"]) + _z(tehsil_stats["drought_frequency"]) + _z(tehsil_stats["cdi_trend"])
    ) / 3.0
    tehsil_stats = tehsil_stats.sort_values("vulnerability", ascending=False).reset_index()

    gdf = D.load_villages().merge(
        tehsil_stats[["tehsil", "vulnerability"]], left_on="tehsil_name", right_on="tehsil", how="left"
    )

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(16.4, 7.8), gridspec_kw={"width_ratios": [1, 1.15]}
    )

    y = np.arange(len(tehsil_stats))[::-1]
    colors = ST.CDI_CMAP(
        (tehsil_stats["vulnerability"] - tehsil_stats["vulnerability"].min())
        / max(np.ptp(tehsil_stats["vulnerability"].to_numpy()), 1e-9)
    )
    ax.barh(y, tehsil_stats["vulnerability"], color=colors, edgecolor="#333333", linewidth=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(tehsil_stats["tehsil"])
    ax.axvline(0, color="#333333", lw=0.9)
    ax.set_xlabel("Vulnerability score (mean of three z-scores)")
    ax.set_title("Tehsil drought vulnerability ranking", fontsize=10.5)
    ax.grid(axis="x", alpha=0.35)
    for yi, (_, row) in zip(y, tehsil_stats.iterrows()):
        offset = 0.03 if row["vulnerability"] >= 0 else -0.03
        ax.text(row["vulnerability"] + offset, yi,
                f"CDI {row['mean_cdi']:.2f}  |  {row['drought_frequency']:.0f}%",
                va="center", ha="left" if offset > 0 else "right", fontsize=7.4, color="#333333")

    merged = gdf.merge(tehsil_stats, on="tehsil", how="left")
    merged.plot(
        column="vulnerability", ax=ax2, cmap=ST.CDI_CMAP,
        edgecolor="#8A8A8A", linewidth=0.12, legend=True,
        legend_kwds={"label": "Vulnerability score", "orientation": "horizontal",
                     "shrink": 0.7, "pad": 0.02},
    )
    tehsils = D.load_tehsils()
    if tehsils is not None:
        tehsils.boundary.plot(ax=ax2, color="#263238", linewidth=0.9)
        for _, row in tehsils.iterrows():
            point = row.geometry.representative_point()
            ax2.text(point.x, point.y, str(row.get("TEHSIL", "")).upper(), fontsize=6.4,
                     weight="bold", ha="center", va="center",
                     path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])
    district = D.load_district()
    if district is not None:
        district.boundary.plot(ax=ax2, color="#000000", linewidth=1.5)
    ax2.set_title("Same ranking, mapped", fontsize=10.5)
    ax2.set_axis_off()

    fig.suptitle(
        "Composite vulnerability: severity, frequency and direction of change together\n"
        "Score = mean of the z-scores of mean CDI, drought frequency and Sen's slope",
        fontsize=13,
    )
    ST.save(
        fig, "spatial", "s5_tehsil_vulnerability_ranking.png",
        "Tehsil vulnerability ranking and its choropleth, built from mean CDI, drought frequency and trend.",
        source="village_with_baseline.csv + latur_villages_latest.geojson",
    )

    out = tehsil_stats.copy()
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def build(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    mean_cdi = fig_village_mean_cdi(panel)
    corr = fig_village_correlation(panel)
    trend = fig_village_trend(panel)
    fig_annual_atlas(panel)
    vulnerability = fig_tehsil_vulnerability(panel)
    return {
        "village_mean_cdi": mean_cdi,
        "village_correlation": corr,
        "village_trend": trend,
        "tehsil_vulnerability": vulnerability,
    }
