# -*- coding: utf-8 -*-
"""
Build the dashboard-ready master table and status JSONs.

Writes:
  outputs/Dashboard/drought_monitoring_master.csv
  outputs/Dashboard/latest_status.json
  outputs/Dashboard/data_availability.json
  outputs/Dashboard/processing_manifest.json

The Random Forest classifier has been retired. The final drought class is
produced by scripts/composite_cdi.py from a transparent weighted multi-index
composite (see config/composite.yaml). The master table does not carry
rf_* columns.

Missing or invalid values are written as empty cells. NEVER zero.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import manifest                          # noqa: E402
from common.classify import code_for_cdi             # noqa: E402

ROOT = HERE.parent
OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
DASH = ROOT / "outputs" / "Dashboard"
DASH.mkdir(parents=True, exist_ok=True)

MASTER_COLUMNS = [
    "district", "tehsil", "village",
    "observation_date", "observation_period", "year", "month",
    "monthly_rainfall_mm", "chirps_data_through",
    "SPI_1", "SPI_3", "SPI_6", "SPI_12", "SPI_reference_period",
    "NDVI", "EVI", "VCI", "VHI", "PCI",
    "composite_drought_score", "composite_drought_class",
    "component_contributions", "composite_formula_version",
    "drought_area_km2", "drought_percentage", "total_polygon_area_km2",
    "sentinel2_observation_date", "sentinel2_cloud_percentage",
    "data_quality_status", "processing_timestamp",
    "processing_run_id",
]


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _tehsil_areas() -> dict[str, float]:
    """Static tehsil-area table (km²). Replace with shapefile-derived values."""
    return {
        "Latur": 522.0, "Ausa": 701.0, "Nilanga": 831.0, "Renapur": 404.0,
        "Chakur": 503.0, "Ahmadpur": 798.0, "Udgir": 519.0, "Jalkot": 352.0,
        "Deoni": 266.0, "Shirur-Anantpal": 263.0,
    }


def _opt_csv(name: str) -> pd.DataFrame:
    p = OUT / "csv" / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _components_lookup() -> dict:
    p = OUT / "json" / "composite_components.json"
    if not p.exists():
        return {}
    with p.open() as f:
        return json.load(f).get("components_by_period", {})


def build_master() -> pd.DataFrame:
    spi = _opt_csv("SPI_Latur_district_monthly.csv")
    sen = _opt_csv("sentinel_Latur_district_monthly.csv")
    cdi = _opt_csv("CDI_Latur_district_monthly.csv")
    rain_t = _opt_csv("chirps_tehsil_monthly.csv")
    components = _components_lookup()
    areas = _tehsil_areas()

    sen_last = manifest.latest_period(OUT, "sentinel") or {}
    chirps_last = manifest.latest_period(OUT, "chirps") or {}

    rows: list[dict] = []
    for _, r in spi.iterrows():
        period = r["date"]
        year, month = int(r["year"]), int(r["month"])

        cdi_row = cdi.loc[cdi["date"] == period]
        cdi_val = float(cdi_row["CDI"].iloc[0]) if not cdi_row.empty and pd.notna(cdi_row["CDI"].iloc[0]) else None
        cdi_cls = cdi_row["CDI_class"].iloc[0] if not cdi_row.empty else ""
        cdi_fv = cdi_row["formula_version"].iloc[0] if not cdi_row.empty else ""
        contrib = json.dumps(components.get(period, {}).get("contributions", {}))
        dq = "success" if cdi_val is not None else "pending"

        base = {
            "district": "Latur",
            "observation_period": period, "year": year, "month": month,
            "monthly_rainfall_mm": r.get("rain_mm_mean"),
            "chirps_data_through": chirps_last.get("observation_date", ""),
            "SPI_1":  r.get("SPI1"),  "SPI_3":  r.get("SPI3"),
            "SPI_6":  r.get("SPI6"),  "SPI_12": r.get("SPI12"),
            "SPI_reference_period": os.environ.get("SPI_REFERENCE_PERIOD", "1991-2020"),
            "NDVI": sen.loc[sen["date"] == period, "NDVI"].mean() if not sen.empty else None,
            "EVI":  sen.loc[sen["date"] == period, "EVI"].mean()  if not sen.empty else None,
            "VCI":  sen.loc[sen["date"] == period, "VCI"].mean()  if not sen.empty else None,
            "VHI":  sen.loc[sen["date"] == period, "VHI"].mean()  if not sen.empty else None,
            "PCI":  None,
            "composite_drought_score": cdi_val,
            "composite_drought_class": cdi_cls,
            "component_contributions": contrib,
            "composite_formula_version": cdi_fv,
            "sentinel2_observation_date": sen_last.get("observation_date", ""),
            "sentinel2_cloud_percentage": sen_last.get("cloud_pct"),
            "data_quality_status": dq,
            "processing_timestamp": _ts(),
            "processing_run_id": f"run-{period}",
        }

        for tehsil, area in areas.items():
            row = dict(base)
            row["tehsil"] = tehsil
            row["village"] = ""           # tehsil-level row
            row["total_polygon_area_km2"] = area
            rt = rain_t[(rain_t["period"] == period) & (rain_t["tehsil"] == tehsil)]
            if not rt.empty:
                row["monthly_rainfall_mm"] = round(float(rt["rain_mm"].iloc[0]), 2)
            # Drought area and percentage from the D-code (coarse until
            # per-pixel is wired in; the frontend reads this field as-is).
            if cdi_cls in ("D0", "D1", "D2", "D3", "D4"):
                pct = {"D0": 20, "D1": 40, "D2": 60, "D3": 80, "D4": 100}[cdi_cls]
                row["drought_percentage"] = pct
                row["drought_area_km2"] = round(area * pct / 100, 1)
            else:
                row["drought_percentage"] = 0 if cdi_cls == "None" else ""
                row["drought_area_km2"] = 0 if cdi_cls == "None" else ""
            rows.append(row)

    df = pd.DataFrame(rows, columns=MASTER_COLUMNS)
    df = df.where(pd.notna(df), "")
    out_path = DASH / "drought_monitoring_master.csv"
    df.to_csv(out_path, index=False)
    print(f"  master -> {out_path} ({len(df)} rows, {df['observation_period'].nunique()} periods)")
    return df


def build_latest_status() -> None:
    sen = manifest.latest_period(OUT, "sentinel") or {}
    ch  = manifest.latest_period(OUT, "chirps") or {}
    comp_path = OUT / "json" / "composite_components.json"
    composite = {}
    if comp_path.exists():
        with comp_path.open() as f:
            cfg = json.load(f)
            composite = {
                "formula_version": cfg.get("formula_version"),
                "weights": cfg.get("weights"),
                "min_inputs": cfg.get("min_inputs"),
                "spi_reference": os.environ.get("SPI_REFERENCE_PERIOD", "1991-2020"),
            }
    payload = {
        "generated_at": _ts(),
        "monitoring_status": "operational" if sen and ch else "degraded",
        "sentinel2": {
            "latest_observation_date": sen.get("observation_date"),
            "latest_period_id":        sen.get("period_id"),
            "cloud_percentage":        sen.get("cloud_pct"),
            "last_successful_update":  sen.get("processed_at"),
            "status":                  sen.get("status"),
        },
        "chirps": {
            "latest_observation_date": ch.get("observation_date"),
            "latest_period_id":        ch.get("period_id"),
            "last_successful_update":  ch.get("processed_at"),
            "status":                  ch.get("status"),
            "qc":                      ch.get("qc"),
        },
        "composite": composite,
        "region": {"district": "Latur", "state": "Maharashtra",
                   "centroid_lat": 18.4088, "centroid_lon": 76.5604},
    }
    out = DASH / "latest_status.json"
    with out.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"  status  -> {out}")


def build_data_availability() -> None:
    sen = manifest.load(OUT, "sentinel")
    ch  = manifest.load(OUT, "chirps")
    payload = {
        "generated_at": _ts(),
        "sentinel2": {
            "periods": [e["period_id"] for e in sen["entries"] if e["status"] == "success"],
            "failed":  [e["period_id"] for e in sen["entries"] if e["status"] == "failed"],
        },
        "chirps": {
            "periods": [e["period_id"] for e in ch["entries"] if e["status"] == "success"],
            "failed":  [e["period_id"] for e in ch["entries"] if e["status"] == "failed"],
        },
    }
    out = DASH / "data_availability.json"
    with out.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"  avail   -> {out}")


def build_processing_manifest() -> None:
    sen = manifest.load(OUT, "sentinel")
    ch  = manifest.load(OUT, "chirps")
    out = DASH / "processing_manifest.json"
    with out.open("w") as f:
        json.dump({"generated_at": _ts(), "sentinel2": sen, "chirps": ch}, f, indent=2)
    print(f"  manif   -> {out}")


def _village_pci_by_year(vil: pd.DataFrame, year: int) -> dict[int, float | None]:
    """Oliver's PCI per village for a given year, from monthly Rain_mm.

    PCI = 100 * sum(P_i^2) / (sum P_i)^2; missing months excluded from sums.
    """
    result: dict[int, float | None] = {}
    sub = vil[vil["year"] == year]
    for vid, g in sub.groupby("village_idx"):
        p = g["Rain_mm"].dropna().values
        if p.size == 0 or p.sum() == 0:
            result[int(vid)] = None
        else:
            result[int(vid)] = float(100.0 * np.sum(p ** 2) / (np.sum(p) ** 2))
    return result


def build_village_latest_geojson() -> None:
    """Build village_latest.geojson / village_latest.json for the dashboard map.

    Reads village-level indices from data/processed/csv/village_Latur_monthly_indices.csv
    (latest period) and joins them with village polygons from
    data/processed/geojson/village_latest.geojson.  Writes to outputs/Dashboard/.
    """
    import geopandas as gpd
    from shapely.geometry import mapping

    village_csv = OUT / "csv" / "village_Latur_monthly_indices.csv"
    geom_json = OUT / "geojson" / "village_latest.geojson"

    if not village_csv.exists():
        print("  village indices CSV missing; skipping village GeoJSON")
        return
    if not geom_json.exists():
        print("  village geometry GeoJSON missing; skipping village GeoJSON")
        return

    df = pd.read_csv(village_csv)
    df["date"] = df["date"].astype(str)
    latest = df["date"].max()
    latest_df = df[df["date"] == latest].copy()
    latest_year = int(pd.to_datetime(latest, format="%Y-%m").year)

    # Compute Oliver's PCI per village for the latest year (fills CSV nulls).
    village_pci = _village_pci_by_year(df, latest_year)

    # Load geometries keyed by village id.
    gdf_geom = gpd.read_file(geom_json)
    gdf_geom = gdf_geom.to_crs(4326)
    geom_by_id: dict[int, object] = {}
    for _, feat in gdf_geom.iterrows():
        vid = feat.get("id") or feat.get("village_idx")
        if vid is not None:
            try:
                geom_by_id[int(vid)] = feat.geometry
            except (ValueError, TypeError):
                continue

    features: list[dict] = []
    for _, r in latest_df.iterrows():
        try:
            vid = int(r["village_idx"]) if pd.notna(r.get("village_idx")) else None
        except (ValueError, TypeError):
            vid = None
        geom = geom_by_id.get(vid) if vid is not None else None
        if geom is None:
            continue
        contrib = r.get("component_contributions", "")
        try:
            contrib_json = json.loads(contrib) if contrib and str(contrib).strip() else {}
        except (json.JSONDecodeError, TypeError):
            contrib_json = {}
        cdi = r.get("composite_drought_score")
        cdi_cls = r.get("composite_drought_class", "")
        csv_pci = r.get("PCI")
        pci_val = None if pd.isna(csv_pci) else float(csv_pci)
        if pci_val is None:
            pci_val = village_pci.get(vid)
        props = {
            "id": vid,
            "village": r.get("village", ""),
            "tehsil": r.get("tehsil", ""),
            "date": latest,
            "period": latest,
            "NDVI": None if pd.isna(r.get("NDVI")) else float(r["NDVI"]),
            "EVI": None if pd.isna(r.get("EVI")) else float(r["EVI"]),
            "VCI": None if pd.isna(r.get("VCI")) else float(r["VCI"]),
            "VHI": None if pd.isna(r.get("VHI")) else float(r["VHI"]),
            "PCI": pci_val,
            "SPI1": None if pd.isna(r.get("SPI1")) else float(r["SPI1"]),
            "SPI3": None if pd.isna(r.get("SPI3")) else float(r["SPI3"]),
            "SPI6": None if pd.isna(r.get("SPI6")) else float(r["SPI6"]),
            "SPI12": None if pd.isna(r.get("SPI12")) else float(r["SPI12"]),
            "Rain_mm": None if pd.isna(r.get("Rain_mm")) else float(r["Rain_mm"]),
            "CDI": None if pd.isna(cdi) else float(cdi),
            "CDI_class": cdi_cls if pd.notna(cdi_cls) else "",
            "class": cdi_cls if pd.notna(cdi_cls) else "",
            "component_contributions": contrib_json,
            "composite_formula_version": r.get("formula_version", ""),
            "data_quality_status": r.get("data_quality_status", ""),
        }
        features.append({"type": "Feature", "properties": props, "geometry": mapping(geom)})

    fc = {"type": "FeatureCollection", "features": features}
    DASH.mkdir(parents=True, exist_ok=True)
    geojson_path = DASH / "village_latest.geojson"
    json_path = DASH / "village_latest.json"
    with geojson_path.open("w") as f:
        json.dump(fc, f, indent=2)
    with json_path.open("w") as f:
        json.dump({
            "generated_at": _ts(),
            "period": latest,
            "count": len(features),
            "villages": {str(f["properties"]["id"]): f["properties"] for f in features},
        }, f, indent=2)
    print(f"  village geojson -> {geojson_path} ({len(features)} villages, period {latest})")


def main():
    build_master()
    build_latest_status()
    build_data_availability()
    build_processing_manifest()
    build_village_latest_geojson()

    # Load regenerated indices into SQLite so the Node.js gateway (/api/v1)
    # can serve them to the frontend dashboard.
    # Uses build_baseline_drought which fixes EVI scaling, computes baselines,
    # and adds drought-month identification.
    from build_baseline_drought import main as build_baseline_main
    build_baseline_main()

    print("Done.")


if __name__ == "__main__":
    main()
