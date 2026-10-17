# -*- coding: utf-8 -*-
"""
Drought legend + class helpers.

Two class scales live here:

  1. SPI value scale (per McKee 1993) — used by the raw SPI layers in
     the map and the time series.
  2. Composite CDI scale (0..1 drought intensity) — used by the final
     drought classification on the dashboard. Thresholds are loaded
     from config/composite.yaml.

Both scales use the same D0..D4 colour ramp so the dashboard looks
consistent regardless of which index drives it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

# ---------------------------------------------------------------------
# US-DM / IMD colour ramp — single source of truth for both scales
# ---------------------------------------------------------------------
D_CODES  = ["None", "D0", "D1", "D2", "D3", "D4"]
D_LABELS = [
    "No drought / Normal",
    "D0 — Abnormally dry",
    "D1 — Moderate drought",
    "D2 — Severe drought",
    "D3 — Extreme drought",
    "D4 — Exceptional drought",
]
D_COLORS = [
    "#FFFFFF",  # None
    "#FFFF00",  # D0 yellow
    "#FCD37F",  # D1 light orange
    "#FFAA00",  # D2 dark orange
    "#E60000",  # D3 red
    "#730000",  # D4 maroon
]

# ---------------------------------------------------------------------
# SPI value scale (McKee 1993 — negative is dry)
# ---------------------------------------------------------------------
SPI_BOUNDS = [10.0, -0.5, -0.8, -1.3, -1.6, -2.0, -10.0]  # desc, matches D-codes
# Note the mapping: value >= -0.5 → None, -0.5..-0.8 → D0, ... <= -2.0 → D4.
SPI_LABELS = D_LABELS
SPI_CODES  = D_CODES
SPI_COLORS = D_COLORS

# matplotlib convention wants ascending bounds for a BoundaryNorm.
SPI_CMAP = ListedColormap(list(reversed(SPI_COLORS)))
SPI_NORM = BoundaryNorm(sorted(SPI_BOUNDS), SPI_CMAP.N)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def classify_spi(value: float | None) -> str:
    """Return the drought label for an SPI value."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "No data"
    # SPI_BOUNDS is descending from +10 to -10
    if value >= SPI_BOUNDS[1]:        return D_LABELS[0]
    if value >= SPI_BOUNDS[2]:        return D_LABELS[1]
    if value >= SPI_BOUNDS[3]:        return D_LABELS[2]
    if value >= SPI_BOUNDS[4]:        return D_LABELS[3]
    if value >= SPI_BOUNDS[5]:        return D_LABELS[4]
    return D_LABELS[5]


def code_for_spi(value: float | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "ND"
    if value >= SPI_BOUNDS[1]:        return "None"
    if value >= SPI_BOUNDS[2]:        return "D0"
    if value >= SPI_BOUNDS[3]:        return "D1"
    if value >= SPI_BOUNDS[4]:        return "D2"
    if value >= SPI_BOUNDS[5]:        return "D3"
    return "D4"


# ---------------------------------------------------------------------
# Composite CDI thresholds — loaded from config/composite.yaml
# ---------------------------------------------------------------------
def _load_composite_cfg() -> dict:
    try:
        import yaml
    except ImportError as e:
        raise SystemExit("pip install pyyaml") from e
    with (CONFIG_DIR / "composite.yaml").open() as f:
        return yaml.safe_load(f)


def composite_thresholds() -> list[dict]:
    """Return the ordered list of {max, code, label} from the YAML."""
    return _load_composite_cfg()["thresholds"]


def code_for_cdi(value: float | None) -> str:
    """Composite CDI → D-code using thresholds from config/composite.yaml."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "ND"
    for t in composite_thresholds():
        if value < t["max"]:
            return t["code"]
    return "D4"


def label_for_cdi(value: float | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "No data"
    for t in composite_thresholds():
        if value < t["max"]:
            return f'{t["code"]} — {t["label"]}' if t["code"] != "None" else t["label"]
    return "D4 — Exceptional drought"


# Legacy aliases kept so older scripts still import cleanly.
code_for_value = code_for_spi
