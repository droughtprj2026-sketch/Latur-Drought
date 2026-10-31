# -*- coding: utf-8 -*-
"""
Near-real-time village update: Sentinel-2 + CHIRPS  ->  SPI, VCI, CDI  ->  dashboard files.

One run, for each target month P (oldest first):

  1. Sentinel-2  (GEE COPERNICUS/S2_SR_HARMONIZED, SCL-masked monthly median)
       village mean NDVI / EVI
  2. CHIRPS      (GEE UCSB-CHG/CHIRPS/DAILY, summed over the month)
       village mean rainfall; the month must be complete (every day published)
  3. Merge into the history tables the dashboard is built from:
       - rain table  -> SPI-1/3/6/12 recomputed with the same gamma/Thom method as
         latur_chirps_spi.py (self-checked against the stored SPI before writing)
       - panel row   -> VCI, VHI, PCI, then CDI against the *frozen* history
         (config/composite.yaml), so past months are never silently rewritten
  4. Rebuild village_with_baseline.csv, village_timeseries.json, baselines, district
     series and the latest-period GeoJSON properties
  5. Write latest_status.json from what actually happened. A source that produced
     nothing keeps its previous date; the run never reports success it did not earn.

Exit code is non-zero when nothing new was ingested for a month that should exist or any
stage failed, so GitHub Actions turns red instead of committing stale data as "operational".

  python scripts/realtime_update.py                    # months that are due
  python scripts/realtime_update.py --period 2026-10   # force one month
  python scripts/realtime_update.py --fixture f.json   # offline: skip GEE, read values from f.json
      f.json = {"2026-11": {"s2": {"1": {"ndvi": .31, "evi": .4, "scenes": 6}, ...},
                            "rain": {"1": 42.1, ...}}}
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import manifest  # noqa: E402
from common.paths import PANEL_THERMAL, PANEL_V1, PANEL_V1_COPY, active_panel, is_thermal  # noqa: E402
from common.thermal import add_thermal_indices, coverage, load_thermal, save_thermal  # noqa: E402
from common.zonal import load_zonal, save_zonal, upsert_period, write_latest_json  # noqa: E402
from common.village_cdi import _classify, _load_cfg, score_new_period  # noqa: E402

ROOT = HERE.parent
PUB = ROOT / "frontend" / "public" / "data"
DASH = ROOT / "outputs" / "Dashboard"
PROC = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
VILLAGES_GEOJSON = PUB / "latur_villages_latest.geojson"

PANEL_PATHS = [
    ROOT / "output" / "indices" / "zonal" / "village" / "village_monthly_indices.csv",
    ROOT / "data" / "processed" / "csv" / "village_Latur_monthly_indices.csv",
]
RAIN_WIDE = ROOT / "output" / "spi" / "extra" / "csv" / "village_monthly_rainfall_wide.csv"
SPI_DIR = ROOT / "output" / "spi" / "csv"
SCALES = (1, 3, 6, 12)

CHUNK = int(os.environ.get("GEE_CHUNK", "100"))        # villages per Earth Engine request
S2_SCALE = int(os.environ.get("GEE_S2_SCALE", "30"))   # metres; raise (e.g. 60) if requests are too slow
MIN_S2_COVERAGE = 0.5      # share of villages that must have an NDVI for the month to count
MAX_SPI_DRIFT_MAE = 0.05   # recomputed vs stored SPI on history must agree this closely


def log(msg: str) -> None:
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def next_period(p: str) -> str:
    y, m = map(int, p.split("-"))
    return f"{y + (m // 12):04d}-{(m % 12) + 1:02d}"


def prev_period(p: str) -> str:
    y, m = map(int, p.split("-"))
    return f"{y - (1 if m == 1 else 0):04d}-{(m - 2) % 12 + 1:02d}"


def months_between(a: str, b: str) -> list[str]:
    out, p = [], a
    while p <= b:
        out.append(p)
        p = next_period(p)
    return out


# ---------------------------------------------------------------------------
# SPI (same maths as scripts/latur_chirps_spi.py: Thom MLE gamma, Stagge zero centre)
# ---------------------------------------------------------------------------
def _gamma_params(x: np.ndarray):
    mean = x.mean()
    a_ = np.log(mean) - np.mean(np.log(x))
    if a_ <= 0:
        return np.nan, np.nan
    alpha = (1.0 + np.sqrt(1.0 + 4.0 * a_ / 3.0)) / (4.0 * a_)
    return alpha, mean / alpha


def _spi_one_series(x_all: np.ndarray, min_nonzero: int = 3) -> np.ndarray:
    from scipy import stats
    out = np.full(x_all.shape, np.nan)
    good = np.isfinite(x_all)
    calib = x_all[good]
    n = calib.size
    if n == 0:
        return out
    nz = calib[calib > 0]
    if nz.size < min_nonzero:
        return out
    q = (n - nz.size) / n
    alpha, beta = _gamma_params(nz)
    if not np.isfinite(alpha):
        return out
    x = x_all[good]
    h = q + (1.0 - q) * stats.gamma.cdf(x, a=alpha, scale=beta)
    h = np.where(x <= 0, q / 2.0, h)
    out[good] = stats.norm.ppf(np.clip(h, 0.0001, 0.9999))
    return out


def compute_spi(rain: np.ndarray, periods: list[str], k: int) -> np.ndarray:
    """rain: villages x months (contiguous). Returns SPI-k, same shape."""
    n_v, n_t = rain.shape
    acc = np.full_like(rain, np.nan, dtype=float)
    for t in range(k - 1, n_t):
        w = rain[:, t - k + 1:t + 1]
        ok = np.isfinite(w).all(axis=1)
        s = np.nansum(w, axis=1)
        s[~ok] = np.nan
        acc[:, t] = s
    months = np.array([int(p[5:7]) for p in periods])
    out = np.full_like(acc, np.nan)
    for m in range(1, 13):
        idx = np.where(months == m)[0]
        if idx.size == 0:
            continue
        for v in range(n_v):
            out[v, idx] = _spi_one_series(acc[v, idx])
    return out


def _periods_of(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if len(c) == 7 and c[4] == "-"]


# ---------------------------------------------------------------------------
# GEE fetchers (thin; everything after them is offline-testable)
# ---------------------------------------------------------------------------
def fetch_s2(ee, feats, period: str, cloud_pct: int = 40) -> dict:
    from common.gee import chunks, run_batches
    start = ee.Date(f"{period}-01")
    end = start.advance(1, "month")
    aoi = ee.FeatureCollection(feats).geometry().bounds()
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
           .filterBounds(aoi).filterDate(start, end)
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct)))
    scenes = int(col.size().getInfo())
    if scenes == 0:
        return {"scenes": 0, "values": {}}

    def prep(img):
        scl = img.select("SCL")
        bad = scl.eq(0).Or(scl.eq(1)).Or(scl.eq(3)).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).Or(scl.eq(11))
        r = img.updateMask(bad.Not()).divide(10000)
        ndvi = r.normalizedDifference(["B8", "B4"]).rename("NDVI")
        evi = r.expression("2.5*(N-R)/(N+6*R-7.5*B+1)",
                           {"N": r.select("B8"), "R": r.select("B4"), "B": r.select("B2")}).rename("EVI")
        return ndvi.addBands(evi)

    comp = col.map(prep).median()
    def one(part):
        fc = comp.reduceRegions(ee.FeatureCollection(part), ee.Reducer.mean(), scale=S2_SCALE, tileScale=8)
        # numbers only: without this every batch also downloads each village's polygon outline
        feats_out = fc.select(["id", "NDVI", "EVI"], None, False).getInfo()["features"]
        return {str(f["properties"]["id"]): {"ndvi": f["properties"].get("NDVI"), "evi": f["properties"].get("EVI")}
                for f in feats_out}

    values = {}
    for r in run_batches(list(chunks(feats, CHUNK)), one, f"sentinel2 {period}", log=log):
        values.update(r)
    return {"scenes": scenes, "values": values}


def fetch_chirps(ee, feats, period: str) -> dict | None:
    """Monthly rainfall (mm) per village, or None when the month is not fully published."""
    from common.gee import chunks, run_batches
    y, m = map(int, period.split("-"))
    expected = calendar.monthrange(y, m)[1]
    start = ee.Date(f"{period}-01")
    col = (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
           .filterDate(start, start.advance(1, "month")).select("precipitation"))
    have = int(col.size().getInfo())
    if have < expected:
        log(f"  CHIRPS {period}: {have}/{expected} daily images published - not complete yet")
        return None
    total = col.sum().rename("rain")
    def one(part):
        fc = total.reduceRegions(ee.FeatureCollection(part), ee.Reducer.mean(), scale=5566, tileScale=4)
        return {str(f["properties"]["id"]): f["properties"].get("mean", f["properties"].get("rain"))
                for f in fc.select(["id", "mean"], None, False).getInfo()["features"]}

    values = {}
    for r in run_batches(list(chunks(feats, CHUNK)), one, f"chirps {period}", log=log):
        values.update(r)
    return values


# ---------------------------------------------------------------------------
# History tables
# ---------------------------------------------------------------------------
def load_rain_wide() -> pd.DataFrame:
    return pd.read_csv(RAIN_WIDE, encoding="utf-8-sig")


def spi_self_check(rain_wide: pd.DataFrame) -> dict:
    """Recompute SPI on the stored history and compare with the stored SPI files."""
    periods = _periods_of(rain_wide)
    R = rain_wide[periods].to_numpy(float)
    res = {}
    for k in SCALES:
        ref = pd.read_csv(SPI_DIR / f"SPI{k}_village_monthly.csv")[periods].to_numpy(float)
        mine = compute_spi(R, periods, k)
        ok = np.isfinite(mine) & np.isfinite(ref)
        res[k] = {"mae": float(np.abs(mine[ok] - ref[ok]).mean()), "n": int(ok.sum())}
    return res


def rain_months(rain_wide: pd.DataFrame) -> list[str]:
    """Months that actually hold rainfall. Gap months (deliberately left empty) are columns of NaN."""
    return [p for p in _periods_of(rain_wide) if rain_wide[p].notna().any()]


def append_rain(rain_wide: pd.DataFrame, period: str, values: dict, allow_gap: bool = False) -> pd.DataFrame:
    """Add one month. A gap before it is an error unless `allow_gap` (an explicit --since): the skipped months
    are then stored as empty columns, never filled, so every SPI window that touches them is empty too."""
    periods = _periods_of(rain_wide)
    if period in periods and period in rain_months(rain_wide):
        raise ValueError(f"{period} already in rain table")
    out = rain_wide.copy()
    if period in periods:                       # an empty gap column that now has data
        out = out.drop(columns=[period])
        periods = [p for p in periods if p != period]
    if periods and next_period(periods[-1]) != period:
        if not allow_gap:
            raise ValueError(f"rain table ends at {periods[-1]}; cannot append {period} without the months in between")
        for gap in months_between(next_period(periods[-1]), prev_period(period)):
            out[gap] = np.nan
    out[period] =[float(values[str(int(v) + 1)]) if values.get(str(int(v) + 1)) is not None else np.nan
                   for v in out["vid"]]
    return out


def write_spi_tables(rain_wide: pd.DataFrame) -> dict[int, pd.DataFrame]:
    periods = _periods_of(rain_wide)
    R = rain_wide[periods].to_numpy(float)
    out = {}
    for k in SCALES:
        path = SPI_DIR / f"SPI{k}_village_monthly.csv"
        old = pd.read_csv(path)
        meta = old[[c for c in old.columns if c not in _periods_of(old)]]
        spi = pd.DataFrame(np.round(compute_spi(R, periods, k), 3), columns=periods)
        full = pd.concat([meta.reset_index(drop=True), spi], axis=1)
        full.to_csv(path, index=False)
        out[k] = full
    rain_wide.to_csv(RAIN_WIDE, index=False, encoding="utf-8-sig")
    return out


def vci_for_new(panel_hist: pd.DataFrame, new_ndvi: pd.Series, month: int) -> pd.Series:
    """VCI = position of NDVI inside the village's own 5th-95th percentile envelope for
    this calendar month (village-level approximation of the pixel-level batch method)."""
    h = panel_hist[panel_hist["month"] == month]
    g = h.groupby("village_idx")["NDVI"]
    lo, hi = g.quantile(0.05), g.quantile(0.95)
    rng = (hi - lo).where((hi - lo) > 1e-6)
    return (100.0 * (new_ndvi - lo.reindex(new_ndvi.index)) / rng.reindex(new_ndvi.index)).clip(0, 100)


def rescore_period(panel: pd.DataFrame, period: str, rain_wide: pd.DataFrame,
                   spi: dict[int, pd.DataFrame], cfg: dict, thermal: pd.DataFrame | None = None) -> pd.DataFrame:
    """A month already in the panel (Sentinel-2 arrived first) just received its CHIRPS rainfall:
    attach rain + SPI and re-score that month only."""
    from common.village_cdi import DERIVED_COLUMNS
    cur = panel[panel["date"] == period].copy()
    rest = panel[panel["date"] != period]
    rain_by = {int(v) + 1: x for v, x in zip(rain_wide["vid"], rain_wide[period])}
    cur["Rain_mm"] = cur["village_idx"].map(rain_by)
    for k in SCALES:
        t = spi[k]
        cur[f"SPI{k}"] = cur["village_idx"].map(dict(zip(t["vid"].astype(int) + 1, t[period])))
    cur = cur.drop(columns=DERIVED_COLUMNS)
    if thermal is not None:
        cur = add_thermal_indices(cur, thermal, cfg["thermal"])
    scored = score_new_period(rest, cur, cfg)
    return pd.concat([rest, scored], ignore_index=True).sort_values(["village_idx", "date"], kind="stable")


def build_panel_rows(panel: pd.DataFrame, period: str, s2: dict | None, rain: dict | None,
                     spi: dict[int, pd.DataFrame], cfg: dict,
                     thermal: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    y, m = map(int, period.split("-"))
    meta = (panel.drop_duplicates("village_idx")[["village_idx", "village", "tehsil", "name"]]
            .sort_values("village_idx").reset_index(drop=True))
    idx = meta["village_idx"]
    new = meta.copy()
    new["year"], new["month"], new["date"] = y, m, period
    qc = {"vci_method": "village-level p5-p95 envelope of village NDVI (approximation of pixel-level batch VCI)"}

    if s2 and s2.get("values"):
        ndvi = pd.Series([s2["values"].get(str(i), {}).get("ndvi") for i in idx], index=idx, dtype=float)
        new["NDVI"] = ndvi.to_numpy()
        # Historic EVI is saturated (see docs); a fresh, correctly scaled EVI against that
        # reference would score as extreme drought, so it is withheld from the composite.
        new["EVI"] = np.nan
        qc["evi"] = "withheld: historical EVI reference is saturated at 1.0"
        hist = panel.assign(month=panel["month"])
        vci = vci_for_new(hist, ndvi, m)
        new["VCI"] = vci.to_numpy()
        # Without a thermal band VHI == VCI (as in history). With one, add_thermal_indices below
        # replaces it by 0.5 VCI + 0.5 TCI.
        new["VHI"] = vci.to_numpy()
        qc["s2_scenes"] = s2.get("scenes")
    else:
        for c in ("NDVI", "EVI", "VCI", "VHI"):
            new[c] = np.nan

    if rain is not None:
        new["Rain_mm"] = [rain.get(str(i)) for i in idx]
    else:
        new["Rain_mm"] = np.nan
    for k in SCALES:
        tbl = spi[k]
        col = tbl[period] if period in tbl.columns else pd.Series(np.nan, index=tbl.index)
        by_vid = dict(zip(tbl["vid"].astype(int) + 1, col))
        new[f"SPI{k}"] = [by_vid.get(int(i), np.nan) for i in idx]

    if thermal is not None:
        new = add_thermal_indices(new, thermal, cfg["thermal"])
        qc["thermal"] = "LST (Landsat 8/9) + Sentinel-1 VV; TCI/SMI against each village's own envelope"
    scored = score_new_period(panel, new, cfg)
    return scored, qc


# ---------------------------------------------------------------------------
# Downstream builds
# ---------------------------------------------------------------------------
def rebuild_downstream() -> None:
    import build_baseline_drought as bb
    import build_village_registry as reg
    import build_village_timeseries as tsb

    cfg = _load_cfg()
    df = bb.load_and_fix_village_data()
    df = bb.add_anomaly_and_drought_flag(df, bb.compute_baseline(df), cfg)
    out_csv = ROOT / "data" / "processed" / "csv" / "village_with_baseline.csv"
    df.to_csv(out_csv, index=False)
    log(f"  wrote {out_csv.name} ({len(df)} rows)")

    data = tsb.build()
    with tsb.OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    reg.main()


def write_district_series(panel: pd.DataFrame, cfg: dict) -> None:
    gj = json.loads(VILLAGES_GEOJSON.read_text(encoding="utf-8"))
    area = {int(f["properties"]["id"]): float(f["properties"].get("AREA_SQKM") or 0) for f in gj["features"]}
    p = panel.copy()
    p["area"] = p["village_idx"].map(area)
    rows = []
    for period, g in p.groupby("date"):
        scored = g["composite_drought_score"].notna()
        a = g.loc[scored, "area"].sum()      # share is of the area that HAS a score (cloud gaps excluded)
        total_a = g["area"].sum()
        dry = g.loc[scored & (g["composite_drought_score"] >= 0.35), "area"].sum()
        mean = lambda c: (None if g[c].notna().sum() == 0 else float(g[c].mean()))  # noqa: E731
        s = mean("composite_drought_score")
        rows.append({
            "month": int(period[5:7]), "date": period,
            "SPI1": mean("SPI1"), "SPI3": mean("SPI3"), "SPI6": mean("SPI6"), "SPI12": mean("SPI12"),
            "Rain_mm": mean("Rain_mm"), "NDVI": mean("NDVI"), "EVI": mean("EVI"),
            "VCI": mean("VCI"), "VHI": mean("VHI"), "PCI": mean("PCI"),
            "TCI": mean("TCI") if "TCI" in g else None, "SMI": mean("SMI") if "SMI" in g else None,
            "LST": mean("LST") if "LST" in g else None,
            "composite_drought_score": s,
            "composite_drought_class": _classify(s, cfg["thresholds"]) if s is not None else "ND",
            "pct_area_dry": round(100.0 * dry / a, 1) if a else None,
            "pct_area_assessed": round(100.0 * a / total_a, 1) if total_a else None,
        })
    rows.sort(key=lambda r: r["date"])
    (PUB / "district_monthly.json").write_text(json.dumps({
        "district": region_from_geometry()["district"], "generated_at": now_iso(), "formula_version": cfg["formula_version"],
        "weights": cfg["weights"], "series": rows}, separators=(",", ":")), encoding="utf-8")


def refresh_latest_geojson(panel: pd.DataFrame, cfg: dict) -> str:
    latest = panel.loc[panel["composite_drought_score"].notna(), "date"].max()
    cur = panel[panel["date"] == latest].set_index("village_idx")
    gj = json.loads(VILLAGES_GEOJSON.read_text(encoding="utf-8"))
    num = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)  # noqa: E731
    for f in gj["features"]:
        p = f["properties"]
        r = cur.loc[int(p["id"])] if int(p["id"]) in cur.index else None
        cdi = num(r["composite_drought_score"]) if r is not None else None
        cls = _classify(cdi, cfg["thresholds"]) if cdi is not None else "ND"
        p.update({"date": latest, "period": latest, "CDI": cdi, "CDI_class": cls, "class": cls,
                  "composite_formula_version": cfg["formula_version"]})
        for k, c in (("NDVI", "NDVI"), ("EVI", "EVI"), ("VCI", "VCI"), ("VHI", "VHI"), ("PCI", "PCI"),
                     ("SPI1", "SPI1"), ("SPI3", "SPI3"), ("SPI6", "SPI6"), ("SPI12", "SPI12"),
                     ("Rain_mm", "Rain_mm"), ("TCI", "TCI"), ("SMI", "SMI"), ("LST", "LST")):
            p[k] = num(r[c]) if r is not None and c in r.index else None
    VILLAGES_GEOJSON.write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
    return latest


# ---------------------------------------------------------------------------
# Manifests + status
# ---------------------------------------------------------------------------
def backfill_chirps_manifest(rain_wide: pd.DataFrame) -> None:
    done = manifest.processed_period_ids(PROC, "chirps")
    for p in rain_months(rain_wide):
        if p not in done:
            manifest.record(PROC, "chirps", p, observation_date=f"{p}-28", status="success",
                            outputs=["output/spi/extra/csv/village_monthly_rainfall_wide.csv"],
                            qc={"note": "backfilled from the archived CHIRPS rain table"})


def region_from_geometry() -> dict:
    """District name and centroid taken from the village polygons themselves."""
    gj = json.loads(VILLAGES_GEOJSON.read_text(encoding="utf-8"))
    xs, ys, names = [], [], set()
    for f in gj["features"]:
        names.add(str(f["properties"].get("DISTRICT", "")).strip())
        ring = f["geometry"]["coordinates"]
        while isinstance(ring[0][0], list):
            ring = ring[0]
        xs += [c[0] for c in ring]
        ys += [c[1] for c in ring]
    return {"district": ", ".join(sorted(n for n in names if n)),
            "centroid_lat": round((min(ys) + max(ys)) / 2, 4), "centroid_lon": round((min(xs) + max(xs)) / 2, 4)}


def _thermal_status(cfg: dict) -> dict:
    """LST / soil-moisture state, reported whichever formula is active."""
    from common.thermal import indices_ready, last_month_with
    tc = cfg.get("thermal") or _load_cfg("config/composite_thermal.yaml")["thermal"]
    th = load_thermal()
    return {
        "in_active_formula": is_thermal(cfg),
        **coverage(th),
        "last_lst": last_month_with(th, "LST"), "last_vv": last_month_with(th, "VV"),
        "tci_smi_ready": indices_ready(th, tc["min_years"]),
        "lst_source": ", ".join(tc["lst_collections"]),
        "soil_moisture_source": tc["vv_collection"] + " (VV backscatter)",
    }


def write_status(run: dict, cfg: dict) -> dict:
    s2 = manifest.latest_period(PROC, "sentinel") or {}
    ch = manifest.latest_period(PROC, "chirps") or {}

    def lag(pid):
        if not pid:
            return None
        today = date.today()
        y, m = map(int, pid.split("-"))
        return (today.year - y) * 12 + (today.month - m)

    worst = max([x for x in (lag(s2.get("period_id")), lag(ch.get("period_id"))) if x is not None] or [99])
    if not run["ok"]:
        state = "degraded"
    else:
        state = "operational" if worst <= 1 else "degraded"
    status = {
        "generated_at": now_iso(),
        "monitoring_status": state,
        "sentinel2": {"latest_observation_date": s2.get("observation_date"),
                      "latest_period_id": s2.get("period_id"),
                      "cloud_percentage": s2.get("cloud_pct"),
                      "last_successful_update": s2.get("processed_at"),
                      "status": s2.get("status")},
        "chirps": {"latest_observation_date": ch.get("observation_date"),
                   "latest_period_id": ch.get("period_id"),
                   "last_successful_update": ch.get("processed_at"),
                   "status": ch.get("status"), "qc": ch.get("qc")},
        "composite": {"formula_version": cfg["formula_version"], "weights": cfg["weights"],
                      "min_inputs": cfg["min_inputs"],
                      "spi_reference": "2016-2026 record (gamma fit per village and calendar month)"},
        "thermal": _thermal_status(cfg),
        "region": region_from_geometry(),
        "synthetic_input": bool(os.environ.get("ALLOW_SYNTHETIC_FIXTURE") == "1"),
        "pipeline_run": run,
    }
    for d in (DASH, PUB):
        d.mkdir(parents=True, exist_ok=True)
        (d / "latest_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


# ---------------------------------------------------------------------------
def due_periods(today: date, since: str | None = None) -> list[str]:
    """Months to try: everything after the last successful Sentinel/CHIRPS period up to this month.

    `since` (YYYY-MM) is a floor: months before it are not ingested and are left empty ("no data"), so the
    pipeline can run forward from a chosen month instead of back-filling a gap."""
    s2 = (manifest.latest_period(PROC, "sentinel") or {}).get("period_id")
    ch = (manifest.latest_period(PROC, "chirps") or {}).get("period_id")
    start = next_period(min(x for x in (s2, ch) if x)) if (s2 or ch) else f"{today.year}-01"
    if since and since > start:
        start = since
    return months_between(start, f"{today.year}-{today.month:02d}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", action="append", help="YYYY-MM (repeatable). Default: months that are due.")
    ap.add_argument("--fixture", help="JSON with per-period s2/rain values; skips Earth Engine.")
    ap.add_argument("--skip-self-check", action="store_true")
    ap.add_argument("--since", default=os.environ.get("PIPELINE_SINCE") or None,
                    help="YYYY-MM floor (env PIPELINE_SINCE): never ingest months before this; they stay empty.")
    args = ap.parse_args()
    if args.since and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.since):
        print(f"--since must be YYYY-MM, got {args.since!r}", file=sys.stderr)
        return 3

    # Fixtures are synthetic. They exist only to test the plumbing, and must never be able to
    # reach the repository's real data by accident.
    if args.fixture and os.environ.get("ALLOW_SYNTHETIC_FIXTURE") != "1":
        print("--fixture feeds invented numbers into the pipeline. Refusing: run it on a scratch copy of the "
              "repository with ALLOW_SYNTHETIC_FIXTURE=1.", file=sys.stderr)
        return 3

    cfg = _load_cfg()          # config/composite.yaml, or $COMPOSITE_CONFIG
    run = {"started_at": now_iso(), "ok": True, "steps": [], "ingested": []}

    def step(name, status, detail=""):
        run["steps"].append({"name": name, "status": status, "detail": detail})
        log(f"[{status}] {name} {detail}")

    def guard(name, fn):
        """Run one source fetch. On error: record it, fail the run, and let the other sources carry on."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            run["ok"] = False
            step(name, "failed", f"{type(exc).__name__}: {str(exc)[:300]}")
            return None

    # Source parameters (collections, scale factors, lags) live in config; they do not depend on which
    # composite formula is active.
    TCFG = cfg.get("thermal") or _load_cfg("config/composite_thermal.yaml")["thermal"]

    try:
        rain_wide = load_rain_wide()
        backfill_chirps_manifest(rain_wide)
        thermal_mode = is_thermal(cfg)
        panel = pd.read_csv(active_panel(cfg))
        panel["date"] = panel["date"].astype(str)
        # LST / Sentinel-1 / NDVI / EVI are always downloaded and kept, whichever formula is active; the
        # formula only decides whether they enter the composite.
        thermal = load_thermal()
        zonal = load_zonal()
        step("formula", "ok", f"{cfg['formula_version']} ({'with LST + soil moisture' if thermal_mode else 'no thermal inputs'})")

        if not args.skip_self_check:
            chk = spi_self_check(rain_wide)
            bad = {k: v for k, v in chk.items() if v["mae"] > MAX_SPI_DRIFT_MAE}
            if bad:
                step("spi-self-check", "failed", f"recomputed SPI disagrees with stored SPI: {bad}")
                run["ok"] = False
                write_status({**run, "finished_at": now_iso()}, cfg)
                return 2
            step("spi-self-check", "ok", ", ".join(f"SPI{k} mae={v['mae']:.4f}" for k, v in chk.items()))

        periods = args.period or due_periods(date.today(), args.since)
        step("targets", "ok", f"{periods}" + (f" (running forward from {args.since}; earlier months stay empty)"
                                               if args.since else ""))
        fixture = json.loads(Path(args.fixture).read_text()) if args.fixture else None
        ee = feats = None
        if not fixture:
            from common.gee import init_ee, village_features
            ee = init_ee()
            feats = village_features(ee, VILLAGES_GEOJSON)
            step("earth-engine", "ok", f"{len(feats)} village polygons")

        spi = None
        changed = False
        for period in periods:
            have_rain = period in rain_months(rain_wide)
            have_s2 = period in set(panel["date"])
            if have_rain and have_s2 and not args.period:
                continue

            s2 = rain = None
            rain_new = False
            if fixture:
                fx = fixture.get(period, {})
                s2 = {"scenes": fx.get("s2_scenes", 1), "values": fx.get("s2", {})} if fx.get("s2") else None
                rain = fx.get("rain")
            else:
                # Each source is independent: one failing must not stop the others, but it must fail the run.
                if not have_s2:
                    got = guard(f"sentinel2 {period}", lambda: fetch_s2(ee, feats, period))
                    if got is not None:
                        cov = sum(1 for v in got["values"].values() if v.get("ndvi") is not None) / max(1, len(feats))
                        if got["scenes"] and cov >= MIN_S2_COVERAGE:
                            s2 = got
                        else:
                            step(f"sentinel2 {period}", "skipped", f"scenes={got['scenes']} coverage={cov:.0%}")
                if not have_rain:
                    rain = guard(f"chirps {period}", lambda: fetch_chirps(ee, feats, period))
                    if rain is None and not any(s["name"] == f"chirps {period}" and s["status"] == "failed"
                                                for s in run["steps"]):
                        step(f"chirps {period}", "skipped", "month not fully published")

            if s2 is not None:                      # keep raw NDVI / EVI exactly as returned (EVI included)
                zonal = upsert_period(zonal, period, s2=s2)
                save_zonal(zonal)

            th_new = False
            if period not in set(thermal["date"]):
                got_t = None
                if fixture:
                    ft = fixture.get(period, {}).get("thermal")
                    got_t = {"values": ft, "lst_images": 3, "vv_images": 6} if ft else None
                else:
                    from common.gee import fetch_lst_sm
                    got_t = guard(f"thermal {period}", lambda: fetch_lst_sm(ee, feats, period, TCFG))
                if got_t:
                    from backfill_thermal import append_month
                    thermal = append_month(thermal, period, got_t)
                    save_thermal(thermal)
                    zonal = upsert_period(zonal, period, thermal=got_t)
                    save_zonal(zonal)
                    th_new = changed = True
                    step(f"thermal {period}", "ok", f"LST (Landsat) + VV (Sentinel-1) for {len(got_t['values'])} villages")
                elif not any(s["name"] == f"thermal {period}" and s["status"] == "failed" for s in run["steps"]):
                    step(f"thermal {period}", "skipped", "LST/soil moisture not fully published")

            if rain is not None and not have_rain:
                try:
                    rain_wide = append_rain(rain_wide, period, rain, allow_gap=bool(args.since))
                except ValueError as e:
                    step(f"chirps {period}", "failed", str(e))
                    rain = None
                else:
                    manifest.record(PROC, "chirps", period, observation_date=f"{period}-28", status="success",
                                    outputs=["output/spi/extra/csv/village_monthly_rainfall_wide.csv"],
                                    qc={"villages": sum(v is not None for v in rain.values())})
                    changed = True
                    rain_new = True
                    step(f"chirps {period}", "ok", "rain appended")
            if rain is not None or have_rain:
                spi = write_spi_tables(rain_wide)
            if (rain_new or (th_new and thermal_mode)) and have_s2 and spi is not None:
                panel = rescore_period(panel, period, rain_wide, spi, cfg, thermal if thermal_mode else None)
                run["ingested"].append(period)
                step(f"rescore {period}", "ok", "existing month re-scored with newly arrived inputs")

            spi_for_rows = spi or {k: pd.read_csv(SPI_DIR / f"SPI{k}_village_monthly.csv") for k in SCALES}
            rain_for_row = rain
            if rain_for_row is None and period in rain_months(rain_wide):
                col = rain_wide[period]
                rain_for_row = {str(int(v) + 1): float(x) for v, x in zip(rain_wide["vid"], col) if pd.notna(x)}
            # Thermal formula: a month with rain + soil moisture but no usable Sentinel-2 composite
            # (monsoon cloud) is still scored, from SPI + PCI + SMI.
            has_th = thermal_mode and period in set(thermal["date"])
            if not have_s2 and (s2 is not None or (has_th and rain_for_row is not None)):
                rows, qc = build_panel_rows(panel, period, s2, rain_for_row, spi_for_rows, cfg,
                                            thermal if thermal_mode else None)
                panel = pd.concat([panel, rows], ignore_index=True)
                if s2 is not None:
                    manifest.record(PROC, "sentinel", period, observation_date=f"{period}-15", status="success",
                                    outputs=[str(active_panel(cfg).relative_to(ROOT))],
                                    qc=qc, notes=f"scenes={s2.get('scenes')}")
                run["ingested"].append(period)
                changed = True
                step(f"{'sentinel2' if s2 is not None else 'rain+soil'} {period}", "ok",
                     f"scenes={(s2 or {}).get('scenes')}, "
                     f"scored={int(rows['composite_drought_score'].notna().sum())}/{len(rows)}")

        if changed:
            for p in ([PANEL_THERMAL] if thermal_mode else PANEL_PATHS):
                panel.to_csv(p, index=False)
            rebuild_downstream()
            write_district_series(panel, cfg)
            latest = refresh_latest_geojson(panel, cfg)
            lj = write_latest_json(zonal, PUB / "zonal_latest.json", region_from_geometry())
            step("rebuild", "ok", f"latest scored period {latest}; zonal_latest.json: "
                 + ", ".join(f"{k} {v}" for k, v in lj["latest"].items()))
        else:
            step("rebuild", "skipped", "no new data")
            if args.period is None and periods:
                # Months that should exist by now produced nothing: say so loudly.
                lagging = [p for p in periods if p < f"{date.today().year}-{date.today().month:02d}"]
                if lagging:
                    run["ok"] = False
                    step("freshness", "failed", f"no data ingested for {lagging}")
    except Exception as exc:  # noqa: BLE001
        run["ok"] = False
        step("pipeline", "failed", f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

    run["finished_at"] = now_iso()
    status = write_status(run, cfg)

    # Publish to Supabase (Storage + Postgres) when configured. A failed publish fails the run:
    # the site must not keep serving old data while the job reports success.
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY") \
            and not args.fixture:
        try:
            import publish_supabase as pubsb
            c = pubsb.client_from_env()
            # SPI is recomputed for the whole record on every ingest, so republish all months
            # whenever anything changed; otherwise only the files and the run log.
            pubsb.publish(c, None if run["ingested"] else [], log=log)
            pubsb.log_run(c, PUB / "latest_status.json")
            step("publish-supabase", "ok", "storage + tables updated")
        except Exception as exc:  # noqa: BLE001
            run["ok"] = False
            step("publish-supabase", "failed", f"{type(exc).__name__}: {exc}")
        run["finished_at"] = now_iso()
        status = write_status(run, cfg)
    log(f"status: {status['monitoring_status']}  (sentinel2 -> {status['sentinel2']['latest_period_id']}, "
        f"chirps -> {status['chirps']['latest_period_id']})")
    return 0 if run["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
