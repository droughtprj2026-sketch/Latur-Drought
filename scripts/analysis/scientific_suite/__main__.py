# -*- coding: utf-8 -*-
"""Allow `python -m scientific_suite` from scripts/analysis, or `python -m analysis.scientific_suite`."""
from __future__ import annotations

import sys

from .run import main

if __name__ == "__main__":
    sys.exit(main())
