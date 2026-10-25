# -*- coding: utf-8 -*-
"""
Processing-manifest utilities.

Two separate manifests live under `data/processed/`:

    manifests/sentinel.json     — one entry per processed Sentinel-2 period
    manifests/chirps.json       — one entry per processed CHIRPS period

They are the source of truth for "what has been successfully processed
and validated". Every pipeline run reads them, picks only the new or
affected periods, and writes them back after validation.

Schema (same for both):

{
  "schema":   1,
  "source":   "sentinel-2 l2a" | "chirps v2.0 monthly",
  "updated":  "2026-10-15T19:40:00+05:30",
  "entries": [
      {
        "period_id":        "2026-09",
        "observation_date": "2026-09-18",
        "processed_at":     "2026-10-15T18:22:11+05:30",
        "status":           "success" | "failed" | "pending",
        "outputs":          ["ndvi/NDVI_Latur_2026_09.geojson", ...],
        "input_ids":        ["S2_...tile_id..."],
        "cloud_pct":        12.3,
        "qc":               {"missing_days": 0, "spatial_coverage_pct": 100},
        "notes":            ""
      }
  ]
}

Only "success" entries are considered done. "failed" and "pending"
entries are retried on the next scheduler tick.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1


def _tz_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _path(root: Path, source: str) -> Path:
    assert source in {"sentinel", "chirps"}, f"unknown source: {source}"
    return root / "manifests" / f"{source}.json"


def load(root: Path, source: str) -> dict:
    path = _path(root, source)
    if not path.exists():
        return {"schema": SCHEMA_VERSION,
                "source": source, "updated": _tz_now(), "entries": []}
    with path.open() as f:
        return json.load(f)


def save(root: Path, source: str, data: dict) -> None:
    path = _path(root, source)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = _tz_now()
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)                       # atomic write


def processed_period_ids(root: Path, source: str) -> set[str]:
    """Return the set of period_ids that have been successfully processed."""
    data = load(root, source)
    return {e["period_id"] for e in data["entries"] if e.get("status") == "success"}


def missing_periods(root: Path, source: str, candidates: Iterable[str]) -> list[str]:
    """candidates are period_ids ('YYYY-MM'); return the ones not yet successful."""
    done = processed_period_ids(root, source)
    return [p for p in candidates if p not in done]


def record(
    root: Path,
    source: str,
    period_id: str,
    *,
    observation_date: str,
    status: str,
    outputs: list[str],
    input_ids: list[str] | None = None,
    cloud_pct: float | None = None,
    qc: dict | None = None,
    notes: str = "",
) -> None:
    """Append or overwrite a manifest entry for `period_id`, then save."""
    assert status in {"success", "failed", "pending"}
    data = load(root, source)
    entries = [e for e in data["entries"] if e["period_id"] != period_id]
    entries.append({
        "period_id":        period_id,
        "observation_date": observation_date,
        "processed_at":     _tz_now(),
        "status":           status,
        "outputs":          outputs,
        "input_ids":        input_ids or [],
        "cloud_pct":        cloud_pct,
        "qc":               qc or {},
        "notes":            notes,
    })
    entries.sort(key=lambda e: e["period_id"])
    data["entries"] = entries
    save(root, source, data)


def affected_periods_for_spi(
    root: Path, new_month: str, scales: tuple[int, ...] = (1, 3, 6, 12),
) -> list[str]:
    """
    If a new CHIRPS month `new_month` ('YYYY-MM') has arrived, every rolling
    SPI window that INCLUDES it is affected. Returns the list of month
    period_ids whose SPI must be recomputed.
    """
    y, m = (int(x) for x in new_month.split("-"))
    out: set[str] = set()
    for k in scales:
        for offset in range(0, k):
            yy, mm = y, m + offset
            while mm > 12:
                mm -= 12; yy += 1
            out.add(f"{yy}-{mm:02d}")
    return sorted(out)


def latest_period(root: Path, source: str) -> dict | None:
    data = load(root, source)
    good = [e for e in data["entries"] if e["status"] == "success"]
    return max(good, key=lambda e: e["period_id"], default=None)
