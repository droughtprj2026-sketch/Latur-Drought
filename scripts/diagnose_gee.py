# -*- coding: utf-8 -*-
"""
Times each Earth Engine step on a small sample, so a slow run can be explained instead of guessed at.
Uses real Earth Engine, no invented data. Reads the same GEE_* variables as the pipeline.

  python scripts/diagnose_gee.py --period 2026-09 [--villages 10]
"""
import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import realtime_update as ru  # noqa: E402
from common.gee import init_ee, village_features  # noqa: E402
from common.village_cdi import _load_cfg  # noqa: E402


def timed(label, fn):
    t = time.time()
    try:
        out = fn()
        print(f"{label:<44} {time.time() - t:6.1f}s   ok", flush=True)
        return out
    except Exception as e:  # noqa: BLE001
        print(f"{label:<44} {time.time() - t:6.1f}s   FAILED {type(e).__name__}: {str(e)[:160]}", flush=True)
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", required=True)
    ap.add_argument("--villages", type=int, default=10)
    a = ap.parse_args()
    ee = timed("earth engine init", init_ee)
    feats = village_features(ee, ru.VILLAGES_GEOJSON)
    sample = feats[: a.villages]
    print(f"{len(feats)} polygons loaded; timing a sample of {len(sample)}", flush=True)
    timed("chirps  (sample)", lambda: ru.fetch_chirps(ee, sample, a.period))
    timed("sentinel-2 (sample)", lambda: ru.fetch_s2(ee, sample, a.period))
    cfg = _load_cfg("config/composite_thermal.yaml")["thermal"]
    from common.gee import fetch_lst_sm
    timed("landsat LST + sentinel-1 VV (sample)", lambda: fetch_lst_sm(ee, sample, a.period, cfg))
    print("\nMultiply a sample time by (954 / sample size) for a full-district estimate per month.")
