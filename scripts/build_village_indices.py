#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 Village-level drought indices for Latur (batch, two stages)
=====================================================================

Index set (config/composite.yaml): SPI, VHI, VCI, NDVI, EVI, PCI.
There is no NDMI / TCI; VHI is set equal to VCI (no LST available).

Two batch stages so the heavy raster work is done once and the zonal
step can be re-run cheaply:

  Stage 1  --stage indices
      1a. For every Sentinel-2 monthly composite in
          output/sentinel_Raw_Composites/ compute NDVI and EVI on a
          single canonical district grid, in REAL units (-1..1,
          float32) under output/indices/rasters/{NDVI,EVI}/, and
          record the source file + processing group per period in
          output/indices/rasters/_meta.json.

      1b. Estimate the per-processing-batch additive NDVI/EVI offset
          (the three filename conventions are radiometrically
          inconsistent) against the largest batch, write
          output/indices/rasters/_offsets.json, and compute the
          per-pixel VCI from the offset-corrected NDVI using the
          per-calendar-month 5th..95th percentile envelope. Write VCI
          (0..100) and VHI = VCI under output/indices/rasters/.

  Stage 2  --stage zonal
      Offset-corrected zonal mean of NDVI / EVI / VCI / VHI per village
      (frontend/public/data/latur_villages.geojson, 954 villages),
      merge CHIRPS SPI-1/3/6/12 and monthly rainfall, derive PCI, then
      fuse the transparent composite CDI. Every component is turned
      into a drought signal with its per-calendar-month robust
      climatological anomaly, S = clip(-z/3, 0, 1), so a normal month
      sits at 0 (None/D0) and only real deficits reach D3/D4.

  --stage all (default) runs both, in order.

Only rasterio / numpy / pandas / pyproj are used; shapely and geopandas
are not required (their DLLs are blocked on some Windows hosts).

Band order of the 6-band composites:
    band 1 = B2 (blue)   band 3 = B4 (red)   band 4 = B8  (NIR)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio import Affine
from rasterio.features import rasterize, bounds
from rasterio.enums import Resampling
from rasterio.warp import transform_geom, reproject as warp_reproject

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import manifest  # noqa: E402

ROOT = HERE.parent
DEFAULT_SENTINEL = ROOT / "output" / "sentinel_Raw_Composites"
DEFAULT_CHIRPS = ROOT / "output" / "CHIRPS_Rainfall"
DEFAULT_SPI = ROOT / "output" / "spi" / "csv"
DEFAULT_VILLAGES = ROOT / "frontend" / "public" / "data" / "latur_villages.geojson"
DEFAULT_OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
DEFAULT_RASTERS = ROOT / "output" / "indices" / "rasters"
DEFAULT_NSMI_CSV = ROOT / "data" / "processed" / "csv" / "village_Latur_monthly_NSMI.csv"
CFG_PATH = ROOT / "config" / "composite.yaml"

DST_CRS = "EPSG:32643"
INDICES = ("NDVI", "EVI", "VCI", "VHI")
FLOAT_INDICES = ("NDVI", "EVI")

SCENE_RE = re.compile(r"(19|20)(\d{2})[_\-](\d{1,2})")
CHIRPS_RE = re.compile(r"(19|20)(\d{2})[_\-](\d{1,2})")
SKIP_SUFFIX = (".aux.xml", ".ovr", ".crdownload", ".py", ".zip", ".csv",
               ".json", ".txt", ".xml")
PREF_SCORE = {"s2_l2a_": 0, "s2_latur_": 1, "latur_s2_": 2, "latur_": 3}


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _group_of(name: str) -> str:
    low = name.lower()
    for pref in PREF_SCORE:
        if low.startswith(pref):
            return pref
    return "other"


# =====================================================================
# scanning / loading
# =====================================================================
def scan_scenes(sentinel_dir: Path) -> dict[tuple[int, int], Path]:
    best: dict[tuple[int, int], tuple[int, Path]] = {}
    for p in sorted(Path(sentinel_dir).rglob("*.tif")):
        name = p.name
        if name.startswith("._"):
            continue
        low = name.lower()
        if any(low.endswith(s) for s in SKIP_SUFFIX):
            continue
        m = SCENE_RE.search(low)
        if not m:
            continue
        year = int(m.group(1) + m.group(2))
        month = int(m.group(3))
        if not 1 <= month <= 12:
            continue
        score = PREF_SCORE.get(_group_of(name), 9)
        key = (year, month)
        if key not in best or score < best[key][0]:
            best[key] = (score, p)
    return {k: v[1] for k, v in sorted(best.items())}


def scan_chirps(chirps_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in sorted(Path(chirps_dir).rglob("*.tif")):
        low = p.name.lower()
        if any(low.endswith(s) for s in SKIP_SUFFIX):
            continue
        m = CHIRPS_RE.search(low)
        if not m:
            continue
        year = int(m.group(1) + m.group(2))
        month = int(m.group(3))
        if not 1 <= month <= 12:
            continue
        out[f"{year:04d}-{month:02d}"] = p
    return dict(sorted(out.items()))


def load_villages(path: Path) -> list[dict]:
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for feat in gj["features"]:
        props = feat.get("properties", {})
        name = props.get("VILLAGE") or props.get("name") or props.get("NAME")
        tehsil = (props.get("TEHSIL") or props.get("tehsil")
                  or props.get("SUB_DIST") or "")
        if not name:
            continue
        rows.append({"village": str(name).strip(),
                     "tehsil": str(tehsil).strip(),
                     "geom": feat["geometry"]})
    return rows


def centroid_lonlat(geom: dict) -> tuple[float, float]:
    if geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
    else:
        ring = geom["coordinates"][0][0]
    arr = np.asarray(ring, dtype="float64")
    return float(arr[:, 0].mean()), float(arr[:, 1].mean())


def reference_grid(villages: list[dict], target_res: float):
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for v in villages:
        g = transform_geom("EPSG:4326", DST_CRS, v["geom"])
        b = bounds(g)
        minx, miny = min(minx, b[0]), min(miny, b[1])
        maxx, maxy = max(maxx, b[2]), max(maxy, b[3])
    left = math.floor(minx / target_res) * target_res
    bottom = math.floor(miny / target_res) * target_res
    right = math.ceil(maxx / target_res) * target_res
    top = math.ceil(maxy / target_res) * target_res
    width = int(round((right - left) / target_res))
    height = int(round((top - bottom) / target_res))
    return height, width, Affine(target_res, 0.0, left, 0.0, -target_res, top)


# =====================================================================
# stage 1a: monthly NDVI / EVI rasters (real units)
# =====================================================================
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


def _read_bands_by_description(path: Path, target_res: float):
    """Read a raster and return dict {short_name: array} using band descriptions.

    Only RED and NIR are strictly required. BLUE is needed for EVI.
    GREEN is optional (not used in NDVI/EVI).
    Returns (bands_dict, dec_transform, src_crs) or None on failure.
    """
    with rasterio.open(path) as src:
        factor = max(1, int(round(target_res / abs(src.res[0]))))
        h = math.ceil(src.height / factor)
        w = math.ceil(src.width / factor)
        dec_transform = src.transform * Affine.scale(src.width / w,
                                                     src.height / h)
        nodata = src.nodata
        bands = {}
        for b in range(1, src.count + 1):
            desc = src.descriptions[b - 1] or ""
            desc = desc.strip().upper()
            short = BAND_DESC_TO_NAME.get(desc)
            if short is None:
                continue  # skip non-spectral bands (e.g. valid_weeks)
            a = src.read(b, out_shape=(h, w),
                         resampling=Resampling.average).astype("float32")
            if nodata is not None:
                a[a == nodata] = np.nan
            bands[short] = a
    return bands, dec_transform, src.crs


def _to_ref(arr, src_transform, src_crs, ref_transform, ref_shape):
    dst = np.full(ref_shape, np.nan, dtype="float32")
    warp_reproject(source=arr, destination=dst,
                   src_transform=src_transform, src_crs=src_crs,
                   dst_transform=ref_transform, dst_crs=DST_CRS,
                   src_nodata=np.nan, dst_nodata=np.nan,
                   resampling=Resampling.bilinear)
    return dst


def _write_float(path: Path, arr: np.ndarray, ref_transform,
                 ref_shape) -> None:
    h, w = ref_shape
    profile = {"driver": "GTiff", "dtype": "float32", "count": 1,
               "nodata": np.nan, "compress": "lzw", "tiled": True,
               "height": h, "width": w, "transform": ref_transform,
               "crs": DST_CRS}
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype("float32"), 1)


def compute_ndvi_evi(scenes, raster_dir, ref, target_res, force,
                     max_scenes) -> int:
    dirs = {k: raster_dir / k for k in FLOAT_INDICES}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    ref_height, ref_width, ref_transform = ref
    ref_shape = (ref_height, ref_width)
    meta_path = raster_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    items = sorted(scenes.items())
    if max_scenes:
        items = items[:max_scenes]
    done = 0
    t0 = time.time()
    for i, ((year, month), path) in enumerate(items, 1):
        period = f"{year:04d}-{month:02d}"
        meta[period] = {"source": path.name, "group": _group_of(path.name)}
        outs = {k: dirs[k] / f"{k}_{period}.tif" for k in dirs}
        if not force and all(p.exists() for p in outs.values()):
            print(f"  [{i}/{len(items)}] {period} cached")
            done += 1
            continue
        print(f"  [{i}/{len(items)}] {period} <- {path.name} ...",
              end="", flush=True)
        try:
            bands, dec_transform, src_crs = _read_bands_by_description(path, target_res)
            # Strictly required: RED and NIR
            if "RED" not in bands or "NIR" not in bands:
                print(" skip (missing RED/NIR bands)")
                continue
            red = bands["RED"].astype("float64")
            nir = bands["NIR"].astype("float64")
            blue = bands["BLUE"].astype("float64") if "BLUE" in bands else None

            # Rescale DN (0-10000) to reflectance (0-1) before EVI
            # so the "+ 1.0" denominator constant works properly
            def _rescale_dn(arr):
                with np.errstate(invalid="ignore"):
                    m = np.nanmax(arr)
                if m > 10:
                    return arr / 10000.0
                return arr

            red = _rescale_dn(red)
            nir = _rescale_dn(nir)
            if blue is not None:
                blue = _rescale_dn(blue)

            valid = np.isfinite(red) & np.isfinite(nir) & (red > 0) & (nir > 0)
            if blue is not None:
                valid &= np.isfinite(blue)

            with np.errstate(invalid="ignore", divide="ignore"):
                ndvi = np.where(valid, (nir - red) / (nir + red), np.nan)
                if blue is not None:
                    evi_den = nir + 6.0 * red - 7.5 * blue + 1.0
                    evi = np.where(valid & (evi_den > 0.01),
                                   2.5 * (nir - red) / evi_den, np.nan)
                else:
                    evi = np.full_like(ndvi, np.nan)
            np.clip(ndvi, -1.0, 1.0, out=ndvi)
            np.clip(evi, -1.0, 1.0, out=evi)
            for name, arr in (("NDVI", ndvi), ("EVI", evi)):
                warped = _to_ref(arr, dec_transform, src_crs,
                                 ref_transform, ref_shape)
                _write_float(outs[name], warped, ref_transform, ref_shape)
            done += 1
            print(" ok")
        except Exception as exc:  # noqa: BLE001
            print(f" FAILED: {type(exc).__name__}: {exc}")
    meta_path.write_text(json.dumps(meta, indent=1, sort_keys=True),
                         encoding="utf-8")
    print(f"[indices] NDVI/EVI {done}/{len(items)} months in "
          f"{(time.time()-t0)/60:.1f} min; meta -> {meta_path.name}")
    return done


# =====================================================================
# stage 1b-helpers: per-batch radiometric offset
# =====================================================================
def _read_first(tif: Path):
    with rasterio.open(tif) as src:
        return src.read(1), (src.height, src.width), src.transform


def estimate_offsets(raster_dir: Path, index: str) -> dict:
    """Per-processing-group additive offset vs the largest group."""
    meta_path = raster_dir / "_meta.json"
    if not meta_path.exists():
        return {"reference": None, "groups": {}}
    meta = json.loads(meta_path.read_text())
    groups: dict[str, list[str]] = {}
    for period, m in meta.items():
        if (raster_dir / index / f"{index}_{period}.tif").exists():
            grp = m.get("group", _group_of(m.get("source", "")))
            groups.setdefault(grp, []).append(period)
    if not groups:
        return {"reference": None, "groups": {}}
    ref = max(groups, key=lambda g: len(groups[g]))

    def gmean(periods):
        stack = []
        for per in periods:
            a, _, _ = _read_first(raster_dir / index / f"{index}_{per}.tif")
            stack.append(a)
        with np.errstate(invalid="ignore"):
            return np.nanmean(np.stack(stack), axis=0)

    ref_month = {}
    for per in groups[ref]:
        ref_month.setdefault(int(per[5:7]), []).append(per)
    ref_mean = {m: gmean(ps) for m, ps in ref_month.items()}

    offsets = {}
    for g, periods in groups.items():
        if g == ref:
            continue
        by_month = {}
        for per in periods:
            by_month.setdefault(int(per[5:7]), []).append(per)
        per_month, vals = {}, []
        for m, ps in by_month.items():
            if m not in ref_mean:
                continue
            diff = gmean(ps) - ref_mean[m]
            v = diff[np.isfinite(diff)]
            if v.size:
                off = float(np.median(v))
                per_month[str(m)] = round(off, 4)
                vals.append(off)
        overall = round(float(np.median(vals)), 4) if vals else 0.0
        for m in range(1, 13):
            per_month.setdefault(str(m), overall)
        per_month["overall"] = overall
        offsets[g] = per_month
    out = {"index": index, "reference": ref, "groups": offsets}
    return out


def _apply_offset(arr, offsets, index_off, group, period):
    if not offsets or offsets.get("reference") in (None, group):
        return arr
    g = offsets["groups"].get(group)
    if not g:
        return arr
    off = g.get(str(int(period[5:7])), g.get("overall", 0.0))
    return arr - off


# =====================================================================
# stage 1b: per-pixel VCI / VHI rasters
# =====================================================================
def compute_vci_vhi(scenes, raster_dir, offsets, force) -> int:
    """VCI per pixel from corrected per-calendar-month NDVI climatology.

    Uses the 5th..95th percentile envelope (robust to remaining
    outliers). VHI = VCI (no thermal band available).
    """
    ndvi_dir = raster_dir / "NDVI"
    dirs = {k: raster_dir / k for k in ("VCI", "VHI")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    meta_path = raster_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    by_month: dict[int, list[str]] = {}
    for (year, month) in sorted(scenes):
        period = f"{year:04d}-{month:02d}"
        if (ndvi_dir / f"NDVI_{period}.tif").exists():
            by_month.setdefault(month, []).append(period)

    done = 0
    t0 = time.time()
    for month, periods in sorted(by_month.items()):
        outs = {per: {k: dirs[k] / f"{k}_{per}.tif" for k in dirs}
                for per in periods}
        if not force and all(p.exists() for v in outs.values()
                             for p in v.values()):
            done += len(periods)
            continue
        stack, ref_transform, ref_shape = [], None, None
        for per in periods:
            a, shape, tr = _read_first(ndvi_dir / f"NDVI_{per}.tif")
            grp = meta.get(per, {}).get("group", "other")
            a = _apply_offset(a, offsets, "NDVI", grp, per)
            stack.append(a)
            ref_transform, ref_shape = tr, shape
        arr = np.stack(stack)
        with np.errstate(invalid="ignore"):
            lo = np.nanpercentile(arr, 5, axis=0)
            hi = np.nanpercentile(arr, 95, axis=0)
            rng = hi - lo
            vci = np.where(rng > 1e-4, 100.0 * (arr - lo) / rng, np.nan)
        vci = np.clip(vci, 0.0, 100.0)
        for j, per in enumerate(periods):
            _write_float(outs[per]["VCI"], vci[j], ref_transform, ref_shape)
            _write_float(outs[per]["VHI"], vci[j], ref_transform, ref_shape)
        done += len(periods)
        print(f"  [VCI] month {month:02d}: {len(periods)} periods "
              f"({(time.time()-t0):.0f}s)")
    print(f"[indices] VCI/VHI {done} months (VHI = VCI, 5-95 pct)")
    return done


# =====================================================================
# stage 2: zonal statistics per village
# =====================================================================
class VillageRasterizer:
    def __init__(self, villages: list[dict]):
        self.villages = villages
        self.n = len(villages)
        self._geoms: list | None = None
        self._labels: dict = {}

    def _geoms_projected(self) -> list:
        if self._geoms is None:
            self._geoms = [(transform_geom("EPSG:4326", DST_CRS, v["geom"]),
                            i + 1) for i, v in enumerate(self.villages)]
        return self._geoms

    def labels(self, shape, transform) -> np.ndarray:
        key = (shape, tuple(round(x, 6) for x in transform)[:6])
        if key not in self._labels:
            if len(self._labels) > 4:
                self._labels.clear()
            self._labels[key] = rasterize(
                self._geoms_projected(), out_shape=shape, transform=transform,
                fill=0, dtype="uint16", all_touched=True)
        return self._labels[key]

    @staticmethod
    def zonal_mean(arr, labels) -> np.ndarray:
        n = int(labels.max())
        out = np.full(n, np.nan, dtype="float64")
        valid = np.isfinite(arr) & (labels > 0)
        if not valid.any():
            return out
        ids = labels[valid].astype("int64")
        vals = arr[valid].astype("float64")
        sums = np.bincount(ids, weights=vals, minlength=n + 1)[1:n + 1]
        cnts = np.bincount(ids, minlength=n + 1)[1:n + 1]
        np.divide(sums, cnts, out=out, where=cnts > 0)
        return out


def load_index_panel(raster_dir, rasterizer, scenes, meta, offsets):
    recs = []
    items = sorted(scenes.keys())
    t0 = time.time()
    for i, (year, month) in enumerate(items, 1):
        period = f"{year:04d}-{month:02d}"
        files = {k: raster_dir / k / f"{k}_{period}.tif" for k in INDICES}
        if not all(p.exists() for p in files.values()):
            continue
        grp = meta.get(period, {}).get("group", "other")
        cols = {}
        for name, p in files.items():
            with rasterio.open(p) as src:
                a = src.read(1).astype("float32")
                if name in FLOAT_INDICES:
                    a = _apply_offset(a, offsets.get(name), name, grp, period)
                labels = rasterizer.labels((src.height, src.width), src.transform)
                cols[name] = rasterizer.zonal_mean(a, labels)
        n = rasterizer.n
        for v in range(n):
            recs.append({
                "village_idx": v + 1, "year": year, "month": month,
                "period": period,
                "NDVI": cols["NDVI"][v], "EVI": cols["EVI"][v],
                "VCI": cols["VCI"][v], "VHI": cols["VHI"][v],
            })
        if i % 20 == 0 or i == len(items):
            print(f"    zonal {i}/{len(items)} ({(time.time()-t0):.0f}s)")
    return pd.DataFrame(recs)


def load_spi_long(spi_dir: Path) -> pd.DataFrame:
    frames = []
    for k in (1, 3, 6, 12):
        p = spi_dir / f"SPI{k}_village_monthly.csv"
        if not p.exists():
            print(f"    missing SPI file: {p.name}")
            continue
        df = pd.read_csv(p, encoding="utf-8-sig")
        id_cols = [c for c in ("VILLAGE", "TEHSIL", "DISTRICT") if c in df.columns]
        date_cols = [c for c in df.columns if re.fullmatch(r"\d{4}-\d{2}", str(c))]
        long = df.melt(id_vars=id_cols, value_vars=date_cols,
                       var_name="period", value_name=f"SPI{k}")
        frames.append(long)
    if not frames:
        return pd.DataFrame(columns=["village", "tehsil", "period"])
    out = frames[0]
    for nxt in frames[1:]:
        out = out.merge(nxt, on=id_cols + ["period"], how="outer")
    out = out.rename(columns={"VILLAGE": "village", "TEHSIL": "tehsil"})
    out["period"] = out["period"].astype(str)
    return out.drop_duplicates(subset=["village", "tehsil", "period"])


def load_nsmi(nsmi_csv: Path) -> pd.DataFrame:
    if not nsmi_csv.exists():
        print(f"    NSMI CSV not found: {nsmi_csv}")
        return pd.DataFrame(columns=["village_idx", "period", "NSMI"])
    df = pd.read_csv(nsmi_csv)
    df = df[["village_idx", "period", "NSMI"]].copy()
    df["village_idx"] = df["village_idx"].astype(int)
    df["period"] = df["period"].astype(str)
    df = df.drop_duplicates(["village_idx", "period"])
    return df


def sample_chirps(chirps_dir: Path, villages: list[dict]) -> pd.DataFrame:
    cent = [centroid_lonlat(v["geom"]) for v in villages]
    lons = np.array([c[0] for c in cent])
    lats = np.array([c[1] for c in cent])
    recs = []
    for period, path in scan_chirps(chirps_dir).items():
        with rasterio.open(path) as src:
            a = src.read(1)
            tr = src.transform
            for i in range(len(villages)):
                colf, rowf = (~tr) * (lons[i], lats[i])
                row, col = int(round(rowf)), int(round(colf))
                if 0 <= row < src.height and 0 <= col < src.width:
                    val = float(a[row, col])
                    recs.append({"village_idx": i + 1, "period": period,
                                 "Rain_mm": val if np.isfinite(val) else np.nan})
    return pd.DataFrame(recs)


# =====================================================================
# derived indices + composite CDI
# =====================================================================
def _load_cfg() -> dict:
    import yaml
    with CFG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


NORMALISERS = {
    "neg_clip": lambda s: (-s / 3.0).clip(0.0, 1.0),
    "inv_0_100": lambda s: (1.0 - s / 100.0).clip(0.0, 1.0),
}


def _robust_z(df: pd.DataFrame, col: str) -> pd.Series:
    """Per (village, calendar month) robust standardised anomaly -> 0..1.

    S = clip(-z / 3, 0, 1) with z = (x - median) / (1.4826 * MAD).
    A normal month (z ~ 0) gives S ~ 0 (None/D0); only deficits score.
    """
    keys = [df["village_idx"], df["month"]]
    med = df.groupby(["village_idx", "month"])[col].transform("median")
    mad = ((df[col] - med).abs()
           .groupby([df["village_idx"], df["month"]]).transform("median"))
    scale = 1.4826 * mad
    z = (df[col] - med) / scale.where(scale > 1e-9)
    return (-z / 3.0).clip(0.0, 1.0)


def _classify(v, thresholds) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "ND"
    for t in thresholds:
        if v < t["max"]:
            return t["code"]
    return "D4"


def _row_cdi(vals: dict, weights: dict, min_inputs: int):
    num = den = 0.0
    contrib = {}
    used = 0
    for name, s in vals.items():
        if s is None or (isinstance(s, float) and math.isnan(s)):
            continue
        w = weights.get(name)
        if w is None:
            continue
        num += w * s
        den += w
        contrib[name] = round(w * s, 4)
        used += 1
    if used < min_inputs or den == 0:
        return None, contrib
    return round(num / den, 4), contrib


def derive_indices(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    panel = panel.copy()
    panel["month"] = panel["period"].str.slice(5, 7).astype(int)
    g_rain = panel.groupby(["village_idx", "month"])["Rain_mm"]
    lo = g_rain.transform("min")
    hi = g_rain.transform("max")
    rng = hi - lo
    panel["PCI"] = ((100.0 * (panel["Rain_mm"] - lo) / rng)
                    .where(rng > 0.1)).clip(0.0, 100.0)
    return panel


def fuse_cdi(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    weights = cfg["weights"]
    min_inputs = int(cfg["min_inputs"])
    norm_cfg = cfg["normalisation"]
    spi_col = {"SPI-1": "SPI1", "SPI-3": "SPI3", "SPI-6": "SPI6",
               "SPI-12": "SPI12"}[cfg["spi_accumulation"]]

    panel = panel.copy()
    panel["SPI"] = panel.get(spi_col)
    sig = {}
    for name in weights:
        method = norm_cfg.get(name, {}).get("method", "robust_z")
        if method == "robust_z":
            sig[name] = _robust_z(panel, name)
        elif method in NORMALISERS:
            sig[name] = NORMALISERS[method](panel[name])
        else:
            sig[name] = pd.Series(np.nan, index=panel.index)

    cdis, contribs = [], []
    for i in range(len(panel)):
        vals = {m: sig[m].iloc[i] for m in weights}
        cdi, contrib = _row_cdi(vals, weights, min_inputs)
        cdis.append(cdi)
        contribs.append(json.dumps(contrib))
    panel["composite_drought_score"] = pd.to_numeric(
        pd.Series(cdis, index=panel.index), errors="coerce")
    panel["component_contributions"] = contribs
    panel["composite_drought_class"] = [
        _classify(v, cfg["thresholds"]) for v in panel["composite_drought_score"]]
    panel["formula_version"] = cfg["formula_version"]
    panel["SPI_scaled"] = np.clip((panel["SPI3"] + 2.0) / 4.0 * 100.0, 0, 100)
    has_cdi = panel["composite_drought_score"].notna()
    has_precip = panel["SPI"].notna() | panel.get("PCI", pd.Series(dtype=float)).notna()
    panel["data_quality_status"] = np.where(
        ~has_cdi, "pending",
        np.where(has_precip, "success", "degraded"))
    return panel


# =====================================================================
# writers
# =====================================================================
def write_outputs(panel, villages, out_dir, cfg, scenes) -> None:
    out_dir = Path(out_dir)
    for sub in ("csv", "json", "geojson"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    meta = pd.DataFrame([{"village_idx": i + 1, "tehsil": v["tehsil"],
                          "village": v["village"]}
                         for i, v in enumerate(villages)])
    df = panel.merge(meta, on="village_idx", how="left")
    df = df.drop_duplicates(["village_idx", "period"])
    df["name"] = df["village"]
    df["date"] = df["period"]
    df = df.sort_values(["village_idx", "period"]).reset_index(drop=True)
    df["data_quality_status"] = df["data_quality_status"].fillna("pending")

    tidy_cols = [
        "village_idx", "village", "tehsil", "name", "year", "month", "date",
        "NDVI", "EVI", "VCI", "VHI", "NSMI", "Rain_mm",
        "SPI1", "SPI3", "SPI6", "SPI12", "PCI", "SPI_scaled",
        "composite_drought_score", "component_contributions",
        "composite_drought_class", "formula_version", "data_quality_status",
    ]
    tidy = df.reindex(columns=tidy_cols)

    legacy = ROOT / "output" / "indices" / "zonal" / "village"
    legacy.mkdir(parents=True, exist_ok=True)
    tidy.to_csv(legacy / "village_monthly_indices.csv", index=False)
    tidy.to_csv(out_dir / "csv" / "village_Latur_monthly_indices.csv", index=False)
    print(f"  csv -> {out_dir / 'csv' / 'village_Latur_monthly_indices.csv'} "
          f"({len(tidy)} rows)")

    num = ["SPI1", "SPI3", "SPI6", "SPI12", "Rain_mm", "NDVI", "EVI",
           "VCI", "VHI", "NSMI", "PCI", "composite_drought_score"]
    dist = (df.groupby(["year", "month"])[num].mean(numeric_only=True)
              .reset_index())
    dist["date"] = (dist["year"].astype(str) + "-" +
                    dist["month"].astype(str).str.zfill(2))
    dist["composite_drought_class"] = [
        _classify(v, cfg["thresholds"]) for v in dist["composite_drought_score"]]
    dry = {"D1", "D2", "D3", "D4"}
    pct = (df.assign(dry=df["composite_drought_class"].isin(dry))
             .groupby(["year", "month"])["dry"].mean().reset_index())
    pct["pct_area_dry"] = (pct["dry"] * 100).round(1)
    dist = dist.merge(pct[["year", "month", "pct_area_dry"]],
                      on=["year", "month"], how="left").sort_values("date")

    district_payload = {
        "district": "Latur", "generated_at": _ts(),
        "formula_version": cfg["formula_version"], "weights": cfg["weights"],
        "series": json.loads(dist.drop(columns=["year"]).to_json(
            orient="records")),
    }
    (out_dir / "json" / "district_monthly.json").write_text(
        json.dumps(district_payload, indent=2, default=float), encoding="utf-8")
    print(f"  json -> {out_dir / 'json' / 'district_monthly.json'}")

    series = {}
    latest_period = df.loc[df["composite_drought_score"].notna(), "period"]
    latest_period = latest_period.max() if not latest_period.empty else ""
    for vidx, g in df.groupby("village_idx"):
        g = g.sort_values("period")
        recs = [{
            "date": r["period"],
            "SPI1": _f(r["SPI1"]), "SPI3": _f(r["SPI3"]),
            "SPI6": _f(r["SPI6"]), "SPI12": _f(r["SPI12"]),
            "Rain_mm": _f(r["Rain_mm"]), "NDVI": _f(r["NDVI"]),
            "EVI": _f(r["EVI"]), "VCI": _f(r["VCI"]), "VHI": _f(r["VHI"]),
            "NSMI": _f(r["NSMI"]), "PCI": _f(r["PCI"]),
            "CDI": _f(r["composite_drought_score"]),
            "class": r["composite_drought_class"],
        } for _, r in g.iterrows()]
        series[str(vidx)] = {"id": int(vidx),
                             "tehsil": g["tehsil"].iloc[0],
                             "village": g["village"].iloc[0], "series": recs}
    (out_dir / "json" / "village_monthly.json").write_text(
        json.dumps({"generated_at": _ts(),
                    "formula_version": cfg["formula_version"],
                    "count": len(series), "latest_period": latest_period,
                    "villages": series}, default=float), encoding="utf-8")
    print(f"  json -> {out_dir / 'json' / 'village_monthly.json'} "
          f"({len(series)} villages)")

    latest = df[df["period"] == latest_period]
    latest_out = {}
    for _, r in latest.iterrows():
        latest_out[str(int(r["village_idx"]))] = {
            "id": int(r["village_idx"]), "tehsil": r["tehsil"],
            "village": r["village"], "date": r["period"],
            "SPI3": _f(r["SPI3"]), "NDVI": _f(r["NDVI"]), "EVI": _f(r["EVI"]),
            "VCI": _f(r["VCI"]), "VHI": _f(r["VHI"]), "NSMI": _f(r["NSMI"]),
            "PCI": _f(r["PCI"]), "CDI": _f(r["composite_drought_score"]),
            "class": r["composite_drought_class"],
        }
    (out_dir / "json" / "village_latest.json").write_text(
        json.dumps({"generated_at": _ts(), "period": latest_period,
                    "villages": latest_out}, default=float), encoding="utf-8")
    _write_latest_geojson(villages, latest, out_dir / "geojson"
                          / "village_latest.geojson")


def _f(v):
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def _write_latest_geojson(villages, latest_df, path: Path) -> None:
    vals = {}
    for _, r in latest_df.iterrows():
        vals[int(r["village_idx"])] = {
            "NDVI": _f(r["NDVI"]), "EVI": _f(r["EVI"]), "VCI": _f(r["VCI"]),
            "VHI": _f(r["VHI"]), "NSMI": _f(r["NSMI"]), "PCI": _f(r["PCI"]),
            "SPI3": _f(r["SPI3"]),
            "CDI": _f(r["composite_drought_score"]),
            "class": r["composite_drought_class"],
        }
    feats = []
    for i, v in enumerate(villages):
        props = {"id": i + 1, "village": v["village"], "tehsil": v["tehsil"]}
        props.update(vals.get(i + 1, {}))
        feats.append({"type": "Feature", "properties": props,
                      "geometry": v["geom"]})
    path.write_text(json.dumps({"type": "FeatureCollection",
                                "features": feats}), encoding="utf-8")
    print(f"  geojson -> {path} ({len(feats)} villages)")


def update_manifest(scenes, panel) -> None:
    have = set(panel.loc[panel["NDVI"].notna(), "period"].unique())
    for (year, month) in sorted(scenes):
        period = f"{year:04d}-{month:02d}"
        manifest.record(DEFAULT_OUT, "sentinel", period,
                        observation_date=f"{period}-15",
                        status="success" if period in have else "failed",
                        outputs=[f"indices/rasters/NDVI/NDVI_{period}.tif",
                                 f"indices/rasters/VCI/VCI_{period}.tif"],
                        cloud_pct=None,
                        qc={"note": "village zonal NDVI/EVI/VCI/VHI"})
    print(f"  manifest -> {DEFAULT_OUT / 'manifests' / 'sentinel.json'}")


# =====================================================================
# main
# =====================================================================
def main():
    ap = argparse.ArgumentParser(description="Latur village drought indices")
    ap.add_argument("--sentinel-dir", type=Path, default=DEFAULT_SENTINEL)
    ap.add_argument("--chirps-dir", type=Path, default=DEFAULT_CHIRPS)
    ap.add_argument("--spi-dir", type=Path, default=DEFAULT_SPI)
    ap.add_argument("--nsmi-csv", type=Path, default=DEFAULT_NSMI_CSV)
    ap.add_argument("--villages", type=Path, default=DEFAULT_VILLAGES)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--raster-dir", type=Path, default=DEFAULT_RASTERS)
    ap.add_argument("--target-res", type=float, default=100.0)
    ap.add_argument("--stage", choices=["indices", "zonal", "all"],
                    default="all")
    ap.add_argument("--max-scenes", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    print("=" * 68)
    print("  LATUR VILLAGE DROUGHT INDICES (batch)")
    print(f"  stage={args.stage}  target_res={args.target_res}m  "
          f"grid={DST_CRS}")
    print("=" * 68)

    scenes = scan_scenes(args.sentinel_dir)
    print(f"[scan] {len(scenes)} unique Sentinel months "
          f"({min(scenes, default='?')} .. {max(scenes, default='?')})")

    villages = load_villages(args.villages)
    ref = reference_grid(villages, args.target_res)
    print(f"[grid] {ref[0]}x{ref[1]} @ {args.target_res}m, "
          f"{len(villages)} villages")

    meta_path = args.raster_dir / "_meta.json"
    offsets = {"NDVI": {"reference": None, "groups": {}},
               "EVI": {"reference": None, "groups": {}}}

    if args.stage in ("indices", "all"):
        stale = args.raster_dir / "NDMI"
        if stale.exists():
            removed = locked = 0
            for p in stale.glob("*.tif"):
                try:
                    p.unlink()
                    removed += 1
                except OSError:
                    locked += 1
            print(f"[clean] stale NDMI rasters: {removed} removed"
                  + (f", {locked} locked (ignored)" if locked else ""))
        print("\n[stage 1a] monthly NDVI / EVI rasters (real units) ...")
        compute_ndvi_evi(scenes, args.raster_dir, ref, args.target_res,
                         args.force, args.max_scenes)

        print("\n[stage 1b] per-batch offset + per-pixel VCI / VHI ...")
        for idx in FLOAT_INDICES:
            offsets[idx] = estimate_offsets(args.raster_dir, idx)
            ref_g = offsets[idx]["reference"]
            for g, m in offsets[idx]["groups"].items():
                print(f"    offset[{idx}] {g} vs {ref_g}: overall "
                      f"{m['overall']:+.4f}, by month "
                      + ", ".join(f"{k}:{v:+.3f}" for k, v in sorted(m.items())
                                  if k.isdigit()))
        (args.raster_dir / "_offsets.json").write_text(
            json.dumps(offsets, indent=1), encoding="utf-8")
        print(f"    offsets -> {args.raster_dir / '_offsets.json'}")
        compute_vci_vhi(scenes, args.raster_dir, offsets["NDVI"], args.force)

    if args.stage in ("zonal", "all"):
        print("\n[stage 2] village zonal statistics + composite CDI ...")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        off_path = args.raster_dir / "_offsets.json"
        if off_path.exists():
            off = json.loads(off_path.read_text())
            offsets = {k: off.get(k, offsets[k]) for k in FLOAT_INDICES}

        rasterizer = VillageRasterizer(villages)
        panel = load_index_panel(args.raster_dir, rasterizer, scenes, meta,
                                 offsets)
        print(f"  zonal panel: {len(panel)} village-month cells")
        if panel.empty:
            print("  no index rasters found; run --stage indices first")
            return

        spi = load_spi_long(args.spi_dir)
        key2idx = {(v["village"], v["tehsil"]): i + 1
                   for i, v in enumerate(villages)}
        spi["village_idx"] = [key2idx.get((r.village, r.tehsil))
                              for r in spi.itertuples()]
        miss = int(spi["village_idx"].isna().sum())
        if miss:
            print(f"  warning: {miss} SPI rows did not match a village")
        spi = spi[spi["village_idx"].notna()].copy()
        spi["village_idx"] = spi["village_idx"].astype(int)
        spi = spi.drop(columns=[c for c in ("village", "tehsil", "DISTRICT")
                                if c in spi.columns])
        spi = spi.drop_duplicates(["village_idx", "period"])
        panel = panel.merge(spi, on=["village_idx", "period"], how="left")
        chirps = sample_chirps(args.chirps_dir, villages)
        panel = panel.merge(chirps, on=["village_idx", "period"], how="left")

        nsmi = load_nsmi(args.nsmi_csv)
        if not nsmi.empty:
            panel = panel.merge(nsmi, on=["village_idx", "period"], how="left")
            nsmi_ok = panel["NSMI"].notna().sum()
            print(f"  NSMI merged: {nsmi_ok}/{len(panel)} rows")
        else:
            panel["NSMI"] = np.nan

        cfg = _load_cfg()
        panel = derive_indices(panel, cfg)
        panel = fuse_cdi(panel, cfg)
        write_outputs(panel, villages, args.out_dir, cfg, scenes)
        update_manifest(scenes, panel)
        print("\nDone.")


if __name__ == "__main__":
    main()
