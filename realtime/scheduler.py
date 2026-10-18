# -*- coding: utf-8 -*-
"""
=============================================================================
 Real-Time Pipeline Cron Scheduler & Daemon Runner
 Latur Drought Monitoring Platform (2016–2026)
=============================================================================

Modes:
  1. Single Run (default):
      python realtime/scheduler.py --once
  2. Standing Background Daemon / Cron Scheduler:
      python realtime/scheduler.py --daemon --interval-hours 6
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "realtime"))

from orchestrator import run_pipeline
from json_updater import mirror_file, _tz_now


def run_daemon(interval_hours: float, period: str | None = None, force: bool = False):
    """Runs the real-time orchestrator on a scheduled loop."""
    interval_sec = int(interval_hours * 3600)
    print("*" * 75)
    print(" STARTING LATUR REAL-TIME PIPELINE CRON SCHEDULER DAEMON")
    print(f" Wakeup Interval: Every {interval_hours} hours ({interval_sec}s)")
    print(f" Process PID:     {os.getpid()}")
    print("*" * 75)

    running = True

    def _sig_handler(sig, frame):
        nonlocal running
        print(f"\n[DAEMON] Received signal {sig}. Initiating graceful shutdown...")
        running = False

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except (ValueError, AttributeError):
        pass

    cycle_count = 0
    while running:
        cycle_count += 1
        now_dt = datetime.now(timezone.utc)
        print(f"\n[DAEMON] Triggering Scheduled Run #{cycle_count} at {now_dt.isoformat()}...")

        try:
            report = run_pipeline(period_str=period, force=force, dry_run=False)
            status_str = report.get("status", "unknown")
            print(f"[DAEMON] Run #{cycle_count} completed with status: {status_str.upper()}")
        except Exception as exc:
            print(f"[DAEMON] Run #{cycle_count} encountered unexpected exception: {exc}")

        if not running:
            break

        next_tick = datetime.now(timezone.utc) + timedelta(seconds=interval_sec)
        heartbeat = {
            "daemon_status": "running",
            "cycle_count": cycle_count,
            "last_cycle_at": _tz_now(),
            "next_cycle_at": next_tick.isoformat(),
            "interval_hours": interval_hours,
        }
        mirror_file("scheduler_status.json", heartbeat)
        print(f"[DAEMON] Heartbeat logged. Next scheduled cycle: {next_tick.isoformat()} UTC\n")

        slept = 0
        while running and slept < interval_sec:
            time.sleep(min(5, interval_sec - slept))
            slept += 5

    print("[DAEMON] Scheduler daemon exited cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Real-Time Drought Pipeline Cron Scheduler")
    parser.add_argument("--once", action="store_true", default=False, help="Run single ingestion pass and exit")
    parser.add_argument("--daemon", action="store_true", default=False, help="Run continuously as background daemon")
    parser.add_argument("--interval-hours", type=float, default=6.0, help="Interval between runs in daemon mode")
    parser.add_argument("--period", type=str, default=None, help="Target observation period YYYY-MM")
    parser.add_argument("--overpass-info", action="store_true", default=False, help="Display Sentinel-2 overpass days, tracks, and optimal sync window for Latur")
    args = parser.parse_args()

    if args.overpass_info:
        from gee_fetcher import get_overpass_schedule
        info = get_overpass_schedule()
        print("\n" + "=" * 70)
        print(" SENTINEL-2 ORBITAL OVERPASS & INGESTION TIMETABLE FOR LATUR")
        print("=" * 70)
        for k, v in info.items():
            print(f"  * {k.replace('_', ' ').title():<28}: {v}")
        print("=" * 70 + "\n")
        return

    if args.daemon:
        run_daemon(interval_hours=args.interval_hours, period=args.period, force=args.force)
    else:
        run_pipeline(period_str=args.period, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
