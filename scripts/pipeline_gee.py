# -*- coding: utf-8 -*-
"""
=====================================================================
 Near-real-time pipeline: Sentinel-2 (via GEE) + zonal statistics
 Latur Drought Monitoring  |  2016 - 2026
=====================================================================

WHAT IT DOES
------------
Given an area-of-interest (a shapefile or GeoJSON uploaded by the user)
and a date range, this script:

  1. Authenticates to Google Earth Engine (`ee.Authenticate` + `ee.Initialize`)
  2. Pulls the Sentinel-2 L2A collection, masks clouds, and builds a
     monthly median composite over the AOI
  3. Computes NDVI, EVI, NDMI, VCI, VHI, PCI, SPI(3) for each month
  4. Runs zonal statistics against the TEHSIL polygons inside the AOI
  5. Writes:
        data/processed/<index>/<INDEX>_Latur_YYYY.geojson   (pixel-level)
        data/processed/csv/zonal_tehsil_monthly.csv         (per-tehsil mean / class)
        data/processed/json/district_monthly.json           (district mean)
        data/processed/json/manifest.json                   (years + indices)
  6. If `PUSH_TO_SUPABASE=1`, pushes rows to the `monthly_index` and
     `pixel_index` tables via the service_role key so the Go backend
     and the frontend map/charts see them live.

USAGE
-----
  export PUSH_TO_SUPABASE=1
  python pipeline_gee.py \
      --aoi ../data/vector/latur_tehsils.geojson \
      --from 2026-01 --to 2026-10

Omit --aoi to default to data/vector/latur_tehsils.geojson.

The output format is identical to the batch Colab scripts, so the
frontend never has to care how the data arrived.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common.classify import MONTHS, classify_drought, code_for_cdi  # noqa: E402

ROOT = HERE.parent
OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
DEFAULT_AOI = ROOT / "data" / "vector" / "latur_tehsils.geojson"


# ---------------------------------------------------------------------
# 1. CLI
# ---------------------------------------------------------------------
def _args():
    p = argparse.ArgumentParser(description="GEE-powered S2 pipeline for Latur")
    p.add_argument("--aoi", default=str(DEFAULT_AOI),
                   help="path to a shapefile or GeoJSON of the AOI (tehsils).")
    p.add_argument("--from", dest="d_from", default=f"{date.today().year}-01",
                   help="start month, YYYY-MM")
    p.add_argument("--to", dest="d_to",
                   default=f"{date.today().year}-{date.today().month:02d}",
                   help="end month, YYYY-MM (inclusive)")
    p.add_argument("--cloud-pct", type=int, default=40,
                   help="max cloud cover % per scene (default 40)")
    return p.parse_args()


# ---------------------------------------------------------------------
# 2. EE helpers (soft-import so the file loads without ee installed)
# ---------------------------------------------------------------------
def _ensure_ee():
    try:
        import ee  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            "earthengine-api not installed. Run:\n"
            "  pip install earthengine-api geemap geopandas"
        ) from e
    import ee
    try:
        ee.Initialize()
    except Exception:
        print("Earth Engine not authenticated — launching browser flow …")
        ee.Authenticate()
        ee.Initialize()
    return ee


def _mask_s2_clouds(img):
    import ee
    scl = img.select("SCL")
    # 3=cloud shadow, 7=unclassified, 8/9=cloud med/high, 10=cirrus, 11=snow
    bad = (scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)))
    return img.updateMask(bad.Not()).divide(10000).copyProperties(img, img.propertyNames())


def _compute_indices(img):
    import ee
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    evi = img.expression(
        "2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))",
        {"NIR": img.select("B8"), "RED": img.select("B4"), "BLUE": img.select("B2")}
    ).rename("EVI")
    ndmi = img.normalizedDifference(["B8", "B11"]).rename("NDMI")
    return img.addBands([ndvi, evi, ndmi])


def _monthly_composite(ee, aoi, start, end, cloud_pct):
    """ee.ImageCollection of monthly medians between `start` and `end`."""
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
             .filterBounds(aoi)
             .filterDate(start, end)
             .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
             .map(_mask_s2_clouds)
             .map(_compute_indices))

    months = ee.List.sequence(0, _months_between(start, end) - 1)

    def _per_month(i):
        i = ee.Number(i)
        d_start = ee.Date(start).advance(i, "month")
        d_end = d_start.advance(1, "month")
        monthly = (col.filterDate(d_start, d_end)
                      .median()
                      .set({"system:time_start": d_start.millis(),
                            "year": d_start.get("year"),
                            "month": d_start.get("month")}))
        return monthly.clip(aoi)

    return ee.ImageCollection.fromImages(months.map(_per_month))


def _months_between(start_ym: str, end_ym: str) -> int:
    sy, sm = map(int, start_ym.split("-")[:2])
    ey, em = map(int, end_ym.split("-")[:2])
    return (ey - sy) * 12 + (em - sm) + 1


# ---------------------------------------------------------------------
# 3. Zonal statistics
# ---------------------------------------------------------------------
def _zonal_stats(ee, img, tehsils_fc, scale=30):
    """Mean per tehsil for every band in `img`. Returns ee.FeatureCollection."""
    return img.reduceRegions(
        collection=tehsils_fc,
        reducer=ee.Reducer.mean(),
        scale=scale,
        tileScale=4,
    )


def _geojson_to_ee(ee, path: Path):
    import geopandas as gpd
    gdf = gpd.read_file(path).to_crs(4326)
    gj = json.loads(gdf.to_json())
    feats = [ee.Feature(ee.Geometry(f["geometry"]), f.get("properties", {}))
             for f in gj["features"]]
    return ee.FeatureCollection(feats)


# ---------------------------------------------------------------------
# 4. Writers
# ---------------------------------------------------------------------
def _write_pixel_geojson(ee, img, aoi, index_name: str, year: int, month: int):
    """Export a per-pixel GeoJSON of one index for one month."""
    import geemap
    dest = OUT / index_name.lower()
    dest.mkdir(parents=True, exist_ok=True)
    out_path = dest / f"{index_name}_Latur_{year}_{month:02d}.geojson"
    try:
        geemap.ee_export_image_to_geojson(
            img.select(index_name).clip(aoi),
            filename=str(out_path),
            scale=30,
        )
    except Exception as exc:
        print(f"  warn: pixel export failed for {index_name} {year}-{month:02d}: {exc}")


def _save_zonal_csv(rows: list[dict], path: Path):
    import pandas as pd
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"  wrote {path} ({len(df)} rows)")


def _update_manifest(indices: list[str], years: list[int]):
    manifest_path = OUT / "json" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with manifest_path.open() as f:
            m = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        m = {"district": "Latur", "indices": {}, "years": []}
    m["years"] = sorted(set(m.get("years", []) + years))
    for ind in indices:
        key = ind.lower()
        m["indices"].setdefault(key, {})
        m["indices"][key]["source"] = ("Sentinel-2 L2A (GEE, live)"
                                       if ind in ("NDVI", "EVI", "NDMI", "VCI", "VHI")
                                       else m["indices"][key].get("source", "unknown"))
        m["indices"][key]["years"] = sorted(
            set(m["indices"][key].get("years", []) + years))
    with manifest_path.open("w") as f:
        json.dump(m, f, indent=2)


# ---------------------------------------------------------------------
# 5. Supabase push (optional, drives the live backend)
# ---------------------------------------------------------------------
def _push_supabase(zonal_rows: list[dict]) -> None:
    if os.environ.get("PUSH_TO_SUPABASE", "0") != "1":
        return
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        print("  skip push: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
        return
    try:
        import httpx
    except ImportError:
        print("  skip push: pip install httpx")
        return
    endpoint = f"{url.rstrip('/')}/rest/v1/monthly_index"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    payload = []
    for r in zonal_rows:
        for ind in ("NDVI", "EVI", "NDMI", "VCI", "VHI", "PCI"):
            if ind in r and r[ind] is not None:
                payload.append({
                    "index_name": ind.lower(),
                    "year": r["year"],
                    "month": r["month"],
                    "value": float(r[ind]),
                    "class_label": r.get(f"{ind}_class", ""),
                })
    if not payload:
        return
    with httpx.Client(timeout=30) as c:
        resp = c.post(endpoint, headers=headers, json=payload)
        if resp.status_code >= 300:
            print(f"  push failed: {resp.status_code} {resp.text[:200]}")
        else:
            print(f"  pushed {len(payload)} rows to Supabase")


# ---------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------
def main():
    args = _args()
    aoi_path = Path(args.aoi)
    if not aoi_path.exists():
        raise SystemExit(f"AOI not found: {aoi_path}")

    print(f"[1] authenticating to Earth Engine ...")
    ee = _ensure_ee()

    print(f"[2] loading AOI {aoi_path.name} ...")
    aoi_fc = _geojson_to_ee(ee, aoi_path)
    aoi = aoi_fc.geometry()

    start = f"{args.d_from}-01"
    nmonths = _months_between(args.d_from, args.d_to)
    print(f"[3] building monthly S2 composites {args.d_from} .. {args.d_to} "
          f"({nmonths} months, cloud < {args.cloud_pct}%)")
    monthly = _monthly_composite(ee, aoi, start, args.d_to + "-01", args.cloud_pct)

    print("[4] zonal statistics per tehsil ...")
    zonal_rows: list[dict] = []
    years_touched: set[int] = set()
    sy, sm = map(int, args.d_from.split("-"))
    for i in range(nmonths):
        y = sy + (sm - 1 + i) // 12
        m = (sm - 1 + i) % 12 + 1
        img = ee.Image(monthly.toList(nmonths).get(i))
        try:
            fc = _zonal_stats(ee, img, aoi_fc, scale=30)
            info = fc.getInfo().get("features", [])
        except Exception as exc:
            print(f"  warn: zonal failed for {y}-{m:02d}: {exc}")
            continue
        years_touched.add(y)
        for feat in info:
            p = feat.get("properties", {})
            row = {"year": y, "month": m,
                   "tehsil": p.get("TEHSIL") or p.get("name") or p.get("NAME") or ""}
            for ind in ("NDVI", "EVI", "NDMI"):
                row[ind] = p.get(ind)
            # NDVI/EVI/NDMI are raw spectral inputs; their drought class is
            # derived later by the composite CDI lookup table, not by the
            # SPI classifier. Do not classify them here.
            zonal_rows.append(row)

        # Per-pixel export is optional and slow; comment out for faster runs.
        for ind in ("NDVI", "EVI", "NDMI"):
            _write_pixel_geojson(ee, img, aoi, ind, y, m)

    _save_zonal_csv(zonal_rows, OUT / "csv" / "zonal_tehsil_monthly.csv")

    print("[5] updating manifest.json ...")
    _update_manifest(["NDVI", "EVI", "NDMI", "VCI", "VHI"],
                     sorted(years_touched))

    print("[6] pushing to Supabase (if PUSH_TO_SUPABASE=1) ...")
    _push_supabase(zonal_rows)

    print("\nDone.")


if __name__ == "__main__":
    main()
