# -*- coding: utf-8 -*-
"""
Scheduled driver for the Latur drought-monitoring pipeline.

Design:
  - Each source (Sentinel-2, CHIRPS) is checked INDEPENDENTLY.
  - Only new or affected periods are processed (dependency-aware).
  - Previous successful outputs are kept until replacements validate.
  - If a step fails, the last successful master table remains published.
  - The system never claims real-time when source latency prevents it.

Run on a schedule (cron, GitHub Actions, Fly machines) e.g.

    # every 6 hours
    0 */6 * * *  cd /app && python scripts/scheduler.py >> logs/scheduler.log 2>&1
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ROOT = HERE.parent
OUT  = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
LOG  = ROOT / "logs"; LOG.mkdir(parents=True, exist_ok=True)


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _run(name: str, cmd: list[str]) -> tuple[bool, str]:
    start = time.time()
    print(f"\n>>> {name}  ({_ts()})")
    print(f"    $ {' '.join(cmd)}")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60 * 60)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    elapsed = time.time() - start
    (LOG / f"{name}.log").open("a").write(
        f"\n=== {_ts()}  ({elapsed:.1f}s)  rc={out.returncode}\n"
        f"--- STDOUT ---\n{out.stdout}\n--- STDERR ---\n{out.stderr}\n")
    ok = out.returncode == 0
    print(f"    {'OK' if ok else 'FAIL'}  ({elapsed:.1f}s)")
    return ok, (out.stderr or out.stdout).splitlines()[-1] if (out.stderr or out.stdout) else ""


def main():
    tz = os.environ.get("TZ", "Asia/Calcutta")
    print(f"=== scheduler tick  {_ts()}  tz={tz} ===")

    results = {"started_at": _ts(), "steps": []}

    # 1) CHIRPS: fast, authoritative source — always run first.
    ok, msg = _run("chirps_gee", [sys.executable, str(HERE / "chirps_gee.py"),
                                   "--to", "latest"])
    results["steps"].append({"step": "chirps_gee", "ok": ok, "msg": msg})

    # 2) SPI recomputation only if CHIRPS added or revised a month.
    stale_path = OUT / "manifests" / "spi_stale.json"
    if stale_path.exists():
        ok, msg = _run("spi", [sys.executable, str(HERE / "latur_chirps_spi.py")])
        results["steps"].append({"step": "spi", "ok": ok, "msg": msg})
        if ok:
            stale_path.unlink()  # SPI consumed the hint
    else:
        results["steps"].append({"step": "spi", "skipped": "no stale months"})

    # 3) Sentinel-2: medium-latency, run independently.
    ok, msg = _run("pipeline_gee", [sys.executable, str(HERE / "pipeline_gee.py"),
                                     "--to", datetime.now().strftime("%Y-%m")])
    results["steps"].append({"step": "pipeline_gee", "ok": ok, "msg": msg})

    # 4) Composite CDI (transparent multi-index; replaces the old RF step).
    #    Re-weights over available inputs; marks pending when < min_inputs.
    ok, msg = _run("composite_cdi", [sys.executable, str(HERE / "composite_cdi.py")])
    results["steps"].append({"step": "composite_cdi", "ok": ok, "msg": msg})

    # 5) Dashboard master table + status files — always run (reads what's
    #    actually there and leaves missing fields empty).
    ok, msg = _run("dashboard_master", [sys.executable, str(HERE / "dashboard_master.py")])
    results["steps"].append({"step": "dashboard_master", "ok": ok, "msg": msg})

    results["finished_at"] = _ts()
    out = ROOT / "outputs" / "Dashboard" / "scheduler_last_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump(results, f, indent=2)
    print(f"\n=== scheduler done  {_ts()} ===")


if __name__ == "__main__":
    main()
