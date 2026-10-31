# -*- coding: utf-8 -*-
"""
Rebuild the village panel under the thermal composite (config/composite_thermal.yaml):

  1. start from the Sentinel-2 panel (cdi-v2026.10 inputs, left untouched on disk)
  2. add a row for every month that has CHIRPS rainfall but no Sentinel-2 composite
     (June-September, mostly), so those months can be scored from SPI + PCI + SMI
  3. attach LST / soil moisture and derive TCI, SMI, and VHI = 0.5 VCI + 0.5 TCI
  4. PCI over the full rain record, then the composite with the thermal weights

Writes output/indices/zonal/village/village_monthly_indices_thermal.csv. Deterministic and offline:
needs output/thermal/village_monthly_lst_sm.csv from scripts/backfill_thermal.py.

  python scripts/rescore_panel.py [--config config/composite_thermal.yaml]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common.paths import PANEL_THERMAL, PANEL_V1, ROOT  # noqa: E402
from common.thermal import add_thermal_indices, coverage, load_thermal  # noqa: E402
from common.village_cdi import _load_cfg, derive_indices, fuse_cdi  # noqa: E402

RAIN_WIDE = ROOT / "output" / "spi" / "extra" / "csv" / "village_monthly_rainfall_wide.csv"
SPI_DIR = ROOT / "output" / "spi" / "csv"
SCALES = (1, 3, 6, 12)


def _periods(df):
    return [c for c in df.columns if len(c) == 7 and c[4] == "-"]


def densify(panel: pd.DataFrame, rain_wide: pd.DataFrame, spi: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Add rows for rain months that have no Sentinel-2 composite. Existing rows are not modified."""
    have = set(panel["date"])
    meta = (panel.drop_duplicates("village_idx")[["village_idx", "village", "tehsil", "name"]]
            .sort_values("village_idx").reset_index(drop=True))
    add = []
    for p in _periods(rain_wide):
        if p in have:
            continue
        r = meta.copy()
        r["year"], r["month"], r["date"] = int(p[:4]), int(p[5:]), p
        by = dict(zip(rain_wide["vid"].astype(int) + 1, rain_wide[p]))
        r["Rain_mm"] = r["village_idx"].map(by)
        for k in SCALES:
            t = spi[k]
            r[f"SPI{k}"] = r["village_idx"].map(dict(zip(t["vid"].astype(int) + 1, t[p])))
        for c in ("NDVI", "EVI", "VCI", "VHI"):
            r[c] = np.nan
        add.append(r)
    if not add:
        return panel
    out = pd.concat([panel, *add], ignore_index=True)
    return out.sort_values(["village_idx", "date"], kind="stable").reset_index(drop=True)


def rescore(panel_v1: pd.DataFrame, rain_wide, spi, thermal, cfg) -> pd.DataFrame:
    p = densify(panel_v1, rain_wide, spi)
    p = p.drop(columns=["PCI", "composite_drought_score", "composite_drought_class",
                        "component_contributions", "SPI_scaled", "formula_version",
                        "data_quality_status"], errors="ignore")
    p = add_thermal_indices(p, thermal, cfg["thermal"])
    p["period"] = p["date"]                      # derive_indices keys on `period`
    p = fuse_cdi(derive_indices(p, cfg), cfg)
    return p.drop(columns=["period"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/composite_thermal.yaml")
    args = ap.parse_args()
    cfg = _load_cfg(args.config)
    thermal = load_thermal()
    cov = coverage(thermal)
    if cov["months"] == 0:
        print("No thermal data: run scripts/backfill_thermal.py first.", file=sys.stderr)
        return 1
    print(f"thermal table: {cov['months']} months ({cov['first']}..{cov['last']})")

    panel = pd.read_csv(PANEL_V1)
    panel["date"] = panel["date"].astype(str)
    rain = pd.read_csv(RAIN_WIDE, encoding="utf-8-sig")
    spi = {k: pd.read_csv(SPI_DIR / f"SPI{k}_village_monthly.csv") for k in SCALES}

    out = rescore(panel, rain, spi, thermal, cfg)
    out.to_csv(PANEL_THERMAL, index=False)
    scored = out["composite_drought_score"].notna()
    print(f"wrote {PANEL_THERMAL.name}: {len(out)} rows, {out['date'].nunique()} months, "
          f"{int(scored.sum())} scored ({100 * scored.mean():.0f}%), formula {cfg['formula_version']}")
    for c in ("TCI", "SMI", "VHI"):
        print(f"  {c}: {100 * out[c].notna().mean():.0f}% of rows have a value")
    return 0


if __name__ == "__main__":
    sys.exit(main())
