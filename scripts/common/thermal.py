# -*- coding: utf-8 -*-
"""
Thermal and soil-moisture indices (pure pandas/numpy; no Earth Engine here).

  TCI  Temperature Condition Index  = 100 * (LSTmax - LST) / (LSTmax - LSTmin)   (Kogan 1995)
       high LST -> low TCI -> thermal stress
  SMI  Soil Moisture Index          = 100 * (VV - VVmin) / (VVmax - VVmin)   (Sentinel-1 backscatter, relative)
       low soil moisture -> low SMI -> agricultural dryness
  VHI  Vegetation Health Index      = 0.5 * VCI + 0.5 * TCI                        (Kogan 1995)

LSTmin/max and SMmin/max are the village's own envelope (5th..95th percentile by default) for
the same calendar month over the record, the same construction VCI uses. An index is issued only
when the village has at least `min_years` values for that calendar month; otherwise it is left
empty (never filled), and the composite drops the input.

The thermal table has one row per (village_idx, date): LST (deg C, Landsat 8/9) and VV (dB, Sentinel-1).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

THERMAL_CSV = Path(__file__).resolve().parent.parent.parent / "output" / "thermal" / "village_monthly_lst_sm.csv"
COLUMNS = ["village_idx", "date", "LST", "VV", "lst_images", "vv_images"]


def load_thermal(path: Path = THERMAL_CSV) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=COLUMNS)
    t = pd.read_csv(path)
    t["date"] = t["date"].astype(str)
    return t


def save_thermal(t: pd.DataFrame, path: Path = THERMAL_CSV) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    t.sort_values(["village_idx", "date"]).to_csv(path, index=False, columns=COLUMNS)


def _envelope(t: pd.DataFrame, col: str, lo_pct: float, hi_pct: float) -> pd.DataFrame:
    d = t[["village_idx", "date", col]].dropna().copy()
    d["month"] = d["date"].str.slice(5, 7).astype(int)
    g = d.groupby(["village_idx", "month"])[col]
    return pd.DataFrame({
        "lo": g.quantile(lo_pct / 100.0), "hi": g.quantile(hi_pct / 100.0), "n": g.count(),
    }).reset_index()


def _position(values: pd.Series, env: pd.DataFrame, keys: pd.DataFrame, min_years: int,
              invert: bool) -> np.ndarray:
    e = keys.merge(env, on=["village_idx", "month"], how="left")
    rng = (e["hi"] - e["lo"]).to_numpy()
    v = values.to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        pos = (e["hi"].to_numpy() - v) / rng if invert else (v - e["lo"].to_numpy()) / rng
    out = np.clip(100.0 * pos, 0.0, 100.0)
    bad = ~(rng > 1e-9) | ~(e["n"].to_numpy() >= min_years) | ~np.isfinite(v)
    out[bad] = np.nan
    return out


def add_thermal_indices(df: pd.DataFrame, thermal: pd.DataFrame, tcfg: dict) -> pd.DataFrame:
    """Attach LST, VV, TCI, SMI (and VHI = w*VCI + w*TCI) to a panel with village_idx/date/VCI."""
    out = df.drop(columns=[c for c in ("LST", "VV", "TCI", "SMI") if c in df.columns]).copy()
    out["date"] = out["date"].astype(str)
    th = thermal[["village_idx", "date", "LST", "VV"]].copy()
    th["date"] = th["date"].astype(str)
    out = out.merge(th, on=["village_idx", "date"], how="left")

    lo_p, hi_p, my = tcfg["envelope_low_pct"], tcfg["envelope_high_pct"], int(tcfg["min_years"])
    keys = pd.DataFrame({"village_idx": out["village_idx"].to_numpy(),
                         "month": out["date"].str.slice(5, 7).astype(int).to_numpy()})
    out["TCI"] = _position(out["LST"], _envelope(thermal, "LST", lo_p, hi_p), keys, my, invert=True)
    out["SMI"] = _position(out["VV"], _envelope(thermal, "VV", lo_p, hi_p), keys, my, invert=False)

    w_v, w_t = float(tcfg["vhi_weight_vci"]), float(tcfg["vhi_weight_tci"])
    out["VHI"] = w_v * out["VCI"] + w_t * out["TCI"]       # NaN unless both halves exist
    return out


def coverage(thermal: pd.DataFrame) -> dict:
    if thermal.empty:
        return {"months": 0, "first": None, "last": None}
    return {"months": int(thermal["date"].nunique()), "first": thermal["date"].min(),
            "last": thermal["date"].max()}
