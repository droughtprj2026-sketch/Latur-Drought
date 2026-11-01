# -*- coding: utf-8 -*-
"""Backwards-compatible entry point for the scientific figure suite.

The original single-file script has been replaced by a structured package:

    scripts/analysis/scientific_suite/
        config.py            paths, index registry, palette (from common.classify)
        data.py              panel loading, availability grids, seasons
        stats.py             Pearson / Spearman / OLS / Mann-Kendall / Sen's slope
        grids.py             reusable month x year, tehsil x year, correlation grids
        plots_availability.py
        plots_correlation.py
        plots_heatmaps.py
        plots_relationships.py
        plots_distributions.py
        plots_temporal.py
        plots_spatial.py
        report.py            INDEX.md and index.html gallery
        run.py               orchestration

Output is written to a structured folder tree:

    output/figures/scientific_suite/
        01_image_availability/
        02_correlation/
        03_heatmaps/
        04_index_relationships/
        05_distributions/
        06_temporal_analysis/
        07_spatial_analysis/
        08_statistics_tables/
        INDEX.md
        index.html

This file is kept so existing documentation and commands keep working.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from scientific_suite.run import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
