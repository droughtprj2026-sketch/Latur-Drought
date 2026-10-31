# -*- coding: utf-8 -*-
"""
Village-level PCI + composite CDI. Pure pandas/numpy (no rasterio), so it
runs both in the batch raster build (build_village_indices.py) and in the
near-real-time update (realtime_update.py) on a plain GitHub runner.

The two entry points operate on a "panel": one row per (village_idx, period)
with columns village_idx, period, NDVI, EVI, VCI, VHI, Rain_mm, SPI1, SPI3,
SPI6, SPI12.  Weights, normalisation and thresholds come from
config/composite.yaml - never from this file.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

CFG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "composite.yaml"


def _load_cfg(path: str | Path | None = None) -> dict:
    """config/composite.yaml, or the file named by `path` / $COMPOSITE_CONFIG (repo-relative ok)."""
    import yaml
    p = Path(path or os.environ.get("COMPOSITE_CONFIG") or CFG_PATH)
    if not p.is_absolute():
        p = CFG_PATH.parent.parent / p
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


NORMALISERS = {
    "neg_clip": lambda s: (-s / 3.0).clip(0.0, 1.0),
    "inv_0_100": lambda s: (1.0 - s / 100.0).clip(0.0, 1.0),
}


def _robust_z(df: pd.DataFrame, col: str) -> pd.Series:
    """Per (village, calendar month) robust standardised anomaly -> 0..1.

    S = clip(-z / 3, 0, 1) with z = (x - median) / (1.4826 * MAD).
    A normal month (z ~ 0) gives S ~ 0 (None/D0); only deficits score.
    """
    keys = [df["village_idx"], df["month"]]
    med = df.groupby(["village_idx", "month"])[col].transform("median")
    mad = ((df[col] - med).abs()
           .groupby([df["village_idx"], df["month"]]).transform("median"))
    scale = 1.4826 * mad
    z = (df[col] - med) / scale.where(scale > 1e-9)
    return (-z / 3.0).clip(0.0, 1.0)


def _classify(v, thresholds) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "ND"
    for t in thresholds:
        if v < t["max"]:
            return t["code"]
    return "D4"


def _row_cdi(vals: dict, weights: dict, min_inputs: int):
    num = den = 0.0
    contrib = {}
    used = 0
    for name, s in vals.items():
        if s is None or (isinstance(s, float) and math.isnan(s)):
            continue
        w = weights.get(name)
        if w is None:
            continue
        num += w * s
        den += w
        contrib[name] = round(w * s, 4)
        used += 1
    if used < min_inputs or den == 0:
        return None, contrib
    return round(num / den, 4), contrib


def derive_indices(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    panel = panel.copy()
    panel["month"] = panel["period"].str.slice(5, 7).astype(int)
    g_rain = panel.groupby(["village_idx", "month"])["Rain_mm"]
    lo = g_rain.transform("min")
    hi = g_rain.transform("max")
    rng = hi - lo
    panel["PCI"] = ((100.0 * (panel["Rain_mm"] - lo) / rng)
                    .where(rng > 0.1)).clip(0.0, 100.0)
    return panel


def fuse_cdi(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    weights = cfg["weights"]
    min_inputs = int(cfg["min_inputs"])
    norm_cfg = cfg["normalisation"]
    spi_col = {"SPI-1": "SPI1", "SPI-3": "SPI3", "SPI-6": "SPI6",
               "SPI-12": "SPI12"}[cfg["spi_accumulation"]]

    panel = panel.copy()
    panel["SPI"] = panel.get(spi_col)
    sig = {}
    for name in weights:
        method = norm_cfg.get(name, {}).get("method", "robust_z")
        if name != "SPI" and name not in panel.columns:
            sig[name] = pd.Series(np.nan, index=panel.index)      # input not available: dropped from the fuse
        elif method == "robust_z":
            sig[name] = _robust_z(panel, name)
        elif method in NORMALISERS:
            sig[name] = NORMALISERS[method](panel[name])
        else:
            sig[name] = pd.Series(np.nan, index=panel.index)

    cdis, contribs = [], []
    for i in range(len(panel)):
        vals = {m: sig[m].iloc[i] for m in weights}
        cdi, contrib = _row_cdi(vals, weights, min_inputs)
        cdis.append(cdi)
        contribs.append(json.dumps(contrib))
    panel["composite_drought_score"] = pd.to_numeric(
        pd.Series(cdis, index=panel.index), errors="coerce")
    panel["component_contributions"] = contribs
    panel["composite_drought_class"] = [
        _classify(v, cfg["thresholds"]) for v in panel["composite_drought_score"]]
    panel["formula_version"] = cfg["formula_version"]
    panel["SPI_scaled"] = np.clip((panel["SPI3"] + 2.0) / 4.0 * 100.0, 0, 100)
    panel["data_quality_status"] = np.where(
        panel["composite_drought_score"].notna(), "success", "pending")
    return panel


DERIVED_COLUMNS = ["PCI", "SPI_scaled", "component_contributions", "composite_drought_score",
                   "composite_drought_class", "formula_version", "data_quality_status"]


def score_new_period(history: pd.DataFrame, new: pd.DataFrame, cfg: dict,
                     include_self: bool = True) -> pd.DataFrame:
    """PCI + CDI for freshly ingested rows, against the FROZEN history.

    The batch `derive_indices` + `fuse_cdi` standardise every month against the whole
    record, so adding a month would nudge every older month of the same calendar month.
    For operations stored history is never rewritten: only the new rows are scored.
    `include_self=True` reproduces the batch convention (a month's own value is part of the
    reference it is judged against); with it, scoring an existing month reproduces its stored
    score exactly. Note the reference holds only ~7 values per village and calendar month, so
    a month's class is sensitive to that convention (see docs/DATA_ACCURACY_AUDIT.md).
    """
    weights, min_inputs = cfg["weights"], int(cfg["min_inputs"])
    norm_cfg = cfg["normalisation"]
    spi_col = {"SPI-1": "SPI1", "SPI-3": "SPI3", "SPI-6": "SPI6", "SPI-12": "SPI12"}[cfg["spi_accumulation"]]

    hist = history.copy()
    hist["month"] = hist["date"].astype(str).str.slice(5, 7).astype(int)
    new = new.copy()
    key = ["village_idx", "month"]

    rain_ref = pd.concat([hist[key + ["Rain_mm"]], new[key + ["Rain_mm"]]]) if include_self else hist[key + ["Rain_mm"]]
    g = rain_ref.groupby(key)["Rain_mm"]
    lo, hi = g.min().rename("lo"), g.max().rename("hi")
    ref = new[key].merge(pd.concat([lo, hi], axis=1).reset_index(), on=key, how="left")
    rng = ref["hi"] - ref["lo"]
    with np.errstate(divide="ignore", invalid="ignore"):
        new["PCI"] = ((100.0 * (new["Rain_mm"].to_numpy() - ref["lo"].to_numpy()) / rng.to_numpy())
                      .clip(0.0, 100.0))
    new.loc[~(rng.to_numpy() > 0.1), "PCI"] = np.nan

    new["SPI"] = new[spi_col]
    if include_self:
        shared = [c for c in hist.columns if c in new.columns]
        hist = pd.concat([hist[shared], new[shared]], ignore_index=True)
    sig: dict[str, pd.Series] = {}
    for name in weights:
        method = norm_cfg.get(name, {}).get("method", "robust_z")
        if name != "SPI" and (name not in hist.columns or name not in new.columns):
            sig[name] = pd.Series(np.nan, index=new.index)
        elif method == "robust_z":
            col = hist[name]
            med = col.groupby([hist["village_idx"], hist["month"]]).median().rename("med")
            mad = ((col - col.groupby([hist["village_idx"], hist["month"]]).transform("median")).abs()
                   .groupby([hist["village_idx"], hist["month"]]).median().rename("mad"))
            r = new[key].merge(pd.concat([med, mad], axis=1).reset_index(), on=key, how="left")
            scale = 1.4826 * r["mad"]
            z = (new[name].to_numpy() - r["med"].to_numpy()) / scale.where(scale > 1e-9).to_numpy()
            sig[name] = pd.Series((-z / 3.0), index=new.index).clip(0.0, 1.0)
        elif method in NORMALISERS:
            sig[name] = NORMALISERS[method](new[name] if name in new else new["SPI"])
        else:
            sig[name] = pd.Series(np.nan, index=new.index)

    cdis, contribs = [], []
    for i in range(len(new)):
        cdi, contrib = _row_cdi({m: sig[m].iloc[i] for m in weights}, weights, min_inputs)
        cdis.append(cdi)
        contribs.append(json.dumps(contrib))
    new["composite_drought_score"] = pd.to_numeric(pd.Series(cdis, index=new.index), errors="coerce")
    new["component_contributions"] = contribs
    new["composite_drought_class"] = [_classify(v, cfg["thresholds"]) for v in new["composite_drought_score"]]
    new["formula_version"] = cfg["formula_version"]
    new["SPI_scaled"] = np.clip((new["SPI3"] + 2.0) / 4.0 * 100.0, 0, 100)
    new["data_quality_status"] = np.where(new["composite_drought_score"].notna(), "success", "pending")
    cols = [c for c in history.columns if c != "month" or "month" in new.columns]
    return new.reindex(columns=cols)
