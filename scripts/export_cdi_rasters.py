#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate CDI (Combined Drought Index) GeoTIFF rasters (2016-2026)
and populate data/processed/ raster directories (NDVI, EVI, VCI, VHI, SPI, CDI).
"""

import os
import sys
import time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

ROOT = Path(__file__).resolve().parent.parent
RASTERS_IN = ROOT / "output" / "indices" / "rasters"
SPI_DIR = ROOT / "output" / "spi" / "geotiff_monthly"
DATA_PROCESSED = ROOT / "data" / "processed"

# Ensure output raster directories exist in both locations
for d in ["NDVI", "EVI", "VCI", "VHI", "CDI"]:
    (RASTERS_IN / d).mkdir(parents=True, exist_ok=True)
    (DATA_PROCESSED / d.lower()).mkdir(parents=True, exist_ok=True)
(DATA_PROCESSED / "spi").mkdir(parents=True, exist_ok=True)

def link_or_copy(src: Path, dst: Path):
    """Hard-link on NTFS or copy if needed."""
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except Exception:
        import shutil
        shutil.copy2(src, dst)

def main():
    print("=" * 70)
    print("Latur Drought Monitoring - CDI Raster Generator & Raster Synchronizer")
    print("=" * 70)
    
    # 1. Sync existing rasters (NDVI, EVI, VCI, VHI) to data/processed/
    print("\n[Stage 1] Synchronizing NDVI, EVI, VCI, VHI to data/processed/ ...")
    synced_counts = {}
    for idx_name in ["NDVI", "EVI", "VCI", "VHI"]:
        src_folder = RASTERS_IN / idx_name
        dst_folder = DATA_PROCESSED / idx_name.lower()
        count = 0
        for src_file in src_folder.glob("*.tif"):
            dst_file = dst_folder / src_file.name
            link_or_copy(src_file, dst_file)
            count += 1
        synced_counts[idx_name] = count
        print(f"  {idx_name}: {count} GeoTIFFs linked to {dst_folder.relative_to(ROOT)}")

    # 2. Sync SPI rasters (SPI1, SPI3, SPI6, SPI12) to data/processed/spi/
    print("\n[Stage 2] Synchronizing SPI GeoTIFFs to data/processed/spi/ ...")
    spi_count = 0
    if SPI_DIR.exists():
        for scale in ["SPI1", "SPI3", "SPI6", "SPI12"]:
            scale_dir = SPI_DIR / scale
            if scale_dir.exists():
                dst_scale = DATA_PROCESSED / "spi" / scale
                dst_scale.mkdir(parents=True, exist_ok=True)
                for f in scale_dir.glob("*.tif"):
                    link_or_copy(f, dst_scale / f.name)
                    spi_count += 1
    print(f"  SPI: {spi_count} GeoTIFFs linked to data/processed/spi/")

    # 3. Compute and export CDI rasters for all observation months
    print("\n[Stage 3] Computing and exporting CDI GeoTIFF rasters (2016-2026) ...")
    ndvi_files = sorted((RASTERS_IN / "NDVI").glob("NDVI_*.tif"))
    print(f"  Found {len(ndvi_files)} base periods.")

    weights = {"SPI": 0.30, "VHI": 0.20, "VCI": 0.15, "NDVI": 0.15, "EVI": 0.10}
    cdi_created = 0
    t0 = time.time()

    for i, p_ndvi in enumerate(ndvi_files, 1):
        period = p_ndvi.stem.replace("NDVI_", "")
        cdi_out_1 = RASTERS_IN / "CDI" / f"CDI_{period}.tif"
        cdi_out_2 = DATA_PROCESSED / "cdi" / f"CDI_{period}.tif"

        # Read base NDVI raster for geometry & bounds
        with rasterio.open(p_ndvi) as f_ndvi:
            ndvi = f_ndvi.read(1)
            meta = f_ndvi.meta.copy()

        # Read other optical indices
        p_vci = RASTERS_IN / "VCI" / f"VCI_{period}.tif"
        p_vhi = RASTERS_IN / "VHI" / f"VHI_{period}.tif"
        p_evi = RASTERS_IN / "EVI" / f"EVI_{period}.tif"

        vci = None
        if p_vci.exists():
            with rasterio.open(p_vci) as f:
                vci = f.read(1)

        vhi = None
        if p_vhi.exists():
            with rasterio.open(p_vhi) as f:
                vhi = f.read(1)

        evi = None
        if p_evi.exists():
            with rasterio.open(p_evi) as f:
                evi = f.read(1)

        # Reproject SPI3 onto this canonical 100m grid
        p_spi = SPI_DIR / "SPI3" / f"SPI3_{period}.tif"
        spi_warped = np.full(ndvi.shape, np.nan, dtype="float32")
        if p_spi.exists():
            with rasterio.open(p_spi) as f_spi:
                reproject(
                    source=rasterio.band(f_spi, 1),
                    destination=spi_warped,
                    src_transform=f_spi.transform,
                    src_crs=f_spi.crs,
                    dst_transform=meta["transform"],
                    dst_crs=meta["crs"],
                    resampling=Resampling.bilinear
                )
            spi_warped[spi_warped == -9999.0] = np.nan

        # Convert raw indices to 0..1 drought intensity signals
        # S = 0 (Normal / Wet), S = 1 (Severe / Extreme Drought)
        s_spi = np.clip(-spi_warped / 3.0, 0.0, 1.0)
        s_vci = 1.0 - np.clip(vci / 100.0, 0.0, 1.0) if vci is not None else np.full(ndvi.shape, np.nan, dtype="float32")
        s_vhi = 1.0 - np.clip(vhi / 100.0, 0.0, 1.0) if vhi is not None else np.full(ndvi.shape, np.nan, dtype="float32")
        s_ndvi = 1.0 - np.clip((ndvi - 0.10) / 0.35, 0.0, 1.0)
        s_evi = 1.0 - np.clip((evi - 0.08) / 0.27, 0.0, 1.0) if evi is not None else np.full(ndvi.shape, np.nan, dtype="float32")

        signals = {"SPI": s_spi, "VHI": s_vhi, "VCI": s_vci, "NDVI": s_ndvi, "EVI": s_evi}

        num = np.zeros(ndvi.shape, dtype="float32")
        den = np.zeros(ndvi.shape, dtype="float32")

        for k, w in weights.items():
            valid = np.isfinite(signals[k])
            num[valid] += w * signals[k][valid]
            den[valid] += w

        # Require at least 40% component weight
        with np.errstate(invalid="ignore", divide="ignore"):
            cdi = np.where(den >= 0.40, np.round(num / den, 4), np.nan)
        
        # Mask out nodata pixels from Sentinel-2 boundary
        valid_sentinel = np.isfinite(ndvi)
        cdi[~valid_sentinel] = np.nan

        # Write CDI GeoTIFF
        meta.update({
            "driver": "GTiff",
            "dtype": "float32",
            "nodata": np.nan,
            "compress": "lzw"
        })

        with rasterio.open(cdi_out_1, "w", **meta) as dst:
            dst.write(cdi.astype("float32"), 1)
            dst.set_band_description(1, f"CDI_{period} Combined Drought Index (0..1)")

        link_or_copy(cdi_out_1, cdi_out_2)
        cdi_created += 1

        if i % 20 == 0 or i == len(ndvi_files):
            print(f"  Progress: {i}/{len(ndvi_files)} CDI rasters written ({cdi_out_2.name})")

    elapsed = time.time() - t0
    print(f"\nDone! Exported {cdi_created} CDI GeoTIFF rasters in {elapsed:.1f}s.")
    print("All raster collections are now fully available under:")
    print("  1. d:\\Droughtprj@2026\\data\\processed\\{ndvi, evi, vci, vhi, spi, cdi}\\")
    print("  2. d:\\Droughtprj@2026\\output\\indices\\rasters\\{NDVI, EVI, VCI, VHI, CDI}\\")
    print("=" * 70)

if __name__ == "__main__":
    main()
