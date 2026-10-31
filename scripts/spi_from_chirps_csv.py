# -*- coding: utf-8 -*-
"""
Compute SPI-1/3/6/12 from the village-level CHIRPS CSV that chirps_gee.py
produces. This bridges the real-time GEE path (zonal rainfall) to the
CDI composite, which needs SPI.

Reads:  data/processed/csv/chirps_village_monthly.csv
Writes: data/processed/csv/SPI_Latur_district_monthly.csv

The output matches the column format that composite_cdi.py expects so it
can supplement the village-level SPI when local rasters are unavailable.

Usage:
    python spi_from_chirps_csv.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "data" / "processed"))
SPI_SCALES = (1, 3, 6, 12)

CHIRPS_CSV = OUT / "csv" / "chirps_village_monthly.csv"
OUT_CSV = OUT / "csv" / "SPI_Latur_district_monthly.csv"


def _rolling_sum(series: pd.Series, k: int) -> pd.Series:
    if k == 1:
        return series.copy()
    return series.rolling(window=k, min_periods=k).sum()


def compute_spi_for_series(rain: pd.Series, k: int) -> pd.Series:
    """Compute SPI-k for a monthly rainfall series using per-calendar-month
    gamma fitting with Stagge (2015) zero correction."""
    from scipy import stats as sp_stats

    accum = _rolling_sum(rain, k)
    spi = pd.Series(np.nan, index=rain.index)
    months_arr = pd.Series([int(d.split("-")[1]) for d in rain.index],
                           index=rain.index)

    for cal_month in range(1, 13):
        mask = months_arr == cal_month
        cal_accum = accum[mask].dropna()
        if len(cal_accum) < 3:
            continue

        vals = cal_accum.values
        zeros = vals[vals <= 0]
        nonzero = vals[vals > 0]
        q = len(zeros) / len(vals)

        if len(nonzero) < 3:
            continue

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                alpha, _, beta = sp_stats.gamma.fit(nonzero, floc=0)
            except Exception:
                continue

        for idx in cal_accum.index:
            x = accum[idx]
            if np.isnan(x):
                continue
            if x <= 0:
                H = q / 2.0
            else:
                G = sp_stats.gamma.cdf(x, alpha, scale=beta)
                H = q + (1.0 - q) * G
            H = np.clip(H, 1e-4, 1.0 - 1e-4)
            spi.loc[idx] = float(sp_stats.norm.ppf(H))

    return spi


def main():
    if not CHIRPS_CSV.exists():
        print(f"  CHIRPS CSV not found: {CHIRPS_CSV}")
        print("  Run chirps_gee.py first to fetch rainfall from GEE.")
        return

    print("[1] reading CHIRPS village monthly rainfall ...")
    df = pd.read_csv(CHIRPS_CSV)
    n_villages = df["village"].nunique() if "village" in df.columns else 0
    print(f"  {len(df)} rows, {n_villages} villages")

    print("[2] computing district-mean monthly rainfall (averaging all villages) ...")
    district = (df.groupby("period")["rain_mm"]
                  .mean()
                  .reset_index()
                  .rename(columns={"rain_mm": "rain_mm_mean"})
                  .sort_values("period"))
    district = district.set_index("period")

    print("[3] computing SPI-1/3/6/12 from district-mean rainfall ...")
    rain = district["rain_mm_mean"]
    for k in SPI_SCALES:
        col = f"SPI{k}"
        district[col] = compute_spi_for_series(rain, k)
        valid = district[col].notna().sum()
        if valid > 0:
            lo = district[col].min()
            hi = district[col].max()
            print(f"  SPI-{k}: {valid} values  (range {lo:+.2f} to {hi:+.2f})")
        else:
            print(f"  SPI-{k}: no valid values (need >= {k} months + 3 cal-month samples)")

    print("[4] writing district SPI CSV ...")
    out = district.reset_index().rename(columns={"period": "date"})
    out["year"] = out["date"].str[:4].astype(int)
    out["month"] = out["date"].str[5:7].astype(int)
    cols = ["date", "year", "month", "rain_mm_mean",
            "SPI1", "SPI3", "SPI6", "SPI12"]
    out = out[[c for c in cols if c in out.columns]]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"  wrote {OUT_CSV} ({len(out)} rows)")

    print("\nDone.")


if __name__ == "__main__":
    main()
