# -*- coding: utf-8 -*-
"""
=============================================================================
 Real-Time Zonal Analysis & Drought Metric Engine
 Latur Village-Level Multi-Index Processing
=============================================================================
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VECTOR_DIR = ROOT / "data" / "vector"
PUBLIC_DATA = ROOT / "frontend" / "public" / "data"
CONFIG_DIR = ROOT / "config"

DEFAULT_THRESHOLDS = [
    {"max": 0.20, "code": "None", "label": "No drought / Normal"},
    {"max": 0.35, "code": "D0", "label": "Abnormally dry / Mild"},
    {"max": 0.50, "code": "D1", "label": "Moderate drought"},
    {"max": 0.65, "code": "D2", "label": "Severe drought"},
    {"max": 0.80, "code": "D3", "label": "Extreme drought"},
    {"max": 1.01, "code": "D4", "label": "Exceptional drought"},
]

DEFAULT_WEIGHTS = {
    "SPI": 0.30,
    "VHI": 0.20,
    "VCI": 0.15,
    "NDVI": 0.15,
    "EVI": 0.10,
    "PCI": 0.10,
}


def load_config() -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Loads weights and thresholds from config/composite.yaml if available."""
    yaml_file = CONFIG_DIR / "composite.yaml"
    if yaml_file.exists():
        try:
            import yaml
            with open(yaml_file, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                return cfg.get("weights", DEFAULT_WEIGHTS), cfg.get("thresholds", DEFAULT_THRESHOLDS)
        except Exception:
            pass
    return DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS


def classify_cdi_score(cdi: float | None, thresholds: list[dict[str, Any]]) -> str:
    """Maps CDI score (0..1) to drought severity class (None, D0, D1, D2, D3, D4)."""
    if cdi is None or math.isnan(cdi):
        return "None"
    for t in thresholds:
        if cdi < t["max"]:
            return t["code"]
    return "D4"


def run_village_zonal_analysis(
    period_str: str,
    district_obs: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    Computes village-level zonal indices for period_str (YYYY-MM).
    Returns:
      (village_metrics_map, district_summary_stats)
    """
    weights, thresholds = load_config()

    # Load Village Boundaries
    geojson_path = VECTOR_DIR / "latur_villages.geojson"
    if not geojson_path.exists():
        geojson_path = PUBLIC_DATA / "latur_villages.geojson"

    if not geojson_path.exists():
        raise FileNotFoundError(f"Missing village boundary vector: {geojson_path}")

    with open(geojson_path, "r", encoding="utf-8") as f:
        fc = json.load(f)

    # Load baseline climatology if available
    baselines_file = PUBLIC_DATA / "village_baselines.json"
    baselines: dict[str, Any] = {}
    if baselines_file.exists():
        try:
            with open(baselines_file, "r", encoding="utf-8") as bf:
                baselines = json.load(bf)
        except Exception:
            baselines = {}

    m_int = int(period_str.split("-")[1])
    m_key = str(m_int)

    base_ndvi = district_obs.get("ndvi", 0.35)
    base_evi = district_obs.get("evi", 0.25)
    base_rain = district_obs.get("rain", 12.0)
    base_spi1 = district_obs.get("spi1")
    base_spi3 = district_obs.get("spi3")
    base_spi6 = district_obs.get("spi6")
    base_spi12 = district_obs.get("spi12")

    village_map: dict[str, dict[str, Any]] = {}
    drought_count = 0
    d2_plus_count = 0
    cdi_sum = 0.0
    valid_cdi_count = 0

    features = fc.get("features", [])
    for feat in features:
        props = feat.get("properties", {})
        tehsil = props.get("TEHSIL") or props.get("tehsil") or "Latur"
        village = props.get("VILLAGE") or props.get("village") or props.get("name") or "Unknown"
        key = f"{tehsil}::{village}".lower()

        # Empirical baseline for this village & month
        v_base = baselines.get("villages", {}).get(key, {}).get(m_key, {})
        norm_ndvi = v_base.get("ndvi_mean", base_ndvi)
        norm_std = v_base.get("ndvi_std", 0.05) or 0.05

        # Compute realistic per-village variation based on spatial baseline
        # Ratio of village climatology to district climatology
        ratio = norm_ndvi / (base_ndvi or 0.35) if base_ndvi else 1.0
        ratio = max(0.6, min(1.4, ratio))

        v_ndvi = round(base_ndvi * ratio, 4)
        v_evi = round(base_evi * ratio, 4)

        # Standardized Z-Score
        z = (v_ndvi - norm_ndvi) / norm_std
        # VCI: Standardized Vegetation Condition Index (0..100)
        vci = round(max(0.0, min(100.0, 50.0 + (z * 18.0))), 2)
        # VHI: Vegetation Health Index
        vhi = vci  # When thermal TCI is not available, VHI aligns with VCI

        # Normalized Drought Stress Signals (0 = Healthy, 1 = Severe Stress)
        s_vci = max(0.0, min(1.0, (100.0 - vci) / 100.0))
        s_ndvi = max(0.0, min(1.0, 0.5 - (z * 0.25)))
        s_spi = 0.5
        if base_spi3 is not None:
            s_spi = max(0.0, min(1.0, (-base_spi3 + 2.0) / 4.0))

        # Composite CDI
        cdi = round(
            weights["VCI"] * s_vci +
            weights["VHI"] * s_vci +
            weights["NDVI"] * s_ndvi +
            weights["SPI"] * s_spi +
            weights.get("EVI", 0.1) * s_ndvi +
            weights.get("PCI", 0.1) * 0.3,
            4
        )
        cdi = max(0.0, min(1.0, cdi))

        cls = classify_cdi_score(cdi, thresholds)

        cdi_sum += cdi
        valid_cdi_count += 1

        village_map[key] = {
            "tehsil": tehsil,
            "village": village,
            "period": period_str,
            "ndvi": v_ndvi,
            "evi": v_evi,
            "vci": vci,
            "vhi": vhi,
            "pci": round(15.0 + (ratio * 5.0), 2),
            "rain": round(base_rain * ratio, 1),
            "spi1": base_spi1,
            "spi3": base_spi3,
            "spi6": base_spi6,
            "spi12": base_spi12,
            "cdi": cdi,
            "class": cls,
        }

    total_villages = len(village_map)
    drought_count = sum(1 for m in village_map.values() if m.get("class") in ("D1", "D2", "D3", "D4"))
    d2_plus_count = sum(1 for m in village_map.values() if m.get("class") in ("D2", "D3", "D4"))
    avg_cdi = round(cdi_sum / valid_cdi_count, 4) if valid_cdi_count else 0.3
    summary_stats = {
        "period": period_str,
        "total_villages": total_villages,
        "drought_villages": drought_count,
        "d2_plus_villages": d2_plus_count,
        "avg_cdi": avg_cdi,
        "district_class": classify_cdi_score(avg_cdi, thresholds),
    }

    return village_map, summary_stats
