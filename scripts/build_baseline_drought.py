# -*- coding: utf-8 -*-
"""
Baseline + Drought Month Identification Pipeline.

For each village and each calendar month:
  1. Compute BASELINE = historical mean across all years (e.g., Oct baseline = mean of all Octobers)
  2. Compute ANOMALY = current value vs baseline (z-score)
  3. Flag DROUGHT MONTH when anomaly is significantly below baseline
  4. RAIN-ONLY fallback: when no satellite data but CHIRPS rain exists, use SPI/PCI

Outputs:
  - data/processed/csv/village_with_baseline.csv   (per village-month with baseline + drought flag)
  - data/processed/json/village_latest.json        (latest period, all villages)
  - outputs/Dashboard/village_latest.geojson       (centroid-based GeoJSON for frontend map)
  - SQLite drought.db                              (master_row + monthly_index + tehsils)
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "drought.db"
VILLAGE_CSV = ROOT / "data" / "processed" / "csv" / "village_Latur_monthly_indices.csv"
VILLAGE_GEOJSON_SRC = ROOT / "frontend" / "public" / "data" / "latur_villages.geojson"
DASH_GEOJSON = ROOT / "outputs" / "Dashboard" / "village_latest.geojson"
DASH_JSON = ROOT / "outputs" / "Dashboard" / "village_latest.json"

RUN_ID = "run-baseline-v2026.10"


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _classify_cdi(v, thresholds):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "ND"
    for t in thresholds:
        if v < t["max"]:
            return t["code"]
    return "D4"


def load_and_fix_village_data():
    """Load village CSV and fix known computation issues."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common.paths import active_panel
    from common.village_cdi import _load_cfg
    df = pd.read_csv(active_panel(_load_cfg()))
    df["date"] = df["date"].astype(str)
    dt = pd.to_datetime(df["date"], format="%Y-%m")
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month

    # Fix EVI: clip to valid range [-1, 1] (values > 1.0 indicate DN not scaled by 10000)
    evi_bad = (df["EVI"] > 1.0) | (df["EVI"] < -1.0)
    print(f"  Fixing {evi_bad.sum()} EVI values outside [-1, 1] (clipping)")
    df.loc[evi_bad, "EVI"] = df.loc[evi_bad, "EVI"].clip(-1.0, 1.0)

    # Fix NDVI: clip to valid range
    ndvi_bad = (df["NDVI"] > 1.0) | (df["NDVI"] < -1.0)
    if ndvi_bad.any():
        print(f"  Fixing {ndvi_bad.sum()} NDVI values outside [-1, 1] (clipping)")
        df.loc[ndvi_bad, "NDVI"] = df.loc[ndvi_bad, "NDVI"].clip(-1.0, 1.0)

    # Fix VCI/VHI: clip to [0, 100]
    for col in ("VCI", "VHI"):
        bad = (df[col] > 100) | (df[col] < 0)
        if bad.any():
            print(f"  Fixing {bad.sum()} {col} values outside [0, 100] (clipping)")
            df.loc[bad, col] = df.loc[bad, col].clip(0.0, 100.0)

    return df


def compute_baseline(df):
    """
    For each village and calendar month, compute historical baseline:
    - baseline_ndvi: mean NDVI for this calendar month across all years
    - baseline_vci: mean VCI for this calendar month across all years
    - baseline_spi3: mean SPI3 for this calendar month across all years
    """
    print("\n[Baseline] computing per-village per-calendar-month baselines ...")

    baseline_cols = ["NDVI", "VCI", "SPI3", "Rain_mm"]
    baseline_df = df.groupby(["village_idx", "month"])[baseline_cols].mean(
        numeric_only=True
    ).reset_index()
    baseline_df = baseline_df.rename(
        columns={c: f"baseline_{c}" for c in baseline_cols}
    )

    # Also compute std for z-score
    baseline_std = df.groupby(["village_idx", "month"])[baseline_cols].std(
        numeric_only=True
    ).reset_index()
    baseline_std = baseline_std.rename(
        columns={c: f"baseline_std_{c}" for c in baseline_cols}
    )

    baseline = baseline_df.merge(baseline_std, on=["village_idx", "month"], how="outer")
    return baseline


def add_anomaly_and_drought_flag(df, baseline, cfg):
    """Merge baseline, compute anomaly z-scores, flag drought months."""
    print("\n[Anomaly] computing z-scores vs baseline ...")

    df = df.merge(baseline, on=["village_idx", "month"], how="left")

    # Z-score anomaly: (current - baseline) / std
    # Negative anomaly = drier than normal
    for col in ["NDVI", "VCI", "SPI3"]:
        bcol = f"baseline_{col}"
        scol = f"baseline_std_{col}"
        acol = f"anomaly_{col}"
        df[acol] = np.where(
            df[scol].notna() & (df[scol] > 1e-6),
            (df[col] - df[bcol]) / df[scol],
            np.nan,
        )

    # Composite drought anomaly: average of NDVI, VCI, SPI3 anomalies
    anomaly_cols = ["anomaly_NDVI", "anomaly_VCI", "anomaly_SPI3"]
    df["composite_anomaly"] = df[anomaly_cols].mean(axis=1)

    # Drought flag: composite_anomaly < -1.0 (more than 1 std below baseline)
    thresholds = cfg["thresholds"]
    cdi = df["composite_drought_score"]
    df["drought_month"] = False
    df.loc[cdi.notna() & (cdi >= 0.35), "drought_month"] = True  # D0 or worse
    # Also flag based on anomaly
    df.loc[
        df["composite_anomaly"].notna() & (df["composite_anomaly"] < -1.0),
        "drought_month",
    ] = True

    # Drought severity class
    def severity(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "No data"
        if v < -2.0:
            return "Exceptional"
        if v < -1.5:
            return "Extreme"
        if v < -1.0:
            return "Severe"
        if v < -0.5:
            return "Moderate"
        if v < 0.0:
            return "Mild"
        return "Normal"

    df["drought_severity"] = [severity(v) for v in df["composite_anomaly"]]

    return df


def generate_village_geojson(df, latest_period, villages_src, out_geojson, out_json):
    """Build village GeoJSON from centroids for the frontend map."""
    print(f"\n[GeoJSON] building village GeoJSON for {latest_period} ...")

    # Load village geometries for centroids
    gj = json.loads(villages_src.read_text(encoding="utf-8"))
    village_centroids = {}
    for feat in gj["features"]:
        props = feat.get("properties", {})
        vid = props.get("id") or props.get("village_idx")
        name = props.get("village") or props.get("name") or props.get("NAME")
        tehsil = props.get("tehsil") or props.get("TEHSIL") or ""
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom["type"] == "Polygon":
            ring = coords[0]
        elif geom["type"] == "MultiPolygon":
            ring = coords[0][0]
        else:
            continue
        arr = np.asarray(ring, dtype="float64")
        cx, cy = float(arr[:, 0].mean()), float(arr[:, 1].mean())
        if vid is not None:
            village_centroids[int(vid)] = {
                "village": str(name).strip() if name else "",
                "tehsil": str(tehsil).strip(),
                "lon": cx,
                "lat": cy,
            }

    latest = df[df["date"] == latest_period].copy()
    print(f"  Villages in {latest_period}: {len(latest)}")

    features = []
    json_villages = {}
    for _, r in latest.iterrows():
        vid = int(r["village_idx"]) if pd.notna(r.get("village_idx")) else None
        cent = village_centroids.get(vid, {"village": "", "tehsil": "", "lon": 0.0, "lat": 0.0})

        cdi = _num(r.get("composite_drought_score"))
        cdi_cls = r.get("composite_drought_class", "")
        is_drought = bool(r.get("drought_month", False))
        severity = r.get("drought_severity", "")

        props = {
            "id": vid,
            "village": cent["village"] or r.get("village", ""),
            "tehsil": cent["tehsil"] or r.get("tehsil", ""),
            "date": latest_period,
            "period": latest_period,
            "NDVI": _num(r.get("NDVI")),
            "EVI": _num(r.get("EVI")),
            "VCI": _num(r.get("VCI")),
            "VHI": _num(r.get("VHI")),
            "NSMI": _num(r.get("NSMI")),
            "PCI": _num(r.get("PCI")),
            "SPI1": _num(r.get("SPI1")),
            "SPI3": _num(r.get("SPI3")),
            "SPI6": _num(r.get("SPI6")),
            "SPI12": _num(r.get("SPI12")),
            "Rain_mm": _num(r.get("Rain_mm")),
            "CDI": cdi,
            "CDI_class": cdi_cls if pd.notna(cdi_cls) else "",
            "class": cdi_cls if pd.notna(cdi_cls) else "",
            "drought_month": is_drought,
            "drought_severity": severity,
            "composite_anomaly": _num(r.get("composite_anomaly")),
            "baseline_ndvi": _num(r.get("baseline_NDVI")),
            "baseline_vci": _num(r.get("baseline_VCI")),
            "baseline_spi3": _num(r.get("baseline_SPI3")),
            "component_contributions": (
                json.loads(r.get("component_contributions", "{}"))
                if r.get("component_contributions") and str(r.get("component_contributions")).strip()
                else {}
            ),
            "composite_formula_version": r.get("formula_version", ""),
            "data_quality_status": r.get("data_quality_status", ""),
            "lon": cent["lon"],
            "lat": cent["lat"],
        }
        features.append({"type": "Feature", "properties": props, "geometry": {
            "type": "Point",
            "coordinates": [cent["lon"], cent["lat"]],
        }})
        if vid is not None:
            json_villages[str(vid)] = props

    fc = {"type": "FeatureCollection", "features": features}
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    with out_geojson.open("w") as f:
        json.dump(fc, f, indent=2)

    with out_json.open("w") as f:
        json.dump(
            {
                "generated_at": _ts(),
                "period": latest_period,
                "count": len(features),
                "villages": json_villages,
            },
            f,
            indent=2,
        )

    print(f"  GeoJSON -> {out_geojson} ({len(features)} villages)")
    print(f"  JSON -> {out_json}")
    return latest


def _ensure_schema(cur):
    """Create tables if they do not exist, and add missing columns."""
    cur.execute("""CREATE TABLE IF NOT EXISTS master_row (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        district TEXT,
        tehsil TEXT NOT NULL,
        village TEXT NOT NULL DEFAULT '',
        observation_period TEXT NOT NULL,
        year INTEGER,
        month INTEGER,
        monthly_rainfall_mm REAL,
        chirps_data_through TEXT,
        spi_1 REAL, spi_3 REAL, spi_6 REAL, spi_12 REAL,
        spi_reference_period TEXT,
        ndvi REAL, evi REAL, vci REAL, vhi REAL, nsmi REAL, pci REAL,
        composite_drought_score REAL,
        composite_drought_class TEXT,
        component_contributions TEXT,
        composite_formula_version TEXT,
        drought_area_km2 REAL,
        drought_percentage REAL,
        total_polygon_area_km2 REAL,
        sentinel2_observation_date TEXT,
        sentinel2_cloud_percentage REAL,
        data_quality_status TEXT,
        processing_timestamp TEXT,
        processing_run_id TEXT,
        lon REAL, lat REAL,
        UNIQUE(tehsil, village, observation_period)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS monthly_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_name TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
        value REAL,
        class_label TEXT,
        pct_area_dry REAL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(index_name, year, month)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS tehsils (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        geom TEXT
    )""")
    existing = {r[1] for r in cur.execute("PRAGMA table_info(master_row)").fetchall()}
    if "nsmi" not in existing:
        cur.execute("ALTER TABLE master_row ADD COLUMN nsmi REAL")


def load_into_sqlite(df, latest_df):
    """Load all data into SQLite drought.db."""
    print("\n[SQLite] loading into drought.db ...")

    cols = [
        "district", "tehsil", "village", "observation_period", "year", "month",
        "monthly_rainfall_mm", "chirps_data_through", "spi_1", "spi_3", "spi_6",
        "spi_12", "spi_reference_period", "ndvi", "evi", "vci", "vhi", "nsmi", "pci",
        "composite_drought_score", "composite_drought_class",
        "component_contributions", "composite_formula_version",
        "drought_area_km2", "drought_percentage", "total_polygon_area_km2",
        "sentinel2_observation_date", "sentinel2_cloud_percentage",
        "data_quality_status", "processing_timestamp", "processing_run_id",
        "lon", "lat",
    ]
    placeholders = ",".join(["?"] * len(cols))
    col_list = ",".join(cols)
    upsert = (
        f"INSERT INTO master_row ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT(tehsil, village, observation_period) DO UPDATE SET "
        + ", ".join(f"{c}=excluded.{c}" for c in cols
                    if c not in ("district", "tehsil", "village", "observation_period"))
    )

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    _ensure_schema(cur)

    # Build rows from full df
    now = _ts()
    rows = []
    for _, r in df.iterrows():
        contrib = r.get("component_contributions", "")
        try:
            contrib_json = json.dumps(json.loads(contrib)) if contrib and str(contrib).strip() else "{}"
        except (json.JSONDecodeError, TypeError):
            contrib_json = "{}"
        cdi = _num(r.get("composite_drought_score"))
        cdi_cls = r.get("composite_drought_class")
        rows.append({
            "district": "Latur",
            "tehsil": r.get("tehsil", ""),
            "village": r.get("village", ""),
            "observation_period": r.get("date", ""),
            "year": int(r["year"]) if pd.notna(r.get("year")) else None,
            "month": int(r["month"]) if pd.notna(r.get("month")) else None,
            "monthly_rainfall_mm": _num(r.get("Rain_mm")),
            "chirps_data_through": None,
            "spi_1": _num(r.get("SPI1")),
            "spi_3": _num(r.get("SPI3")),
            "spi_6": _num(r.get("SPI6")),
            "spi_12": _num(r.get("SPI12")),
            "spi_reference_period": "1991-2020",
            "ndvi": _num(r.get("NDVI")),
            "evi": _num(r.get("EVI")),
            "vci": _num(r.get("VCI")),
            "vhi": _num(r.get("VHI")),
            "nsmi": _num(r.get("NSMI")),
            "pci": _num(r.get("PCI")),
            "composite_drought_score": cdi,
            "composite_drought_class": cdi_cls if pd.notna(cdi_cls) else None,
            "component_contributions": contrib_json,
            "composite_formula_version": r.get("formula_version", "") or "cdi-v2026.10",
            "drought_area_km2": None,
            "drought_percentage": None,
            "total_polygon_area_km2": None,
            "sentinel2_observation_date": None,
            "sentinel2_cloud_percentage": None,
            "data_quality_status": r.get("data_quality_status", "success" if cdi is not None else "pending"),
            "processing_timestamp": now,
            "processing_run_id": RUN_ID,
            "lon": _num(r.get("lon")),
            "lat": _num(r.get("lat")),
        })

    cur.executemany(upsert, [[row[c] for c in cols] for row in rows])
    print(f"  master_row upserted: {cur.rowcount}")

    # monthly_index timeseries
    monthly_rows = []
    for (year, month), g in df.groupby(["year", "month"]):
        for iname, col in {
            "spi1": "SPI1", "spi3": "SPI3", "spi6": "SPI6", "spi12": "SPI12",
            "ndvi": "NDVI", "evi": "EVI", "vci": "VCI", "vhi": "VHI",
            "nsmi": "NSMI", "pci": "PCI",
            "cdi": "composite_drought_score",
        }.items():
            val = _num(g[col].mean())
            if val is None:
                continue
            monthly_rows.append((iname, int(year), int(month), val, None, None))

    cur.executemany(
        "INSERT INTO monthly_index (index_name, year, month, value, class_label, pct_area_dry) "
        "VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(index_name, year, month) DO UPDATE SET "
        "value=excluded.value, class_label=excluded.class_label, pct_area_dry=excluded.pct_area_dry, "
        "updated_at=CURRENT_TIMESTAMP",
        monthly_rows,
    )
    print(f"  monthly_index upserted: {cur.rowcount}")

    # Tehsils from village centroids
    gj = json.loads(VILLAGE_GEOJSON_SRC.read_text(encoding="utf-8"))
    by_tehsil = {}
    for feat in gj["features"]:
        props = feat.get("properties", {})
        tehsil = props.get("tehsil") or props.get("TEHSIL") or ""
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom["type"] == "Polygon":
            ring = coords[0]
        elif geom["type"] == "MultiPolygon":
            ring = coords[0][0]
        else:
            continue
        arr = np.asarray(ring, dtype="float64")
        by_tehsil.setdefault(tehsil, []).append((float(arr[:, 0].mean()), float(arr[:, 1].mean())))

    cur.execute("DELETE FROM tehsils")
    for tehsil, pts in sorted(by_tehsil.items()):
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        cur.execute("INSERT INTO tehsils (name, geom) VALUES (?,?)", [tehsil, f"POINT({cx} {cy})"])
    print(f"  tehsils replaced: {len(by_tehsil)}")

    con.commit()
    con.close()
    print("  SQLite load complete.")


def main():
    import yaml
    cfg_path = ROOT / "config" / "composite.yaml"
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("=" * 60)
    print(" BASELINE + DROUGHT MONTH IDENTIFICATION")
    print("=" * 60)

    # 1. Load and fix data
    print("\n[1] loading village indices ...")
    df = load_and_fix_village_data()
    print(f"  Loaded {len(df)} village-month records, {df['date'].nunique()} periods")

    # 2. Compute baseline
    baseline = compute_baseline(df)

    # 3. Add anomaly + drought flag
    df = add_anomaly_and_drought_flag(df, baseline, cfg)

    # 4. Save enriched CSV
    out_csv = ROOT / "data" / "processed" / "csv" / "village_with_baseline.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[Save] enriched CSV -> {out_csv} ({len(df)} rows)")

    # 5. Generate GeoJSON for latest period
    latest_period = df["date"].max()
    latest_df = generate_village_geojson(
        df, latest_period, VILLAGE_GEOJSON_SRC, DASH_GEOJSON, DASH_JSON
    )

    # 5b. Add village centroids (lon/lat) to df for SQLite village points
    print("\n[5b] adding village centroids to dataframe ...")
    gj = json.loads(VILLAGE_GEOJSON_SRC.read_text(encoding="utf-8"))
    centroid_lookup = {}
    for feat in gj["features"]:
        props = feat.get("properties", {})
        # Match by village name (case-insensitive)
        vname = (props.get("VILLAGE") or props.get("village") or props.get("name") or "").strip()
        if not vname:
            continue
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom["type"] == "Polygon":
            ring = coords[0]
        elif geom["type"] == "MultiPolygon":
            ring = coords[0][0]
        else:
            continue
        arr = np.asarray(ring, dtype="float64")
        centroid_lookup[vname.lower()] = {
            "lon": float(arr[:, 0].mean()),
            "lat": float(arr[:, 1].mean()),
        }
    df["lon"] = df["village"].apply(lambda v: centroid_lookup.get(str(v).lower(), {}).get("lon") if pd.notna(v) else None)
    df["lat"] = df["village"].apply(lambda v: centroid_lookup.get(str(v).lower(), {}).get("lat") if pd.notna(v) else None)

    # 6. Load into SQLite
    load_into_sqlite(df, latest_df)

    # Summary
    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    drought_count = int(df["drought_month"].sum())
    total = len(df)
    print(f"  Total village-month records: {total}")
    print(f"  Drought months flagged: {drought_count} ({drought_count/total*100:.1f}%)")
    print(f"  Latest period: {latest_period}")
    print(f"  Baseline computed for {len(baseline)} village-month combinations")
    print("\nDone.")


if __name__ == "__main__":
    main()
