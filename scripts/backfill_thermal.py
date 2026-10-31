# -*- coding: utf-8 -*-
"""
One-off (and resumable) backfill of land-surface temperature and soil moisture for every village
and month, from Earth Engine:

  LST  Landsat 8 + 9 Collection 2 L2 surface temperature (30 m), clear pixels -> village-polygon monthly mean, deg C
  VV   Sentinel-1 IW VV backscatter (10 m), incidence-angle normalised        -> village-polygon monthly mean, dB
       (Sentinel-2 has no thermal band; VV is the relative soil-moisture signal that SMI is built from)

Writes output/thermal/village_monthly_lst_sm.csv. Months already present are skipped, the file is
saved after every month, so an interrupted run resumes where it stopped.

Then, offline and deterministic:
    python scripts/rescore_panel.py          # TCI, SMI, VHI = 0.5 VCI + 0.5 TCI, new CDI

  python scripts/backfill_thermal.py                       # 2016-01 .. last complete month
  python scripts/backfill_thermal.py --from 2020-01 --to 2020-12
  python scripts/backfill_thermal.py --fixture f.json      # offline: {"2020-01": {"1": {"lst": 31.2, "vv": -11.4}, ...}}
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common.thermal import THERMAL_CSV, load_thermal, save_thermal  # noqa: E402
from common.village_cdi import _load_cfg  # noqa: E402

ROOT = HERE.parent
VILLAGES = ROOT / "frontend" / "public" / "data" / "latur_villages_latest.geojson"


def months(a: str, b: str) -> list[str]:
    out, (y, m) = [], map(int, a.split("-"))
    while (y, m) <= tuple(map(int, b.split("-"))):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def append_month(t: pd.DataFrame, period: str, got: dict) -> pd.DataFrame:
    rows = [{"village_idx": int(i), "date": period, "LST": v.get("lst"), "VV": v.get("vv"),
             "lst_images": got.get("lst_images"), "vv_images": got.get("vv_images")}
            for i, v in got["values"].items()]
    t = t[t["date"] != period]
    return pd.concat([t, pd.DataFrame(rows)], ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d_from", default="2016-01")
    ap.add_argument("--to", dest="d_to", default=None)
    ap.add_argument("--fixture")
    args = ap.parse_args()
    if args.fixture and __import__("os").environ.get("ALLOW_SYNTHETIC_FIXTURE") != "1":
        print("--fixture feeds invented numbers into the thermal table. Refusing: use a scratch copy of the "
              "repository with ALLOW_SYNTHETIC_FIXTURE=1.", file=sys.stderr)
        return 3
    today = date.today()
    d_to = args.d_to or (f"{today.year}-{today.month - 1:02d}" if today.month > 1 else f"{today.year - 1}-12")

    tcfg = _load_cfg("config/composite_thermal.yaml")["thermal"]
    t = load_thermal()
    todo = [p for p in months(args.d_from, d_to) if p not in set(t["date"])]
    print(f"{len(todo)} months to fetch ({args.d_from}..{d_to}); {t['date'].nunique()} already stored")

    fixture = json.loads(Path(args.fixture).read_text()) if args.fixture else None
    ee = feats = None
    if not fixture:
        from common.gee import init_ee, village_features
        ee = init_ee()
        feats = village_features(ee, VILLAGES)

    failed = []
    for p in todo:
        if fixture:
            got = {"values": fixture.get(p, {}), "lst_images": 3, "vv_images": 6} if p in fixture else None
        else:
            from common.gee import fetch_lst_sm
            got = fetch_lst_sm(ee, feats, p, tcfg)
        if not got:
            print(f"  {p}: not fully published / no data - skipped")
            failed.append(p)
            continue
        t = append_month(t, p, got)
        save_thermal(t)
        ok = sum(1 for v in got["values"].values() if v.get("lst") is not None)
        print(f"  {p}: {ok}/{len(got['values'])} villages with LST")
    print(f"done; thermal table has {t['date'].nunique()} months -> {THERMAL_CSV}")
    return 1 if failed and not fixture and len(failed) == len(todo) else 0


if __name__ == "__main__":
    sys.exit(main())
