# -*- coding: utf-8 -*-
"""
Re-score the whole village panel under the active composite config (config/composite.yaml).

Run this after changing weights, normalisation, min_inputs or the formula version: the robust
standardisation is against the full record, so every month has to be re-scored together.
Inputs (NDVI, VCI, NSMI, SPI, rain) are never touched, only the derived score columns.

  python scripts/analysis/rescore_history.py              # re-score the panel only
  python scripts/analysis/rescore_history.py --rebuild    # ...and regenerate every dashboard output from it

--rebuild runs the same downstream steps as the weekly job (realtime_update.py): village_with_baseline.csv,
village_timeseries.json, baselines, district series, latest GeoJSON, plus the master table and tehsil analytics.
Then publish with `python scripts/realtime/publish_supabase.py --full`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.paths import PANEL_V1, PANEL_V1_COPY, is_thermal  # noqa: E402
from common.village_cdi import DERIVED_COLUMNS, _load_cfg, derive_indices, fuse_cdi  # noqa: E402


def rescore(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    p = panel.drop(columns=[c for c in DERIVED_COLUMNS + ["PCI"] if c in panel.columns])
    p["period"] = p["date"].astype(str)
    out = fuse_cdi(derive_indices(p, cfg), cfg).drop(columns=["period"])
    return out[[c for c in panel.columns if c != "PCI"]]


def rebuild_outputs(panel: pd.DataFrame, cfg: dict) -> None:
    from analysis import build_tehsil_analytics, dashboard_master
    from realtime import realtime_update as ru
    ru.rebuild_downstream()
    ru.write_district_series(panel, cfg)
    ru.refresh_latest_geojson(panel, cfg)
    dashboard_master.build_master()
    dashboard_master.build_data_availability()
    dashboard_master.build_processing_manifest()
    build_tehsil_analytics.build()
    started = ru.now_iso()
    ru.write_status({"started_at": started, "finished_at": ru.now_iso(), "ok": True, "ingested": [], "steps": [
        {"name": "rescore-history", "status": "ok",
         "detail": f"{cfg['formula_version']}: whole record re-scored from stored inputs; no new satellite data fetched"}]}, cfg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="regenerate every dashboard output after re-scoring")
    args = ap.parse_args()
    cfg = _load_cfg()
    if is_thermal(cfg):
        print("The thermal formula is rescored by scripts/analysis/rescore_panel.py", file=sys.stderr)
        return 2
    panel = pd.read_csv(PANEL_V1, keep_default_na=False, na_values=[""], low_memory=False)
    out = rescore(panel, cfg)
    for path in (PANEL_V1, PANEL_V1_COPY):
        out.to_csv(path, index=False)
    scored = int(out["composite_drought_score"].notna().sum())
    print(f"{cfg['formula_version']}: {scored}/{len(out)} village-months scored "
          f"(min_inputs={cfg['min_inputs']}); classes {out['composite_drought_class'].value_counts().to_dict()}")
    if args.rebuild:
        rebuild_outputs(out, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
