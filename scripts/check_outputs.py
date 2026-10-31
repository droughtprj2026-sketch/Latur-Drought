# -*- coding: utf-8 -*-
"""
Sanity checks on pipeline outputs. Run after every update; exits non-zero when something is implausible, so a
scheduled run cannot quietly publish broken numbers. The limits are physical bounds, not tuning values.

  python scripts/check_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common.paths import active_panel  # noqa: E402
from common.thermal import THERMAL_CSV, load_thermal  # noqa: E402
from common.zonal import load_zonal  # noqa: E402
from common.village_cdi import _load_cfg  # noqa: E402

ROOT = HERE.parent
PUB = ROOT / "frontend" / "public" / "data"

# Physical plausibility of village-mean values
BOUNDS = {"LST": (0.0, 60.0), "VV": (-30.0, 5.0), "NDVI": (-1.0, 1.0), "Rain_mm": (0.0, 2000.0),
          "SPI1": (-4.0, 4.0), "SPI3": (-4.0, 4.0), "TCI": (0.0, 100.0), "SMI": (0.0, 100.0),
          "VHI": (0.0, 100.0), "VCI": (0.0, 100.0), "composite_drought_score": (0.0, 1.0)}


def check_bounds(df: pd.DataFrame, cols=None) -> list[str]:
    """Names of columns holding values outside their physical range."""
    bad = []
    for c, (lo, hi) in BOUNDS.items():
        if cols and c not in cols:
            continue
        if c in df.columns:
            v = df[c].dropna()
            if len(v) and ((v < lo) | (v > hi)).any():
                bad.append(f"{c}: {int(((v < lo) | (v > hi)).sum())} values outside [{lo}, {hi}] "
                           f"(min {v.min():.3g}, max {v.max():.3g})")
    return bad


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []
    cfg = _load_cfg()

    panel = pd.read_csv(active_panel(cfg))
    panel["date"] = panel["date"].astype(str)
    latest_scored = panel.loc[panel["composite_drought_score"].notna(), "date"].max()
    cur = panel[panel["date"] == latest_scored]
    notes.append(f"formula {cfg['formula_version']}; latest scored month {latest_scored}; "
                 f"{int(cur['composite_drought_score'].notna().sum())}/{len(cur)} villages scored")
    problems += check_bounds(panel)
    if cur["composite_drought_score"].notna().mean() < 0.5:
        problems.append(f"fewer than half of the villages have a CDI in {latest_scored}")

    th = load_thermal()
    if th.empty:
        (problems if "thermal" in cfg else notes).append(
            f"{THERMAL_CSV.name} is empty (run scripts/backfill_thermal.py)")
    else:
        notes.append(f"thermal table: {th['date'].nunique()} months, {th['date'].min()}..{th['date'].max()}")
        problems += check_bounds(th)
        last = th[th["date"] == th["date"].max()]
        lst_share, vv_share = last["LST"].notna().mean(), last["VV"].notna().mean()
        notes.append(f"LST coverage in {th['date'].max()}: {100 * lst_share:.0f}% of villages "
                     "(cloud-limited: low values are normal in the monsoon)")
        notes.append(f"VV coverage in {th['date'].max()}: {100 * vv_share:.0f}% of villages")
        if vv_share < 0.5:      # radar sees through cloud, so low coverage is a real fault
            problems.append(f"Sentinel-1 VV present for only {100 * vv_share:.0f}% of villages in {th['date'].max()}")

    zon = load_zonal()
    if not zon.empty:
        notes.append(f"zonal archive: {zon['date'].nunique()} months, latest {zon['date'].max()}")
        problems += check_bounds(zon.rename(columns={"NDVI": "NDVI"}), cols=["NDVI", "LST", "VV"])
        if zon["EVI"].dropna().abs().max() > 1.5:
            problems.append("EVI in the zonal archive is outside the physical range (|EVI| > 1.5): check band scaling")

    ts = json.loads((PUB / "village_timeseries.json").read_text(encoding="utf-8"))
    gj = json.loads((PUB / "latur_villages_latest.geojson").read_text(encoding="utf-8"))
    ids = {str(f["properties"]["id"]) for f in gj["features"]}
    if ids != set(ts):
        problems.append(f"published history covers {len(set(ts) & ids)}/{len(ids)} polygons")

    st = json.loads((PUB / "latest_status.json").read_text(encoding="utf-8"))
    notes.append(f"status: {st.get('monitoring_status')}; sentinel2 {st['sentinel2'].get('latest_period_id')}; "
                 f"chirps {st['chirps'].get('latest_period_id')}")
    if st.get("synthetic_input"):
        problems.append("latest_status.json is marked synthetic_input")
    if not (st.get("pipeline_run") or {}).get("ok", False):
        problems.append("last pipeline run did not finish ok")

    for n in notes:
        print("  " + n)
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  - " + p)
        return 1
    print("outputs look plausible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
