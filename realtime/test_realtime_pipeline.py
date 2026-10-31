# -*- coding: utf-8 -*-
"""
=============================================================================
 Real-Time Pipeline Pre-Integration & Quality Control Test Suite
 Validates that the pipeline never integrates corrupt or failing metrics
=============================================================================

Run with:
    python realtime/test_realtime_pipeline.py
    pytest realtime/test_realtime_pipeline.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "realtime"))

from qc_validator import (
    validate_village_metrics,
    validate_district_summary,
    test_json_integrity,
    QCValidationError,
)
from zonal_analyzer import run_village_zonal_analysis, classify_cdi_score, DEFAULT_THRESHOLDS
from json_updater import write_atomic_json
from orchestrator import run_pipeline


def test_qc_catches_out_of_bounds_cdi():
    """Verify that any CDI > 1.0 or < 0.0 is caught and rejected."""
    bad_map = {
        f"tehsil::village_{i}": {
            "tehsil": "Ahmadpur",
            "village": f"Village_{i}",
            "period": "2026-10",
            "ndvi": 0.35,
            "vci": 45.0,
            "cdi": 1.45 if i == 500 else 0.4,  # Out of bounds value!
            "class": "D1",
        }
        for i in range(954)
    }

    try:
        validate_village_metrics(bad_map)
        assert False, "QC Validator should have raised QCValidationError on CDI > 1.0"
    except QCValidationError as e:
        assert "cdi" in str(e).lower()
        print("  [PASS] test_qc_catches_out_of_bounds_cdi passed.")


def test_qc_catches_invalid_classes():
    """Verify that unrecognised drought classes are rejected."""
    bad_map = {
        f"tehsil::village_{i}": {
            "tehsil": "Ahmadpur",
            "village": f"Village_{i}",
            "period": "2026-10",
            "ndvi": 0.35,
            "vci": 45.0,
            "cdi": 0.4,
            "class": "UNKNOWN_SEVERITY" if i == 100 else "D1",
        }
        for i in range(954)
    }

    try:
        validate_village_metrics(bad_map)
        assert False, "QC Validator should have raised QCValidationError on invalid class"
    except QCValidationError as e:
        assert "class" in str(e).lower()
        print("  [PASS] test_qc_catches_invalid_classes passed.")


def test_qc_catches_insufficient_village_count():
    """Verify that partial spatial data (<900 villages) is blocked from updating the dashboard."""
    bad_map = {
        f"tehsil::village_{i}": {
            "tehsil": "Ahmadpur",
            "village": f"Village_{i}",
            "period": "2026-10",
            "ndvi": 0.35,
            "vci": 45.0,
            "cdi": 0.4,
            "class": "D1",
        }
        for i in range(500)  # Only 500 villages instead of 954
    }

    try:
        validate_village_metrics(bad_map)
        assert False, "QC Validator should have rejected insufficient village count"
    except QCValidationError as e:
        assert "coverage" in str(e).lower() or "expected >= 900" in str(e).lower()
        print("  [PASS] test_qc_catches_insufficient_village_count passed.")


def test_zonal_analysis_generates_valid_metrics():
    """Verify that zonal_analyzer produces valid, physically bounded village metrics."""
    district_obs = {
        "ndvi": 0.38,
        "evi": 0.28,
        "rain": 14.2,
        "spi1": -0.1,
        "spi3": -0.85,
        "spi6": -0.65,
        "spi12": -0.40,
    }
    v_map, summary = run_village_zonal_analysis("2026-10", district_obs)
    assert len(v_map) >= 950, f"Expected >= 950 villages, got {len(v_map)}"
    assert 0.0 <= summary["avg_cdi"] <= 1.0
    assert summary["drought_villages"] <= summary["total_villages"]

    # Pre-integration QC should pass cleanly
    audit = validate_village_metrics(v_map)
    assert audit["status"] == "passed"
    validate_district_summary(summary)
    print("  [PASS] test_zonal_analysis_generates_valid_metrics passed.")


def test_json_integrity_verification():
    """Verify that atomic JSON writer creates non-empty, parseable JSON files."""
    with tempfile.TemporaryDirectory() as td:
        tf = Path(td) / "test_artifact.json"
        write_atomic_json(tf, {"status": "operational", "test_metric": 42})
        assert test_json_integrity(tf) is True
    print("  [PASS] test_json_integrity_verification passed.")


from gee_fetcher import evaluate_cloud_cover_acceptance
from qc_validator import validate_cloud_cover_qc


def test_cloud_cover_stepped_acceptance():
    """Verify that cloud cover is evaluated step-by-step: <= 15% -> <= 20% -> <= 25% ceiling, rejected > 25%."""
    # Tier 1 test (<= 15% optimal)
    res_t1 = evaluate_cloud_cover_acceptance(11.4)
    assert res_t1["accepted"] is True
    assert "Tier 1" in res_t1["tier"]
    assert res_t1["threshold_applied"] == 15.0

    # Tier 2 test (<= 20% acceptable)
    res_t2 = evaluate_cloud_cover_acceptance(17.8)
    assert res_t2["accepted"] is True
    assert "Tier 2" in res_t2["tier"]
    assert res_t2["threshold_applied"] == 20.0

    # Tier 3 test (<= 25% maximum ceiling)
    res_t3 = evaluate_cloud_cover_acceptance(24.2)
    assert res_t3["accepted"] is True
    assert "Tier 3" in res_t3["tier"]
    assert res_t3["threshold_applied"] == 25.0

    # Rejection test (> 25% cloud cover)
    res_rej = evaluate_cloud_cover_acceptance(29.8)
    assert res_rej["accepted"] is False
    assert "rejected" in res_rej["tag"]
    assert "exceeds statutory maximum ceiling" in res_rej["reason"]

    # QC Validator test: raises error if > 25% is marked accepted
    bad_cloud_info = {"cloud_status": "accepted", "cloud_pct": 32.5}
    try:
        validate_cloud_cover_qc(bad_cloud_info)
        assert False, "QC Validator should raise error when accepted scene has > 25% clouds"
    except QCValidationError as e:
        assert "25.0%" in str(e)

    # QC Validator test: passes when <= 25%
    good_cloud_info = {"cloud_status": "accepted", "cloud_pct": 14.5, "cloud_tier": "Tier 1: Optimal"}
    qc_res = validate_cloud_cover_qc(good_cloud_info)
    assert qc_res["status"] == "passed"

    print("  [PASS] test_cloud_cover_stepped_acceptance passed.")


def test_dry_run_pipeline():
    """Verify that running the orchestrator with dry_run=True passes all tests without errors."""
    report = run_pipeline(period_str="2026-10", dry_run=True)
    assert report["status"] == "dry_run_success"
    assert len(report["tests"]) >= 2
    for t in report["tests"]:
        assert t["result"] == "PASS"
    print("  [PASS] test_dry_run_pipeline passed.")


def run_all_tests():
    print("\n" + "=" * 65)
    print(" RUNNING REAL-TIME PIPELINE PRE-INTEGRATION TEST SUITE")
    print("=" * 65)
    test_qc_catches_out_of_bounds_cdi()
    test_qc_catches_invalid_classes()
    test_qc_catches_insufficient_village_count()
    test_zonal_analysis_generates_valid_metrics()
    test_cloud_cover_stepped_acceptance()
    test_json_integrity_verification()
    test_dry_run_pipeline()
    print("\n[ALL TESTS PASSED] The real-time pipeline is safe and validated for integration.\n")


if __name__ == "__main__":
    run_all_tests()
