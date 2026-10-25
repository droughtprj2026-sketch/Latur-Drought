# -*- coding: utf-8 -*-
"""
Compatibility entry point for the scheduled workflow.

The real work lives in scripts/realtime_update.py. This wrapper only exists so
older docs and local habits (`python scripts/run_realtime_pipeline_sync.py`) keep working.

The previous version of this file reported success regardless of outcome, overwrote
latest_status.json with "operational", never touched village_timeseries.json, and wrote
a hard-coded record (village "Latur", cloud 5.2 %) to Supabase. None of that is kept.

  python scripts/run_realtime_pipeline_sync.py [--period YYYY-MM ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from realtime_update import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
