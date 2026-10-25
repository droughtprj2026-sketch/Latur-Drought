# -*- coding: utf-8 -*-
"""
CHIRPS rainfall from Google Earth Engine (collection UCSB-CHG/CHIRPS/monthly).

Fetches monthly precipitation (mm) for Latur from GEE, aggregates it over
tehsils, and feeds the SPI calculator. Reads manifests/chirps.json first
to process only new or affected months.

Usage:

    python chirps_gee.py --aoi ../data/vector/latur_tehsils.geojson \\
                        --from 2016-01 --to latest

    # or, with environment:
    DATA_DIR=./data/raw OUTPUT_DIR=./data/processed python chirps_gee.py --to latest
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

from common import manifest  # noqa: E402
from common.classify import MONTHS, classify_spi  # noqa: E402

ROOT = HERE.parent
OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
DEFAULT_AOI = ROOT / "frontend" / "public" / "data" / "latur_tehsils.geojson"

# CHIRPS on Earth Engine is published as DAILY and PENTAD collections only (there is no
# monthly collection), so a month is the sum of its daily images.
COLLECTION = "UCSB-CHG/CHIRPS/DAILY"
PRECIP_BAND = "precipitation"            # mm/month
NATIVE_RES = 5566                        # ~5 km, matches CHIRPS native pixel
CALIB_START = os.environ.get("SPI_CALIB_START", "1991-01")
CALIB_END   = os.environ.get("SPI_CALIB_END",   "2020-12")


def _args():
    p = argparse.ArgumentParser(description="CHIRPS monthly from GEE for Latur")
    p.add_argument("--aoi", default=str(DEFAULT_AOI))
    p.add_argument("--from", dest="d_from", default="2016-01")
    p.add_argument("--to",   dest="d_to",   default="latest",
                   help="YYYY-MM, or 'latest' to use whatever GEE has now")
    return p.parse_args()


def _ensure_ee():
    from common.gee import init_ee
    return init_ee()


def _geojson_to_fc(ee, path: Path):
    import geopandas as gpd
    gdf = gpd.read_file(path).to_crs(4326)
    gj = json.loads(gdf.to_json())
    feats = [ee.Feature(ee.Geometry(f["geometry"]), f.get("properties", {}))
             for f in gj["features"]]
    return ee.FeatureCollection(feats)


def _latest_available(ee) -> str:
    """Latest CHIRPS month for which every daily image exists, as 'YYYY-MM'."""
    import calendar
    col = ee.ImageCollection(COLLECTION).sort("system:time_start", False)
    last = ee.Date(col.first().get("system:time_start")).format("YYYY-MM-dd").getInfo()
    y, m, d = (int(x) for x in last.split("-"))
    if d < calendar.monthrange(y, m)[1]:        # last month is still filling up
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return f"{y:04d}-{m:02d}"


def _list_months(d_from: str, d_to: str) -> list[str]:
    sy, sm = (int(x) for x in d_from.split("-"))
    ey, em = (int(x) for x in d_to.split("-"))
    out = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def _zonal_monthly(ee, aoi_fc, period: str):
    """Per-feature monthly rainfall (mm), or None when the month is not fully published."""
    import calendar
    y, m = (int(x) for x in period.split("-"))
    start = ee.Date(f"{period}-01")
    col = (ee.ImageCollection(COLLECTION)
             .filterDate(start, start.advance(1, "month"))
             .select(PRECIP_BAND))
    if int(col.size().getInfo()) < calendar.monthrange(y, m)[1]:
        return None
    stats = col.sum().reduceRegions(
        collection=aoi_fc,
        reducer=ee.Reducer.mean(),
        scale=NATIVE_RES,
        tileScale=2,
    )
    return stats.getInfo().get("features", [])


def main():
    args = _args()
    aoi_path = Path(args.aoi)
    if not aoi_path.exists():
        raise SystemExit(f"AOI not found: {aoi_path}")

    print(f"[1] authenticating to Earth Engine (CHIRPS) ...")
    ee = _ensure_ee()

    d_to = args.d_to
    if d_to == "latest":
        d_to = _latest_available(ee)
        print(f"  latest CHIRPS month published: {d_to}")

    print(f"[2] loading AOI {aoi_path.name} ...")
    aoi_fc = _geojson_to_fc(ee, aoi_path)

    print("[3] consulting manifests/chirps.json for missing months ...")
    all_months = _list_months(args.d_from, d_to)
    missing = manifest.missing_periods(OUT, "chirps", all_months)
    print(f"  {len(missing)}/{len(all_months)} months need processing")

    if not missing:
        print("  nothing to do; manifest is up to date.")
        return

    print("[4] fetching + zonal statistics per missing month ...")
    csv_dir = OUT / "csv"; csv_dir.mkdir(parents=True, exist_ok=True)
    out_csv = csv_dir / "chirps_tehsil_monthly.csv"
    header_needed = not out_csv.exists()
    f = out_csv.open("a")
    if header_needed:
        f.write("period,year,month,tehsil,rain_mm\n")

    affected_spi: set[str] = set()
    for period in missing:
        feats = _zonal_monthly(ee, aoi_fc, period)
        if not feats:
            manifest.record(OUT, "chirps", period,
                            observation_date=period + "-28",
                            status="failed", outputs=[],
                            notes="CHIRPS image not found in GEE")
            continue
        y, m = period.split("-")
        for feat in feats:
            p = feat.get("properties", {})
            tehsil = p.get("TEHSIL") or p.get("name") or ""
            rain = p.get("mean")
            if rain is None:
                continue
            f.write(f"{period},{y},{int(m)},{tehsil},{rain:.3f}\n")
        manifest.record(OUT, "chirps", period,
                        observation_date=period + "-28",
                        status="success",
                        outputs=[f"csv/chirps_tehsil_monthly.csv"],
                        qc={"spatial_coverage_pct": 100})
        affected_spi.update(manifest.affected_periods_for_spi(OUT, period))
        print(f"  recorded {period}")
    f.close()

    print(f"[5] marking {len(affected_spi)} SPI periods as stale "
          f"(latur_chirps_spi.py will pick them up on next run)")
    stale = OUT / "manifests" / "spi_stale.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    with stale.open("w") as sf:
        json.dump({"affected": sorted(affected_spi),
                   "calib_start": CALIB_START,
                   "calib_end": CALIB_END}, sf, indent=2)

    print("\nDone.")


if __name__ == "__main__":
    main()
