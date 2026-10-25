# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from common.thermal import add_thermal_indices  # noqa: E402
from common.village_cdi import _load_cfg  # noqa: E402

CFG = _load_cfg("config/composite_thermal.yaml")
T = CFG["thermal"]


def table(years, lst, sm):
    return pd.DataFrame({"village_idx": 1, "date": [f"{y}-05" for y in years], "LST": lst, "VV": sm})


def panel(years, vci):
    return pd.DataFrame({"village_idx": 1, "date": [f"{y}-05" for y in years], "VCI": vci})


def test_hottest_month_has_tci_zero_and_coolest_has_100():
    years = list(range(2016, 2027))
    lst = np.linspace(30, 40, len(years))                  # 2016 coolest, 2026 hottest
    out = add_thermal_indices(panel(years, [50.0] * len(years)), table(years, lst, np.linspace(.1, .3, len(years))), T)
    assert out["TCI"].iloc[0] == pytest.approx(100.0)       # cool -> no thermal stress
    assert out["TCI"].iloc[-1] == pytest.approx(0.0)        # hot -> maximum stress
    assert out["SMI"].iloc[0] == pytest.approx(0.0)         # driest soil
    assert out["SMI"].iloc[-1] == pytest.approx(100.0)


def test_vhi_is_half_vci_plus_half_tci():
    years = list(range(2016, 2027))
    lst = np.linspace(30, 40, len(years))
    out = add_thermal_indices(panel(years, [40.0] * len(years)), table(years, lst, [.2] * len(years)), T)
    assert out["VHI"].iloc[0] == pytest.approx(0.5 * 40 + 0.5 * 100)


def test_index_withheld_with_too_few_years():
    years = [2024, 2025, 2026]                               # below min_years
    out = add_thermal_indices(panel(years, [50.0] * 3), table(years, [31, 33, 35], [.1, .2, .3]), T)
    assert out["TCI"].isna().all() and out["SMI"].isna().all() and out["VHI"].isna().all()


def test_missing_lst_leaves_vhi_empty_not_vci():
    years = list(range(2016, 2027))
    lst = [np.nan] * len(years)
    out = add_thermal_indices(panel(years, [50.0] * len(years)), table(years, lst, np.linspace(.1, .3, len(years))), T)
    assert out["VHI"].isna().all()                           # never silently falls back to VCI
    assert out["SMI"].notna().all()


def test_thermal_formula_weights_and_inputs():
    w = CFG["weights"]
    assert w == {"SPI": 0.25, "PCI": 0.10, "SMI": 0.20, "VHI": 0.30, "NDVI": 0.15}
    assert sum(w.values()) == pytest.approx(1.0)
    assert "TCI" not in w and "VCI" not in w and "EVI" not in w   # no double counting, no broken EVI
    assert CFG["thresholds"] == _load_cfg()["thresholds"]          # same class cut-offs as the default formula


def test_thermal_config_without_panel_is_an_error(monkeypatch, tmp_path):
    import common.paths as paths
    monkeypatch.setattr(paths, "PANEL_THERMAL", tmp_path / "missing.csv")
    with pytest.raises(FileNotFoundError):
        paths.active_panel(CFG)


def test_fixture_is_refused_without_explicit_opt_in(monkeypatch, capsys):
    import realtime_update as ru
    monkeypatch.delenv("ALLOW_SYNTHETIC_FIXTURE", raising=False)
    monkeypatch.setattr(sys, "argv", ["realtime_update.py", "--fixture", "x.json"])
    assert ru.main() == 3
    assert "Refusing" in capsys.readouterr().err


def test_no_earth_engine_project_is_baked_into_code():
    import re
    for f in (ROOT / "scripts").rglob("*.py"):
        if "tests" in f.parts:
            continue
        assert not re.search(r"igneous-effort|ee-latur|ee-drought", f.read_text(encoding="utf-8")), f


def test_thermal_sources_are_field_scale_not_modis_or_smap():
    t = CFG["thermal"]
    assert all("LANDSAT" in c for c in t["lst_collections"])
    assert t["vv_collection"] == "COPERNICUS/S1_GRD"
    assert "MODIS" not in str(t) and "SMAP" not in str(t)


def test_output_check_flags_implausible_values():
    import check_outputs as co
    ok = pd.DataFrame({"LST": [25.0, 41.0], "VV": [-12.0, -8.0], "TCI": [10.0, 90.0]})
    assert co.check_bounds(ok) == []
    bad = pd.DataFrame({"LST": [25.0, 330.0], "VV": [-12.0, 40.0]})   # kelvin left in, dB sign error
    flagged = co.check_bounds(bad)
    assert len(flagged) == 2 and any(f.startswith("LST") for f in flagged)


# ---- Earth Engine batch runner: parallel, retried, and never waits forever ---------------
def test_run_batches_returns_results_in_order_and_retries():
    from common.gee import run_batches
    calls = {"n": 0}

    def fn(part):
        calls["n"] += 1
        if part == [2] and calls["n"] < 4:       # batch 2 fails the first time it is tried
            raise RuntimeError("transient")
        return {"v": part[0] * 10}

    import time as _t
    orig = _t.sleep
    _t.sleep = lambda s: None
    try:
        out = run_batches([[0], [1], [2], [3]], fn, "t", log=lambda *_: None, workers=2, retries=3)
    finally:
        _t.sleep = orig
    assert [o["v"] for o in out] == [0, 10, 20, 30]


def test_run_batches_gives_up_after_retries():
    import time as _t
    from common.gee import run_batches
    orig = _t.sleep
    _t.sleep = lambda s: None
    try:
        with pytest.raises(RuntimeError, match="failed 2 times"):
            run_batches([[0]], lambda p: (_ for _ in ()).throw(ValueError("boom")), "t",
                        log=lambda *_: None, retries=2)
    finally:
        _t.sleep = orig


def test_run_batches_hits_the_deadline_instead_of_hanging():
    import threading
    from common.gee import run_batches
    block = threading.Event()
    with pytest.raises(TimeoutError, match="not finished"):
        run_batches([[0]], lambda p: block.wait(30), "t", log=lambda *_: None, deadline_s=1)
    block.set()


# ---- raw zonal archive -------------------------------------------------------------------
def test_zonal_archive_merges_sources_arriving_separately(tmp_path):
    from common.zonal import load_zonal, save_zonal, upsert_period, write_latest_json
    z = load_zonal(tmp_path / "none.csv")
    z = upsert_period(z, "2026-11", s2={"scenes": 5, "values": {"1": {"ndvi": 0.31, "evi": 0.42}, "2": {"ndvi": 0.2, "evi": 0.3}}})
    z = upsert_period(z, "2026-11", thermal={"lst_images": 3, "vv_images": 6,
                                             "values": {"1": {"lst": 33.0, "vv": -11.5}}})
    row1 = z[(z.village_idx == 1) & (z.date == "2026-11")].iloc[0]
    assert (row1.NDVI, row1.EVI, row1.LST, row1.VV) == (0.31, 0.42, 33.0, -11.5)
    row2 = z[(z.village_idx == 2) & (z.date == "2026-11")].iloc[0]
    assert row2.NDVI == 0.2 and pd.isna(row2.LST)                         # nothing invented for village 2
    save_zonal(z, tmp_path / "z.csv")
    assert len(load_zonal(tmp_path / "z.csv")) == 2
    out = write_latest_json(z, tmp_path / "zonal_latest.json")
    assert out["latest"] == {"ndvi": "2026-11", "evi": "2026-11", "lst": "2026-11", "vv": "2026-11"}
    assert out["villages"]["1"]["lst"] == 33.0 and "lst" not in out["villages"]["2"]


def test_indices_ready_needs_min_years_of_every_calendar_month():
    from common.thermal import indices_ready
    rows = [{"village_idx": 1, "date": f"{y}-{m:02d}", "LST": 30.0} for y in range(2016, 2021) for m in range(1, 13)]
    assert indices_ready(pd.DataFrame(rows), 5)
    assert not indices_ready(pd.DataFrame(rows[:-1]), 5)                  # December has only 4 years
    assert not indices_ready(pd.DataFrame(columns=["village_idx", "date", "LST"]), 5)
