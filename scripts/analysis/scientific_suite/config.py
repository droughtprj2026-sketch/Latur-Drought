# -*- coding: utf-8 -*-
"""Paths, index registry and shared constants for the scientific figure suite.

Everything that describes the data (paths, column names, labels) lives here so
that the plotting modules stay generic. The drought palette is imported from
``scripts/common/classify.py`` so the figures can never drift away from the
dashboard / Supabase colours (see AGENTS.md, "threshold / palette parity").
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: the suite is meant to run in CI / Colab

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common import classify  # noqa: E402  (needs the path fix above)

# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
PANEL_CSV = ROOT / "data" / "processed" / "csv" / "village_with_baseline.csv"
SPI_DIR = ROOT / "output" / "spi" / "csv"
RAIN_CSV = ROOT / "output" / "spi" / "extra" / "csv" / "village_monthly_rainfall_wide.csv"
VILLAGE_GEOJSON = ROOT / "frontend" / "public" / "data" / "latur_villages_latest.geojson"
FALLBACK_VILLAGE_GEOJSON = ROOT / "data" / "vector" / "latur_villages.geojson"
TEHSIL_GEOJSON = ROOT / "data" / "vector" / "latur_tehsils.geojson"
DISTRICT_GEOJSON = ROOT / "data" / "vector" / "latur_district.geojson"
AVAILABILITY_JSON = ROOT / "outputs" / "Dashboard" / "data_availability.json"

# --------------------------------------------------------------------------
# Outputs: one folder per analytical theme, so the suite never dumps a flat
# pile of PNGs into a single directory.
# --------------------------------------------------------------------------
OUT_ROOT = ROOT / "output" / "figures" / "scientific_suite"

SECTIONS = {
    "availability": "01_image_availability",
    "correlation": "02_correlation",
    "heatmap": "03_heatmaps",
    "relationships": "04_index_relationships",
    "distribution": "05_distributions",
    "temporal": "06_temporal_analysis",
    "spatial": "07_spatial_analysis",
    "tables": "08_statistics_tables",
}

SECTION_TITLES = {
    "availability": "Image availability and sampling completeness",
    "correlation": "Inter-index correlation structure (Pearson and Spearman)",
    "heatmap": "Full heatmap atlas of every index over time and space",
    "relationships": "Index relationships, regressions and response lags",
    "distribution": "Index distributions and drought-class separation",
    "temporal": "Temporal evolution and drought episodes",
    "spatial": "Spatial pattern across villages and tehsils",
    "tables": "Machine-readable statistics",
}

DPI = 300
RECORD_FORMAT = "png"


# --------------------------------------------------------------------------
# Index registry
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class IndexSpec:
    """One column of the village panel, with everything a plot needs to label it."""

    column: str
    label: str          # full label for titles / axis
    short: str          # compact tick label
    unit: str
    group: str          # meteorological | vegetation | soil | composite
    kind: str = "continuous"   # continuous | spi | percent | composite


INDEXES: tuple[IndexSpec, ...] = (
    IndexSpec("Rain_mm", "Monthly rainfall", "Rain", "mm", "meteorological"),
    IndexSpec("SPI1", "SPI-1", "SPI-1", "z", "meteorological", "spi"),
    IndexSpec("SPI3", "SPI-3", "SPI-3", "z", "meteorological", "spi"),
    IndexSpec("SPI6", "SPI-6", "SPI-6", "z", "meteorological", "spi"),
    IndexSpec("SPI12", "SPI-12", "SPI-12", "z", "meteorological", "spi"),
    IndexSpec("NDVI", "NDVI", "NDVI", "-", "vegetation"),
    IndexSpec("EVI", "EVI", "EVI", "-", "vegetation"),
    IndexSpec("VCI", "Vegetation Condition Index", "VCI", "%", "vegetation", "percent"),
    IndexSpec("VHI", "Vegetation Health Index", "VHI", "%", "vegetation", "percent"),
    IndexSpec("NSMI", "Normalized Soil Moisture Index", "NSMI", "-", "soil"),
    IndexSpec("composite_drought_score", "Composite Drought Index", "CDI", "0-1", "composite", "composite"),
)

COL: dict[str, IndexSpec] = {spec.column: spec for spec in INDEXES}

# Compact name lists used by the correlation figures.
SPI_COLUMNS = ["SPI1", "SPI3", "SPI6", "SPI12"]
VEG_COLUMNS = ["NDVI", "EVI", "VCI", "VHI"]
CDI_COLUMN = "composite_drought_score"
RAIN_COLUMN = "Rain_mm"
CLASS_COLUMN = "composite_drought_class"

# Main block of the correlation matrices: meteorology -> soil -> vegetation -> composite.
CORE_COLUMNS = ["Rain_mm", "SPI1", "SPI3", "SPI6", "SPI12", "NSMI", "NDVI", "EVI", "VCI", "VHI", CDI_COLUMN]

# Narrow set used for the year-by-year grids where readability matters.
ANNUAL_COLUMNS = ["Rain_mm", "SPI3", "NSMI", "NDVI", "VCI", CDI_COLUMN]

GROUP_COLORS = {
    "meteorological": "#1F6FB2",
    "soil": "#8C6D31",
    "vegetation": "#2E7D32",
    "composite": "#6E1423",
}

# --------------------------------------------------------------------------
# Drought classes: single source of truth is scripts/common/classify.py
# --------------------------------------------------------------------------
D_CODES = list(classify.D_CODES)
D_COLORS = list(classify.D_COLORS)
D_CLASS_LABELS = {
    "None": "Not in drought",
    "D0": "D0 Abnormally dry",
    "D1": "D1 Moderate",
    "D2": "D2 Severe",
    "D3": "D3 Extreme",
    "D4": "D4 Exceptional",
    "ND": "No data",
}
DROUGHT_COLORS = dict(zip(D_CODES, D_COLORS))
DROUGHT_COLORS["ND"] = "#9E9E9E"
# Ordered codes used on stacked bars: wettest to driest.
CLASS_ORDER = ["None", "D0", "D1", "D2", "D3", "D4"]
DROUGHT_CODES = ["D0", "D1", "D2", "D3", "D4"]

MONTHS = list(classify.MONTHS)
MONTH_NUMBERS = list(range(1, 13))

# The CDI thresholds are read from config/composite.yaml at runtime, never
# duplicated here; ``classify.composite_thresholds()`` is the accessor.

MIN_PAIRS_VILLAGE = 24  # village-months needed before a per-village correlation is plotted


def section_dir(section: str) -> Path:
    return OUT_ROOT / SECTIONS[section]


def ensure_dirs() -> None:
    for name in SECTIONS:
        section_dir(name).mkdir(parents=True, exist_ok=True)
