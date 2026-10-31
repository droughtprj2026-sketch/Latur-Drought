# -*- coding: utf-8 -*-
"""
Simple, fast pipeline: load existing village indices CSV into SQLite
and build village GeoJSON from centroids. No heavy raster processing.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "drought.db"
VILLAGE_CSV = ROOT / "data" / "processed" / "csv" / "village_Latur_monthly_indices.csv"
VILLAGE_GEOJSON = ROOT / "frontend" / "public" / "data" / "latur_villages.geojson"
RUN_ID = "run-centroid-v2026.10"


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


def load_master_rows() -> list[dict]:
    """Read village indices CSV; return village rows + aggregated tehsil rows."""
    df = pd.read_csv(VILLAGE_CSV)
    df["date"] = df["date"].astype(str)
    dt = pd.to_datetime(df["date"], format="%Y-%m")
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month

    rows: list[dict] = []
    now = _ts()

    # ---- village-level rows ----
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
            "data_quality_status": "success" if cdi is not None else "pending",
            "processing_timestamp": now,
            "processing_run_id": RUN_ID,
        })

    # ---- tehsil-level rows (mean across villages in each tehsil-period) ----
    g = df.groupby(["tehsil", "date"]).agg({
        "Rain_mm": "mean", "SPI1": "mean", "SPI3": "mean", "SPI6": "mean",
        "SPI12": "mean", "NDVI": "mean", "EVI": "mean", "VCI": "mean",
        "VHI": "mean", "PCI": "mean", "composite_drought_score": "mean",
    }).reset_index()

    cdi_map: dict[tuple[str, str], str] = {}
    for _, r in df.iterrows():
        key = (r.get("tehsil", ""), r.get("date", ""))
        c = r.get("composite_drought_class")
        if pd.notna(c):
            cdi_map[key] = c

    for _, r in g.iterrows():
        tehsil = r["tehsil"]; period = r["date"]
        dt2 = pd.to_datetime(period, format="%Y-%m")
        cdi = _num(r.get("composite_drought_score"))
        if cdi is None:
            cls = None
        elif cdi < 0.20:
            cls = "None"
        elif cdi < 0.35:
            cls = "D0"
        elif cdi < 0.50:
            cls = "D1"
        elif cdi < 0.65:
            cls = "D2"
        elif cdi < 0.80:
            cls = "D3"
        else:
            cls = "D4"
        key = (tehsil, period)
        cls = cdi_map.get(key, cls)
        rows.append({
            "district": "Latur",
            "tehsil": tehsil,
            "village": "",
            "observation_period": period,
            "year": int(dt2.year),
            "month": int(dt2.month),
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
            "pci": _num(r.get("PCI")),
            "composite_drought_score": cdi,
            "composite_drought_class": cls,
            "component_contributions": "{}",
            "composite_formula_version": "cdi-v2026.10",
            "drought_area_km2": None,
            "drought_percentage": None,
            "total_polygon_area_km2": None,
            "sentinel2_observation_date": None,
            "sentinel2_cloud_percentage": None,
            "data_quality_status": "success" if cdi is not None else "pending",
            "processing_timestamp": now,
            "processing_run_id": RUN_ID,
        })
    return rows


def load_monthly_index() -> list[dict]:
    """District-mean timeseries per index from village CSV."""
    df = pd.read_csv(VILLAGE_CSV)
    df["date"] = df["date"].astype(str)
    dt = pd.to_datetime(df["date"], format="%Y-%m")
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month

    col_map = {
        "spi1": "SPI1", "spi3": "SPI3", "spi6": "SPI6", "spi12": "SPI12",
        "ndvi": "NDVI", "evi": "EVI", "vci": "VCI", "vhi": "VHI", "pci": "PCI",
        "cdi": "composite_drought_score",
    }
    rows: list[dict] = []
    for (year, month), g in df.groupby(["year", "month"]):
        for iname, col in col_map.items():
            val = _num(g[col].mean())
            if val is None:
                continue
            rows.append({
                "index_name": iname,
                "year": int(year),
                "month": int(month),
                "value": val,
                "class_label": None,
                "pct_area_dry": None,
            })
    return rows


def load_tehsil_centroids() -> list[dict]:
    """Build tehsil point geometries from village centroids."""
    if not VILLAGE_GEOJSON.exists():
        return []
    gj = json.loads(VILLAGE_GEOJSON.read_text(encoding="utf-8"))
    by_tehsil: dict[str, list[tuple[float, float]]] = {}
    for feat in gj["features"]:
        props = feat.get("properties", {})
        tehsil = props.get("TEHSIL") or props.get("tehsil") or ""
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom["type"] == "Polygon":
            ring = coords[0]
        elif geom["type"] == "MultiPolygon":
            ring = coords[0][0]
        else:
            continue
        arr = __import__("numpy").asarray(ring, dtype="float64")
        cx, cy = float(arr[:, 0].mean()), float(arr[:, 1].mean())
        by_tehsil.setdefault(tehsil, []).append((cx, cy))

    out: list[dict] = []
    for tehsil, pts in sorted(by_tehsil.items()):
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        out.append({"name": tehsil, "lon": cx, "lat": cy})
    return out


def main():
    if not VILLAGE_CSV.exists():
        raise SystemExit(f"missing {VILLAGE_CSV}")

    master_rows = load_master_rows()
    monthly_rows = load_monthly_index()
    tehsil_pts = load_tehsil_centroids()

    print(f"master rows: {len(master_rows)}")
    print(f"monthly_index rows: {len(monthly_rows)}")
    print(f"tehsil centroids: {len(tehsil_pts)}")

    cols = [
        "district", "tehsil", "village", "observation_period", "year", "month",
        "monthly_rainfall_mm", "chirps_data_through", "spi_1", "spi_3", "spi_6",
        "spi_12", "spi_reference_period", "ndvi", "evi", "vci", "vhi", "pci",
        "composite_drought_score", "composite_drought_class",
        "component_contributions", "composite_formula_version",
        "drought_area_km2", "drought_percentage", "total_polygon_area_km2",
        "sentinel2_observation_date", "sentinel2_cloud_percentage",
        "data_quality_status", "processing_timestamp", "processing_run_id",
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

    cur.executemany(upsert, [[r[c] for c in cols] for r in master_rows])
    print(f"master_row upserted: {cur.rowcount}")

    cur.executemany(
        "INSERT INTO monthly_index (index_name, year, month, value, class_label, pct_area_dry) "
        "VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(index_name, year, month) DO UPDATE SET "
        "value=excluded.value, class_label=excluded.class_label, pct_area_dry=excluded.pct_area_dry, "
        "updated_at=CURRENT_TIMESTAMP",
        [[r["index_name"], r["year"], r["month"], r["value"], r["class_label"], r["pct_area_dry"]]
         for r in monthly_rows],
    )
    print(f"monthly_index upserted: {cur.rowcount}")

    if tehsil_pts:
        cur.execute("DELETE FROM tehsils")
        for t in tehsil_pts:
            wkt = f"POINT({t['lon']} {t['lat']})"
            cur.execute("INSERT INTO tehsils (name, geom) VALUES (?,?)", [t["name"], wkt])
        print(f"tehsils replaced: {len(tehsil_pts)}")

    con.commit()
    con.close()
    print("SQLite load complete.")


if __name__ == "__main__":
    main()
