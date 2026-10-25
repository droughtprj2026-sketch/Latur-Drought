# -*- coding: utf-8 -*-
"""Which village panel is current: the original (cdi-v2026.10) or the thermal one."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL_V1 = ROOT / "output" / "indices" / "zonal" / "village" / "village_monthly_indices.csv"
PANEL_V1_COPY = ROOT / "data" / "processed" / "csv" / "village_Latur_monthly_indices.csv"
PANEL_THERMAL = ROOT / "output" / "indices" / "zonal" / "village" / "village_monthly_indices_thermal.csv"


def is_thermal(cfg: dict) -> bool:
    return "thermal" in cfg


def active_panel(cfg: dict) -> Path:
    """Panel matching the active composite config. A thermal config without a rescored panel
    is an error: silently falling back would publish v1 numbers under a v2 label."""
    if is_thermal(cfg):
        if not PANEL_THERMAL.exists():
            raise FileNotFoundError(
                f"{PANEL_THERMAL.name} is missing. Run scripts/backfill_thermal.py then "
                "scripts/rescore_panel.py before selecting config/composite_thermal.yaml.")
        return PANEL_THERMAL
    return PANEL_V1
