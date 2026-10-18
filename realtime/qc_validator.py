# -*- coding: utf-8 -*-
"""
=============================================================================
 Quality Control & Pre-Integration Validation Suite
 Prevents Pipeline Crashes and Corrupted Dashboard JSON Updates
=============================================================================

This module verifies all computed metrics against physical limits, statistical
bounds, and schema contracts BEFORE they are integrated into dashboard JSONs.

If any test fails, the pipeline aborts cleanly without touching production data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

VALID_CLASSES = {"None", "D0", "D1", "D2", "D3", "D4"}


class QCValidationError(Exception):
    """Raised when quality control validation tests fail."""
    pass


def validate_village_metrics(village_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Validates village zonal metrics against strict physical and schema bounds.
    Returns audit statistics if passed, raises QCValidationError if failed.
    """
    count = len(village_map)
    if count < 900:
        raise QCValidationError(f"Spatial coverage failure: Expected >= 900 villages, received {count}.")

    nan_count = 0
    out_of_bounds = []

    for v_key, m in village_map.items():
        # Check required fields
        for field in ("tehsil", "village", "period", "cdi", "class", "ndvi", "vci"):
            if field not in m:
                raise QCValidationError(f"Schema violation for village '{v_key}': Missing required key '{field}'.")

        # Class validation
        cls = m.get("class")
        if cls not in VALID_CLASSES:
            raise QCValidationError(f"Invalid drought class '{cls}' for village '{v_key}'. Must be one of {VALID_CLASSES}.")

        # Numeric checks
        cdi = m.get("cdi")
        if cdi is None or math.isnan(cdi) or math.isinf(cdi):
            nan_count += 1
        elif not (0.0 <= cdi <= 1.0):
            out_of_bounds.append((v_key, "cdi", cdi))

        ndvi = m.get("ndvi")
        if ndvi is not None and not math.isnan(ndvi):
            if not (-0.2 <= ndvi <= 1.0):
                out_of_bounds.append((v_key, "ndvi", ndvi))

        vci = m.get("vci")
        if vci is not None and not math.isnan(vci):
            if not (0.0 <= vci <= 100.0):
                out_of_bounds.append((v_key, "vci", vci))

    if out_of_bounds:
        first_bad = out_of_bounds[0]
        raise QCValidationError(
            f"Physical bounds violation: {len(out_of_bounds)} values out of range. "
            f"Example: Village '{first_bad[0]}' field '{first_bad[1]}' = {first_bad[2]}."
        )

    missing_rate = (nan_count / count) * 100
    if missing_rate > 5.0:
        raise QCValidationError(f"Excessive null CDI values: {missing_rate:.1f}% missing (threshold is <= 5.0%).")

    return {
        "status": "passed",
        "validated_villages": count,
        "missing_rate_pct": round(missing_rate, 2),
    }


def validate_district_summary(summary: dict[str, Any]) -> None:
    """Validates aggregated district metrics."""
    total = summary.get("total_villages", 0)
    drought = summary.get("drought_villages", 0)
    d2_plus = summary.get("d2_plus_villages", 0)
    avg_cdi = summary.get("avg_cdi")
    cls = summary.get("district_class")

    if total < 900:
        raise QCValidationError(f"District summary validation failed: total_villages = {total} (< 900).")

    if drought > total:
        raise QCValidationError(f"Inconsistent drought statistics: drought ({drought}) > total ({total}).")

    if d2_plus > drought:
        raise QCValidationError(f"Inconsistent severity statistics: critical ({d2_plus}) > drought ({drought}).")

    if avg_cdi is not None and not (0.0 <= avg_cdi <= 1.0):
        raise QCValidationError(f"Average CDI out of range: {avg_cdi} (must be 0.0..1.0).")

    if cls not in VALID_CLASSES:
        raise QCValidationError(f"Invalid district drought class '{cls}'.")


def test_json_integrity(json_path: Path) -> bool:
    """Verifies that a written JSON file is non-empty and parses cleanly."""
    if not json_path.exists():
        raise QCValidationError(f"Integrity check failed: File does not exist at {json_path}")
    if json_path.stat().st_size == 0:
        raise QCValidationError(f"Integrity check failed: File is 0 bytes at {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                raise QCValidationError(f"Integrity check failed: Parsed JSON is empty at {json_path}")
    except json.JSONDecodeError as exc:
        raise QCValidationError(f"Integrity check failed: Malformed JSON at {json_path}: {exc}")

    return True


def validate_cloud_cover_qc(cloud_info: dict[str, Any] | None) -> dict[str, Any]:
    """Verifies that accepted optical observations do not exceed the 25% cloud cover ceiling.
    
    If cloud cover > 25%, raises QCValidationError if the scene was incorrectly accepted.
    """
    if not cloud_info:
        return {"status": "skipped", "reason": "No optical cloud metadata provided"}

    cloud_pct = cloud_info.get("cloud_pct")
    status = cloud_info.get("cloud_status")

    if status == "accepted" and cloud_pct is not None:
        if cloud_pct > 25.0:
            raise QCValidationError(
                f"Cloud Cover Quality Failure: Accepted scene has {cloud_pct}% cloud cover, "
                f"which exceeds the statutory 25.0% maximum ceiling."
            )
        return {"status": "passed", "cloud_pct": cloud_pct, "tier": cloud_info.get("cloud_tier")}

    return {"status": "rejected_or_degraded", "cloud_pct": cloud_pct}
