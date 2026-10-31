#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export NDMI and NSMI GeoTIFF Rasters and Separate Deliverable Files (CSV & Excel)
================================================================================
Formulas:
  NDMI = (NIR - SWIR1) / (NIR + SWIR1)   [Gao 1996; Sentinel-2 B8 & B11]
  NSMI = (SWIR1 - SWIR2) / (SWIR1 + SWIR2) [Normalized Soil Moisture Index; Boles 2020; B11 & B12]

Outputs:
  - GeoTIFF Rasters (100 m, EPSG:32643, LZW compressed):
      output/indices/rasters/NDMI/NDMI_YYYY-MM.tif
      output/indices/rasters/NSMI/NSMI_YYYY-MM.tif
      data/processed/ndmi/NDMI_YYYY-MM.tif
      data/processed/nsmi/NSMI_YYYY-MM.tif
  - Separate CSV files:
      data/processed/csv/village_Latur_monthly_NDMI.csv
      data/processed/csv/village_Latur_monthly_NSMI.csv
  - Separate Master Excel Workbooks:
      data/processed/excel/Latur_village_NDMI_2016_2026.xlsx
      data/processed/excel/Latur_village_NSMI_2016_2026.xlsx
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject as warp_reproject, Resampling

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pipeline_rerun_2016_2026 import scan_sentinel, read_bands, _rescale_dn, ndmi, nsmi

ROOT = HERE.parent
DEFAULT_SENTINEL = ROOT / "output" / "sentinel_Raw_Composites"
RASTERS_IN = ROOT / "output" / "indices" / "rasters"
DATA_PROCESSED = ROOT / "data" / "processed"

DIR_NDMI_OUT1 = RASTERS_IN / "NDMI"
DIR_NSMI_OUT1 = RASTERS_IN / "NSMI"
DIR_NDMI_OUT2 = DATA_PROCESSED / "ndmi"
DIR_NSMI_OUT2 = DATA_PROCESSED / "nsmi"

for d in [DIR_NDMI_OUT1, DIR_NSMI_OUT1, DIR_NDMI_OUT2, DIR_NSMI_OUT2]:
    d.mkdir(parents=True, exist_ok=True)

(DATA_PROCESSED / "csv").mkdir(parents=True, exist_ok=True)
(DATA_PROCESSED / "excel").mkdir(parents=True, exist_ok=True)


def link_or_copy(src: Path, dst: Path):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except Exception:
        import shutil
        shutil.copy2(src, dst)


def main():
    print("=" * 70)
    print("Exporting NDMI & NSMI GeoTIFF Rasters & Separate Village Tables (2016-2026)")
    print("=" * 70)

    # 1. Obtain reference grid from existing NDVI raster
    sample_ndvi = next((RASTERS_IN / "NDVI").glob("NDVI_*.tif"), None)
    if not sample_ndvi:
        raise SystemExit("No reference NDVI rasters found in output/indices/rasters/NDVI")

    with rasterio.open(sample_ndvi) as f_ref:
        ref_meta = f_ref.meta.copy()
        ref_shape = (f_ref.height, f_ref.width)
        ref_transform = f_ref.transform
        ref_crs = f_ref.crs

    ref_meta.update({
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": np.nan,
        "compress": "lzw",
        "count": 1
    })

    # 2. Scan raw Sentinel-2 composites
    print("\n[Stage 1] Scanning Sentinel-2 raw scenes ...")
    scenes = scan_sentinel(DEFAULT_SENTINEL)
    print(f"  Found {len(scenes)} unique monthly composites.")

    # 3. Generate 2D GeoTIFF rasters for NDMI and NSMI
    print("\n[Stage 2] Computing & writing NDMI & NSMI GeoTIFF rasters ...")
    ndmi_written = 0
    nsmi_written = 0
    t0 = time.time()

    for i, ((year, month), path) in enumerate(scenes.items(), 1):
        period = f"{year:04d}-{month:02d}"
        p_ndmi_1 = DIR_NDMI_OUT1 / f"NDMI_{period}.tif"
        p_ndmi_2 = DIR_NDMI_OUT2 / f"NDMI_{period}.tif"
        p_nsmi_1 = DIR_NSMI_OUT1 / f"NSMI_{period}.tif"
        p_nsmi_2 = DIR_NSMI_OUT2 / f"NSMI_{period}.tif"

        try:
            bands, dec_transform, src_crs = read_bands(path, target_res=100.0)
            has_nir = "NIR" in bands
            has_swir1 = "SWIR1" in bands
            has_swir2 = "SWIR2" in bands

            nir = _rescale_dn(bands["NIR"]) if has_nir else None
            swir1 = _rescale_dn(bands["SWIR1"]) if has_swir1 else None
            swir2 = _rescale_dn(bands["SWIR2"]) if has_swir2 else None

            # NDMI = (NIR - SWIR1) / (NIR + SWIR1)
            if has_nir and has_swir1 and nir is not None and swir1 is not None:
                arr_ndmi = ndmi(nir, swir1)
                warped_ndmi = np.full(ref_shape, np.nan, dtype="float32")
                warp_reproject(
                    source=arr_ndmi.astype("float32"),
                    destination=warped_ndmi,
                    src_transform=dec_transform,
                    src_crs=src_crs,
                    dst_transform=ref_transform,
                    dst_crs=ref_crs,
                    src_nodata=np.nan,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear
                )
                with rasterio.open(p_ndmi_1, "w", **ref_meta) as dst:
                    dst.write(warped_ndmi, 1)
                    dst.set_band_description(1, f"NDMI_{period} Normalized Difference Moisture Index")
                link_or_copy(p_ndmi_1, p_ndmi_2)
                ndmi_written += 1

            # NSMI = (SWIR1 - SWIR2) / (SWIR1 + SWIR2)
            if has_swir1 and has_swir2 and swir1 is not None and swir2 is not None:
                arr_nsmi = nsmi(swir1, swir2)
                warped_nsmi = np.full(ref_shape, np.nan, dtype="float32")
                warp_reproject(
                    source=arr_nsmi.astype("float32"),
                    destination=warped_nsmi,
                    src_transform=dec_transform,
                    src_crs=src_crs,
                    dst_transform=ref_transform,
                    dst_crs=ref_crs,
                    src_nodata=np.nan,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear
                )
                with rasterio.open(p_nsmi_1, "w", **ref_meta) as dst:
                    dst.write(warped_nsmi, 1)
                    dst.set_band_description(1, f"NSMI_{period} Normalized Soil Moisture Index")
                link_or_copy(p_nsmi_1, p_nsmi_2)
                nsmi_written += 1

            if i % 20 == 0 or i == len(scenes):
                print(f"  Processed {i}/{len(scenes)}: {period} (NDMI={p_ndmi_1.exists()}, NSMI={p_nsmi_1.exists()})")

        except Exception as exc:
            print(f"  Warning on {path.name}: {exc}")

    print(f"  Finished: {ndmi_written} NDMI rasters & {nsmi_written} NSMI rasters in {time.time()-t0:.1f}s.")

    # 4. Generate Separate CSV & Excel files for NDMI and NSMI
    print("\n[Stage 3] Generating separate village CSV & Excel files for NDMI and NSMI ...")
    master_csv = DATA_PROCESSED / "csv" / "village_Latur_monthly_indices.csv"
    if not master_csv.exists():
        print("  Error: village_Latur_monthly_indices.csv not found!")
        return

    df = pd.read_csv(master_csv)
    meta_cols = ["village_idx", "village", "tehsil", "name", "year", "month", "date", "period"]

    # --- NDMI Files ---
    if "NDMI" in df.columns:
        print("  Building separate NDMI deliverables ...")
        df_ndmi = df[meta_cols + ["NDMI"]].copy()
        
        # 1. Long CSV
        ndmi_csv = DATA_PROCESSED / "csv" / "village_Latur_monthly_NDMI.csv"
        df_ndmi.to_csv(ndmi_csv, index=False)
        print(f"    CSV -> {ndmi_csv} ({len(df_ndmi)} rows)")

        # 2. Master Excel with pivot table and per-year sheets
        ndmi_xlsx = DATA_PROCESSED / "excel" / "Latur_village_NDMI_2016_2026.xlsx"
        print(f"    Excel -> {ndmi_xlsx} ...")
        
        pivot_ndmi = df_ndmi.pivot_table(
            index=["village_idx", "village", "tehsil"],
            columns="period",
            values="NDMI",
            aggfunc="first"
        ).reset_index()

        with pd.ExcelWriter(ndmi_xlsx, engine="openpyxl") as xw:
            # README sheet
            pd.DataFrame({
                "Parameter": [
                    "Index Name",
                    "Full Name",
                    "Spectral Formula",
                    "Bands Used",
                    "Theoretical Range",
                    "Physical Meaning",
                    "Citation",
                    "Study Area",
                    "Temporal Coverage"
                ],
                "Value": [
                    "NDMI",
                    "Normalized Difference Moisture Index",
                    "(NIR - SWIR1) / (NIR + SWIR1)",
                    "Sentinel-2 Band 8 (842 nm) & Band 11 (1610 nm)",
                    "-1.0 to +1.0",
                    "Vegetation canopy liquid water content & plant moisture stress",
                    "Gao, B. C. (1996). Remote Sensing of Environment, 58(3), 257-266",
                    "Latur District, Maharashtra (954 villages, 10 tehsils)",
                    "2016 to 2026 (Monthly)"
                ]
            }).to_excel(xw, sheet_name="README_Formulas", index=False)

            # Master Matrix Sheet (All periods 2016-2026 side-by-side)
            pivot_ndmi.to_excel(xw, sheet_name="NDMI_Matrix_2016_2026", index=False)

            # Per-year sheets
            years = sorted(df_ndmi["year"].unique())
            for y in years:
                sub = df_ndmi[df_ndmi["year"] == y]
                sub_pivot = sub.pivot_table(
                    index=["village_idx", "village", "tehsil"],
                    columns="period",
                    values="NDMI",
                    aggfunc="first"
                ).reset_index()
                sub_pivot.to_excel(xw, sheet_name=f"NDMI_{y}", index=False)

        print(f"    Excel written: {ndmi_xlsx}")

    # --- NSMI Files ---
    if "NSMI" in df.columns:
        print("  Building separate NSMI deliverables ...")
        df_nsmi = df[meta_cols + ["NSMI"]].copy()

        # 1. Long CSV
        nsmi_csv = DATA_PROCESSED / "csv" / "village_Latur_monthly_NSMI.csv"
        df_nsmi.to_csv(nsmi_csv, index=False)
        print(f"    CSV -> {nsmi_csv} ({len(df_nsmi)} rows)")

        # 2. Master Excel with pivot table and per-year sheets
        nsmi_xlsx = DATA_PROCESSED / "excel" / "Latur_village_NSMI_2016_2026.xlsx"
        print(f"    Excel -> {nsmi_xlsx} ...")

        pivot_nsmi = df_nsmi.pivot_table(
            index=["village_idx", "village", "tehsil"],
            columns="period",
            values="NSMI",
            aggfunc="first"
        ).reset_index()

        with pd.ExcelWriter(nsmi_xlsx, engine="openpyxl") as xw:
            # README sheet
            pd.DataFrame({
                "Parameter": [
                    "Index Name",
                    "Full Name",
                    "Spectral Formula",
                    "Bands Used",
                    "Theoretical Range",
                    "Physical Meaning",
                    "Citation",
                    "Study Area",
                    "Temporal Coverage"
                ],
                "Value": [
                    "NSMI",
                    "Normalized Soil Moisture Index",
                    "(SWIR1 - SWIR2) / (SWIR1 + SWIR2)",
                    "Sentinel-2 Band 11 (1610 nm) & Band 12 (2190 nm)",
                    "-1.0 to +1.0",
                    "Surface soil moisture & topsoil hygroscopic water retention",
                    "Boles et al. (2020); Gao (1996)",
                    "Latur District, Maharashtra (954 villages, 10 tehsils)",
                    "2016 to 2026 (Monthly)"
                ]
            }).to_excel(xw, sheet_name="README_Formulas", index=False)

            # Master Matrix Sheet (All periods 2016-2026 side-by-side)
            pivot_nsmi.to_excel(xw, sheet_name="NSMI_Matrix_2016_2026", index=False)

            # Per-year sheets
            years = sorted(df_nsmi["year"].unique())
            for y in years:
                sub = df_nsmi[df_nsmi["year"] == y]
                sub_pivot = sub.pivot_table(
                    index=["village_idx", "village", "tehsil"],
                    columns="period",
                    values="NSMI",
                    aggfunc="first"
                ).reset_index()
                sub_pivot.to_excel(xw, sheet_name=f"NSMI_{y}", index=False)

        print(f"    Excel written: {nsmi_xlsx}")

    print("\n" + "=" * 70)
    print("NDMI & NSMI Rasters and Separate Deliverable Files Successfully Created!")
    print("=" * 70)


if __name__ == "__main__":
    main()
