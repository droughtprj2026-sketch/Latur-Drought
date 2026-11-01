# -*- coding: utf-8 -*-
"""Entry point for the structured scientific visualization suite.

Usage
-----
    python scripts/analysis/generate_scientific_visualizations.py
    python scripts/analysis/generate_scientific_visualizations.py --only correlation heatmap
    python scripts/analysis/generate_scientific_visualizations.py --list

All figures are written under ``output/figures/scientific_suite/<section>/`` and
indexed in ``INDEX.md`` and ``index.html``.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from . import data as D
from . import report
from . import stats as S
from . import style as ST
from . import plots_availability as A
from . import plots_correlation as K
from . import plots_distributions as DI
from . import plots_heatmaps as H
from . import plots_relationships as R
from . import plots_spatial as SP
from . import plots_temporal as T

SECTION_RUNNERS = {
    "availability": lambda p: A.build(p),
    "correlation": lambda p: K.build(p),
    "heatmap": lambda p: H.build(p),
    "relationships": lambda p: R.build(p),
    "distribution": lambda p: DI.build(p),
    "temporal": lambda p: T.build(p),
    "spatial": lambda p: SP.build(p),
}


# --------------------------------------------------------------------------
# Machine-readable tables
# --------------------------------------------------------------------------
def statistics_tables(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}

    # Correlation matrices, full precision, labelled.
    for method in ("pearson", "spearman"):
        corr = S.corr_matrix(panel, C.CORE_COLUMNS, method)
        corr.index = [C.COL[c].label if c in C.COL else c for c in corr.index]
        corr.columns = [C.COL[c].label if c in C.COL else c for c in corr.columns]
        tables[f"correlation_{method}_matrix"] = corr.round(4).reset_index(names="index")

    pvalues = S.corr_pvalues(panel, C.CORE_COLUMNS, "pearson")
    pvalues.index = [C.COL[c].label if c in C.COL else c for c in pvalues.index]
    pvalues.columns = [C.COL[c].label if c in C.COL else c for c in pvalues.columns]
    tables["correlation_pearson_pvalues"] = pvalues.round(6).reset_index(names="index")

    # Availability per tehsil and year, per source.
    for label, column in A.SOURCES.items():
        slug = column.lower()
        table = D.availability_table(panel, column)
        if not table.empty:
            tables[f"availability_{slug}_tehsil_year"] = table.round(3)

    tables["availability_summary"] = D.source_availability_summary(panel, A.SOURCES)

    # Tehsil summary.
    scored = panel[panel["dclass"].isin(C.CLASS_ORDER)]
    tehsil = panel.groupby("tehsil").agg(
        villages=("village_idx", "nunique"),
        village_months=("period", "size"),
        mean_cdi=(C.CDI_COLUMN, "mean"),
        max_cdi=(C.CDI_COLUMN, "max"),
        mean_spi3=("SPI3", "mean"),
        mean_spi12=("SPI12", "mean"),
        mean_rain_mm=("Rain_mm", "mean"),
        mean_ndvi=("NDVI", "mean"),
        mean_nsmi=("NSMI", "mean"),
    )
    drought = scored[scored["dclass"].isin(C.DROUGHT_CODES)].groupby("tehsil").size()
    severe = scored[scored["dclass"].isin(["D2", "D3", "D4"])].groupby("tehsil").size()
    tehsil["drought_frequency_pct"] = (100.0 * drought / scored.groupby("tehsil").size()).round(2)
    tehsil["severe_frequency_pct"] = (100.0 * severe / scored.groupby("tehsil").size()).round(2)

    ndvi_avail = D.availability_table(panel, "NDVI").groupby("tehsil")["pct"].mean()
    tehsil["ndvi_coverage_pct"] = ndvi_avail.round(2)

    trend_rows = []
    annual = panel.dropna(subset=[C.CDI_COLUMN]).pivot_table(
        index="year", columns="tehsil", values=C.CDI_COLUMN, aggfunc="mean"
    )
    for name in annual.columns:
        y = annual[name].dropna()
        mk = S.mann_kendall(y.to_numpy())
        ss = S.sens_slope(y.to_numpy(), index=y.index.to_numpy())
        trend_rows.append({"tehsil": name, "cdi_sens_slope": ss["slope"], "mk_p": mk["p"],
                           "trend": mk["trend"]})
    tehsil = tehsil.join(pd.DataFrame(trend_rows).set_index("tehsil"))
    tables["tehsil_summary"] = tehsil.reset_index().round(4)

    # Annual summary.
    yearly = panel.groupby("year").agg(
        mean_cdi=(C.CDI_COLUMN, "mean"),
        mean_spi1=("SPI1", "mean"),
        mean_spi3=("SPI3", "mean"),
        mean_spi6=("SPI6", "mean"),
        mean_spi12=("SPI12", "mean"),
        mean_rain_mm=("Rain_mm", "mean"),
        total_rain_mm=("Rain_mm", "sum"),
        mean_ndvi=("NDVI", "mean"),
        mean_vci=("VCI", "mean"),
        mean_nsmi=("NSMI", "mean"),
    )
    yearly["scored_village_months"] = scored.groupby("year").size()
    yearly["drought_share_pct"] = (
        100.0 * scored[scored["dclass"].isin(C.DROUGHT_CODES)].groupby("year").size()
        / scored.groupby("year").size()
    )
    yearly["severe_share_pct"] = (
        100.0 * scored[scored["dclass"].isin(["D2", "D3", "D4"])].groupby("year").size()
        / scored.groupby("year").size()
    )
    tables["annual_summary"] = yearly.reset_index().round(4)

    # Village summary.
    village = panel.groupby(["village_idx", "village", "tehsil"]).agg(
        months=("period", "size"),
        mean_cdi=(C.CDI_COLUMN, "mean"),
        p90_cdi=(C.CDI_COLUMN, lambda s: s.quantile(0.90)),
        mean_ndvi=("NDVI", "mean"),
        mean_nsmi=("NSMI", "mean"),
    )
    drought_v = scored[scored["dclass"].isin(C.DROUGHT_CODES)].groupby("village_idx").size()
    village["drought_months"] = drought_v.reindex(village.index.get_level_values("village_idx")).to_numpy()
    village["drought_frequency_pct"] = (
        100.0 * village["drought_months"] / village["months"]
    ).round(2)
    tables["village_summary"] = village.reset_index().round(4)

    # Formal tests.
    tests = []
    for column in ("SPI3", "NSMI", "NDVI", "VCI", C.CDI_COLUMN):
        row = S.kruskal_by(scored, column, "dclass")
        tests.append({"test": "Kruskal-Wallis across drought classes", "variable": C.COL[column].label,
                      "statistic": round(row["h"], 3), "p_value": row["p"], "groups": row["groups"]})
    for column in ("SPI3", "NDVI", "NSMI", C.CDI_COLUMN):
        row = S.kruskal_by(panel, column, "tehsil")
        tests.append({"test": "Kruskal-Wallis across tehsils", "variable": C.COL[column].label,
                      "statistic": round(row["h"], 3), "p_value": row["p"], "groups": row["groups"]})
    for column in ("SPI3", "NDVI", "NSMI", C.CDI_COLUMN):
        row = S.normality(panel[column])
        tests.append({"test": row["test"], "variable": C.COL[column].label,
                      "statistic": round(row["w"], 4), "p_value": row["p"], "groups": row["n"]})
    tables["statistical_tests"] = pd.DataFrame(tests)

    return tables


def write_tables(tables: dict[str, pd.DataFrame]) -> int:
    out = C.section_dir("tables")
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    for name, frame in tables.items():
        if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        path = out / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8")
        print(f"  [tables] {path.name}  ({len(frame)} rows)")
        written += 1
    return written


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def run(sections: list[str] | None = None) -> dict:
    ST.apply_style()
    C.ensure_dirs()
    report.clear()

    panel = D.load_panel()
    district = D.district_name()
    span = D.time_span_label(panel)
    meta = {
        "district": district,
        "period": f"{panel['period'].min()} to {panel['period'].max()} ({span})",
        "villages": D.n_villages(panel),
        "tehsils": int(panel["tehsil"].nunique()),
        "rows": f"{len(panel):,}",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "panel": str(C.PANEL_CSV.relative_to(C.ROOT)),
    }

    print("=" * 72)
    print("LATUR DROUGHT - SCIENTIFIC VISUALIZATION SUITE")
    print(f"  panel      : {meta['panel']}")
    print(f"  study area : {district}")
    print(f"  period     : {meta['period']}")
    print(f"  villages   : {meta['villages']}   tehsils: {meta['tehsils']}   rows: {meta['rows']}")
    print(f"  output     : {C.OUT_ROOT}")
    print("=" * 72)

    selected = sections or list(SECTION_RUNNERS)
    unknown = [s for s in selected if s not in SECTION_RUNNERS]
    if unknown:
        raise SystemExit(f"Unknown section(s): {unknown}. Choose from {list(SECTION_RUNNERS)}")

    results: dict[str, pd.DataFrame] = {}
    for name in selected:
        print(f"\n[{name}]")
        produced = SECTION_RUNNERS[name](panel) or {}
        for key, frame in produced.items():
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                results[key] = frame

    print("\n[tables]")
    tables = statistics_tables(panel)
    tables.update(results)
    n_tables = write_tables(tables)

    md = report.write_markdown(meta)
    html = report.write_html(meta)

    print("\n" + "=" * 72)
    print(f"  figures : {len(report.figures())}")
    print(f"  tables  : {n_tables}")
    print(f"  index   : {md}")
    print(f"  gallery : {html}")
    print("=" * 72)
    return {"meta": meta, "figures": len(report.figures()), "tables": n_tables}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scientific visualization suite for the drought pipeline.")
    parser.add_argument("--only", nargs="+", metavar="SECTION",
                        help=f"subset of sections to render: {', '.join(SECTION_RUNNERS)}")
    parser.add_argument("--list", action="store_true", help="list sections and exit")
    args = parser.parse_args(argv)

    if args.list:
        for key, value in C.SECTIONS.items():
            print(f"{key:15s} -> {value}")
        return 0

    run(args.only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
