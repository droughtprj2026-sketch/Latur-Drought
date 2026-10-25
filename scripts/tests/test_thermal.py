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
