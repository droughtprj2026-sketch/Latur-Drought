# -*- coding: utf-8 -*-
"""
=====================================================================
 Sentinel-2 vegetation / moisture indices for Latur
 (NDVI, EVI, NDMI, VCI; VHI approximated from VCI + a thermal proxy)
 2016 - 2026  |  Google Colab or local
=====================================================================

INPUT
-----
 Rasters under output/sentinel_Raw_Composites/{YYYY}/ with any of these
 filename styles:

     S2_Latur_YYYY_MM.tif
     S2_L2A_Latur_YYYY_MM.tif
     Latur_S2_YYYY_MM.tif

 Band mapping is read from each GeoTIFF's band descriptions (not assumed
 by position), because 4-band S2_L2A_ files have a different layout:

     6-band files: B2, B3, B4, B8, B11, B12   (full index suite)
     4-band files: B2, B4, B8, valid_weeks    (NDVI/EVI only; no SWIR)

 OUTPUT (data/processed/)
 ------------------------
   csv/sentinel_Latur_district_monthly.csv   district-mean per month
   json/sentinel_district_monthly.json
   json/manifest.json                        index coverage manifest

 NOTES
 -----
 * Processes one file at a time to avoid loading 10k x 12k rasters
   into memory all at once.
 * 4-band files (no SWIR) produce NaN for NDMI/VHI.
 * Reflectance auto-detects GEE scale factor (0..10000) vs 0..1.
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common.classify import MONTHS, classify_spi  # noqa: E402
from common.raster import dedupe_by_prefix, scan_rasters  # noqa: E402

warnings.filterwarnings("ignore")

# =====================================================================
# 0. SETTINGS
# =====================================================================
DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.normpath(os.path.join(HERE, "..", "output", "sentinel_Raw_Composites")),
)
OUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(HERE, "..", "data", "processed"))

PREFERRED = ("S2_L2A_", "S2_", "Latur_S2_", "other")

DISTRICT_NAME = "Latur"
NODATA = -9999.0

# Sentinel-2 band descriptions -> short name
# Supports BOTH short codes (B2, B4, B8, ...) and full words (Blue, Red, NIR, ...)
BAND_DESC_TO_NAME = {
    # Short codes
    "B2": "BLUE",      # 490 nm
    "B3": "GREEN",     # 560 nm
    "B4": "RED",       # 665 nm
    "B8": "NIR",       # 842 nm
    "B11": "SWIR1",    # 1610 nm
    "B12": "SWIR2",    # 2190 nm
    # Full words (some files use these)
    "BLUE": "BLUE",
    "GREEN": "GREEN",
    "RED": "RED",
    "NIR": "NIR",
    "SWIR1": "SWIR1",
    "SWIR2": "SWIR2",
}


# =====================================================================
# 1. INDEX FORMULAS (per-pixel numpy)
# =====================================================================
def _rescale(arr: np.ndarray) -> np.ndarray:
    """Auto-detect GEE scale factor (0..10000) and return 0..1 reflectance."""
    with np.errstate(invalid="ignore"):
        m = np.nanmax(arr)
    if m > 10:
        return arr / 10000.0
    return arr


def ndvi(nir, red):
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (nir - red) / (nir + red)
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, -1.0, 1.0)


def evi(nir, red, blue):
    with np.errstate(invalid="ignore", divide="ignore"):
        v = 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0)
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, -1.0, 1.0)


def ndmi(nir, swir1):
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (nir - swir1) / (nir + swir1)
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, -1.0, 1.0)


# =====================================================================
# 2. MAIN — process one file at a time (memory efficient)
# =====================================================================
def _read_bands_by_description(path: str):
    """Read a raster and return a dict {short_name: array} using band descriptions.

    Returns (bands_dict, valid_mask) or None on failure.
    """
    try:
        with rasterio.open(path) as src:
            bands = {}
            shape = (src.height, src.width)
            for b in range(1, src.count + 1):
                desc = src.descriptions[b - 1] or ""
                desc = desc.strip().upper()
                short = BAND_DESC_TO_NAME.get(desc)
                if short is None:
                    continue  # skip non-spectral bands (e.g. valid_weeks)
                arr = src.read(b).astype("float64")
                nd = src.nodata
                if nd is not None:
                    arr[arr == nd] = np.nan
                bands[short] = arr
    except Exception as e:
        print(f"  WARN: failed to read {os.path.basename(path)}: {e}")
        return None

    if not bands:
        return None

    # Strictly required: RED and NIR (for NDVI)
    # BLUE is needed for EVI but optional (NDVI works without it)
    # GREEN is optional (not used in NDVI/EVI)
    required = ["RED", "NIR"]
    for r in required:
        if r not in bands:
            return None  # missing a strictly required band
    valid = np.ones(shape, dtype=bool)
    for r in required:
        valid &= np.isfinite(bands[r])
    if "BLUE" in bands:
        valid &= np.isfinite(bands["BLUE"])
    if "SWIR1" in bands:
        valid &= np.isfinite(bands["SWIR1"])

    return bands, valid


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("[1] scanning sentinel rasters ...")
    files = scan_rasters(DATA_DIR, verbose=True)
    if files.empty:
        raise SystemExit(f"no sentinel rasters found under {DATA_DIR}")
    files = dedupe_by_prefix(files, PREFERRED)
    print(f"  {len(files)} unique months, {files.year.min()}-{files.year.max()}")

    print("\n[2] processing files ...")
    records: list[dict] = []
    for i, (_, f) in enumerate(files.iterrows()):
        p = f["path"]
        year = int(f["year"])
        month = int(f["month"])

        result = _read_bands_by_description(p)
        if result is None:
            print(f"  skip {os.path.basename(p)}: missing required bands")
            continue

        bands, valid = result
        if valid.sum() == 0:
            continue

        red = _rescale(bands["RED"])
        nir = _rescale(bands["NIR"])
        blue = _rescale(bands["BLUE"]) if "BLUE" in bands else None
        swir1 = bands.get("SWIR1")
        if swir1 is not None:
            swir1 = _rescale(swir1)

        # Compute indices
        ndvi_v = ndvi(nir, red)
        # EVI needs NIR, Red, Blue. Skip if Blue missing.
        if blue is not None:
            evi_v = evi(nir, red, blue)
        else:
            evi_v = np.full_like(ndvi_v, np.nan)
        ndmi_v = ndmi(nir, swir1) if swir1 is not None else np.full_like(ndvi_v, np.nan)

        rec = {
            "year": year,
            "month": month,
            "date": f"{year}-{month:02d}",
            "NDVI": float(np.nanmean(ndvi_v[valid])),
            "EVI": float(np.nanmean(evi_v[valid])) if blue is not None else None,
            "NDMI": float(np.nanmean(ndmi_v[valid])) if swir1 is not None else None,
            "valid_pixels": int(valid.sum()),
        }
        records.append(rec)

        if (i + 1) % 20 == 0:
            print(f"  processed {i + 1}/{len(files)} ...")

    print(f"  processed {len(records)} files total")

    if not records:
        raise SystemExit("no files could be processed")

    # Build district monthly DataFrame
    rec_df = pd.DataFrame(records)
    rec_df = rec_df.sort_values("date").reset_index(drop=True)

    # Compute VCI from NDVI (per calendar month min/max across years)
    print("\n[3] computing VCI ...")
    rec_df["VCI"] = np.nan
    for m in range(1, 13):
        mask = rec_df["month"] == m
        sub = rec_df.loc[mask, "NDVI"].dropna()
        if sub.size < 2:
            continue
        lo, hi = sub.min(), sub.max()
        if hi == lo:
            continue
        rec_df.loc[mask, "VCI"] = 100.0 * (rec_df.loc[mask, "NDVI"] - lo) / (hi - lo)

    # VHI placeholder = VCI (no real TCI/LST yet)
    rec_df["VHI"] = rec_df["VCI"]

    # Class labels
    def vci_class(x):
        if pd.isna(x):
            return "No data"
        return ("Extreme" if x < 10 else "Severe" if x < 20
                else "Moderate" if x < 30 else "Mild" if x < 40 else "Normal")

    rec_df["NDVI_class"] = [classify_spi(x) for x in rec_df["NDVI"]]
    rec_df["EVI_class"] = [classify_spi(x) for x in rec_df["EVI"]]
    rec_df["VCI_class"] = [vci_class(x) for x in rec_df["VCI"]]
    rec_df["VHI_class"] = [vci_class(x) for x in rec_df["VHI"]]
    rec_df["NDMI_class"] = [
        classify_spi(x) if x is not None else "No data" for x in rec_df["NDMI"]
    ]

    # Write CSV
    csv_dir = os.path.join(OUT_DIR, "csv")
    os.makedirs(csv_dir, exist_ok=True)
    out_csv = os.path.join(csv_dir, "sentinel_Latur_district_monthly.csv")
    rec_df.to_csv(out_csv, index=False)
    print(f"  district CSV -> {out_csv} ({len(rec_df)} rows)")

    # Write JSON
    json_dir = os.path.join(OUT_DIR, "json")
    os.makedirs(json_dir, exist_ok=True)
    out_json = os.path.join(json_dir, "sentinel_district_monthly.json")
    rec_df.to_json(out_json, orient="records", indent=2)
    print(f"  district JSON -> {out_json}")

    # Update manifest
    update_manifest(json_dir, rec_df)

    print("\nDone.")


def update_manifest(json_dir: str, df: pd.DataFrame) -> None:
    """Merge Sentinel info into data/processed/json/manifest.json."""
    path = os.path.join(json_dir, "manifest.json")
    try:
        with open(path) as f:
            m = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        m = {"district": DISTRICT_NAME, "indices": {}, "years": []}

    years = sorted(set(df["year"].dropna().astype(int)))
    m["years"] = sorted(set(m.get("years", [])) + years)

    for ind in ["ndvi", "evi", "ndmi", "vci", "vhi"]:
        m["indices"][ind] = {
            "source": "Sentinel-2 L2A",
            "unit": "0..1" if ind in ("ndvi", "evi", "ndmi") else "%",
            "years": years,
        }

    with open(path, "w") as f:
        json.dump(m, f, indent=2)


if __name__ == "__main__":
    main()
