#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
Latur District drought-index pipeline — full rerun 2016-2026
=====================================================================

End-to-end: Sentinel-2 indices -> village zonal stats -> CHIRPS SPI/PCI
-> transparent composite CDI -> tidy long-format CSV + per-year Excel
sheets + one complete 2016-2026 CSV.

Tolerates the messy raw folders (multiple filename styles, two
band-description conventions, GDAL sidecars, duplicate months) exactly
as the existing pipeline scripts do.

All formulas are cited inline.  CDI weights/thresholds come from
config/composite.yaml and are NOT changed here.

FORMULAS & REFERENCES
---------------------
  NDVI   = (NIR - Red) / (NIR + Red)                                    [Rouse et al. 1973; Tucker 1979]
  EVI    = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1.0)           [Huete et al. 2002]
  NDMI   = (NIR - SWIR1) / (NIR + SWIR1)                                [Gao 1996]
  VCI    = 100 * (NDVI - NDVI_min_m) / (NDVI_max_m - NDVI_min_m)
         per calendar month m (5th..95th percentile envelope)           [Kogan 1995]
  VHI    = VCI   (no LST / thermal band available -> VHI approximated)
  PCI    = 100 * sum(P_i^2) / (sum P_i)^2   per village per year        [Oliver 1980]
  SPI    = Phi^{-1}(H(x));  H(x) = q + (1-q)*G(x);  G = gamma CDF
         shape/scale by Thom (1958) MLE; zero-rain H(0)=q/2             [McKee et al. 1993; Thom 1958; Stagge et al. 2015]
  CDI    = sum(w_i * S_i) / sum(w_i)  over inputs actually present
         missing input excluded from numerator AND denominator          [config/composite.yaml; composite_cdi.py]
         S_i = component normalised to 0..1 drought intensity
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio import Affine
from rasterio.features import rasterize
from rasterio.enums import Resampling
from rasterio.warp import transform_geom, reproject as warp_reproject

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common.raster import scan_rasters, dedupe_by_prefix  # noqa: E402

ROOT = HERE.parent
DEFAULT_SENTINEL = ROOT / "output" / "sentinel_Raw_Composites"
DEFAULT_CHIRPS = ROOT / "output" / "CHIRPS_Rainfall"
DEFAULT_VILLAGES = ROOT / "frontend" / "public" / "data" / "latur_villages.geojson"
DEFAULT_OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
DEFAULT_RASTERS = ROOT / "output" / "indices" / "rasters"
CFG_PATH = ROOT / "config" / "composite.yaml"

DST_CRS = "EPSG:32643"
INDICES = ("NDVI", "EVI", "NDMI", "NSMI", "VCI", "VHI")
SPI_SCALES = (1, 3, 6, 12)
NODATA = -9999.0

BAND_DESC_TO_NAME = {
    "B2": "BLUE", "B3": "GREEN", "B4": "RED", "B8": "NIR",
    "B11": "SWIR1", "B12": "SWIR2",
    "BLUE": "BLUE", "GREEN": "GREEN", "RED": "RED", "NIR": "NIR",
    "SWIR1": "SWIR1", "SWIR2": "SWIR2",
}

SCENE_RE = __import__("re").compile(r"(19|20)(\d{2})[_\-](\d{1,2})")
SKIP_SUFFIX = (".aux.xml", ".ovr", ".crdownload", ".py", ".zip", ".csv",
               ".json", ".txt", ".xml", ".ipynb")
PREF_SCORE = {"s2_l2a_": 0, "s2_latur_": 1, "latur_s2_": 2, "other": 9}
PREFERRED = ("S2_L2A_", "S2_", "Latur_S2_", "other")


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# =====================================================================
# 0. scanning (dual-naming parser preserved from AGENTS.md §4)
# =====================================================================
def scan_sentinel(sentinel_dir: Path) -> dict[tuple[int, int], Path]:
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
            print(f"  skip (no date in name): {name}")
            continue
        year = int(m.group(1) + m.group(2))
        month = int(m.group(3))
        if not 1 <= month <= 12:
            continue
        low2 = name.lower()
        score = 0
        if "s2_l2a_" in low2: score = 0
        elif "s2_latur_" in low2: score = 1
        elif "latur_s2_" in low2: score = 2
        else: score = 9
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
        m = SCENE_RE.search(low)
        if not m:
            continue
        year = int(m.group(1) + m.group(2))
        month = int(m.group(3))
        if not 1 <= month <= 12:
            continue
        out[f"{year:04d}-{month:02d}"] = p
    return dict(sorted(out.items()))


def _centroid_lonlat(geom: dict) -> tuple[float, float]:
    """Robust centroid for Polygon or MultiPolygon geometries."""
    coords = geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        rings = [ring for poly in coords for ring in poly]
    else:
        rings = [coords[0]]
    arr = np.vstack([np.asarray(ring, dtype="float64") for ring in rings])
    return float(arr[:, 0].mean()), float(arr[:, 1].mean())


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


def _geom_bounds(geom: dict):
    """Return (minx, miny, maxx, maxy) for Polygon or MultiPolygon."""
    coords = geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        rings = [ring for poly in coords for ring in poly]
    else:
        rings = [coords[0]]
    xs = []; ys = []
    for ring in rings:
        a = np.asarray(ring, dtype="float64")
        xs.append(a[:, 0]); ys.append(a[:, 1])
    xs = np.concatenate(xs); ys = np.concatenate(ys)
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def reference_grid(villages: list[dict], target_res: float):
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for v in villages:
        g = transform_geom("EPSG:4326", DST_CRS, v["geom"])
        bx0, by0, bx1, by1 = _geom_bounds(g)
        minx = min(minx, bx0); miny = min(miny, by0)
        maxx = max(maxx, bx1); maxy = max(maxy, by1)
    left = math.floor(minx / target_res) * target_res
    bottom = math.floor(miny / target_res) * target_res
    right = math.ceil(maxx / target_res) * target_res
    top = math.ceil(maxy / target_res) * target_res
    width = int(round((right - left) / target_res))
    height = int(round((top - bottom) / target_res))
    return height, width, Affine(target_res, 0.0, left, 0.0, -target_res, top)


# =====================================================================
# 1. band reading (band-description based; tolerates mixed conventions)
# =====================================================================
def _rescale_dn(arr: np.ndarray) -> np.ndarray:
    """Auto-detect GEE DN scale (0..10000) -> reflectance 0..1."""
    with np.errstate(invalid="ignore"):
        m = np.nanmax(arr)
    if m > 10:
        return arr / 10000.0
    return arr


def read_bands(path: Path, target_res: float):
    """Return {short_name: array} on the reference grid, plus transform/crs."""
    with rasterio.open(path) as src:
        factor = max(1, int(round(target_res / abs(src.res[0]))))
        h = math.ceil(src.height / factor)
        w = math.ceil(src.width / factor)
        dec_transform = src.transform * Affine.scale(src.width / w, src.height / h)
        nodata = src.nodata
        bands = {}
        for b in range(1, src.count + 1):
            desc = (src.descriptions[b - 1] or "").strip().upper()
            short = BAND_DESC_TO_NAME.get(desc)
            if short is None:
                continue
            a = src.read(b, out_shape=(h, w),
                         resampling=Resampling.average).astype("float64")
            if nodata is not None:
                a[a == nodata] = np.nan
            bands[short] = a
    return bands, dec_transform, src.crs


def to_ref(arr: np.ndarray, src_transform, src_crs, ref_transform, ref_shape):
    dst = np.full(ref_shape, np.nan, dtype="float32")
    warp_reproject(source=arr, destination=dst,
                   src_transform=src_transform, src_crs=src_crs,
                   dst_transform=ref_transform, dst_crs=DST_CRS,
                   src_nodata=np.nan, dst_nodata=np.nan,
                   resampling=Resampling.bilinear)
    return dst


# =====================================================================
# 2. index formulas (per-pixel) — cited
# =====================================================================
def ndvi(nir, red):
    # (NIR - Red) / (NIR + Red)  — Rouse et al. 1973; Tucker 1979
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (nir - red) / (nir + red)
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, -1.0, 1.0)


def evi(nir, red, blue):
    # 2.5*(NIR-Red)/(NIR + 6*Red - 7.5*Blue + 1) — Huete et al. 2002
    with np.errstate(invalid="ignore", divide="ignore"):
        v = 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0)
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, -1.0, 1.0)


def ndmi(nir, swir1):
    # (NIR - SWIR1) / (NIR + SWIR1) — Gao 1996
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (nir - swir1) / (nir + swir1)
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, -1.0, 1.0)


def nsmi(swir1, swir2):
    # (SWIR1 - SWIR2) / (SWIR1 + SWIR2) — Normalized Soil Moisture Index
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (swir1 - swir2) / (swir1 + swir2)
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, -1.0, 1.0)



# =====================================================================
# 3. stage 1: monthly NDVI/EVI/NDMI rasters + zonal means per village
# =====================================================================
class VillageRasterizer:
    def __init__(self, villages: list[dict]):
        self.villages = villages
        self.n = len(villages)
        self._geoms = None
        self._labels = {}

    def _geoms_projected(self):
        if self._geoms is None:
            self._geoms = [(transform_geom("EPSG:4326", DST_CRS, v["geom"]), i + 1)
                           for i, v in enumerate(self.villages)]
        return self._geoms

    def labels(self, shape, transform):
        key = (shape, tuple(round(x, 6) for x in transform)[:6])
        if key not in self._labels:
            if len(self._labels) > 4:
                self._labels.clear()
            self._labels[key] = rasterize(
                self._geoms_projected(), out_shape=shape, transform=transform,
                fill=0, dtype="uint32", all_touched=True)
        return self._labels[key]

    @staticmethod
    def zonal_sum_count(arr, labels, n):
        valid = np.isfinite(arr) & (labels > 0)
        if not valid.any():
            return np.full(n, np.nan), np.zeros(n, dtype=np.int64)
        ids = labels[valid].astype("int64")
        vals = arr[valid].astype("float64")
        sums = np.bincount(ids, weights=vals, minlength=n + 1)[1:n + 1]
        cnts = np.bincount(ids, minlength=n + 1)[1:n + 1]
        return sums, cnts


def compute_sentinel_zonal(scenes, raster_dir, rasterizer, target_res, force):
    """NDVI/EVI/NDMI/NSMI zonal mean per village per period. Returns DataFrame."""
    recs = []
    ref = None
    t0 = time.time()
    n_scenes = len(scenes)
    optical_indices = INDICES[:4]  # ("NDVI", "EVI", "NDMI", "NSMI")
    for i, ((year, month), path) in enumerate(scenes.items(), 1):
        period = f"{year:04d}-{month:02d}"
        out_meta = raster_dir / "_meta.json"
        meta = json.loads(out_meta.read_text()) if out_meta.exists() else {}

        needed = [name for name in optical_indices
                  if force or not (raster_dir / name / f"{name}_{period}.npz").exists()]

        if not needed:
            print(f"  [{i}/{n_scenes}] {period} cached")
            for name in optical_indices:
                p = raster_dir / name / f"{name}_{period}.npz"
                if p.exists():
                    d = np.load(p)
                    for v in range(rasterizer.n):
                        recs.append({
                            "village_idx": v + 1, "year": year, "month": month,
                            "period": period, "indice": name,
                            "value": float(d["val"][v]) if v < len(d["val"]) else np.nan,
                        })
            continue

        print(f"  [{i}/{n_scenes}] {period} <- {path.name} (computing {needed}) ...", end="", flush=True)
        try:
            # First load any indices that are already cached
            for name in optical_indices:
                if name not in needed:
                    p = raster_dir / name / f"{name}_{period}.npz"
                    if p.exists():
                        d = np.load(p)
                        for v in range(rasterizer.n):
                            recs.append({
                                "village_idx": v + 1, "year": year, "month": month,
                                "period": period, "indice": name,
                                "value": float(d["val"][v]) if v < len(d["val"]) else np.nan,
                            })

            bands, dec_transform, src_crs = read_bands(path, target_res)
            red = _rescale_dn(bands["RED"]) if "RED" in bands else None
            nir = _rescale_dn(bands["NIR"]) if "NIR" in bands else None
            blue = _rescale_dn(bands["BLUE"]) if "BLUE" in bands else None
            swir1 = _rescale_dn(bands["SWIR1"]) if "SWIR1" in bands else None
            swir2 = _rescale_dn(bands["SWIR2"]) if "SWIR2" in bands else None

            to_compute = {}
            target_shape = None

            if red is not None and nir is not None:
                target_shape = red.shape
                valid = np.isfinite(red) & np.isfinite(nir)
                if "NDVI" in needed:
                    to_compute["NDVI"] = ndvi(nir, red)
                if "EVI" in needed and blue is not None:
                    to_compute["EVI"] = evi(nir, red, blue)
                if "NDMI" in needed and swir1 is not None:
                    to_compute["NDMI"] = ndmi(nir, swir1)

            if "NSMI" in needed and swir1 is not None and swir2 is not None:
                target_shape = swir1.shape
                to_compute["NSMI"] = nsmi(swir1, swir2)

            if target_shape is not None:
                labels = rasterizer.labels(target_shape, dec_transform)
                n = rasterizer.n
                for name, arr in to_compute.items():
                    sums, cnts = VillageRasterizer.zonal_sum_count(arr, labels, n)
                    mean = np.divide(sums, cnts, out=np.full(n, np.nan), where=cnts > 0)
                    npz_path = raster_dir / name / f"{name}_{period}.npz"
                    npz_path.parent.mkdir(parents=True, exist_ok=True)
                    np.savez(npz_path, val=mean)
                    for v in range(n):
                        recs.append({
                            "village_idx": v + 1, "year": year, "month": month,
                            "period": period, "indice": name, "value": float(mean[v]),
                        })
            meta[period] = {"zonal_done": True, "source": path.name,
                            "bands": list(bands.keys())}
            out_meta.write_text(json.dumps(meta, indent=1), encoding="utf-8")
            print(" ok")
        except Exception as exc:  # noqa: BLE001
            print(f" FAILED: {type(exc).__name__}: {exc}")
            meta[period] = {"zonal_done": False, "source": path.name, "error": str(exc)}
            out_meta.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    meta_path = raster_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"[sentinel zonal] {len(recs)} records in {(time.time()-t0)/60:.1f} min")
    return pd.DataFrame(recs)


# =====================================================================
# 4. VCI / VHI per village per calendar month (Kogan 1995)
# =====================================================================
def compute_vci_vhi(df_sen: pd.DataFrame, rasterizer) -> pd.DataFrame:
    """VCI per (village, calendar month) from NDVI climatology; VHI = VCI."""
    df = df_sen[df_sen["indice"] == "NDVI"].copy() if not df_sen.empty else df_sen.iloc[0:0].copy()
    if df.empty:
        print("[VCI/VHI] no NDVI records; skipping")
        return pd.DataFrame(columns=["village_idx","year","month","period","indice","value"])
    df["month"] = df["period"].str.slice(5, 7).astype(int)
    out_rows = []
    # group by village then month to build per-village-per-month envelope
    for (vidx, m), g in df.groupby(["village_idx", "month"]):
        vals = g["value"].dropna().values
        if vals.size < 2:
            continue
        lo = np.nanpercentile(vals, 5)
        hi = np.nanpercentile(vals, 95)
        rng = hi - lo
        for _, r in g.iterrows():
            v = r["value"]
            vci = 100.0 * (v - lo) / rng if rng > 1e-4 else np.nan
            out_rows.append({
                "village_idx": int(vidx), "year": int(r["year"]), "month": int(m),
                "period": r["period"], "indice": "VCI",
                "value": float(np.clip(vci, 0, 100)) if np.isfinite(vci) else np.nan,
            })
            out_rows.append({
                "village_idx": int(vidx), "year": int(r["year"]), "month": int(m),
                "period": r["period"], "indice": "VHI",
                "value": float(np.clip(vci, 0, 100)) if np.isfinite(vci) else np.nan,
            })
    res = pd.DataFrame(out_rows)
    print(f"[VCI/VHI] {len(res)} records")
    return res


# =====================================================================
# 5. CHIRPS rainfall per village per period (centroid sample)
# =====================================================================
def sample_chirps(chirps_dir: Path, villages: list[dict]) -> pd.DataFrame:
    scans = scan_chirps(chirps_dir)
    cents = [_centroid_lonlat(v["geom"]) for v in villages]
    lons = np.array([c[0] for c in cents])
    lats = np.array([c[1] for c in cents])
    recs = []
    for period, path in scans.items():
        with rasterio.open(path) as src:
            a = src.read(1)
            tr = src.transform
            nd = src.nodata
            for i in range(len(villages)):
                colf, rowf = ~tr * (lons[i], lats[i])
                row, col = int(round(rowf)), int(round(colf))
                if 0 <= row < src.height and 0 <= col < src.width:
                    val = float(a[row, col])
                    if nd is not None and val == nd:
                        val = np.nan
                    if not np.isfinite(val) or val < 0:
                        val = np.nan
                    recs.append({"village_idx": i + 1, "period": period, "Rain_mm": val})
    df = pd.DataFrame(recs)
    df["year"] = df["period"].str.slice(0, 4).astype(int)
    df["month"] = df["period"].str.slice(5, 7).astype(int)
    print(f"[CHIRPS] {len(df)} village-rainfall records ({len(scans)} months)")
    return df


# =====================================================================
# 6. SPI — McKee et al. 1993 / Thom 1958 / Stagge et al. 2015 (cited)
# =====================================================================
def gamma_params(x: np.ndarray):
    """Thom (1958) MLE shape/scale for non-zero values."""
    mean = x.mean()
    A = np.log(mean) - np.mean(np.log(x))
    if A <= 0:
        return np.nan, np.nan
    alpha = (1.0 + np.sqrt(1.0 + 4.0 * A / 3.0)) / (4.0 * A)
    beta = mean / alpha
    return alpha, beta


def spi_from_series(x_all: np.ndarray, zero_centre: bool = True,
                    min_nonzero: int = 3) -> np.ndarray:
    out = np.full(x_all.shape, np.nan)
    good = np.isfinite(x_all)
    calib = x_all[good]
    n = calib.size
    if n == 0:
        return out
    nonzero = calib[calib > 0]
    q = (n - nonzero.size) / n
    if nonzero.size < min_nonzero:
        return out
    alpha, beta = gamma_params(nonzero)
    if not np.isfinite(alpha):
        return out
    from scipy import stats
    x = x_all[good]
    G = stats.gamma.cdf(x, a=alpha, scale=beta)
    Hx = q + (1.0 - q) * G
    Hx = np.where(x <= 0, q / 2.0 if zero_centre else q, Hx)
    Hx = np.clip(Hx, 0.0001, 0.9999)
    out[good] = stats.norm.ppf(Hx)
    return out


def rolling_sum(arr: np.ndarray, k: int) -> np.ndarray:
    if k == 1:
        return arr.copy()
    T = arr.shape[0]
    out = np.full_like(arr, np.nan)
    for t in range(k - 1, T):
        win = arr[t - k + 1:t + 1]
        ok = np.isfinite(win).all()
        if ok:
            out[t] = np.nansum(win)
    return out


def compute_spi_village(rain_df: pd.DataFrame, village_idx: int,
                        periods: list[str]) -> dict:
    """SPI-1/3/6/12 for one village across periods (indexed by calendar month)."""
    g = rain_df[rain_df["village_idx"] == village_idx].sort_values("period")
    if g.empty:
        return {}
    p = g.set_index("period")["Rain_mm"]
    # align to full period index (missing -> NaN)
    full = p.reindex(periods)
    vals = full.values.astype("float64")
    T = len(periods)
    # months present
    months = np.array([int(per[5:7]) for per in periods])
    out = {k: np.full(T, np.nan) for k in SPI_SCALES}
    for k in SPI_SCALES:
        acc = rolling_sum(vals, k)
        for m in range(1, 13):
            tidx = np.where(months == m)[0]
            if tidx.size == 0:
                continue
            out[k][tidx] = spi_from_series(acc[tidx])
    return {f"SPI{k}": out[k] for k in SPI_SCALES}


# =====================================================================
# 7. PCI — Oliver 1980 (per village per year)
# =====================================================================
def compute_pci(rain_df: pd.DataFrame) -> pd.DataFrame:
    """PCI = 100*sum(P_i^2)/(sum P_i)^2 per village-year (Oliver 1980)."""
    rows = []
    for (vidx, yr), g in rain_df.groupby(["village_idx", "year"]):
        p = g["Rain_mm"].dropna().values
        if p.size == 0 or p.sum() == 0:
            pci = np.nan
        else:
            pci = 100.0 * float(np.sum(p ** 2)) / float(p.sum() ** 2)
        rows.append({"village_idx": int(vidx), "year": int(yr), "PCI": pci})
    return pd.DataFrame(rows)


# =====================================================================
# 8. CDI fusion — config/composite.yaml (transparent weighted composite)
# =====================================================================
def _load_cfg() -> dict:
    import yaml
    with CFG_PATH.open() as f:
        return yaml.safe_load(f)


def _robust_z(df: pd.DataFrame, col: str) -> pd.Series:
    """Per (village, calendar month) robust standardised anomaly -> 0..1."""
    med = df.groupby(["village_idx", "month"])[col].transform("median")
    mad = ((df[col] - med).abs()
           .groupby([df["village_idx"], df["month"]]).transform("median"))
    scale = 1.4826 * mad
    z = (df[col] - med) / scale.where(scale > 1e-9)
    return (-z / 3.0).clip(0.0, 1.0)


def _neg_clip(s: pd.Series) -> pd.Series:
    return (-s / 3.0).clip(0.0, 1.0)


def _classify(v, thresholds):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "ND"
    for t in thresholds:
        if v < t["max"]:
            return t["code"]
    return "D4"


def fuse_cdi(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    weights = cfg["weights"]
    min_inputs = int(cfg["min_inputs"])
    norm_cfg = cfg["normalisation"]
    spi_col = {"SPI-1": "SPI1", "SPI-3": "SPI3", "SPI-6": "SPI6",
               "SPI-12": "SPI12"}[cfg["spi_accumulation"]]
    panel = panel.copy()
    panel["month"] = panel["period"].str.slice(5, 7).astype(int)
    spi_col = {"SPI-1": "SPI1", "SPI-3": "SPI3", "SPI-6": "SPI6",
               "SPI-12": "SPI12"}[cfg["spi_accumulation"]]
    # ensure the SPI column used for fusion exists
    if spi_col in panel.columns:
        panel["SPI"] = panel[spi_col]
    else:
        panel["SPI"] = np.nan
    # ensure every weighted component column exists (missing -> all NaN)
    for name in weights:
        if name not in panel.columns:
            panel[name] = np.nan
    sig = {}
    for name in weights:
        method = norm_cfg.get(name, {}).get("method", "robust_z")
        if name == "SPI":
            sig[name] = _neg_clip(panel["SPI"])
        elif method == "robust_z":
            sig[name] = _robust_z(panel, name)
        else:
            sig[name] = pd.Series(np.nan, index=panel.index)

    cdis, contribs, used_n = [], [], []
    for i in range(len(panel)):
        vals = {m: sig[m].iloc[i] for m in weights}
        num = den = 0.0
        contrib = {}
        used = 0
        for m, s in vals.items():
            if s is None or (isinstance(s, float) and math.isnan(s)):
                continue
            w = weights.get(m)
            if w is None:
                continue
            num += w * s; den += w
            contrib[m] = round(w * s, 4)
            used += 1
        if used < min_inputs or den == 0:
            cdis.append(np.nan); contribs.append({}); used_n.append(used); continue
        cdis.append(round(num / den, 4))
        contribs.append(contrib)
        used_n.append(used)

    panel["composite_drought_score"] = cdis
    panel["component_contributions"] = [json.dumps(c) for c in contribs]
    panel["inputs_available"] = used_n
    panel["composite_drought_class"] = [
        _classify(v, cfg["thresholds"]) for v in panel["composite_drought_score"]]
    panel["formula_version"] = cfg["formula_version"]
    panel["data_quality_status"] = np.where(
        panel["composite_drought_score"].notna(), "success", "pending")
    return panel


# =====================================================================
# 9. writers: tidy long CSV + per-year Excel + complete CSV
# =====================================================================
def write_tidy(panel: pd.DataFrame, villages: list[dict], out_dir: Path,
               cfg: dict):
    meta = pd.DataFrame([{"village_idx": i + 1, "tehsil": v["tehsil"],
                          "village": v["village"]} for i, v in enumerate(villages)])
    # panel is wide (one column per indice); melt to long tidy form
    id_vars = ["village_idx", "year", "month", "period"]
    EXCLUDE_TIDY = {"SPI", "inputs_available"}
    value_vars = [c for c in panel.select_dtypes(include="number").columns
                  if c not in id_vars and c not in EXCLUDE_TIDY]
    long = panel.melt(id_vars=id_vars, value_vars=value_vars,
                      var_name="indice", value_name="value")
    df = long.merge(meta, on="village_idx", how="left")
    df = df.drop_duplicates(["village_idx", "period", "indice"])

    tidy_cols = ["village", "tehsil", "year", "month", "period", "indice", "value"]
    tidy = df.reindex(columns=tidy_cols)
    tidy["value"] = pd.to_numeric(tidy["value"], errors="coerce")

    out_dir = Path(out_dir)
    (out_dir / "csv").mkdir(parents=True, exist_ok=True)
    (out_dir / "excel").mkdir(parents=True, exist_ok=True)
    (out_dir / "json").mkdir(parents=True, exist_ok=True)

    # complete CSV 2016-2026
    complete_csv = out_dir / "csv" / "village_indices_complete_2016_2026.csv"
    tidy.sort_values(["village", "period", "indice"]).to_csv(complete_csv, index=False)
    print(f"  complete CSV -> {complete_csv} ({len(tidy)} rows)")

    # per-year Excel sheets inside one workbook per year + one combined workbook
    years = sorted(tidy["year"].dropna().unique())
    combined_path = out_dir / "excel" / "Latur_village_indices_2016_2026.xlsx"
    with pd.ExcelWriter(combined_path, engine="openpyxl") as xw:
        # README sheet citing formulas
        readme = pd.DataFrame({
            "Item": ["Study area", "Period", "Indices",
                     "SPI formula", "SPI reference",
                     "NDVI formula", "NDVI reference",
                     "EVI formula", "EVI reference",
                     "NDMI formula", "NDMI reference",
                     "NSMI formula", "NSMI reference",
                     "VCI formula", "VCI reference",
                     "PCI formula", "PCI reference",
                     "CDI formula", "CDI config",
                     "VHI note"],
            "Description": [
                "Latur district, Marathwada, Maharashtra (954 villages)",
                "2016-01 to 2026-12 (monthly)",
                "NDVI, EVI, NDMI, NSMI, VCI, VHI, SPI-1/3/6/12, Rain_mm, PCI, CDI",
                "SPI = inverse standard normal of H(x); H(x) = q + (1-q)*G(x)",
                "McKee et al. 1993; Thom 1958 MLE; zero-correction Stagge et al. 2015",
                "NDVI = (NIR - Red)/(NIR + Red)",
                "Rouse et al. 1973; Tucker 1979",
                "EVI = 2.5*(NIR - Red)/(NIR + 6*Red - 7.5*Blue + 1)",
                "Huete et al. 2002",
                "NDMI = (NIR - SWIR1)/(NIR + SWIR1)",
                "Gao 1996",
                "NSMI = (SWIR1 - SWIR2)/(SWIR1 + SWIR2) [Normalized Soil Moisture Index]",
                "Gao 1996; Boles et al. 2020; Sentinel-2 SWIR1 (B11) & SWIR2 (B12)",
                "VCI = 100*(NDVI - NDVI_min_m)/(NDVI_max_m - NDVI_min_m) per calendar month",
                "Kogan 1995",
                "PCI (Precipitation Concentration Index) = 100*sum(P_i^2)/(sum P_i)^2 per village-year",
                "Oliver 1980",
                "CDI = sum(w_i*S_i)/sum(w_i) over inputs actually present",
                "config/composite.yaml (formula_version " + cfg["formula_version"] + ")",
                "VHI = VCI (no LST/thermal band available)",
            ]})
        readme.to_excel(xw, sheet_name="README_Formulas", index=False)

        for y in years:
            sub = tidy[tidy["year"] == y]
            sheet = f"{y}"
            sub.to_excel(xw, sheet_name=sheet, index=False)
    print(f"  Excel (per-year sheets + combined) -> {combined_path}")

    # per-year separate workbooks
    for y in years:
        sub = tidy[tidy["year"] == y]
        ypath = out_dir / "excel" / f"Latur_village_indices_{y}.xlsx"
        sub.to_excel(ypath, index=False)
    print(f"  per-year Excel workbooks -> {out_dir / 'excel'}")

    # latest-period snapshot JSON for the dashboard
    latest = panel.loc[panel["composite_drought_score"].notna(), "period"]
    latest = latest.max() if not latest.empty else ""
    snap = {}
    panel_meta = panel.merge(meta, on="village_idx", how="left")
    for _, r in panel_meta[panel_meta["period"] == latest].iterrows():
        snap[str(int(r["village_idx"]))] = {
            "id": int(r["village_idx"]), "village": str(r.get("village", "")),
            "tehsil": str(r.get("tehsil", "")), "date": str(r.get("period", "")),
            "CDI": float(r["composite_drought_score"]) if pd.notna(r.get("composite_drought_score")) else None,
            "class": str(r.get("composite_drought_class", "pending")),
            "NDVI": float(r["NDVI"]) if "NDVI" in r and pd.notna(r["NDVI"]) else None,
            "EVI": float(r["EVI"]) if "EVI" in r and pd.notna(r["EVI"]) else None,
            "NDMI": float(r["NDMI"]) if "NDMI" in r and pd.notna(r["NDMI"]) else None,
            "NSMI": float(r["NSMI"]) if "NSMI" in r and pd.notna(r["NSMI"]) else None,
            "VCI": float(r["VCI"]) if "VCI" in r and pd.notna(r["VCI"]) else None,
            "VHI": float(r["VHI"]) if "VHI" in r and pd.notna(r["VHI"]) else None,
            "SPI3": float(r["SPI3"]) if "SPI3" in r and pd.notna(r["SPI3"]) else None,
            "PCI": float(r["PCI"]) if "PCI" in r and pd.notna(r["PCI"]) else None,
        }
    (out_dir / "json" / "village_latest.json").write_text(
        json.dumps({"generated_at": _ts(), "period": latest,
                    "formula_version": cfg["formula_version"], "villages": snap},
                   default=float), encoding="utf-8")
    print(f"  latest snapshot -> {out_dir / 'json' / 'village_latest.json'} ({len(snap)} villages)")
    return tidy, complete_csv


# =====================================================================
# main
# =====================================================================
def main():
    ap = argparse.ArgumentParser(description="Latur drought-index pipeline 2016-2026")
    ap.add_argument("--sentinel-dir", type=Path, default=DEFAULT_SENTINEL)
    ap.add_argument("--chirps-dir", type=Path, default=DEFAULT_CHIRPS)
    ap.add_argument("--villages", type=Path, default=DEFAULT_VILLAGES)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--raster-dir", type=Path, default=DEFAULT_RASTERS)
    ap.add_argument("--target-res", type=float, default=100.0,
                    help="resampling resolution in metres (default 100 m for speed)")
    ap.add_argument("--force", action="store_true", help="recompute even if cached")
    ap.add_argument("--max-scenes", type=int, default=None,
                    help="limit scenes (test run)")
    args = ap.parse_args()

    cfg = _load_cfg()
    print("=" * 70)
    print("  LATUR DROUGHT-INDEX PIPELINE 2016-2026  (full rerun)")
    print(f"  target_res={args.target_res}m  force={args.force}")
    print(f"  CDI formula_version={cfg['formula_version']}  min_inputs={cfg['min_inputs']}")
    print("=" * 70)

    scenes = scan_sentinel(args.sentinel_dir)
    print(f"[scan] {len(scenes)} unique Sentinel months")
    if args.max_scenes:
        scenes = dict(list(scenes.items())[:args.max_scenes])
        print(f"  limited to {len(scenes)} scenes")

    villages = load_villages(args.villages)
    ref = reference_grid(villages, args.target_res)
    print(f"[grid] {ref[0]}x{ref[1]} @ {args.target_res}m, {len(villages)} villages")

    rasterizer = VillageRasterizer(villages)
    args.raster_dir.mkdir(parents=True, exist_ok=True)

    print("\n[stage 1] Sentinel NDVI/EVI/NDMI zonal means ...")
    df_sen = compute_sentinel_zonal(scenes, args.raster_dir, rasterizer,
                                    args.target_res, args.force)

    print("\n[stage 2] VCI / VHI from NDVI climatology (Kogan 1995) ...")
    df_vci = compute_vci_vhi(df_sen, rasterizer)

    print("\n[stage 3] CHIRPS rainfall per village (centroid sample) ...")
    df_rain = sample_chirps(args.chirps_dir, villages)
    periods = sorted(df_rain["period"].unique())

    print("\n[stage 4] SPI-1/3/6/12 per village (McKee 1993 / Thom 1958) ...")
    from scipy import stats  # ensure imported
    spi_frames = []
    n_v = len(villages)
    for i, v in enumerate(villages, 1):
        sp = compute_spi_village(df_rain, i, periods)
        if not sp:
            continue
        g = df_rain[df_rain["village_idx"] == i].set_index("period")["Rain_mm"]
        for per in periods:
            if per not in g.index:
                continue
            rec = {"village_idx": i, "period": per, "Rain_mm": float(g.get(per, np.nan))}
            for k, arr in sp.items():
                tidx = periods.index(per)
                rec[k] = float(arr[tidx])
            spi_frames.append(rec)
        if i % 100 == 0:
            print(f"    SPI {i}/{n_v}")
    df_spi = pd.DataFrame(spi_frames)
    df_spi = df_spi.drop(columns=["Rain_mm"], errors="ignore")
    print(f"  SPI records: {len(df_spi)}")

    print("\n[stage 5] PCI per village-year (Oliver 1980) ...")
    df_pci = compute_pci(df_rain)

    print("\n[stage 6] pivot indices to wide + fuse CDI (config/composite.yaml) ...")
    panel_sv = pd.concat([df_sen, df_vci], ignore_index=True)
    panel_sv["year"] = panel_sv["period"].str.slice(0, 4).astype(int)
    panel_sv["month"] = panel_sv["period"].str.slice(5, 7).astype(int)

    wide = panel_sv.pivot_table(index=["village_idx", "year", "month", "period"],
                                columns="indice", values="value",
                                aggfunc="first").reset_index()
    wide = wide.merge(df_spi, on=["village_idx", "period"], how="left")
    wide = wide.merge(df_rain[["village_idx", "period", "Rain_mm"]],
                      on=["village_idx", "period"], how="left")
    wide = wide.merge(df_pci, on=["village_idx", "year"], how="left")
    wide["year"] = wide["period"].str.slice(0, 4).astype(int)
    wide["month"] = wide["period"].str.slice(5, 7).astype(int)
    wide = fuse_cdi(wide, cfg)

    print("\n[stage 7] write tidy CSV + per-year Excel + complete CSV ...")
    tidy, complete_csv = write_tidy(wide, villages, args.out_dir, cfg)

    # legacy wide CSV for compatibility with composite_cdi.py / dashboard
    wide_out = args.out_dir / "csv" / "village_Latur_monthly_indices.csv"
    wide_out.parent.mkdir(parents=True, exist_ok=True)
    meta = pd.DataFrame([{"village_idx": i + 1, "tehsil": v["tehsil"], "village": v["village"]} for i, v in enumerate(villages)])
    wide_with_meta = wide.merge(meta, on="village_idx", how="left")
    wide_with_meta["name"] = wide_with_meta["village"]
    wide_with_meta["date"] = wide_with_meta["period"]
    lead = ["village_idx", "village", "tehsil", "name", "year", "month", "date", "period"]
    rest = [c for c in wide_with_meta.columns if c not in lead]
    wide_with_meta[lead + rest].to_csv(wide_out, index=False)
    print(f"  legacy wide CSV -> {wide_out} ({len(wide_with_meta)} rows)")

    print("\nDone. Outputs under", args.out_dir)


if __name__ == "__main__":
    main()
