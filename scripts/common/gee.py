# -*- coding: utf-8 -*-
"""
Earth Engine helpers shared by the near-real-time scripts.

Authentication order (first that is set wins):
  1. GEE_SERVICE_ACCOUNT_KEY  - JSON text of a service-account key, or a path to it
  2. GEE_PROJECT              - uses stored user credentials (local dev)
An interactive browser login is only attempted when a TTY is attached; in CI
a missing credential raises immediately instead of hanging the job.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


class GeeAuthError(RuntimeError):
    pass


def init_ee():
    try:
        import ee
    except ImportError as e:  # pragma: no cover
        raise GeeAuthError("earthengine-api is not installed (pip install earthengine-api)") from e

    project = os.environ.get("GEE_PROJECT") or None
    raw = os.environ.get("GEE_SERVICE_ACCOUNT_KEY", "").strip()
    if not raw and not project:
        raise GeeAuthError("Set GEE_PROJECT (and GEE_SERVICE_ACCOUNT_KEY in CI). No Earth Engine project is assumed.")
    try:
        if raw:
            text = raw if raw.startswith("{") else Path(raw).read_text(encoding="utf-8")
            key = json.loads(text)
            creds = ee.ServiceAccountCredentials(key["client_email"], key_data=text)
            ee.Initialize(creds, project=project or key.get("project_id"))
        else:
            ee.Initialize(project=project)
    except Exception as exc:  # noqa: BLE001
        if raw or not sys.stdin.isatty():
            raise GeeAuthError(
                f"Earth Engine initialisation failed ({exc}). Check GEE_SERVICE_ACCOUNT_KEY / "
                "GEE_PROJECT and that the service account is registered for Earth Engine."
            ) from exc
        ee.Authenticate()
        ee.Initialize(project=project)
    return ee


def village_features(ee, geojson_path: Path):
    """[ee.Feature] with only an integer `id` property (geometry kept)."""
    gj = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    feats = []
    for f in gj["features"]:
        feats.append(ee.Feature(ee.Geometry(f["geometry"], proj="EPSG:4326", geodesic=False),
                                {"id": int(f["properties"]["id"])}))
    return feats


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run_batches(parts, fn, label, log=print, workers=None, retries=3, deadline_s=None):
    """Run fn(part) for every batch in parallel, with retries and a hard overall deadline.

    The Earth Engine client retries throttled requests silently, so a slow or throttled run can look
    frozen. This prints every batch as it finishes or fails, retries a failed batch (default 3 times with
    back-off), and raises TimeoutError after `deadline_s` (env GEE_DEADLINE_S, default 1200) instead of
    waiting forever. Worker count: env GEE_WORKERS (default 6). Workers are daemon threads, so a request
    that never returns cannot keep the process alive. Returns the batch results in order.
    """
    import os
    import queue
    import threading
    import time

    workers = int(workers or os.environ.get("GEE_WORKERS", "6"))
    deadline_s = float(deadline_s or os.environ.get("GEE_DEADLINE_S", "1200"))
    todo: "queue.Queue[int]" = queue.Queue()
    for i in range(len(parts)):
        todo.put(i)
    done: "queue.Queue[tuple]" = queue.Queue()

    def worker():
        while True:
            try:
                i = todo.get_nowait()
            except queue.Empty:
                return
            err = None
            for attempt in range(retries):
                t0 = time.time()
                try:
                    r = fn(parts[i])
                    log(f"  {label}: batch {i + 1}/{len(parts)} ok in {time.time() - t0:.0f}s")
                    done.put((i, r, None))
                    break
                except Exception as e:  # noqa: BLE001
                    err = e
                    log(f"  {label}: batch {i + 1} attempt {attempt + 1}/{retries} failed after "
                        f"{time.time() - t0:.0f}s: {type(e).__name__}: {str(e)[:160]}")
                    time.sleep(min(60, 5 * 2 ** attempt))
            else:
                done.put((i, None, err))

    for _ in range(min(workers, len(parts))):
        threading.Thread(target=worker, daemon=True).start()

    out: list = [None] * len(parts)
    t_end = time.time() + deadline_s
    for _ in range(len(parts)):
        try:
            i, r, err = done.get(timeout=max(0.1, t_end - time.time()))
        except queue.Empty:
            raise TimeoutError(f"{label}: not finished after {deadline_s:.0f}s "
                               "(Earth Engine slow or throttled; try GEE_WORKERS, GEE_CHUNK, GEE_S2_SCALE)") from None
        if err is not None:
            raise RuntimeError(f"{label}: batch {i + 1} failed {retries} times: {err}") from err
        out[i] = r
    return out


def fetch_lst_sm(ee, feats, period: str, tcfg: dict) -> dict | None:
    """Village-mean LST (deg C, Landsat 8/9) and Sentinel-1 VV backscatter (dB) for one month.

    Sentinel-2 has no thermal band, so LST comes from Landsat 8 + 9 Collection 2 Level 2 (ST_B10, clear
    pixels only). Soil moisture is represented by Sentinel-1 IW VV backscatter, normalised to a reference
    incidence angle; SMI is derived from it in common/thermal.py.

    Returns None while the month is not over (plus `publish_lag_days`) or either source has too few
    observations, so a partial month is never turned into an index. A village that is cloud-covered in every
    Landsat image gets no LST (empty, not filled).
    Result: {"values": {id: {"lst", "vv"}}, "lst_images", "vv_images"}.
    """
    import calendar
    import datetime as dt
    y, m = map(int, period.split("-"))
    last_day = dt.date(y, m, calendar.monthrange(y, m)[1])
    if dt.date.today() < last_day + dt.timedelta(days=int(tcfg["publish_lag_days"])):
        return None

    start = ee.Date(f"{period}-01")
    end = start.advance(1, "month")
    aoi = ee.FeatureCollection(feats).geometry().bounds()

    # --- Landsat 8/9 LST -------------------------------------------------------------------
    lst_col = None
    for name in tcfg["lst_collections"]:
        c = ee.ImageCollection(name).filterBounds(aoi).filterDate(start, end)
        lst_col = c if lst_col is None else lst_col.merge(c)

    def lst_img(img):
        qa = img.select(tcfg["lst_qa_band"])
        # QA_PIXEL bits: 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow, 5 snow
        bad = qa.bitwiseAnd(0b111111).neq(0)
        k = img.select(tcfg["lst_band"]).multiply(float(tcfg["lst_scale"])).add(float(tcfg["lst_offset"]))
        return k.subtract(273.15).updateMask(bad.Not()).rename("lst")

    n_lst = int(lst_col.size().getInfo())
    n_vv_col = (ee.ImageCollection(tcfg["vv_collection"]).filterBounds(aoi).filterDate(start, end)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .filter(ee.Filter.listContains("transmitterReceiverPolarisation", tcfg["vv_band"])))
    n_vv = int(n_vv_col.size().getInfo())
    if n_lst < int(tcfg["lst_min_images"]) or n_vv < int(tcfg["vv_min_images"]):
        return None

    # --- Sentinel-1 VV, angle-normalised, averaged in linear power then back to dB ---------------
    ref = float(tcfg["vv_reference_angle_deg"])

    def vv_lin(img):
        theta = img.select("angle").multiply(3.141592653589793 / 180.0)
        db = img.select(tcfg["vv_band"])
        valid = db.gt(-30)                                   # drop thermal-noise / border pixels
        # sigma0_ref = sigma0 * cos(theta_ref) / cos(theta)  ->  dB shift = 10*log10(cos(theta_ref)/cos(theta))
        shift = ee.Image.constant(ee.Number(ref).multiply(3.141592653589793 / 180.0).cos()).divide(theta.cos()).log10().multiply(10)
        return ee.Image(10).pow(db.add(shift).divide(10)).updateMask(valid).rename("vv_lin")

    lst = ee.ImageCollection(lst_col.map(lst_img)).mean().rename("lst")
    vv = ee.ImageCollection(n_vv_col.map(vv_lin)).mean()
    vv_db = vv.log10().multiply(10).rename("vv")

    def one(part):
        fc = ee.FeatureCollection(part)
        a = lst.reduceRegions(fc, ee.Reducer.mean(), scale=30, tileScale=8).select(["id", "mean"], None, False).getInfo()["features"]
        b = vv_db.reduceRegions(fc, ee.Reducer.mean(), scale=30, tileScale=8).select(["id", "mean"], None, False).getInfo()["features"]
        return {str(fa["properties"]["id"]): {"lst": fa["properties"].get("mean", fa["properties"].get("lst")),
                                              "vv": fb["properties"].get("mean", fb["properties"].get("vv"))}
                for fa, fb in zip(a, b)}

    values: dict[str, dict] = {}
    for r in run_batches(list(chunks(feats, int(__import__("os").environ.get("GEE_CHUNK", "100")))), one,
                         f"landsat+sentinel1 {period}"):
        values.update(r)
    return {"values": values, "lst_images": n_lst, "vv_images": n_vv}
