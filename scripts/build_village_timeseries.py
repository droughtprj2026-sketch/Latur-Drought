# -*- coding: utf-8 -*-
"""
Generate an optimized, compact historical time-series JSON (2016-2026)
for all villages in Latur from outputs/Dashboard/drought_monitoring_master.csv.
Saves to frontend/public/data/village_timeseries.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MASTER_CSV = ROOT / "outputs" / "Dashboard" / "drought_monitoring_master.csv"
OUT_JSON = ROOT / "frontend" / "public" / "data" / "village_timeseries.json"


def build():
    if not MASTER_CSV.exists():
        raise FileNotFoundError(f"Missing master CSV: {MASTER_CSV}")

    print(f"Reading master CSV: {MASTER_CSV}...")
    df = pd.read_csv(MASTER_CSV, usecols=[
        "tehsil", "village", "observation_period",
        "composite_drought_score", "composite_drought_class",
        "monthly_rainfall_mm", "NDVI", "VHI", "VCI", "SPI_3"
    ])

    # Filter to village records only
    village_df = df[df["village"].notna() & (df["village"] != "")].copy()
    village_df["observation_period"] = village_df["observation_period"].astype(str)
    village_df = village_df.sort_values("observation_period")

    print(f"Aggregating time-series for {len(village_df)} rows...")

    ts_data: dict[str, list[dict]] = {}

    for _, r in village_df.iterrows():
        t = str(r["tehsil"]).strip()
        v = str(r["village"]).strip()
        key = f"{t}::{v}".lower()

        if key not in ts_data:
            ts_data[key] = []

        cdi = r["composite_drought_score"]
        rain = r["monthly_rainfall_mm"]
        ndvi = r["NDVI"]
        vhi = r["VHI"]
        vci = r["VCI"]
        spi3 = r["SPI_3"]
        cls_code = r["composite_drought_class"]

        ts_data[key].append({
            "p": r["observation_period"],
            "cdi": round(float(cdi), 3) if pd.notna(cdi) else None,
            "cls": str(cls_code) if pd.notna(cls_code) else "None",
            "rain": round(float(rain), 1) if pd.notna(rain) else None,
            "ndvi": round(float(ndvi), 3) if pd.notna(ndvi) else None,
            "vhi": round(float(vhi), 1) if pd.notna(vhi) else None,
            "vci": round(float(vci), 1) if pd.notna(vci) else None,
            "spi3": round(float(spi3), 2) if pd.notna(spi3) else None,
        })

    print(f"Indexed {len(ts_data)} unique villages.")
    print(f"Writing to {OUT_JSON}...")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(ts_data, f, separators=(",", ":"))

    size_mb = OUT_JSON.stat().st_size / (1024 * 1024)
    print(f"Successfully created {OUT_JSON} ({size_mb:.2f} MB).")


if __name__ == "__main__":
    build()
