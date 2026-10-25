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

# Matplotlib is optional — only needed for color map / norm objects used
# in visualization. The classification logic itself does not require it.
try:
    from matplotlib.colors import BoundaryNorm, ListedColormap
    _HAS_MATPLOTLIB = True
except ImportError:
    BoundaryNorm = None  # type: ignore
    ListedColormap = None  # type: ignore
    _HAS_MATPLOTLIB = False

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

# ---------------------------------------------------------------------
# US-DM / IMD colour ramp — single source of truth for both scales
# ---------------------------------------------------------------------
D_CODES  = ["None", "D0", "D1", "D2", "D3", "D4"]
D_LABELS = [
    "Not in drought",
    "D0 — Abnormally dry",
    "D1 — Moderate drought",
    "D2 — Severe drought",
    "D3 — Extreme drought",
    "D4 — Exceptional drought",
]
D_COLORS = [
    "#E2DED2",  # None (pale stone: neutral, deliberately not green and not white)
    "#F2E26B",  # D0 straw
    "#F6BC63",  # D1 amber
    "#E9822F",  # D2 orange
    "#C23B22",  # D3 brick red
    "#6E1423",  # D4 oxblood
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
# Only create these if matplotlib is available (needed for visualization,
# not for classification logic).
if _HAS_MATPLOTLIB:
    SPI_CMAP = ListedColormap(list(reversed(SPI_COLORS)))
    SPI_NORM = BoundaryNorm(sorted(SPI_BOUNDS), SPI_CMAP.N)  # type: ignore
else:
    SPI_CMAP = None  # type: ignore
    SPI_NORM = None  # type: ignore

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


# ---------------------------------------------------------------------
# Centralized Drought Classification Lookup Table
# ---------------------------------------------------------------------
# Near-real-time pipelines need to decide drought / non-drought / wet
# instantly from a CDI score without recomputing thresholds each time.
# This table is built once from config/composite.yaml and shared by
# pipeline_gee.py, run_realtime_pipeline_sync.py, and sync_dashboard_data.py.
# Severity bands:
#   score < 0.20  -> no_drought   (None)
#   0.20-0.35     -> drought      (D0 - abnormally dry / mild)
#   0.35-0.50     -> drought      (D1 - moderate)
#   0.50-0.65     -> drought      (D2 - severe)
#   0.65-0.80     -> drought      (D3 - extreme)
#   0.80+         -> drought      (D4 - exceptional)
# Wet conditions are signalled by a strongly positive SPI anomaly
# (SPI >= +1.0) even when CDI is low; that is a separate input.
# ---------------------------------------------------------------------

DROUGHT_SEVERITY_MAP = {
    "None":  "no_drought",
    "D0":    "drought",
    "D1":    "drought",
    "D2":    "drought",
    "D3":    "drought",
    "D4":    "drought",
    "ND":    "no_data",
}


def build_drought_lookup_table() -> list[dict]:
    """
    Build the centralized drought classification lookup table from
    config/composite.yaml thresholds.

    Returns a list of entries, each with:
      min_score, max_score, code, label, severity, color
    where severity is one of: "no_drought", "drought", "no_data".
    """
    cfg = _load_composite_cfg()
    thresholds = cfg["thresholds"]
    weights = cfg["weights"]

    lookup = []
    prev_max = 0.0
    for t in thresholds:
        code = t["code"]
        max_score = t["max"]
        label = t["label"]
        entry = {
            "min_score": round(prev_max, 4),
            "max_score": round(max_score, 4),
            "code": code,
            "label": label,
            "severity": DROUGHT_SEVERITY_MAP.get(code, "no_data"),
            "weights": weights,
            "formula_version": cfg.get("formula_version", "cdi-v2026.10"),
        }
        lookup.append(entry)
        prev_max = max_score

    return lookup


def classify_drought(cdi_score: float | None) -> dict:
    """
    Classify a CDI score into the full drought status using the lookup table.

    Returns:
      {"code": str, "label": str, "severity": str, "min_score": float, "max_score": float}
    """
    if cdi_score is None or (isinstance(cdi_score, float) and np.isnan(cdi_score)):
        return {
            "code": "ND",
            "label": "No data",
            "severity": "no_data",
            "min_score": None,
            "max_score": None,
        }

    for entry in build_drought_lookup_table():
        if entry["min_score"] <= cdi_score < entry["max_score"]:
            return {
                "code": entry["code"],
                "label": entry["label"],
                "severity": entry["severity"],
                "min_score": entry["min_score"],
                "max_score": entry["max_score"],
            }

    # Score at or above the highest threshold
    last = build_drought_lookup_table()[-1]
    return {
        "code": last["code"],
        "label": last["label"],
        "severity": last["severity"],
        "min_score": last["min_score"],
        "max_score": last["max_score"],
    }


def is_drought(cdi_score: float | None) -> bool:
    """Return True if the CDI score indicates any drought (D0-D4)."""
    result = classify_drought(cdi_score)
    return result["severity"] == "drought"


def is_no_drought(cdi_score: float | None) -> bool:
    """Return True if the CDI score indicates no drought / normal."""
    result = classify_drought(cdi_score)
    return result["severity"] == "no_drought"


def is_wet_from_spi(spi_value: float | None, spi_wet_threshold: float = 1.0) -> bool:
    """Return True if SPI indicates wet conditions (strong positive anomaly)."""
    if spi_value is None or (isinstance(spi_value, float) and np.isnan(spi_value)):
        return False
    return spi_value >= spi_wet_threshold


# Legacy aliases kept so older scripts still import cleanly.
code_for_value = code_for_spi
