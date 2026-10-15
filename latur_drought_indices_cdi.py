#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
latur_drought_indices_cdi.py
============================
Comprehensive Remote Sensing & Meteorological Drought Indices Pipeline for Latur District (2016–2026).

Calculates:
1. NDVI (Normalized Difference Vegetation Index): (NIR - Red) / (NIR + Red)
2. EVI  (Enhanced Vegetation Index): 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1.0)
3. SPI  (Standardized Precipitation Index): Reads SPI-1, SPI-3, SPI-6, SPI-12 from CHIRPS
4. VCI  (Vegetation Condition Index): 100 * (NDVI - NDVI_min) / (NDVI_max - NDVI_min)
5. PCI  (Precipitation Condition Index): 100 * (Rain - Rain_min) / (Rain_max - Rain_min)
6. VHI  (Vegetation Health Index): 0.5 * VCI + 0.5 * PCI
7. CDI  (Combined Drought Index): Multi-criteria synthesis of SPI, VCI, PCI, and VHI

Generates:
- Zonal statistics for all 10 Tehsils and all 954 Villages
- Excel workbooks, CSV tables, GeoJSON spatial files, and publication-ready charts
- Optional GeoTIFF rasters for NDVI, EVI, VCI, PCI, VHI, CDI

Usage:
    python latur_drought_indices_cdi.py                 # Fast zonal pipeline + charts + Excel
    python latur_drought_indices_cdi.py --save-rasters   # Also export full-resolution GeoTIFFs
"""

import argparse
import glob
import os
import re
import sys
import time
import warnings

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

warnings.filterwarnings("ignore")

# =============================================================================
# DIRECTORIES & PATHS
# =============================================================================
BASE_DIR = r"D:\Droughtprj@2026"
SENTINEL_DIR = os.path.join(BASE_DIR, "output", "sentinel")
CHIRPS_SPI_DIR = os.path.join(BASE_DIR, "output", "spi", "SPI_output (1)")
TEHSIL_SHP = os.path.join(BASE_DIR, "Latur.shp")
VILLAGE_ZIP = os.path.join(BASE_DIR, "Latur_Tehsil_Villages.zip")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "indices")

TEHSIL_OUT_DIR = os.path.join(OUTPUT_DIR, "zonal", "tehsil")
VILLAGE_OUT_DIR = os.path.join(OUTPUT_DIR, "zonal", "village")
CHARTS_OUT_DIR = os.path.join(OUTPUT_DIR, "charts")
RASTERS_OUT_DIR = os.path.join(OUTPUT_DIR, "rasters")

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# =============================================================================
# DROUGHT CLASSIFICATIONS
# =============================================================================
CDI_CLASSES = [
    ("Emergency", 0, 20, "#7f0000"),    # Extreme drought
    ("Alert", 20, 30, "#d7301f"),        # Severe drought
    ("Warning", 30, 40, "#fdae61"),      # Moderate drought
    ("Watch", 40, 50, "#fee08b"),        # Mild drought
    ("Normal", 50, 100, "#1a9850"),      # No drought / Favorable
]

def classify_cdi(val):
    if pd.isna(val) or val is None:
        return "No Data"
    for label, lo, hi, _ in CDI_CLASSES:
        if lo <= val < hi:
            return label
    return "Normal" if val >= 50 else "Emergency"

def classify_vci(val):
    if pd.isna(val) or val is None:
        return "No Data"
    if val < 10: return "Extreme Drought"
    elif val < 20: return "Severe Drought"
    elif val < 30: return "Moderate Drought"
    elif val < 40: return "Mild Drought"
    else: return "Normal"

# =============================================================================
# 1. SCANNING SENTINEL-2 FILES
# =============================================================================
def scan_sentinel_files():
    """Identifies and indexes all Sentinel-2 composite GeoTIFFs."""
    pattern = os.path.join(SENTINEL_DIR, "**", "*.tif")
    all_tifs = sorted(glob.glob(pattern, recursive=True))
    all_tifs = [f for f in all_tifs if not os.path.basename(f).startswith("._")]

    re_date = re.compile(r"(?:S2_Latur_|Latur_S2_|S2_L2A_Latur_)(\d{4})_(\d{2})")
    records = []
    for path in all_tifs:
        fn = os.path.basename(path)
        m = re_date.search(fn)
        if m:
            records.append({
                "path": path,
                "file": fn,
                "year": int(m.group(1)),
                "month": int(m.group(2))
            })
    df = pd.DataFrame(records)
    if df.empty:
        raise RuntimeError("No Sentinel-2 composite .tif files found!")
    # Prefer S2_Latur_ over Latur_S2_ if duplicates exist
    df["pref"] = df["file"].str.startswith("S2_Latur_").astype(int)
    df = df.sort_values(["year", "month", "pref"], ascending=[True, True, False])
    df = df.drop_duplicates(subset=["year", "month"], keep="first").reset_index(drop=True)
    return df

# =============================================================================
# 2. ZONE RASTERIZATION CACHE
# =============================================================================
class ZoneRasterizer:
    def __init__(self, tehsil_gdf, village_gdf):
        self.tehsil_gdf = tehsil_gdf
        self.village_gdf = village_gdf
        self.cache = {}

    def get_zones(self, shape, transform, crs):
        key = (shape, tuple(transform)[:6], str(crs))
        if key in self.cache:
            return self.cache[key]

        # Reproject vectors to raster CRS
        teh = self.tehsil_gdf.to_crs(crs)
        vil = self.village_gdf.to_crs(crs)

        h, w = shape
        teh_shapes = [(geom, idx + 1) for idx, geom in enumerate(teh.geometry)]
        vil_shapes = [(geom, idx + 1) for idx, geom in enumerate(vil.geometry)]

        zones_teh = rasterize(teh_shapes, out_shape=(h, w), transform=transform, fill=0, dtype="uint8")
        zones_vil = rasterize(vil_shapes, out_shape=(h, w), transform=transform, fill=0, dtype="uint16")

        self.cache[key] = (zones_teh, zones_vil)
        return zones_teh, zones_vil

# =============================================================================
# 3. FAST ZONAL MEAN EXTRACTION
# =============================================================================
def calc_zonal_stats(arr, valid_mask, zones, n_zones):
    """Computes mean, min, max per zone using bincount for lightning speed."""
    mask = (zones > 0) & valid_mask
    if not np.any(mask):
        return (np.full(n_zones, np.nan), np.full(n_zones, np.nan), np.full(n_zones, np.nan))

    z_ids = zones[mask]
    z_vals = arr[mask]

    sums = np.bincount(z_ids, weights=z_vals, minlength=n_zones + 1)[1:n_zones + 1]
    counts = np.bincount(z_ids, minlength=n_zones + 1)[1:n_zones + 1]
    means = np.where(counts > 0, sums / counts, np.nan)
    return means

# =============================================================================
# 4. PROCESS SENTINEL-2 IMAGERY & EXTRACT NDVI / EVI
# =============================================================================
def process_sentinel_imagery(s2_df, rasterizer, n_tehsils, n_villages, save_rasters=False):
    print(f"\n[1/5] Processing {len(s2_df)} Sentinel-2 scenes for NDVI and EVI...")
    records_tehsil = []
    records_village = []

    for idx, row in s2_df.iterrows():
        y, m, path = row["year"], row["month"], row["path"]
        t0 = time.time()
        print(f"  -> [{idx+1}/{len(s2_df)}] {y}-{m:02d} ({os.path.basename(path)})...", end="", flush=True)

        try:
            with rasterio.open(path) as src:
                transform = src.transform
                crs = src.crs
                h, w = src.height, src.width
                nodata = src.nodata if src.nodata is not None else 0

                # S2 bands: Band 1=Blue (B2), Band 3=Red (B4), Band 4=NIR (B8)
                blue = src.read(1).astype("float32")
                red = src.read(3).astype("float32")
                nir = src.read(4).astype("float32")
                meta = src.meta.copy()

            # Mask invalid/nodata
            valid = (red > 0) & (nir > 0) & (red != nodata) & (nir != nodata)
            denom_ndvi = nir + red
            valid = valid & (denom_ndvi > 0)

            # 1. NDVI
            ndvi = np.full((h, w), np.nan, dtype="float32")
            ndvi[valid] = (nir[valid] - red[valid]) / denom_ndvi[valid]
            np.clip(ndvi, -1.0, 1.0, out=ndvi)

            # 2. EVI: 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1.0)
            # Scaling DN to reflectance [0, 1]
            b_refl = blue / 10000.0
            r_refl = red / 10000.0
            n_refl = nir / 10000.0
            denom_evi = n_refl + 6.0 * r_refl - 7.5 * b_refl + 1.0
            valid_evi = valid & (denom_evi > 0.01)

            evi = np.full((h, w), np.nan, dtype="float32")
            evi[valid_evi] = 2.5 * (n_refl[valid_evi] - r_refl[valid_evi]) / denom_evi[valid_evi]
            np.clip(evi, -1.0, 1.0, out=evi)

            # Get cached rasterized zones
            zones_teh, zones_vil = rasterizer.get_zones((h, w), transform, crs)

            # Zonal means
            teh_ndvi = calc_zonal_stats(ndvi, valid, zones_teh, n_tehsils)
            teh_evi = calc_zonal_stats(evi, valid_evi, zones_teh, n_tehsils)
            vil_ndvi = calc_zonal_stats(ndvi, valid, zones_vil, n_villages)
            vil_evi = calc_zonal_stats(evi, valid_evi, zones_vil, n_villages)

            # Record Tehsil results
            for t_idx in range(n_tehsils):
                records_tehsil.append({
                    "zone_id": t_idx + 1,
                    "year": y,
                    "month": m,
                    "date": f"{y}-{m:02d}",
                    "NDVI": round(float(teh_ndvi[t_idx]), 4) if np.isfinite(teh_ndvi[t_idx]) else np.nan,
                    "EVI": round(float(teh_evi[t_idx]), 4) if np.isfinite(teh_evi[t_idx]) else np.nan,
                })

            # Record Village results
            for v_idx in range(n_villages):
                records_village.append({
                    "zone_id": v_idx + 1,
                    "year": y,
                    "month": m,
                    "date": f"{y}-{m:02d}",
                    "NDVI": round(float(vil_ndvi[v_idx]), 4) if np.isfinite(vil_ndvi[v_idx]) else np.nan,
                    "EVI": round(float(vil_evi[v_idx]), 4) if np.isfinite(vil_evi[v_idx]) else np.nan,
                })

            # Optional GeoTIFF write
            if save_rasters:
                os.makedirs(os.path.join(RASTERS_OUT_DIR, "NDVI"), exist_ok=True)
                os.makedirs(os.path.join(RASTERS_OUT_DIR, "EVI"), exist_ok=True)
                out_meta = meta.copy()
                out_meta.update(count=1, dtype="int16", nodata=-32768, compress="lzw", tiled=True)

                # Scaled to int16 (multiply by 10000)
                ndvi_out = np.full((h, w), -32768, dtype="int16")
                ndvi_out[valid] = (ndvi[valid] * 10000).astype("int16")
                with rasterio.open(os.path.join(RASTERS_OUT_DIR, "NDVI", f"NDVI_{y}_{m:02d}.tif"), "w", **out_meta) as dst:
                    dst.write(ndvi_out, 1)

                evi_out = np.full((h, w), -32768, dtype="int16")
                evi_out[valid_evi] = (evi[valid_evi] * 10000).astype("int16")
                with rasterio.open(os.path.join(RASTERS_OUT_DIR, "EVI", f"EVI_{y}_{m:02d}.tif"), "w", **out_meta) as dst:
                    dst.write(evi_out, 1)

            print(f" done ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f" error: {e}")

    df_teh = pd.DataFrame(records_tehsil)
    df_vil = pd.DataFrame(records_village)
    return df_teh, df_vil

# =============================================================================
# 5. MERGE WITH CHIRPS SPI & CALCULATE VCI, PCI, VHI, CDI
# =============================================================================
def calculate_drought_indices(df_veg, chirps_csv_path, zone_type="tehsil"):
    print(f"\n[2/5] Merging with CHIRPS SPI and calculating VCI, PCI, VHI, CDI for {zone_type}...")
    chirps_df = pd.read_csv(chirps_csv_path)

    # Base columns to merge
    cols = ["zone_id", "year", "month", "rain_mm_mean", "SPI1_mean", "SPI3_mean", "SPI6_mean", "SPI12_mean"]
    chirps_sub = chirps_df[[c for c in cols if c in chirps_df.columns]].copy()
    chirps_sub = chirps_sub.rename(columns={
        "rain_mm_mean": "Rain_mm",
        "SPI1_mean": "SPI1",
        "SPI3_mean": "SPI3",
        "SPI6_mean": "SPI6",
        "SPI12_mean": "SPI12"
    })

    # Merge on zone_id, year, month
    merged = pd.merge(df_veg, chirps_sub, on=["zone_id", "year", "month"], how="right")

    # 1. Historical monthly Min & Max for NDVI (to compute VCI)
    ndvi_stats = merged.groupby(["zone_id", "month"])["NDVI"].agg(["min", "max"]).reset_index()
    ndvi_stats = ndvi_stats.rename(columns={"min": "NDVI_min", "max": "NDVI_max"})
    merged = pd.merge(merged, ndvi_stats, on=["zone_id", "month"], how="left")

    # VCI = 100 * (NDVI - NDVI_min) / (NDVI_max - NDVI_min)
    ndvi_range = merged["NDVI_max"] - merged["NDVI_min"]
    merged["VCI"] = np.where(ndvi_range > 0.01, 100.0 * (merged["NDVI"] - merged["NDVI_min"]) / ndvi_range, np.nan)
    merged["VCI"] = np.clip(merged["VCI"], 0.0, 100.0)

    # 2. Historical monthly Min & Max for Precipitation (to compute PCI)
    rain_stats = merged.groupby(["zone_id", "month"])["Rain_mm"].agg(["min", "max"]).reset_index()
    rain_stats = rain_stats.rename(columns={"min": "Rain_min", "max": "Rain_max"})
    merged = pd.merge(merged, rain_stats, on=["zone_id", "month"], how="left")

    # PCI = 100 * (Rain - Rain_min) / (Rain_max - Rain_min)
    rain_range = merged["Rain_max"] - merged["Rain_min"]
    merged["PCI"] = np.where(rain_range > 0.1, 100.0 * (merged["Rain_mm"] - merged["Rain_min"]) / rain_range, 50.0)
    merged["PCI"] = np.clip(merged["PCI"], 0.0, 100.0)

    # 3. VHI = 0.5 * VCI + 0.5 * PCI
    merged["VHI"] = np.where(merged["VCI"].notna(), 0.5 * merged["VCI"] + 0.5 * merged["PCI"], merged["PCI"])
    merged["VHI"] = np.clip(merged["VHI"], 0.0, 100.0)

    # 4. Normalized SPI (scale -2.0 .. +2.0 to 0 .. 100)
    # Prefer SPI3 (agricultural scale), fallback to SPI1
    spi_val = merged["SPI3"].combine_first(merged["SPI1"])
    spi_norm = np.clip((spi_val - (-2.0)) / (2.0 - (-2.0)) * 100.0, 0.0, 100.0)
    merged["SPI_scaled"] = np.round(spi_norm, 1)

    # 5. Combined Drought Index (CDI) Score & Classification
    # Weights: 35% SPI, 35% VCI, 30% PCI (or 50% SPI + 50% PCI if VCI missing)
    cdi_score = np.where(
        merged["VCI"].notna(),
        0.35 * merged["SPI_scaled"] + 0.35 * merged["VCI"] + 0.30 * merged["PCI"],
        0.50 * merged["SPI_scaled"] + 0.50 * merged["PCI"]
    )
    merged["CDI"] = np.round(np.clip(cdi_score, 0.0, 100.0), 1)
    merged["CDI_class"] = merged["CDI"].apply(classify_cdi)
    merged["VCI_class"] = merged["VCI"].apply(classify_vci)

    # Round floats
    for col in ["NDVI", "EVI", "VCI", "PCI", "VHI", "CDI"]:
        if col in merged.columns:
            merged[col] = merged[col].round(2)

    return merged

# =============================================================================
# 6. YEARLY SUMMARY AGGREGATION
# =============================================================================
def make_yearly_summary(df, id_cols):
    rows = []
    for keys, g in df.groupby(id_cols + ["year"]):
        if not isinstance(keys, tuple):
            keys = (keys,)
        rec = dict(zip(id_cols, keys[:-1]))
        rec["year"] = keys[-1]
        rec["annual_rain_mm"] = round(g["Rain_mm"].sum(), 1)
        rec["monsoon_rain_mm"] = round(g[g["month"].between(6, 9)]["Rain_mm"].sum(), 1)
        rec["NDVI_mean"] = round(g["NDVI"].mean(), 3)
        rec["NDVI_max"] = round(g["NDVI"].max(), 3)
        rec["EVI_mean"] = round(g["EVI"].mean(), 3)
        rec["VCI_mean"] = round(g["VCI"].mean(), 1)
        rec["PCI_mean"] = round(g["PCI"].mean(), 1)
        rec["VHI_mean"] = round(g["VHI"].mean(), 1)
        rec["CDI_mean"] = round(g["CDI"].mean(), 1)
        rec["CDI_min"] = round(g["CDI"].min(), 1)
        rec["drought_months_CDI(<40)"] = int((g["CDI"] < 40).sum())
        rec["severe_drought_months(<30)"] = int((g["CDI"] < 30).sum())
        rec["worst_CDI_class"] = classify_cdi(g["CDI"].min())
        rows.append(rec)
    return pd.DataFrame(rows)

# =============================================================================
# 7. EXCEL EXPORT WITH FORMATTING
# =============================================================================
def save_excel_workbook(monthly_df, yearly_df, metadata_dict, file_path):
    print(f"  Saving master Excel: {file_path}...")
    with pd.ExcelWriter(file_path, engine="openpyxl") as xw:
        # Readme
        pd.DataFrame(list(metadata_dict.items()), columns=["Attribute", "Description"]).to_excel(
            xw, sheet_name="README", index=False
        )
        # Monthly Data
        monthly_df.to_excel(xw, sheet_name="Monthly_Indices", index=False)
        # Yearly Summary
        yearly_df.to_excel(xw, sheet_name="Yearly_Summary", index=False)

        # Pivots for CDI, VCI, NDVI
        for idx_name in ["CDI", "VCI", "NDVI", "Rain_mm"]:
            if idx_name in monthly_df.columns:
                pv = monthly_df.pivot(index=["zone_id", "name"], columns="month", values=idx_name).reset_index()
                pv = pv.rename(columns={m: MONTH_NAMES[m - 1] for m in range(1, 13) if m in pv.columns})
                pv.to_excel(xw, sheet_name=f"{idx_name}_Matrix", index=False)

        # Style headers
        from openpyxl.styles import Font, PatternFill
        hdr_fill = PatternFill("solid", fgColor="1F4E78")
        hdr_font = Font(color="FFFFFF", bold=True)
        for ws in xw.book.worksheets:
            for cell in ws[1]:
                cell.fill = hdr_fill
                cell.font = hdr_font
            ws.freeze_panes = "C2"

# =============================================================================
# 8. VISUALIZATION CHARTS
# =============================================================================
def plot_visualizations(tehsil_df, output_charts_dir):
    print("\n[4/5] Generating publication-quality charts...")
    os.makedirs(output_charts_dir, exist_ok=True)

    # 1. District Mean Timeseries (NDVI, EVI, Rain, SPI3, VCI, CDI)
    dist_monthly = tehsil_df.groupby(["year", "month"]).mean(numeric_only=True).reset_index()
    dist_monthly["date_dt"] = pd.to_datetime(dist_monthly["year"].astype(str) + "-" + dist_monthly["month"].astype(str) + "-01")
    dist_monthly = dist_monthly.sort_values("date_dt").reset_index(drop=True)

    fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)

    # Panel A: Vegetation Indices (NDVI & EVI)
    axes[0].plot(dist_monthly["date_dt"], dist_monthly["NDVI"], label="NDVI", color="#2ca02c", lw=2)
    axes[0].plot(dist_monthly["date_dt"], dist_monthly["EVI"], label="EVI", color="#1f77b4", lw=1.8, ls="--")
    axes[0].set_ylabel("Vegetation Index", fontweight="bold")
    axes[0].set_title("District-Wide Remote Sensing & Combined Drought Dynamics | Latur (2016–2026)", fontsize=14, fontweight="bold")
    axes[0].legend(loc="upper left")
    axes[0].grid(alpha=0.3)

    # Panel B: Rainfall (mm) & SPI-3
    ax_rain = axes[1]
    ax_spi = ax_rain.twinx()
    ax_rain.bar(dist_monthly["date_dt"], dist_monthly["Rain_mm"], width=20, color="#4a90d9", alpha=0.5, label="Rainfall (mm)")
    ax_spi.plot(dist_monthly["date_dt"], dist_monthly["SPI3"], color="#b2182b", lw=1.8, label="SPI-3")
    ax_spi.axhline(-1.0, color="#d7301f", ls="--", lw=0.8)
    ax_rain.set_ylabel("Monthly Rain (mm)", fontweight="bold", color="#2c5f8a")
    ax_spi.set_ylabel("SPI-3", fontweight="bold", color="#b2182b")
    ax_rain.grid(alpha=0.3)

    # Panel C: Condition Indices (VCI, PCI, VHI)
    axes[2].plot(dist_monthly["date_dt"], dist_monthly["VCI"], label="VCI (Vegetation Condition)", color="#31a354", lw=1.7)
    axes[2].plot(dist_monthly["date_dt"], dist_monthly["PCI"], label="PCI (Precipitation Condition)", color="#3182bd", lw=1.5, ls=":")
    axes[2].plot(dist_monthly["date_dt"], dist_monthly["VHI"], label="VHI (Vegetation Health)", color="#756bb1", lw=1.8)
    axes[2].axhline(40, color="orange", ls="--", lw=0.8, label="Drought Threshold (40)")
    axes[2].set_ylabel("Condition Score (0–100)", fontweight="bold")
    axes[2].set_ylim(0, 105)
    axes[2].legend(loc="upper left", ncol=4)
    axes[2].grid(alpha=0.3)

    # Panel D: Combined Drought Index (CDI) with Severity Bands
    cdi_vals = dist_monthly["CDI"].values
    colors = [CDI_CLASSES[np.searchsorted([c[2] for c in CDI_CLASSES], v, side="right")][3] if np.isfinite(v) else "grey" for v in cdi_vals]
    axes[3].bar(dist_monthly["date_dt"], cdi_vals, width=22, color=colors, edgecolor="grey", linewidth=0.3)
    axes[3].axhline(40, color="#fdae61", ls="--", label="Warning (40)")
    axes[3].axhline(30, color="#d7301f", ls="--", label="Alert (30)")
    axes[3].axhline(20, color="#7f0000", ls="-", label="Emergency (20)")
    axes[3].set_ylabel("CDI Score (0–100)", fontweight="bold")
    axes[3].set_ylim(0, 105)
    axes[3].legend(loc="upper left", ncol=4)
    axes[3].grid(alpha=0.3)

    plt.tight_layout()
    chart_path = os.path.join(output_charts_dir, "CDI_comprehensive_timeseries.png")
    fig.savefig(chart_path, dpi=200)
    plt.close(fig)
    print(f"  Saved chart: {chart_path}")

    # 2. Tehsil Heatmap of CDI
    pv_cdi = tehsil_df.groupby(["tehsil", "year"])["CDI"].mean().unstack()
    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(pv_cdi.values, cmap="RdYlGn", vmin=15, vmax=80, aspect="auto")
    ax.set_xticks(range(len(pv_cdi.columns)))
    ax.set_xticklabels(pv_cdi.columns, fontsize=10, fontweight="bold")
    ax.set_yticks(range(len(pv_cdi.index)))
    ax.set_yticklabels(pv_cdi.index, fontsize=10, fontweight="bold")
    for r in range(pv_cdi.shape[0]):
        for c in range(pv_cdi.shape[1]):
            val = pv_cdi.values[r, c]
            if np.isfinite(val):
                ax.text(c, r, f"{val:.1f}", ha="center", va="center", fontsize=9,
                        color="white" if val < 30 or val > 65 else "black")
    fig.colorbar(im, ax=ax, label="Mean Annual CDI Score")
    ax.set_title("Tehsil-Level Mean Annual Combined Drought Index (CDI) | Latur", fontsize=13, fontweight="bold")
    plt.tight_layout()
    heatmap_path = os.path.join(output_charts_dir, "Tehsil_CDI_annual_heatmap.png")
    fig.savefig(heatmap_path, dpi=200)
    plt.close(fig)
    print(f"  Saved heatmap: {heatmap_path}")

# =============================================================================
# 9. GEOJSON SPATIAL LAYERS EXPORT
# =============================================================================
def export_geojson_layers(merged_df, gdf, id_col, name_col, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    years = sorted(merged_df["year"].unique())
    for y in years:
        sub = merged_df[merged_df["year"] == y]
        # Pivot annual means of key indices
        pv = sub.groupby(id_col)[["NDVI", "EVI", "VCI", "PCI", "VHI", "CDI", "Rain_mm"]].mean().reset_index()
        # Merge with geometry
        geo_gdf = gdf[[id_col, name_col, "geometry"]].merge(pv, on=id_col, how="left")
        geo_gdf["CDI_class"] = geo_gdf["CDI"].apply(classify_cdi)
        if geo_gdf.crs is not None and geo_gdf.crs.to_epsg() != 4326:
            geo_gdf = geo_gdf.to_crs(4326)
        out_geo = os.path.join(out_dir, f"CDI_Latur_{y}.geojson")
        geo_gdf.to_file(out_geo, driver="GeoJSON")
    print(f"  Exported GeoJSON layers for {len(years)} years into {out_dir}")

# =============================================================================
# 10. MAIN PIPELINE
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Calculate NDVI, EVI, VCI, PCI, VHI, and CDI for Latur district.")
    parser.add_argument("--save-rasters", action="store_true", help="Also export 10 m GeoTIFF rasters for NDVI and EVI.")
    args = parser.parse_args()

    t_start = time.time()
    print("=" * 70)
    print("  LATUR COMPREHENSIVE DROUGHT INDICES & CDI PIPELINE (2016–2026)")
    print("=" * 70)
    print(f"Working Directory: {BASE_DIR}")
    print(f"Output Directory:  {OUTPUT_DIR}")

    os.makedirs(TEHSIL_OUT_DIR, exist_ok=True)
    os.makedirs(VILLAGE_OUT_DIR, exist_ok=True)
    os.makedirs(CHARTS_OUT_DIR, exist_ok=True)

    # Load Vector Boundaries
    print("\nLoading shapefiles...")
    tehsil_gdf = gpd.read_file(TEHSIL_SHP)
    village_gdf = gpd.read_file(f"zip://{VILLAGE_ZIP}!Latur_Tehsil_Villages.shp")
    print(f"  Loaded {len(tehsil_gdf)} Tehsils and {len(village_gdf)} Villages.")

    rasterizer = ZoneRasterizer(tehsil_gdf, village_gdf)

    # Scan S2 GeoTIFFs
    s2_df = scan_sentinel_files()
    print(f"  Found {len(s2_df)} unique Sentinel-2 monthly composites (2016–2026).")

    # Step 1: Process S2 and extract NDVI & EVI
    df_teh_veg, df_vil_veg = process_sentinel_imagery(
        s2_df, rasterizer, len(tehsil_gdf), len(village_gdf), save_rasters=args.save_rasters
    )

    # Step 2: Merge with CHIRPS SPI & calculate VCI, PCI, VHI, CDI
    chirps_teh_csv = os.path.join(CHIRPS_SPI_DIR, "zonal", "tehsil", "csv", "tehsil_monthly_zonal_stats.csv")
    chirps_vil_csv = os.path.join(CHIRPS_SPI_DIR, "zonal", "village", "csv", "village_monthly_zonal_stats.csv")

    tehsil_cdi = calculate_drought_indices(df_teh_veg, chirps_teh_csv, zone_type="tehsil")
    village_cdi = calculate_drought_indices(df_vil_veg, chirps_vil_csv, zone_type="village")

    # Attach Names and Codes
    tehsil_meta = tehsil_gdf[["SUB_DIST", "SUBDIS_LGD"]].copy().reset_index()
    tehsil_meta["zone_id"] = tehsil_meta["index"] + 1
    tehsil_meta = tehsil_meta.rename(columns={"SUB_DIST": "tehsil", "SUBDIS_LGD": "tehsil_code"})
    tehsil_meta["name"] = tehsil_meta["tehsil"]
    tehsil_cdi = pd.merge(tehsil_meta[["zone_id", "tehsil", "tehsil_code", "name"]], tehsil_cdi, on="zone_id", how="right")

    village_meta = village_gdf[["VILLAGE", "TEHSIL", "CEN_2001"]].copy().reset_index()
    village_meta["zone_id"] = village_meta["index"] + 1
    village_meta = village_meta.rename(columns={"VILLAGE": "village", "TEHSIL": "tehsil", "CEN_2001": "village_code"})
    village_meta["name"] = village_meta["village"]
    village_cdi = pd.merge(village_meta[["zone_id", "village", "village_code", "tehsil", "name"]], village_cdi, on="zone_id", how="right")

    # Step 3: Summaries
    print("\n[3/5] Generating yearly summaries...")
    tehsil_yearly = make_yearly_summary(tehsil_cdi, ["zone_id", "tehsil", "tehsil_code", "name"])
    village_yearly = make_yearly_summary(village_cdi, ["zone_id", "village", "village_code", "tehsil", "name"])

    # Export CSVs
    tehsil_csv = os.path.join(TEHSIL_OUT_DIR, "tehsil_monthly_indices.csv")
    tehsil_yr_csv = os.path.join(TEHSIL_OUT_DIR, "tehsil_yearly_cdi_summary.csv")
    tehsil_cdi.to_csv(tehsil_csv, index=False)
    tehsil_yearly.to_csv(tehsil_yr_csv, index=False)
    print(f"  Saved Tehsil CSVs: {tehsil_csv}")

    village_csv = os.path.join(VILLAGE_OUT_DIR, "village_monthly_indices.csv")
    village_yr_csv = os.path.join(VILLAGE_OUT_DIR, "village_yearly_cdi_summary.csv")
    village_cdi.to_csv(village_csv, index=False)
    village_yearly.to_csv(village_yr_csv, index=False)
    print(f"  Saved Village CSVs: {village_csv}")

    # Export Master Excels
    readme_teh = {
        "Project": "Drought Monitoring & Combined Drought Index (CDI) for Latur",
        "Scale": "Tehsil Level (10 Administrative Tehsils)",
        "Period": f"{tehsil_cdi['year'].min()} to {tehsil_cdi['year'].max()}",
        "NDVI": "Normalized Difference Vegetation Index: (B8-B4)/(B8+B4)",
        "EVI": "Enhanced Vegetation Index: 2.5*(B8-B4)/(B8+6*B4-7.5*B2+1.0)",
        "SPI": "Standardized Precipitation Index (1, 3, 6, 12 months) from CHIRPS",
        "VCI": "Vegetation Condition Index: 100*(NDVI-NDVI_min)/(NDVI_max-NDVI_min)",
        "PCI": "Precipitation Condition Index: 100*(Rain-Rain_min)/(Rain_max-Rain_min)",
        "VHI": "Vegetation Health Index: 0.5*VCI + 0.5*PCI",
        "CDI": "Combined Drought Index: 0.35*SPI_scaled + 0.35*VCI + 0.30*PCI",
        "CDI Classes": "Emergency (<20), Alert (20-30), Warning (30-40), Watch (40-50), Normal (>=50)"
    }
    save_excel_workbook(tehsil_cdi, tehsil_yearly, readme_teh, os.path.join(TEHSIL_OUT_DIR, "CDI_Latur_tehsil_zonal_stats.xlsx"))

    readme_vil = readme_teh.copy()
    readme_vil["Scale"] = "Village Level (954 Cadastral Villages)"
    save_excel_workbook(village_cdi, village_yearly, readme_vil, os.path.join(VILLAGE_OUT_DIR, "CDI_Latur_village_zonal_stats.xlsx"))

    # Step 4: Visualizations
    plot_visualizations(tehsil_cdi, CHARTS_OUT_DIR)

    # Step 5: GeoJSON Layers
    print("\n[5/5] Exporting annual GeoJSON spatial layers...")
    tehsil_gdf["zone_id"] = range(1, len(tehsil_gdf) + 1)
    village_gdf["zone_id"] = range(1, len(village_gdf) + 1)
    export_geojson_layers(tehsil_cdi, tehsil_gdf, "zone_id", "SUB_DIST", os.path.join(TEHSIL_OUT_DIR, "geojson"))
    export_geojson_layers(village_cdi, village_gdf, "zone_id", "VILLAGE", os.path.join(VILLAGE_OUT_DIR, "geojson"))

    elapsed = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"  CDI PIPELINE EXECUTION COMPLETED IN {elapsed/60:.2f} MINUTES!")
    print(f"  All outputs saved locally in: {OUTPUT_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    main()
