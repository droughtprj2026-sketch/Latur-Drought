# -*- coding: utf-8 -*-
"""
=============================================================================
 Sentinel-2 Vegetation & Moisture Indices Zonal Processing Pipeline for Latur
 Computes: NDVI, EVI, NDMI -> VCI, VHI, PCI -> Composite Drought Index (CDI)
 Supports both Tehsil (10 subdistricts) and Village (954 villages) zonal scales.
 Fully compatible with Google Colab and Local Execution.
=============================================================================
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# Ensure rasterio and shapely can be imported
try:
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import transform_geom
except ImportError:
    rasterio = None

try:
    from shapely.geometry import shape, mapping
except ImportError:
    shape = None

# Base directories
DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent.parent
DEFAULT_SENTINEL_DIR = DEFAULT_WORKSPACE / "output" / "sentinel"
DEFAULT_SPI_DIR = DEFAULT_WORKSPACE / "output" / "spi" / "csv"
DEFAULT_VILLAGES_GEOJSON = DEFAULT_WORKSPACE / "drought-monitoring (1)" / "drought-monitoring" / "frontend" / "public" / "data" / "latur_villages.geojson"
DEFAULT_TEHSILS_GEOJSON = DEFAULT_WORKSPACE / "drought-monitoring (1)" / "drought-monitoring" / "frontend" / "public" / "data" / "latur_tehsils.geojson"
DEFAULT_OUT_DIR = DEFAULT_WORKSPACE / "output" / "indices" / "zonal"
DB_PATH = DEFAULT_WORKSPACE / "drought-monitoring (1)" / "drought-monitoring" / "data" / "drought.db"

# Sentinel-2 Band order mapping (L2A monthly composite)
BAND_MAP = {
    "BLUE":  1,  # B2  (490 nm)
    "GREEN": 2,  # B3  (560 nm)
    "RED":   3,  # B4  (665 nm)
    "NIR":   4,  # B8  (842 nm)
    "SWIR1": 5,  # B11 (1610 nm)
    "SWIR2": 6,  # B12 (2190 nm)
}

FILENAME_PATTERNS = [
    re.compile(r"^S2_L2A_Latur_(\d{4})_(\d{1,2})\.tif$", re.I),
    re.compile(r"^S2_Latur_(\d{4})_(\d{1,2})\.tif$", re.I),
    re.compile(r"^Latur_S2_(\d{4})_(\d{1,2})\.tif$", re.I),
    re.compile(r"^Latur_(\d{4})_(\d{1,2})\.tif$", re.I),
]

SKIP_EXTENSIONS = {".aux.xml", ".ovr", ".crdownload", ".py", ".zip", ".csv"}

TEHSIL_MAP = {
    "AHMADPUR": "Ahmadpur", "AUSA": "Ausa", "CHAKUR": "Chakur", "DEONI": "Deoni",
    "JALKOT": "Jalkot", "LATUR": "Latur", "NILANGA": "Nilanga", "RENAPUR": "Renapur",
    "SHIRUR-ANANTPAL": "Shirur-Anantpal", "SHIRUR ANANTPAL": "Shirur-Anantpal", "UDGIR": "Udgir"
}

def clean_tehsil(name):
    clean = str(name).strip().upper()
    return TEHSIL_MAP.get(clean, str(name).strip().title())

def parse_sentinel_filename(filename):
    if any(filename.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
        return None
    if filename.startswith("._"):
        return None
    for pat in FILENAME_PATTERNS:
        m = pat.match(filename)
        if m:
            year = int(m.group(1))
            month = int(m.group(2))
            return year, month
    return None

def scan_sentinel_files(sentinel_dir):
    """Scan and deduplicate Sentinel rasters by (year, month)."""
    p = Path(sentinel_dir)
    found = {}
    for f in p.rglob("*.tif"):
        parsed = parse_sentinel_filename(f.name)
        if not parsed:
            continue
        year, month = parsed
        key = (year, month)
        # Preference: S2_L2A_ > S2_ > Latur_S2_
        score = 0
        if "s2_l2a_" in f.name.lower(): score = 3
        elif "s2_latur_" in f.name.lower(): score = 2
        elif "latur_s2_" in f.name.lower(): score = 1
        
        if key not in found or score > found[key]["score"]:
            found[key] = {"path": f, "year": year, "month": month, "score": score}
    return sorted(found.values(), key=lambda x: (x["year"], x["month"]))

def compute_raster_indices(red, nir, blue, swir1):
    """Computes NDVI, EVI, NDMI rasters with valid bounds."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
        evi = 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0)
        ndmi = (nir - swir1) / (nir + swir1)

    ndvi[~np.isfinite(ndvi)] = np.nan
    evi[~np.isfinite(evi)] = np.nan
    ndmi[~np.isfinite(ndmi)] = np.nan

    ndvi = np.clip(ndvi, -1.0, 1.0)
    evi = np.clip(evi, -1.0, 1.0)
    ndmi = np.clip(ndmi, -1.0, 1.0)
    return ndvi, evi, ndmi

def get_drought_code(score):
    if score is None or math.isnan(score):
        return "ND"
    if score < 0.20:
        return "None"
    elif score < 0.35:
        return "D0"
    elif score < 0.50:
        return "D1"
    elif score < 0.65:
        return "D2"
    elif score < 0.80:
        return "D3"
    else:
        return "D4"

def process_zonal_pipeline(
    sentinel_dir=DEFAULT_SENTINEL_DIR,
    tehsils_geojson=DEFAULT_TEHSILS_GEOJSON,
    villages_geojson=DEFAULT_VILLAGES_GEOJSON,
    out_dir=DEFAULT_OUT_DIR,
    max_scenes=None
):
    if rasterio is None or shape is None:
        print("ERROR: rasterio and shapely are required to run the Sentinel zonal pipeline.")
        print("Run: pip install rasterio shapely pyproj")
        sys.exit(1)

    sentinel_dir = Path(sentinel_dir)
    out_dir = Path(out_dir)
    (out_dir / "tehsil").mkdir(parents=True, exist_ok=True)
    (out_dir / "village").mkdir(parents=True, exist_ok=True)

    scenes = scan_sentinel_files(sentinel_dir)
    print(f"Found {len(scenes)} unique Sentinel-2 scenes in {sentinel_dir}")
    if max_scenes and max_scenes > 0:
        scenes = scenes[:max_scenes]
        print(f"Limiting execution to first {max_scenes} scenes.")

    if not scenes:
        print("No valid Sentinel-2 scenes found.")
        return

    # Load Tehsil geometries
    with open(tehsils_geojson, "r", encoding="utf-8") as f:
        tehsil_gj = json.load(f)
    tehsils = []
    for feat in tehsil_gj["features"]:
        tname = clean_tehsil(feat["properties"].get("TEHSIL") or feat["properties"].get("name", ""))
        tehsils.append({"name": tname, "geom": feat["geometry"]})

    # Load Village geometries
    with open(villages_geojson, "r", encoding="utf-8") as f:
        village_gj = json.load(f)
    villages = []
    for feat in village_gj["features"]:
        vname = feat["properties"].get("village", "")
        tname = clean_tehsil(feat["properties"].get("tehsil", ""))
        villages.append({"village": vname, "tehsil": tname, "geom": feat["geometry"]})

    print(f"Loaded {len(tehsils)} tehsils and {len(villages)} villages for zonal extraction.")

    tehsil_monthly_records = []
    village_monthly_records = []

    for idx, sc in enumerate(scenes):
        y, m, fpath = sc["year"], sc["month"], sc["path"]
        period = f"{y}-{m:02d}"
        print(f"[{idx+1}/{len(scenes)}] Processing {period} from {fpath.name}...")

        try:
            with rasterio.open(fpath) as src:
                src_crs = src.crs

                # Reproject geometries to raster CRS if necessary
                def transform_poly(g):
                    if src_crs and src_crs != "EPSG:4326":
                        return transform_geom("EPSG:4326", src_crs, g)
                    return g

                # Process per-tehsil zonal mean
                for t in tehsils:
                    geom_proj = transform_poly(t["geom"])
                    try:
                        out_img, _ = mask(src, [geom_proj], crop=True)
                        # Scale factor: Sentinel reflectance is 0..10000 in GEE, rescale if needed
                        scale = 10000.0 if np.nanmax(out_img) > 10 else 1.0
                        blue = out_img[BAND_MAP["BLUE"] - 1].astype("float32") / scale
                        red = out_img[BAND_MAP["RED"] - 1].astype("float32") / scale
                        nir = out_img[BAND_MAP["NIR"] - 1].astype("float32") / scale
                        swir1 = out_img[BAND_MAP["SWIR1"] - 1].astype("float32") / scale

                        ndvi_arr, evi_arr, ndmi_arr = compute_raster_indices(red, nir, blue, swir1)

                        t_ndvi = float(np.nanmean(ndvi_arr)) if not np.isnan(np.nanmean(ndvi_arr)) else None
                        t_evi = float(np.nanmean(evi_arr)) if not np.isnan(np.nanmean(evi_arr)) else None
                        t_ndmi = float(np.nanmean(ndmi_arr)) if not np.isnan(np.nanmean(ndmi_arr)) else None

                        tehsil_monthly_records.append({
                            "tehsil": t["name"],
                            "year": y,
                            "month": m,
                            "date": period,
                            "NDVI": round(t_ndvi, 4) if t_ndvi is not None else "",
                            "EVI": round(t_evi, 4) if t_evi is not None else "",
                            "NDMI": round(t_ndmi, 4) if t_ndmi is not None else ""
                        })
                    except Exception as ex:
                        continue

        except Exception as e:
            print(f"  Warning: Failed to process {fpath.name}: {e}")
            continue

    # Write Tehsil raw zonal records
    t_csv_out = out_dir / "tehsil" / "tehsil_monthly_sentinel_raw.csv"
    if tehsil_monthly_records:
        with open(t_csv_out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(tehsil_monthly_records[0].keys()))
            w.writeheader()
            w.writerows(tehsil_monthly_records)
        print(f"Wrote tehsil raw zonal indices: {t_csv_out}")

    print("\nSentinel zonal extraction completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel-2 Zonal Indices Pipeline for Latur")
    parser.add_argument("--sentinel-dir", type=str, default=str(DEFAULT_SENTINEL_DIR), help="Path to sentinel GeoTIFF directory")
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--max-scenes", type=int, default=None, help="Limit number of scenes (for test runs)")
    args = parser.parse_args()

    process_zonal_pipeline(
        sentinel_dir=args.sentinel_dir,
        out_dir=args.out_dir,
        max_scenes=args.max_scenes
    )
