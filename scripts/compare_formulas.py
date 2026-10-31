# -*- coding: utf-8 -*-
"""
Compare the default formula (cdi-v2026.10) with the thermal one (cdi-v2026.11-thermal) so the team can review the
effect before switching COMPOSITE_CONFIG. Needs the thermal panel from scripts/rescore_panel.py.

  python scripts/compare_formulas.py [--period YYYY-MM]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common.paths import PANEL_THERMAL, PANEL_V1  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--period")
    a = ap.parse_args()
    if not PANEL_THERMAL.exists():
        sys.exit("thermal panel missing: run scripts/rescore_panel.py first")
    v1, v2 = pd.read_csv(PANEL_V1), pd.read_csv(PANEL_THERMAL)
    v1["date"], v2["date"] = v1["date"].astype(str), v2["date"].astype(str)
    p = a.period or v2.loc[v2["composite_drought_score"].notna(), "date"].max()
    m = v1[v1.date == p].merge(v2[v2.date == p], on="village_idx", suffixes=("_v1", "_v2"))
    order = ["None", "D0", "D1", "D2", "D3", "D4"]
    print(f"period {p}: scored v1 {m.composite_drought_score_v1.notna().sum()}, thermal {m.composite_drought_score_v2.notna().sum()} of {len(m)}")
    for name, col in (("default", "composite_drought_class_v1"), ("thermal", "composite_drought_class_v2")):
        print(f"{name:8}", m[col].fillna("ND").value_counts().reindex(order + ["ND"]).fillna(0).astype(int).to_dict())
    both = m.dropna(subset=["composite_drought_score_v1", "composite_drought_score_v2"])
    if len(both):
        print(f"mean score {both.composite_drought_score_v1.mean():.3f} -> {both.composite_drought_score_v2.mean():.3f}; "
              f"class agreement {(both.composite_drought_class_v1 == both.composite_drought_class_v2).mean():.0%}; "
              f"correlation {both.composite_drought_score_v1.corr(both.composite_drought_score_v2):.2f}")
