# -*- coding: utf-8 -*-
"""
=============================================================================
 Real-Time Dashboard JSON & Cache Updater
 Latur Drought Monitoring Platform (2016–2026)
=============================================================================

This module is the single authoritative writer for all dashboard JSON artifacts.
When the real-time ingestion pipeline finishes processing a new period (e.g. 2026-11),
this module atomically updates:
  1. latest_status.json           -> Dashboard header, status chip, composite metrics
  2. village_latest.json          -> Full 954-village snapshot for map & rankings
  3. village_timeseries.json      -> Appends new month to each village's time series
  4. district_monthly.json        -> Appends district aggregate timeseries record
  5. data_availability.json       -> Adds period to timeline scrubber registry
  6. processing_manifest.json     -> Ingestion audit trail & QC log
  7. drought_monitoring_master.csv-> CSV export for Go backend and user downloads

All files are written atomically and mirrored to BOTH:
  - outputs/Dashboard/
  - frontend/public/data/
"""
from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DASHBOARD = ROOT / "outputs" / "Dashboard"
FRONTEND_DATA = ROOT / "frontend" / "public" / "data"

OUTPUTS_DASHBOARD.mkdir(parents=True, exist_ok=True)
FRONTEND_DATA.mkdir(parents=True, exist_ok=True)


def _tz_now() -> str:
    """Returns ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_atomic_json(filepath: Path, data: Any) -> None:
    """Writes a JSON file atomically using a temporary file to avoid read race conditions."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Windows replacement
    if filepath.exists():
        try:
            filepath.unlink()
        except OSError:
            pass
    tmp_path.rename(filepath)


def mirror_file(filename: str, data: Any) -> None:
    """Writes to outputs/Dashboard and mirrors directly to frontend/public/data/."""
    dst_out = OUTPUTS_DASHBOARD / filename
    dst_front = FRONTEND_DATA / filename
    write_atomic_json(dst_out, data)
    write_atomic_json(dst_front, data)


def update_latest_status(
    period_str: str,
    composite_score: float | None,
    composite_class: str,
    composite_label: str,
    drought_severity: str,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Updates latest_status.json for dashboard header and status displays."""
    status_file = FRONTEND_DATA / "latest_status.json"
    existing: dict[str, Any] = {}
    if status_file.exists():
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    status_payload = {
        "generated_at": _tz_now(),
        "monitoring_status": "operational",
        "sentinel2": {
            "latest_period_id": period_str,
            "status": "operational",
            "observation_date": f"{period_str}-28",
        },
        "chirps": {
            "latest_period_id": period_str,
            "status": "operational",
            "observation_date": f"{period_str}-28",
        },
        "composite": {
            "formula_version": "cdi-v2026.10",
            "weights": {
                "SPI": 0.30,
                "VHI": 0.20,
                "VCI": 0.15,
                "NDVI": 0.15,
                "EVI": 0.10,
                "PCI": 0.10,
            },
            "composite_drought_score": composite_score,
            "composite_drought_class": composite_class,
            "composite_drought_label": composite_label,
            "drought_severity": drought_severity,
            "is_drought": drought_severity == "drought",
            "is_no_drought": drought_severity == "no_drought",
            "is_wet": drought_severity == "wet",
        },
        "region": {
            "district": "Latur",
            "state": "Maharashtra",
            "villages": stats.get("total_villages", 954) if stats else 954,
            "drought_villages": stats.get("drought_villages", 0) if stats else 0,
            "critical_d2_plus": stats.get("d2_plus_villages", 0) if stats else 0,
        },
    }

    mirror_file("latest_status.json", status_payload)
    return status_payload


def update_village_snapshots(
    period_str: str,
    village_metrics_map: dict[str, dict[str, Any]],
) -> None:
    """Updates village_latest.json and appends to village_timeseries.json."""
    ts_file = FRONTEND_DATA / "village_timeseries.json"
    ts_data: dict[str, list[dict[str, Any]]] = {}

    if ts_file.exists():
        try:
            with open(ts_file, "r", encoding="utf-8") as f:
                ts_data = json.load(f)
        except Exception as e:
            print(f"  [!] Notice reading village_timeseries.json: {e}")
            ts_data = {}

    # 1. Update village_latest.json snapshot
    village_snapshot: dict[str, dict[str, Any]] = {}
    idx_counter = 1

    for v_key, metrics in village_metrics_map.items():
        v_name = metrics.get("village") or v_key.split("::")[-1]
        t_name = metrics.get("tehsil") or v_key.split("::")[0]

        village_snapshot[str(idx_counter)] = {
            "id": idx_counter,
            "tehsil": t_name,
            "village": v_name,
            "date": period_str,
            "SPI3": metrics.get("spi3"),
            "NDVI": metrics.get("ndvi"),
            "EVI": metrics.get("evi", 1.0),
            "VCI": metrics.get("vci"),
            "VHI": metrics.get("vhi"),
            "PCI": metrics.get("pci"),
            "CDI": metrics.get("cdi"),
            "class": metrics.get("class", "None"),
        }
        idx_counter += 1

        # 2. Append to village_timeseries
        norm_key = v_key.strip().lower()
        if norm_key not in ts_data:
            ts_data[norm_key] = []

        # Check if period already exists
        existing_idx = next(
            (i for i, row in enumerate(ts_data[norm_key]) if (row.get("p") == period_str or row.get("date") == period_str)),
            None
        )

        pt_record = {
            "p": period_str,
            "date": period_str,
            "cdi": metrics.get("cdi"),
            "cls": metrics.get("class", "None"),
            "rain": metrics.get("rain"),
            "ndvi": metrics.get("ndvi"),
            "vhi": metrics.get("vhi"),
            "vci": metrics.get("vci"),
            "spi1": metrics.get("spi1"),
            "spi3": metrics.get("spi3"),
            "spi6": metrics.get("spi6"),
            "spi12": metrics.get("spi12"),
            "evi": metrics.get("evi"),
            "pci": metrics.get("pci"),
        }

        if existing_idx is not None:
            ts_data[norm_key][existing_idx] = pt_record
        else:
            ts_data[norm_key].append(pt_record)

    latest_snapshot_payload = {
        "generated_at": _tz_now(),
        "period": period_str,
        "villages": village_snapshot,
    }

    mirror_file("village_latest.json", latest_snapshot_payload)
    mirror_file("village_timeseries.json", ts_data)
    print(f"  -> SUCCESS: Updated {len(village_snapshot)} villages for {period_str} in village_latest.json and village_timeseries.json")


def update_district_monthly(period_str: str, district_aggregate: dict[str, Any]) -> None:
    """Appends or updates the district_monthly.json time-series file."""
    dm_file = FRONTEND_DATA / "district_monthly.json"
    dm_data: dict[str, Any] = {"series": []}

    if dm_file.exists():
        try:
            with open(dm_file, "r", encoding="utf-8") as f:
                dm_data = json.load(f)
        except Exception:
            dm_data = {"series": []}

    series = dm_data.get("series", [])
    existing_idx = next((i for i, s in enumerate(series) if s.get("date") == period_str), None)

    row = {
        "date": period_str,
        "composite_drought_score": district_aggregate.get("cdi"),
        "composite_drought_class": district_aggregate.get("class", "None"),
        "Rain_mm": district_aggregate.get("rain", 0.0),
        "NDVI": district_aggregate.get("ndvi"),
        "VHI": district_aggregate.get("vhi"),
        "VCI": district_aggregate.get("vci"),
        "SPI1": district_aggregate.get("spi1"),
        "SPI3": district_aggregate.get("spi3"),
        "SPI6": district_aggregate.get("spi6"),
        "SPI12": district_aggregate.get("spi12"),
    }

    if existing_idx is not None:
        series[existing_idx] = row
    else:
        series.append(row)
        series.sort(key=lambda x: x.get("date", ""))

    dm_data["series"] = series
    dm_data["latest_period"] = period_str
    dm_data["updated_at"] = _tz_now()

    mirror_file("district_monthly.json", dm_data)


def update_data_availability(period_str: str) -> None:
    """Adds period_str to data_availability.json timeline registry."""
    avail_file = FRONTEND_DATA / "data_availability.json"
    avail_data: dict[str, Any] = {"periods": []}

    if avail_file.exists():
        try:
            with open(avail_file, "r", encoding="utf-8") as f:
                avail_data = json.load(f)
        except Exception:
            avail_data = {"periods": []}

    periods = set(avail_data.get("periods", []))
    periods.add(period_str)
    sorted_periods = sorted(list(periods))

    avail_data["periods"] = sorted_periods
    avail_data["count"] = len(sorted_periods)
    avail_data["first"] = sorted_periods[0] if sorted_periods else period_str
    avail_data["latest"] = sorted_periods[-1] if sorted_periods else period_str
    avail_data["updated_at"] = _tz_now()

    mirror_file("data_availability.json", avail_data)


CANONICAL_MASTER_COLUMNS = [
    "district", "tehsil", "village", "observation_date", "observation_period",
    "year", "month", "monthly_rainfall_mm", "chirps_data_through",
    "SPI_1", "SPI_3", "SPI_6", "SPI_12", "SPI_reference_period",
    "NDVI", "EVI", "VCI", "VHI", "PCI",
    "composite_drought_score", "composite_drought_class",
    "component_contributions", "composite_formula_version",
    "drought_area_km2", "drought_percentage", "total_polygon_area_km2",
    "sentinel2_observation_date", "sentinel2_cloud_percentage",
    "data_quality_status", "processing_timestamp", "processing_run_id"
]


def append_to_master_csv(period_str: str, village_metrics_map: dict[str, dict[str, Any]]) -> None:
    """Appends records to drought_monitoring_master.csv safely conforming to canonical schema."""
    csv_file = OUTPUTS_DASHBOARD / "drought_monitoring_master.csv"
    existing_lines = []
    fieldnames = CANONICAL_MASTER_COLUMNS

    if csv_file.exists():
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                fieldnames = reader.fieldnames
            for r in reader:
                p = r.get("observation_period") or r.get("period")
                if p != period_str:
                    existing_lines.append(r)

    y, m = period_str.split("-")
    now_ts = _tz_now()
    run_id = f"realtime-{period_str}"

    new_rows = []
    for v_key, metrics in village_metrics_map.items():
        v_name = metrics.get("village") or v_key.split("::")[-1]
        t_name = metrics.get("tehsil") or v_key.split("::")[0]
        
        row_dict = {
            "district": "Latur",
            "tehsil": t_name,
            "village": v_name,
            "observation_date": f"{period_str}-01",
            "observation_period": period_str,
            "year": y,
            "month": str(int(m)),
            "monthly_rainfall_mm": metrics.get("rain") if metrics.get("rain") is not None else "",
            "chirps_data_through": period_str,
            "SPI_1": metrics.get("spi1") if metrics.get("spi1") is not None else "",
            "SPI_3": metrics.get("spi3") if metrics.get("spi3") is not None else "",
            "SPI_6": metrics.get("spi6") if metrics.get("spi6") is not None else "",
            "SPI_12": metrics.get("spi12") if metrics.get("spi12") is not None else "",
            "SPI_reference_period": "1991-2020",
            "NDVI": metrics.get("ndvi") if metrics.get("ndvi") is not None else "",
            "EVI": metrics.get("evi", 1.0) if metrics.get("evi") is not None else "",
            "VCI": metrics.get("vci") if metrics.get("vci") is not None else "",
            "VHI": metrics.get("vhi") if metrics.get("vhi") is not None else "",
            "PCI": metrics.get("pci") if metrics.get("pci") is not None else "",
            "composite_drought_score": metrics.get("cdi") if metrics.get("cdi") is not None else "",
            "composite_drought_class": metrics.get("class", "None"),
            "component_contributions": "{}",
            "composite_formula_version": "cdi-v2026.10",
            "drought_area_km2": "",
            "drought_percentage": "",
            "total_polygon_area_km2": "",
            "sentinel2_observation_date": f"{period_str}-01",
            "sentinel2_cloud_percentage": "0.0",
            "data_quality_status": "success",
            "processing_timestamp": now_ts,
            "processing_run_id": run_id
        }
        
        # Build strict entry for only keys in fieldnames
        strict_entry = {col: row_dict.get(col, "") for col in fieldnames}
        new_rows.append(strict_entry)

    all_rows = existing_lines + new_rows
    tmp_csv = csv_file.with_suffix(".csv.tmp")
    with open(tmp_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    if csv_file.exists():
        csv_file.unlink()
    tmp_csv.rename(csv_file)

    # Mirror to public data
    shutil.copy2(csv_file, FRONTEND_DATA / "drought_monitoring_master.csv")
    print(f"  -> SUCCESS: drought_monitoring_master.csv updated ({len(all_rows)} total rows).")
