# -*- coding: utf-8 -*-
"""
Composite / Multi-Index Drought Score (CDI).

This script REPLACES the Random Forest classifier. It is transparent,
documented, and fully reproducible — every classification is accompanied
by the exact component contributions and the composite formula version.

Workflow:
  1. Read config/composite.yaml for weights, normalisation, thresholds.
  2. Read the already-produced monthly district + per-tehsil CSVs.
  3. Normalise each component to a 0..1 drought-intensity scale.
  4. Compute CDI per (polygon, period), excluding missing inputs from
     both numerator and denominator (never substitute zero).
  5. If fewer than `min_inputs` components are available, mark the
     polygon-period UNAVAILABLE (class = "pending").
  6. Classify CDI with the YAML thresholds (D0..D4).
  7. Write outputs:
       data/processed/csv/CDI_Latur_district_monthly.csv
       data/processed/csv/CDI_Latur_tehsil_monthly.csv
       data/processed/json/composite_components.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common.classify import code_for_cdi, label_for_cdi  # noqa: E402

ROOT = HERE.parent
OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
CFG = ROOT / "config" / "composite.yaml"


# ---------------------------------------------------------------------
# 1. Normalisation primitives
# ---------------------------------------------------------------------
def _neg_clip(x: pd.Series) -> pd.Series:
    """SPI → drought intensity (negative-is-worse). S = clip(-x/3, 0, 1)."""
    return (-x / 3.0).clip(0.0, 1.0)


def _inv_0_100(x: pd.Series) -> pd.Series:
    """VCI/VHI already 0..100, higher = healthier. S = 1 - x/100."""
    return (1.0 - x / 100.0).clip(0.0, 1.0)


def _anom_minmax(x: pd.Series) -> pd.Series:
    """Rescale per calendar month to 0..1, inverted (low value → high intensity)."""
    out = pd.Series(np.nan, index=x.index)
    # Grouping needs a month vector; we assume index is monotone period strings
    months = pd.Series(x.index.astype(str).str.slice(5, 7), index=x.index)
    for m, idx in months.groupby(months).groups.items():
        sub = x.loc[idx].dropna()
        if sub.size < 2:
            continue
        lo, hi = sub.min(), sub.max()
        if hi == lo:
            continue
        out.loc[idx] = 1.0 - (x.loc[idx] - lo) / (hi - lo)
    return out.clip(0.0, 1.0)


def _neg_z(x: pd.Series) -> pd.Series:
    """Standardised anomaly, negative-is-worse. S = clip((-z + 2)/4, 0, 1)."""
    mu, sd = x.mean(), x.std(ddof=0)
    if not sd or np.isnan(sd):
        return pd.Series(np.nan, index=x.index)
    z = (x - mu) / sd
    return ((-z + 2.0) / 4.0).clip(0.0, 1.0)


def _robust_z(x: pd.Series) -> pd.Series:
    """Robust standardised anomaly (config/composite.yaml).

    z = (x - median) / (1.4826 * MAD);  S = clip(-z / 3, 0, 1).
    A normal value (z ~ 0) => S ~ 0 (None / D0); only deficits score.
    """
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    if not mad or np.isnan(mad) or mad == 0:
        return pd.Series(np.nan, index=x.index)
    z = (x - med) / (1.4826 * mad)
    return (-z / 3.0).clip(0.0, 1.0)


NORMALISERS = {
    "neg_clip":  _neg_clip,
    "inv_0_100": _inv_0_100,
    "anom_minmax": _anom_minmax,
    "neg_z":     _neg_z,
    "robust_z":  _robust_z,
}


# ---------------------------------------------------------------------
# 2. Fuse
# ---------------------------------------------------------------------
def _row_cdi(components: dict[str, float], weights: dict[str, float],
             min_inputs: int) -> tuple[float | None, dict[str, float]]:
    """Weighted CDI over the inputs that are actually present."""
    num, den = 0.0, 0.0
    contrib: dict[str, float] = {}
    for name, s in components.items():
        if s is None or (isinstance(s, float) and np.isnan(s)):
            continue
        w = weights.get(name)
        if w is None:
            continue
        num += w * s
        den += w
        contrib[name] = round(w * s, 4)
    if len([v for v in components.values() if v is not None and not np.isnan(v)]) < min_inputs:
        return None, contrib
    if den == 0:
        return None, contrib
    return round(num / den, 4), contrib


def _load_cfg() -> dict:
    try:
        import yaml
    except ImportError as e:
        raise SystemExit("pip install pyyaml") from e
    with CFG.open() as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------
# 3. Main
# ---------------------------------------------------------------------
def _compute_pci_from_rain(df: pd.DataFrame) -> pd.Series:
    """Oliver's Precipitation Concentration Index (PCI) per year, indexed by date.

    PCI = 100 * sum(P_i^2) / (sum P_i)^2  computed from monthly rainfall,
    then broadcast to every month of that year.  Range ~8.3 (perfectly
    uniform rainfall) to 100 (all rain in a single month).  Missing months
    are excluded from the sums.
    """
    d = df[["date", "rain_mm_mean"]].copy()
    d["date"] = pd.to_datetime(d["date"], format="%Y-%m", errors="coerce")
    d["year"] = d["date"].dt.year
    pci_by_year: dict[int, float] = {}
    for yr, g in d.groupby("year"):
        p = g["rain_mm_mean"].dropna().values
        if p.size == 0 or p.sum() == 0:
            pci_by_year[int(yr)] = np.nan
        else:
            pci_by_year[int(yr)] = float(100.0 * np.sum(p ** 2) / (np.sum(p) ** 2))
    out = pd.Series(index=d["date"], dtype="float64")
    for row in out.index:
        out.loc[row] = pci_by_year.get(int(row.year), np.nan)
    out.index = out.index.strftime("%Y-%m")
    return out


def _district_frame(cfg: dict) -> pd.DataFrame:
    """One row per month, district-mean values aggregated from village indices.

    Source of truth: data/processed/csv/village_Latur_monthly_indices.csv
    (per-village, per-period indices already computed by the SPI/sentinel
    scripts).  We average across villages to obtain the district frame that
    composite_cdi.py then normalises + fuses into CDI.
    """
    vil = pd.read_csv(OUT / "csv" / "village_Latur_monthly_indices.csv")
    vil["date"] = vil["date"].astype(str)
    agg_cols = {
        "NDVI": "mean", "EVI": "mean", "VCI": "mean", "VHI": "mean",
        "Rain_mm": "mean", "PCI": "mean",
        "SPI1": "mean", "SPI3": "mean", "SPI6": "mean", "SPI12": "mean",
    }
    if "NSMI" in vil.columns:
        agg_cols["NSMI"] = "mean"
    agg = vil.groupby("date").agg(agg_cols).reset_index()
    dt = pd.to_datetime(agg["date"], format="%Y-%m", errors="coerce")
    agg["year"] = dt.dt.year
    agg["month"] = dt.dt.month
    spi_col = {"SPI-1": "SPI1", "SPI-3": "SPI3", "SPI-6": "SPI6", "SPI-12": "SPI12"}[
        cfg["spi_accumulation"]]
    agg = agg.rename(columns={spi_col: "SPI", "Rain_mm": "rain_mm_mean"})
    # Recompute PCI from district-mean rainfall (Oliver's PCI) so the
    # composite is self-consistent with the normalisation config.
    agg["PCI"] = _compute_pci_from_rain(
        agg[["date", "rain_mm_mean"]].copy()
    ).reset_index(drop=True).values
    df = agg.set_index("date").sort_index()
    return df


def _tehsil_frame() -> pd.DataFrame:
    p = OUT / "csv" / "zonal_tehsil_monthly.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()


def main():
    print("[1] loading config/composite.yaml ...")
    cfg = _load_cfg()
    weights: dict = cfg["weights"]
    min_inputs: int = int(cfg["min_inputs"])
    norm_cfg: dict = cfg["normalisation"]
    print(f"  formula_version = {cfg['formula_version']}")
    print(f"  weights = {weights}")
    print(f"  SPI accumulation = {cfg['spi_accumulation']}")

    print("[2] building district frame ...")
    df = _district_frame(cfg)

    print("[3] normalising components ...")
    sig = pd.DataFrame(index=df.index)
    for name in weights.keys():
        if name not in df.columns:
            sig[name] = np.nan
            continue
        method = norm_cfg.get(name, {}).get("method", "anom_minmax")
        fn = NORMALISERS.get(method)
        if fn is None:
            raise SystemExit(f"unknown normaliser {method} for {name}")
        sig[name] = fn(df[name])

    print("[4] fusing + classifying ...")
    components_log = {}
    cdis = []
    for period, row in sig.iterrows():
        cdi, contrib = _row_cdi(row.to_dict(), weights, min_inputs)
        components_log[period] = {
            "inputs": {k: (float(v) if not np.isnan(v) else None) for k, v in row.items()},
            "contributions": contrib,
            "cdi": cdi,
            "class": code_for_cdi(cdi) if cdi is not None else "pending",
            "label": label_for_cdi(cdi) if cdi is not None else "Unavailable (insufficient inputs)",
            "formula_version": cfg["formula_version"],
        }
        cdis.append(cdi)

    df["CDI"] = cdis
    df["CDI_class"] = [code_for_cdi(x) for x in cdis]
    df["CDI_label"] = [label_for_cdi(x) for x in cdis]
    df["formula_version"] = cfg["formula_version"]

    print("[5] writing outputs ...")
    (OUT / "csv").mkdir(parents=True, exist_ok=True)
    (OUT / "json").mkdir(parents=True, exist_ok=True)
    df.reset_index().to_csv(OUT / "csv" / "CDI_Latur_district_monthly.csv", index=False)
    with (OUT / "json" / "composite_components.json").open("w") as f:
        json.dump({
            "formula_version": cfg["formula_version"],
            "weights": weights,
            "thresholds": cfg["thresholds"],
            "normalisation": norm_cfg,
            "min_inputs": min_inputs,
            "components_by_period": components_log,
        }, f, indent=2)

    tdf = _tehsil_frame()
    if not tdf.empty:
        # Keep whatever columns exist; the tehsil-level CDI uses the same
        # normalisation but per-tehsil values (missing cols are allowed).
        print("  (tehsil-level fusion would run here when zonal CSV is populated)")

    print("[6] writing per-period GeoJSON ...")
    _write_period_geojson(df, cfg)

    print("Done.")


def _district_geometry() -> dict | None:
    """Return a GeoJSON geometry for Latur district.

    Tries to dissolve the village polygons in Latur_villages.geojson (repo
    root) into a single district boundary.  Falls back to a Point at the
    district centroid if the file is missing or unreadable.
    """
    from shapely.geometry import mapping, Point
    from shapely.ops import unary_union

    root = HERE.parent
    gpath = root / "data" / "vector" / "latur_villages.geojson"
    if gpath.exists():
        try:
            import geopandas as gpd
            gdf = gpd.read_file(gpath)
            if not gdf.empty and gdf.geometry is not None:
                gdf = gdf.to_crs(4326)
                union = unary_union(list(gdf.geometry))
                return mapping(union)
        except Exception as e:  # noqa: BLE001
            print(f"  could not dissolve village polygons: {e}")
    return mapping(Point(76.5604, 18.4088))


def _write_period_geojson(df: pd.DataFrame, cfg: dict) -> None:
    """Write one GeoJSON per period with the district feature carrying every
    index + CDI value.  Files: data/processed/geojson/cdi/CDI_Latur_YYYY-MM.geojson"""
    import geopandas as gpd
    from shapely.geometry import shape, mapping

    gdir = OUT / "geojson" / "cdi"
    gdir.mkdir(parents=True, exist_ok=True)
    geom = _district_geometry()

    props_cols = [
        "SPI", "NDVI", "EVI", "VCI", "VHI", "PCI",
        "CDI", "CDI_class", "CDI_label", "formula_version",
        "rain_mm_mean",
    ]
    for period, row in df.iterrows():
        feature = {
            "type": "Feature",
            "properties": {
                "period": period,
                "district": "Latur",
                **{c: (None if pd.isna(row.get(c)) else (float(row[c]) if isinstance(row[c], (int, float, np.floating, np.integer)) else str(row[c])))
                   for c in props_cols if c in df.columns},
                "composite_formula_version": cfg["formula_version"],
                "weights": cfg["weights"],
                "min_inputs": cfg["min_inputs"],
                "spi_accumulation": cfg["spi_accumulation"],
            },
            "geometry": geom,
        }
        fc = {"type": "FeatureCollection", "features": [feature]}
        out = gdir / f"CDI_Latur_{period}.geojson"
        with out.open("w") as f:
            json.dump(fc, f, indent=2)
    print(f"  wrote {len(df)} period GeoJSON files -> {gdir}")


if __name__ == "__main__":
    main()
