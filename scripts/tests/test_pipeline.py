# -*- coding: utf-8 -*-
"""Regression tests for the pieces that silently went wrong before:
legend/threshold drift, village-count mismatch, CDI/SPI reproducibility, rain-table gaps."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from common import classify as py_classify  # noqa: E402
from common.village_cdi import DERIVED_COLUMNS, _load_cfg, score_new_period  # noqa: E402
import realtime_update as ru  # noqa: E402

PUB = ROOT / "frontend" / "public" / "data"
TS_SRC = (ROOT / "frontend" / "lib" / "classify.ts").read_text(encoding="utf-8")


# ---- one palette, one set of thresholds, everywhere ------------------------
def test_palette_matches_between_python_and_typescript():
    ts_colors = re.search(r"D_COLORS\s*=\s*\[(.*?)\]", TS_SRC, re.S).group(1)
    assert re.findall(r'"(#[0-9A-Fa-f]{6})"', ts_colors) == py_classify.D_COLORS


def test_cdi_thresholds_match_yaml_and_typescript():
    cfg = _load_cfg()
    yaml_max = [t["max"] for t in cfg["thresholds"]][:-1]
    body = re.search(r"function codeForCDI.*?\n}", TS_SRC, re.S).group(0)
    assert [float(x) for x in re.findall(r"v < ([0-9.]+)\)", body)] == yaml_max


def test_spi_thresholds_match_between_python_and_typescript():
    body = re.search(r"function codeForSPI.*?\n}", TS_SRC, re.S).group(0)
    ts = [float(x) for x in re.findall(r"v >= (-[0-9.]+)\)", body)]
    assert ts == py_classify.SPI_BOUNDS[1:5 + 1][:5]


def test_map_metric_bins_use_the_class_thresholds():
    m = (ROOT / "frontend" / "lib" / "metrics.ts").read_text(encoding="utf-8")
    cfg = _load_cfg()
    for t in [t["max"] for t in cfg["thresholds"]][:-1]:
        assert f"{t:.2f}" in m, f"CDI threshold {t} missing from frontend/lib/metrics.ts"


# ---- villages ----------------------------------------------------------------
def test_every_polygon_has_its_own_history():
    gj = json.loads((PUB / "latur_villages_latest.geojson").read_text(encoding="utf-8"))
    ids = [str(f["properties"]["id"]) for f in gj["features"]]
    assert len(ids) == len(set(ids)) == 954
    ts = json.loads((PUB / "village_timeseries.json").read_text(encoding="utf-8"))
    assert set(ids) == set(ts)
    by_tehsil = json.loads((PUB / "villages_by_tehsil.json").read_text(encoding="utf-8"))
    assert sum(len(v) for v in by_tehsil.values()) == 954


# ---- CDI / SPI are reproducible from the stored inputs ---------------------------
@pytest.fixture(scope="module")
def panel():
    p = pd.read_csv(ru.PANEL_PATHS[0])
    p["date"] = p["date"].astype(str)
    return p


def test_cdi_for_an_existing_month_is_reproduced_exactly(panel):
    cfg = _load_cfg()
    last = panel["date"].max()
    stored = panel[panel["date"] == last].reset_index(drop=True)
    new = stored.drop(columns=DERIVED_COLUMNS)
    out = score_new_period(panel[panel["date"] != last], new, cfg)
    a = out["composite_drought_score"].to_numpy(float)
    b = stored["composite_drought_score"].to_numpy(float)
    assert np.array_equal(np.isnan(a), np.isnan(b))
    assert np.nanmax(np.abs(a - b)) < 1e-9


def test_recomputed_spi_matches_stored_spi():
    rain = ru.load_rain_wide().iloc[:60]
    periods = ru._periods_of(rain)
    R = rain[periods].to_numpy(float)
    ref = pd.read_csv(ru.SPI_DIR / "SPI3_village_monthly.csv").iloc[:60][periods].to_numpy(float)
    mine = ru.compute_spi(R, periods, 3)
    ok = np.isfinite(mine) & np.isfinite(ref)
    assert ok.sum() > 1000
    assert np.abs(mine[ok] - ref[ok]).mean() < ru.MAX_SPI_DRIFT_MAE


def test_rain_table_refuses_a_gap():
    rain = ru.load_rain_wide()
    last = ru._periods_of(rain)[-1]
    gap = ru.next_period(ru.next_period(last))
    with pytest.raises(ValueError):
        ru.append_rain(rain, gap, {})
    with pytest.raises(ValueError):
        ru.append_rain(rain, last, {})


# ---- running forward from a chosen month (--since / PIPELINE_SINCE) ---------------------------
def test_due_periods_respects_the_since_floor():
    from datetime import date
    base = ru.due_periods(date(2026, 12, 5))
    floor = ru.due_periods(date(2026, 12, 5), since="2026-11")
    assert floor == ["2026-11", "2026-12"]
    assert len(base) > len(floor) and base[-2:] == floor
    assert ru.due_periods(date(2026, 12, 5), since="2020-01") == base      # a floor in the past changes nothing


def test_gap_months_are_left_empty_not_filled():
    rain = ru.load_rain_wide()
    last = ru.rain_months(rain)[-1]
    target = ru.next_period(ru.next_period(ru.next_period(last)))          # skip two months
    vals = {str(int(v) + 1): 5.0 for v in rain["vid"]}
    with pytest.raises(ValueError):
        ru.append_rain(rain, target, vals)                                 # default: a gap is an error
    out = ru.append_rain(rain, target, vals, allow_gap=True)
    gap = [ru.next_period(last), ru.next_period(ru.next_period(last))]
    assert all(out[g].isna().all() for g in gap)                           # empty, never invented
    assert ru.rain_months(out)[-1] == target and not set(gap) & set(ru.rain_months(out))
    spi3 = ru.compute_spi(out[ru._periods_of(out)].to_numpy(float), ru._periods_of(out), 3)
    assert np.isnan(spi3[:, -1]).all()                                     # SPI-3 window touches the gap -> empty
    spi1 = ru.compute_spi(out[ru._periods_of(out)].to_numpy(float), ru._periods_of(out), 1)
    assert np.isfinite(spi1[:, -1]).any()                                  # SPI-1 of the new month still works
