# -*- coding: utf-8 -*-
"""Structured scientific visualization suite for the Latur drought system.

The suite is split by analytical theme so figures land in their own folders:

    01_image_availability       sampling completeness per source / tehsil / month
    02_correlation              Pearson and Spearman across every index pair
    03_heatmaps                 every index rendered as month x year and tehsil x year
    04_index_relationships      scatter regressions, response lags, index agreement
    05_distributions            per-index distributions, class separation, CDI/NDVI context
    06_temporal_analysis        Hovmoller, annual trends, episodes, trends per tehsil
    07_spatial_analysis         village choropleths, annual atlas, tehsil vulnerability
    08_statistics_tables        machine-readable CSV results

Run with:
    python scripts/analysis/generate_scientific_visualizations.py
"""
from __future__ import annotations

__all__ = ["config", "data", "stats", "style", "report", "run"]

__version__ = "1.0.0"
