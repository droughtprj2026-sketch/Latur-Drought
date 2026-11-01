# -*- coding: utf-8 -*-
"""Data loading and derived sampling-availability tables.

All counts are derived from the panel; nothing about the study period, the
tehsil list or the calendar is hard-coded (see AGENTS.md section 2).
"""
from __future__ import annotations

import json
from functools import lru_cache

import geopandas as gpd
import numpy as np
import pandas as pd

from . import config as C


# --------------------------------------------------------------------------
# Authoritative continuous SPI & Rainfall loader
# --------------------------------------------------------------------------
def load_authoritative_spi() -> pd.DataFrame:
    """Load the full 129-month continuous CHIRPS rainfall & SPI tables from output/spi/csv/."""
    if not C.SPI_DIR.exists():
        return pd.DataFrame()

    spi_dfs = {}
    for k in (1, 3, 6, 12):
        p = C.SPI_DIR / f"SPI{k}_village_monthly.csv"
        if p.exists():
            df = pd.read_csv(p, encoding="utf-8-sig")
            date_cols = [c for c in df.columns if len(c) == 7 and c[4] == "-"]
            long = df.melt(id_vars=["vid"], value_vars=date_cols, var_name="date", value_name=f"SPI{k}")
            long["village_idx"] = long["vid"].astype(int) + 1
            spi_dfs[k] = long[["village_idx", "date", f"SPI{k}"]]

    if C.RAIN_CSV.exists():
        rain_df = pd.read_csv(C.RAIN_CSV, encoding="utf-8-sig")
        rain_dates = [c for c in rain_df.columns if len(c) == 7 and c[4] == "-"]
        rain_long = rain_df.melt(id_vars=["vid"], value_vars=rain_dates, var_name="date", value_name="Rain_mm")
        rain_long["village_idx"] = rain_long["vid"].astype(int) + 1
        spi_merged = rain_long[["village_idx", "date", "Rain_mm"]]
    else:
        spi_merged = pd.DataFrame(columns=["village_idx", "date", "Rain_mm"])

    for k in (1, 3, 6, 12):
        if k in spi_dfs:
            spi_merged = spi_merged.merge(spi_dfs[k], on=["village_idx", "date"], how="outer")

    return spi_merged


# --------------------------------------------------------------------------
# Panel
# --------------------------------------------------------------------------
def load_panel() -> pd.DataFrame:
    """Village x month panel with continuous SPI from output/spi/csv/ and valid period index."""
    if not C.PANEL_CSV.exists():
        raise SystemExit(
            f"Missing panel: {C.PANEL_CSV}\n"
            "Build it first: python scripts/analysis/build_baseline_drought.py"
        )

    numeric = [spec.column for spec in C.INDEXES]
    df = pd.read_csv(C.PANEL_CSV, low_memory=False)

    # Reconcile with authoritative continuous SPI & Rainfall from output/spi/csv
    spi_auth = load_authoritative_spi()
    if not spi_auth.empty:
        vmap = df[["village_idx", "village", "tehsil"]].dropna().drop_duplicates("village_idx").set_index("village_idx")
        spi_cols = [c for c in ("Rain_mm", "SPI1", "SPI3", "SPI6", "SPI12") if c in df.columns]
        df_base = df.drop(columns=spi_cols)
        df = pd.merge(df_base, spi_auth, on=["village_idx", "date"], how="outer")

        missing_v = df["village"].isna()
        if missing_v.any():
            df.loc[missing_v, "village"] = df.loc[missing_v, "village_idx"].map(vmap["village"])
            df.loc[missing_v, "tehsil"] = df.loc[missing_v, "village_idx"].map(vmap["tehsil"])
            df.loc[missing_v, "name"] = df.loc[missing_v, "village"]
            dt = pd.to_datetime(df.loc[missing_v, "date"], format="%Y-%m")
            df.loc[missing_v, "year"] = dt.dt.year
            df.loc[missing_v, "month"] = dt.dt.month

        # Months whose optical inputs are missing but whose rainfall is published
        # (monsoon cloud) are scored by the official scorer with the remaining
        # components re-weighted, exactly as config/composite.yaml's
        # `min_inputs: 1` specifies. Never invent a score with an ad-hoc formula.
        score_inputs = [c for c in ("SPI3", "NDVI", "VCI", "NSMI") if c in df.columns]
        needs_score = df[C.CDI_COLUMN].isna() & df[score_inputs].notna().any(axis=1)
        if needs_score.any():
            from common import village_cdi

            cfg = village_cdi._load_cfg()
            tmp = df.copy()
            tmp["period"] = tmp["date"].astype(str)
            scored = village_cdi.fuse_cdi(tmp, cfg)
            for column in (C.CDI_COLUMN, "component_contributions", "formula_version"):
                if column in scored.columns:
                    df.loc[needs_score, column] = scored.loc[needs_score, column].to_numpy()

    df["date"] = df["date"].astype(str)
    df["period"] = pd.PeriodIndex(df["date"], freq="M")
    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)

    # Drought class: derived from the score with the thresholds in config/composite.yaml
    if C.CDI_COLUMN in df.columns:
        df["dclass"] = classify_scores(df[C.CDI_COLUMN].to_numpy(dtype=float))

    df["tehsil"] = df["tehsil"].astype(str)
    return df


def study_periods(df: pd.DataFrame) -> pd.PeriodIndex:
    """Every calendar month spanned by the study, including months with no rows."""
    return pd.period_range(df["period"].min(), df["period"].max(), freq="M")


def period_frame(df: pd.DataFrame) -> pd.DataFrame:
    periods = study_periods(df)
    return pd.DataFrame(
        {"period": periods, "year": periods.year.to_numpy(), "month": periods.month.to_numpy()}
    )


def classify_scores(values: np.ndarray) -> np.ndarray:
    """Map CDI scores to D-codes using config/composite.yaml, vectorised."""
    bands = C.classify.composite_thresholds()
    edges = [-np.inf] + [float(b["max"]) for b in bands]
    labels = [b["code"] for b in bands]
    codes = pd.cut(values, bins=edges, labels=labels, right=False)
    out = pd.Series(codes, index=None).astype(object)
    out[~np.isfinite(values)] = "ND"
    return out.to_numpy()


def n_villages(df: pd.DataFrame) -> int:
    return int(df["village_idx"].nunique())


def villages_per_tehsil(df: pd.DataFrame) -> pd.Series:
    return df.drop_duplicates("village_idx").groupby("tehsil")["village_idx"].nunique()


def months_per_year(df: pd.DataFrame) -> pd.Series:
    pf = period_frame(df)
    return pf.groupby("year").size()


def time_span_label(df: pd.DataFrame) -> str:
    lo, hi = df["period"].min(), df["period"].max()
    return f"{lo.year}-{hi.year}" if lo.year != hi.year else str(lo.year)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_villages() -> gpd.GeoDataFrame:
    """Village polygons keyed by ``id`` (== ``village_idx`` in the panel)."""
    path = C.VILLAGE_GEOJSON if C.VILLAGE_GEOJSON.exists() else C.FALLBACK_VILLAGE_GEOJSON
    if not path.exists():
        raise SystemExit(f"Missing village geometry: {C.VILLAGE_GEOJSON}")
    gdf = gpd.read_file(path)
    if "id" not in gdf.columns:
        # Fallback file carries no id: the polygon order matches village_idx 1..N.
        gdf = gdf.reset_index(drop=True)
        gdf["id"] = np.arange(1, len(gdf) + 1)
    gdf["id"] = gdf["id"].astype(int)
    gdf = gdf.rename(columns={"VILLAGE": "village_name", "TEHSIL": "tehsil_name"})
    return gdf.to_crs(4326)


@lru_cache(maxsize=1)
def load_tehsils() -> gpd.GeoDataFrame | None:
    if not C.TEHSIL_GEOJSON.exists():
        return None
    gdf = gpd.read_file(C.TEHSIL_GEOJSON)
    return gdf.to_crs(4326)


@lru_cache(maxsize=1)
def load_district() -> gpd.GeoDataFrame | None:
    if not C.DISTRICT_GEOJSON.exists():
        return None
    return gpd.read_file(C.DISTRICT_GEOJSON).to_crs(4326)


def district_name() -> str:
    try:
        names = sorted({str(v) for v in load_villages()["DISTRICT"].dropna().unique()})
    except Exception:  # pragma: no cover - geometry optional for non-map figures
        names = []
    return ", ".join(names) if names else "Study area"


# --------------------------------------------------------------------------
# Sampling availability
# --------------------------------------------------------------------------
def availability_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Coverage % of one source, per (tehsil, year).

    Coverage = observed village-months with a valid value, divided by
    (villages in the tehsil x months in that year inside the study window).
    A month with no rows at all therefore counts as missing, which is the
    honest denominator for "how much of the period did we actually observe".
    """
    if column not in df.columns:
        return pd.DataFrame()

    vill = villages_per_tehsil(df)
    mpy = months_per_year(df)
    years = sorted(df["year"].unique())
    tehsils = sorted(df["tehsil"].unique())

    idx = pd.MultiIndex.from_product([tehsils, years], names=["tehsil", "year"])
    expected = pd.Series(
        [vill[t] * mpy.get(y, 0) for t, y in idx], index=idx, dtype="float64"
    )

    observed = df[df[column].notna()].groupby(["tehsil", "year"]).size().reindex(idx, fill_value=0)
    pct = (100.0 * observed / expected.where(expected > 0)).rename("pct")
    out = pd.concat([observed.rename("observed"), expected.rename("expected"), pct], axis=1)
    return out.reset_index()


def availability_matrix(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Coverage % per (tehsil, year) as a pivot, rows ordered by overall coverage."""
    table = availability_table(df, column)
    if table.empty:
        return pd.DataFrame()
    wide = table.pivot(index="tehsil", columns="year", values="pct").clip(upper=100)
    order = wide.mean(axis=1).sort_values(ascending=False).index
    return wide.loc[order]


def availability_by_month(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Coverage % per (year, month) across the whole extent, as a month x year grid."""
    if column not in df.columns:
        return pd.DataFrame()
    total = n_villages(df)
    observed = df[df[column].notna()].groupby(["year", "month"]).size()
    pct = 100.0 * observed / total
    grid = pct.unstack("year").reindex(index=C.MONTH_NUMBERS, columns=sorted(df["year"].unique()))
    return grid.clip(upper=100)


def annual_availability(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Per year: share of months observed, and share of village-months covered."""
    if column not in df.columns:
        return pd.DataFrame()
    mpy = months_per_year(df)
    total = n_villages(df)
    rows = []
    for year in sorted(df["year"].unique()):
        expected_months = int(mpy.get(year, 0))
        sub = df[(df["year"] == year) & df[column].notna()]
        months_seen = int(sub["month"].nunique())
        village_months = len(sub)
        rows.append(
            {
                "year": year,
                "months_observed": months_seen,
                "months_expected": expected_months,
                "month_pct": 100.0 * months_seen / expected_months if expected_months else np.nan,
                "village_month_pct": 100.0 * village_months / (total * expected_months)
                if expected_months
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def source_availability_summary(df: pd.DataFrame, sources: dict[str, str]) -> pd.DataFrame:
    """One row per source: overall coverage, and per-tehsil min/max."""
    rows = []
    for label, column in sources.items():
        table = availability_table(df, column)
        if table.empty:
            continue
        total_obs = table["observed"].sum()
        total_exp = table["expected"].sum()
        per_tehsil = table.groupby("tehsil")["pct"].mean()
        rows.append(
            {
                "source": label,
                "column": column,
                "coverage_pct": round(100.0 * total_obs / total_exp, 2) if total_exp else np.nan,
                "tehsil_min_pct": round(float(per_tehsil.min()), 2),
                "tehsil_max_pct": round(float(per_tehsil.max()), 2),
                "tehsil_spread_pct": round(float(per_tehsil.max() - per_tehsil.min()), 2),
            }
        )
    return pd.DataFrame(rows)


def availability_manifest() -> dict:
    """The pipeline's own record of which periods were ingested / failed."""
    if not C.AVAILABILITY_JSON.exists():
        return {}
    return json.loads(C.AVAILABILITY_JSON.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Seasons, derived from the rainfall climatology (never hard-coded)
# --------------------------------------------------------------------------
def _season_months_from(means: tuple[float, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Longest run of consecutive months whose mean rainfall clears 50% of the peak."""
    means_arr = np.asarray(means, dtype=float)
    if np.all(np.isnan(means_arr)) or np.nanmax(means_arr) <= 0:
        wet = (7, 8, 9)
        return wet, tuple(m for m in C.MONTH_NUMBERS if m not in wet)

    threshold = 0.5 * np.nanmax(means_arr)
    candidate = [m for m in C.MONTH_NUMBERS if means_arr[m - 1] >= threshold]

    # Keep the longest run of consecutive months that clears the threshold.
    best: list[int] = []
    run: list[tuple[int, int]] = []
    prev = None
    for m in candidate:
        if prev is not None and m == prev + 1:
            run.append((run[-1][0], m))
        else:
            run.append((m, m))
        prev = m
    for lo, hi in run:
        block = list(range(lo, hi + 1))
        if len(block) > len(best):
            best = block

    wet = tuple(best) if best else (7, 8, 9)
    dry = tuple(m for m in C.MONTH_NUMBERS if m not in wet)
    return wet, dry


def season_months(df: pd.DataFrame) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return (wet, dry) month numbers implied by the district rainfall climatology."""
    means = (
        df.dropna(subset=[C.RAIN_COLUMN])
        .groupby("month")[C.RAIN_COLUMN]
        .mean()
        .reindex(C.MONTH_NUMBERS)
    )
    means = means.fillna(0.0).round(4)
    return _season_months_from(tuple(means.tolist()))


def season_label(months: tuple[int, ...]) -> str:
    names = [C.MONTHS[m - 1] for m in months]
    if len(names) >= 3:
        return f"{names[0]}-{names[-1]} ({len(names)} months)"
    return ", ".join(names)


# --------------------------------------------------------------------------
# Small helpers used by several figures
# --------------------------------------------------------------------------
def pivot_period_village(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """period x village matrix, used for lagged correlations."""
    return df.pivot_table(index="period", columns="village_idx", values=column, aggfunc="mean")


def component_count(df: pd.DataFrame) -> pd.Series:
    """How many of the CDI components were available for each village-month.

    Derived from the same four inputs the composite can use (SPI-3, NDVI, VCI,
    NSMI), so a monsoon month scored from rainfall alone shows up as 1.
    """
    cols = [c for c in ("SPI3", "NDVI", "VCI", "NSMI") if c in df.columns]
    return df[cols].notna().sum(axis=1)


def parse_contributions(value) -> dict:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
