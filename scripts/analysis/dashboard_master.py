# -*- coding: utf-8 -*-
"""
Build the dashboard-ready master table and the availability / manifest JSONs.
latest_status.json is owned by scripts/realtime/realtime_update.py and is not written here.

Writes:
  outputs/Dashboard/drought_monitoring_master.csv   (village rows + tehsil aggregate rows)
  outputs/Dashboard/data_availability.json
  outputs/Dashboard/processing_manifest.json

The Random Forest classifier has been retired. The final drought class is
produced by scripts/historical/composite_cdi.py from a transparent weighted multi-index
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

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from common import manifest                          # noqa: E402

ROOT = HERE.parent
OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
DASH = ROOT / "outputs" / "Dashboard"
DASH.mkdir(parents=True, exist_ok=True)

MASTER_COLUMNS = [
    "district", "tehsil", "village",
    "observation_date", "observation_period", "year", "month",
    "monthly_rainfall_mm", "chirps_data_through",
    "SPI_1", "SPI_3", "SPI_6", "SPI_12", "SPI_reference_period",
    "NDVI", "EVI", "VCI", "VHI", "NSMI",
    "composite_drought_score", "composite_drought_class",
    "component_contributions", "composite_formula_version",
    "drought_area_km2", "drought_percentage", "total_polygon_area_km2",
    "sentinel2_observation_date", "sentinel2_cloud_percentage",
    "data_quality_status", "processing_timestamp",
    "processing_run_id",
]


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


PANEL_CSV = ROOT / "data" / "processed" / "csv" / "village_Latur_monthly_indices.csv"
VILLAGES_GEOJSON = ROOT / "frontend" / "public" / "data" / "latur_villages_latest.geojson"
DROUGHT_CLASSES = ("D0", "D1", "D2", "D3", "D4")


def _polygons() -> tuple[dict[int, float], str]:
    """Village polygon areas (km2) by id, and the district name, both read from the polygons."""
    gj = json.loads(VILLAGES_GEOJSON.read_text(encoding="utf-8"))
    area = {int(f["properties"]["id"]): float(f["properties"].get("AREA_SQKM") or 0.0) for f in gj["features"]}
    names = sorted({str(f["properties"].get("DISTRICT", "")).strip() for f in gj["features"]} - {""})
    return area, ", ".join(names)


def build_master() -> pd.DataFrame:
    """One row per village and month, plus one aggregate row per tehsil and month (village == "").

    Everything comes from the scored village panel: tehsil values are village means, and the drought share is
    the polygon area in D0-D4 over the area that has a score. Nothing is copied from the district series.
    """
    from common.village_cdi import _classify, _load_cfg
    cfg = _load_cfg()
    panel = pd.read_csv(PANEL_CSV, keep_default_na=False, na_values=[""], low_memory=False)
    panel["date"] = panel["date"].astype(str)
    area, district = _polygons()
    panel["area"] = panel["village_idx"].map(area)
    ref = f"{int(panel['year'].min())}-{int(panel['year'].max())}"
    ts, d = _ts(), panel["date"]

    villages = pd.DataFrame({
        "district": district, "tehsil": panel["tehsil"], "village": panel["village"],
        "observation_date": d + "-15", "observation_period": d, "year": panel["year"], "month": panel["month"],
        "monthly_rainfall_mm": panel["Rain_mm"].round(2),
        "chirps_data_through": np.where(panel["Rain_mm"].notna(), d + "-28", ""),
        "SPI_1": panel["SPI1"].round(3), "SPI_3": panel["SPI3"].round(3),
        "SPI_6": panel["SPI6"].round(3), "SPI_12": panel["SPI12"].round(3), "SPI_reference_period": ref,
        "NDVI": panel["NDVI"].round(4), "EVI": panel["EVI"].round(4), "VCI": panel["VCI"].round(2),
        "VHI": panel["VHI"].round(2), "NSMI": panel["NSMI"].round(4),
        "composite_drought_score": panel["composite_drought_score"].round(4),
        "composite_drought_class": panel["composite_drought_class"],
        "component_contributions": panel["component_contributions"],
        "composite_formula_version": panel["formula_version"],
        "drought_area_km2": "", "drought_percentage": "", "total_polygon_area_km2": panel["area"].round(3),
        "sentinel2_observation_date": np.where(panel["NDVI"].notna(), d + "-15", ""),
        "sentinel2_cloud_percentage": "",
        "data_quality_status": panel["data_quality_status"],
        "processing_timestamp": ts, "processing_run_id": "run-" + d,
    })

    key = ["tehsil", "date"]
    scored = panel[panel["composite_drought_score"].notna()]
    agg = panel.groupby(key).agg(
        year=("year", "first"), month=("month", "first"), rain=("Rain_mm", "mean"),
        spi1=("SPI1", "mean"), spi3=("SPI3", "mean"), spi6=("SPI6", "mean"), spi12=("SPI12", "mean"),
        ndvi=("NDVI", "mean"), evi=("EVI", "mean"), vci=("VCI", "mean"), vhi=("VHI", "mean"),
        nsmi=("NSMI", "mean"), cdi=("composite_drought_score", "mean"), total_area=("area", "sum"),
    ).reset_index()
    assessed = scored.groupby(key)["area"].sum().rename("assessed")
    dry = scored[scored["composite_drought_class"].isin(DROUGHT_CLASSES)].groupby(key)["area"].sum().rename("dry")
    agg = agg.join(assessed, on=key).join(dry, on=key)
    agg["dry"] = agg["dry"].fillna(0.0).where(agg["assessed"].notna())
    a = agg["date"]
    tehsils = pd.DataFrame({
        "district": district, "tehsil": agg["tehsil"], "village": "",
        "observation_date": a + "-15", "observation_period": a, "year": agg["year"], "month": agg["month"],
        "monthly_rainfall_mm": agg["rain"].round(2),
        "chirps_data_through": np.where(agg["rain"].notna(), a + "-28", ""),
        "SPI_1": agg["spi1"].round(3), "SPI_3": agg["spi3"].round(3),
        "SPI_6": agg["spi6"].round(3), "SPI_12": agg["spi12"].round(3), "SPI_reference_period": ref,
        "NDVI": agg["ndvi"].round(4), "EVI": agg["evi"].round(4), "VCI": agg["vci"].round(2),
        "VHI": agg["vhi"].round(2), "NSMI": agg["nsmi"].round(4),
        "composite_drought_score": agg["cdi"].round(4),
        "composite_drought_class": [_classify(v, cfg["thresholds"]) for v in agg["cdi"]],
        "component_contributions": "{}", "composite_formula_version": cfg["formula_version"],
        "drought_area_km2": agg["dry"].round(1),
        "drought_percentage": (100.0 * agg["dry"] / agg["assessed"].where(agg["assessed"] > 0)).round(1),
        "total_polygon_area_km2": agg["total_area"].round(3),
        "sentinel2_observation_date": np.where(agg["ndvi"].notna(), a + "-15", ""),
        "sentinel2_cloud_percentage": "",
        "data_quality_status": np.where(agg["cdi"].notna(), "success", "pending"),
        "processing_timestamp": ts, "processing_run_id": "run-" + a,
    })

    df = pd.concat([tehsils, villages], ignore_index=True)[MASTER_COLUMNS]
    df = df.sort_values(["observation_period", "tehsil", "village"], kind="stable").reset_index(drop=True)
    df = df.where(pd.notna(df), "")
    out_path = DASH / "drought_monitoring_master.csv"
    df.to_csv(out_path, index=False)
    print(f"  master -> {out_path} ({len(df)} rows, {df['observation_period'].nunique()} periods)")
    return df


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

    df = pd.read_csv(village_csv, keep_default_na=False, na_values=[""])
    df["date"] = df["date"].astype(str)
    latest = df["date"].max()
    latest_df = df[df["date"] == latest].copy()


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
            "NSMI": None if pd.isna(r.get("NSMI")) else float(r["NSMI"]),
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
    build_data_availability()
    build_processing_manifest()
    build_village_latest_geojson()

    # Load regenerated indices into SQLite so the Node.js gateway (/api/v1)
    # can serve them to the frontend dashboard.
    # Uses build_baseline_drought which fixes EVI scaling, computes baselines,
    # and adds drought-month identification.
    from analysis.build_baseline_drought import main as build_baseline_main
    build_baseline_main()

    print("Done.")


if __name__ == "__main__":
    main()
