# -*- coding: utf-8 -*-
"""
Google Colab Execution Script: Latur Sentinel-2 Zonal Drought Indices & CDI Pipeline
=====================================================================================
Usage in Google Colab:
  1. Open a new Google Colab notebook (Python 3, CPU or T4 GPU).
  2. Run the first cell to mount Google Drive and install requirements:
       from google.colab import drive
       drive.mount('/content/drive')
       !pip install rasterio shapely pyproj geopandas tqdm
  3. Upload your Sentinel GeoTIFFs to a Google Drive folder (e.g., /content/drive/MyDrive/sentinel/)
     and vector files (latur_tehsils.geojson, latur_villages.geojson).
  4. Run this script:
       !python colab_sentinel_pipeline.py --sentinel-dir "/content/drive/MyDrive/sentinel" --out-dir "/content/drive/MyDrive/output"
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path
import numpy as np

try:
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import transform_geom
except ImportError:
    print("Installing rasterio...")
    os.system("pip install rasterio shapely pyproj")
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import transform_geom

BAND_MAP = {
    "BLUE": 1, "GREEN": 2, "RED": 3, "NIR": 4, "SWIR1": 5, "SWIR2": 6
}

FILENAME_PATTERNS = [
    re.compile(r"^S2_L2A_Latur_(\d{4})_(\d{1,2})\.tif$", re.I),
    re.compile(r"^S2_Latur_(\d{4})_(\d{1,2})\.tif$", re.I),
    re.compile(r"^Latur_S2_(\d{4})_(\d{1,2})\.tif$", re.I),
    re.compile(r"^Latur_(\d{4})_(\d{1,2})\.tif$", re.I),
]

def parse_filename(name):
    if any(name.lower().endswith(ext) for ext in [".aux.xml", ".ovr", ".crdownload", ".py", ".zip", ".csv"]):
        return None
    for pat in FILENAME_PATTERNS:
        m = pat.match(name)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None

def compute_indices(red, nir, blue, swir1):
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
        evi = 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0)
        ndmi = (nir - swir1) / (nir + swir1)

    ndvi[~np.isfinite(ndvi)] = np.nan
    evi[~np.isfinite(evi)] = np.nan
    ndmi[~np.isfinite(ndmi)] = np.nan
    return np.clip(ndvi, -1.0, 1.0), np.clip(evi, -1.0, 1.0), np.clip(ndmi, -1.0, 1.0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentinel-dir", type=str, required=True, help="Directory with Sentinel GeoTIFFs")
    parser.add_argument("--tehsils-geojson", type=str, default="latur_tehsils.geojson")
    parser.add_argument("--villages-geojson", type=str, default="latur_villages.geojson")
    parser.add_argument("--out-dir", type=str, default="./output_zonal")
    args = parser.parse_args()

    s_dir = Path(args.sentinel_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for f in s_dir.rglob("*.tif"):
        parsed = parse_filename(f.name)
        if parsed:
            files.append({"path": f, "year": parsed[0], "month": parsed[1]})
    
    files.sort(key=lambda x: (x["year"], x["month"]))
    print(f"Discovered {len(files)} Sentinel-2 scenes.")

    if not Path(args.tehsils_geojson).exists():
        print(f"Warning: {args.tehsils_geojson} not found.")
        return

    with open(args.tehsils_geojson, "r", encoding="utf-8") as f:
        tehsil_gj = json.load(f)

    results = []
    for i, item in enumerate(files):
        y, m, fpath = item["year"], item["month"], item["path"]
        print(f"[{i+1}/{len(files)}] Processing {y}-{m:02d} ({fpath.name})...")
        with rasterio.open(fpath) as src:
            for feat in tehsil_gj["features"]:
                tname = feat["properties"].get("TEHSIL") or feat["properties"].get("name")
                geom = feat["geometry"]
                if src.crs and src.crs != "EPSG:4326":
                    geom = transform_geom("EPSG:4326", src.crs, geom)
                try:
                    img, _ = mask(src, [geom], crop=True)
                    scale = 10000.0 if np.nanmax(img) > 10 else 1.0
                    b = img[BAND_MAP["BLUE"] - 1].astype("float32") / scale
                    r = img[BAND_MAP["RED"] - 1].astype("float32") / scale
                    nir = img[BAND_MAP["NIR"] - 1].astype("float32") / scale
                    swir1 = img[BAND_MAP["SWIR1"] - 1].astype("float32") / scale

                    ndvi, evi, ndmi = compute_indices(r, nir, b, swir1)
                    results.append({
                        "tehsil": tname,
                        "year": y,
                        "month": m,
                        "date": f"{y}-{m:02d}",
                        "NDVI": round(float(np.nanmean(ndvi)), 4),
                        "EVI": round(float(np.nanmean(evi)), 4),
                        "NDMI": round(float(np.nanmean(ndmi)), 4),
                    })
                except Exception as ex:
                    continue

    out_csv = out_dir / "tehsil_sentinel_indices.csv"
    if results:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
        print(f"Completed! Output written to {out_csv}")

if __name__ == "__main__":
    main()
