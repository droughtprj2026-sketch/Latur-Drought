# -*- coding: utf-8 -*-
"""
Raster + file-scanning helpers shared by the SPI and Sentinel scripts.

The raw folders are messy: multiple naming conventions, GDAL sidecars,
incomplete Chrome downloads, stray Python / zip / CSV files. The helpers
here keep that mess contained in ONE place so the index-computation code
can stay simple.
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Files we always skip when scanning a raw folder.
SIDECAR_SUFFIXES = (".aux.xml", ".ovr", ".crdownload")
NON_DATA_SUFFIXES = (".py", ".zip", ".csv", ".json", ".txt", ".ipynb")

# Any filename that contains YYYY_MM or YYYY-MM anywhere in it. Years
# must start with 19 or 20; months are 01..12.
NAME_RE = re.compile(r"(19|20)(\d{2})[_\-](\d{2})")


@dataclass
class RasterFile:
    path: str
    file: str
    year: int
    month: int
    naming: str          # "S2_L2A_" | "S2_" | "Latur_S2_" | "CHIRPS_" | "Latur_precip_" | "other"
    folder: str


def _naming_for(name: str) -> str:
    """Classify a filename into one of the known naming conventions."""
    if name.startswith("S2_L2A_"):     return "S2_L2A_"
    if name.startswith("S2_"):          return "S2_"
    if name.startswith("Latur_S2_"):    return "Latur_S2_"
    if name.startswith("CHIRPS_"):      return "CHIRPS_"
    if name.startswith("Latur_precip"): return "Latur_precip_"
    return "other"


def scan_rasters(root: str, verbose: bool = True) -> pd.DataFrame:
    """
    Walk `root` recursively and return a DataFrame of every valid raster
    with its (year, month) parsed from the FILENAME (not the folder).

    Skips sidecars, incomplete downloads, and non-data files. If the raw
    folder year disagrees with the filename year (e.g. a 2026 file sitting
    inside the 2024 subfolder), the filename wins and the mismatch is
    logged.
    """
    tifs = sorted(
        p for p in glob.glob(os.path.join(root, "**", "*.tif"), recursive=True)
        if not any(os.path.basename(p).endswith(s) for s in SIDECAR_SUFFIXES)
        and not any(os.path.basename(p).endswith(s) for s in NON_DATA_SUFFIXES)
        and not os.path.basename(p).startswith("._")
    )

    rows = []
    for t in tifs:
        name = os.path.basename(t)
        m = NAME_RE.search(name)
        if not m:
            if verbose:
                print(f"  skipped (no YYYY_MM in name): {name}")
            continue
        year = int(m.group(1) + m.group(2))
        month = int(m.group(3))
        if not 1 <= month <= 12:
            if verbose:
                print(f"  skipped (bad month): {name}")
            continue
        folder = os.path.basename(os.path.dirname(t))
        if verbose and folder.isdigit() and folder != str(year):
            print(f"  note: {name} is in folder {folder}; "
                  f"using filename -> {year}-{month:02d}")
        rows.append(
            RasterFile(path=t, file=name, year=year, month=month,
                       naming=_naming_for(name), folder=folder).__dict__
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["year", "month", "naming"]).reset_index(drop=True)


def dedupe_by_prefix(df: pd.DataFrame, preferred: tuple[str, ...]) -> pd.DataFrame:
    """
    Where the same (year, month) appears under more than one naming style
    keep the one whose prefix comes first in `preferred`. Report the drops.
    """
    if df.empty:
        return df
    rank = {name: i for i, name in enumerate(preferred)}
    df = df.copy()
    df["rank"] = df["naming"].map(rank).fillna(len(preferred)).astype(int)
    df = df.sort_values(["year", "month", "rank"])

    dup_mask = df.duplicated(["year", "month"], keep=False)
    if dup_mask.any():
        dups = df[dup_mask][["year", "month", "file", "naming"]]
        print(f"\n  duplicates found ({dups['file'].nunique()} files, "
              f"{dups.groupby(['year','month']).ngroups} months):")
        for (y, m), g in dups.groupby(["year", "month"]):
            kept = g.iloc[0]["file"]
            dropped = ", ".join(g.iloc[1:]["file"].tolist())
            print(f"    {y}-{m:02d}: keeping {kept}; dropping {dropped}")

    kept = df.drop_duplicates(["year", "month"], keep="first")
    return kept.drop(columns="rank").reset_index(drop=True)


def read_stack(files_df: pd.DataFrame, band: int = 1,
               valid_range: tuple[float, float] = (-1e6, 1e6)):
    """
    Read every raster in `files_df` into one 3-D array (T, H, W) resampled
    onto a common grid (the finest-resolution file in the set).

    Returns (stack, dates, profile, transform, crs, valid_mask).
    """
    import rasterio
    from rasterio.warp import Resampling, reproject

    # Reference grid: finest resolution so nothing is downsampled.
    best = None
    for p in files_df["path"]:
        with rasterio.open(p) as src:
            res = abs(src.transform.a)
            if best is None or res < best[0] - 1e-12:
                best = (res, p)
    with rasterio.open(best[1]) as ref:
        profile = ref.profile.copy()
        H, W = ref.height, ref.width
        ref_transform, ref_crs = ref.transform, ref.crs
    print(f"  reference grid: {os.path.basename(best[1])} "
          f"({H}x{W} px, res {best[0]:.6f})")

    # Complete calendar; gaps -> NaN.
    start = pd.Timestamp(int(files_df.year.min()), 1, 1)
    last = files_df.sort_values(["year", "month"]).iloc[-1]
    end = pd.Timestamp(int(last.year), int(last.month), 1)
    dates = pd.date_range(start, end, freq="MS")
    lut = {(int(r.year), int(r.month)): r.path for r in files_df.itertuples()}

    stack = np.full((len(dates), H, W), np.nan, dtype="float64")
    missing = []
    for i, d in enumerate(dates):
        p = lut.get((d.year, d.month))
        if p is None:
            missing.append(d.strftime("%Y-%m"))
            continue
        with rasterio.open(p) as src:
            if band > src.count:
                print(f"  WARN: {os.path.basename(p)} has {src.count} bands, "
                      f"band {band} requested; using band 1")
                b = 1
            else:
                b = band
            arr = src.read(b).astype("float64")
            nd = src.nodata
            if nd is not None:
                arr[arr == nd] = np.nan
            lo, hi = valid_range
            arr[(arr < lo) | (arr > hi)] = np.nan
            same = (src.height == H and src.width == W
                    and src.crs == ref_crs
                    and np.allclose(tuple(src.transform)[:6],
                                    tuple(ref_transform)[:6], atol=1e-9))
            if same:
                stack[i] = arr
            else:
                dst = np.full((H, W), np.nan)
                reproject(arr, dst,
                          src_transform=src.transform, src_crs=src.crs,
                          src_nodata=np.nan,
                          dst_transform=ref_transform, dst_crs=ref_crs,
                          dst_nodata=np.nan,
                          resampling=Resampling.bilinear)
                stack[i] = dst
    if missing:
        print(f"  missing months (left as NaN): {', '.join(missing)}")

    valid_mask = np.isfinite(stack).any(axis=0)
    profile.update(dtype="float32", count=1, nodata=-9999.0, compress="lzw")
    return stack, dates, profile, ref_transform, ref_crs, valid_mask


def to_geojson_pixels(values_month: np.ndarray, transform, crs, valid_mask):
    """Build a GeoDataFrame of one polygon per valid pixel with its value."""
    import geopandas as gpd
    from shapely.geometry import box
    rr, cc = np.where(valid_mask)
    xs = transform.c + (cc + 0.5) * transform.a
    ys = transform.f + (rr + 0.5) * transform.e
    geoms = [
        box(min(transform.c + c * transform.a,
                transform.c + (c + 1) * transform.a),
            min(transform.f + r * transform.e,
                transform.f + (r + 1) * transform.e),
            max(transform.c + c * transform.a,
                transform.c + (c + 1) * transform.a),
            max(transform.f + r * transform.e,
                transform.f + (r + 1) * transform.e))
        for r, c in zip(rr, cc)
    ]
    df = pd.DataFrame({
        "pixel_id": np.arange(rr.size),
        "lon": np.round(xs, 6),
        "lat": np.round(ys, 6),
        "value": np.round(values_month[rr, cc], 4),
    })
    gdf = gpd.GeoDataFrame(df, geometry=geoms, crs=crs)
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    return gdf
