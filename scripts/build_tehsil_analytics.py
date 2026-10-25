# -*- coding: utf-8 -*-
"""
Generate comprehensive Tehsil-wise analytics, correlation matrices, and risk rankings
from outputs/Dashboard/drought_monitoring_master.csv to power the executive analytics tab.
Saves to frontend/public/data/tehsil_analytics.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MASTER_CSV = ROOT / "outputs" / "Dashboard" / "drought_monitoring_master.csv"
OUT_JSON = ROOT / "frontend" / "public" / "data" / "tehsil_analytics.json"


def build():
    df = pd.read_csv(MASTER_CSV)
    df["date"] = df["observation_period"].astype(str)

    # 1. Latest Period Tehsil Summary
    latest_p = df["observation_period"].max()
    latest_v = df[(df["observation_period"] == latest_p) & df["village"].notna() & (df["village"] != "")]

    tehsil_ranking = []
    for tehsil, g in latest_v.groupby("tehsil"):
        total = len(g)
        d0_cnt = int((g["composite_drought_class"] == "D0").sum())
        d1_cnt = int((g["composite_drought_class"] == "D1").sum())
        d2_cnt = int((g["composite_drought_class"] == "D2").sum())
        d3_cnt = int((g["composite_drought_class"] == "D3").sum())
        d4_cnt = int((g["composite_drought_class"] == "D4").sum())
        drought_cnt = d0_cnt + d1_cnt + d2_cnt + d3_cnt + d4_cnt
        normal_cnt = total - drought_cnt

        avg_cdi = round(float(g["composite_drought_score"].mean()), 3) if g["composite_drought_score"].notna().any() else 0.0
        avg_ndvi = round(float(g["NDVI"].mean()), 3) if g["NDVI"].notna().any() else 0.0
        avg_vci = round(float(g["VCI"].mean()), 1) if g["VCI"].notna().any() else 0.0
        avg_vhi = round(float(g["VHI"].mean()), 1) if g["VHI"].notna().any() else 0.0
        avg_spi3 = round(float(g["SPI_3"].mean()), 2) if g["SPI_3"].notna().any() else 0.0

        tehsil_ranking.append({
            "tehsil": tehsil,
            "villages": total,
            "avg_cdi": avg_cdi,
            "avg_ndvi": avg_ndvi,
            "avg_vci": avg_vci,
            "avg_vhi": avg_vhi,
            "avg_spi3": avg_spi3,
            "drought_villages": drought_cnt,
            "normal_villages": normal_cnt,
            "d2_plus": d2_cnt + d3_cnt + d4_cnt,
            "drought_pct": round((drought_cnt / total) * 100, 1) if total > 0 else 0,
        })

    tehsil_ranking.sort(key=lambda x: x["avg_cdi"], reverse=True)

    # 2. Historical Tehsil Progression (Annual average CDI per Tehsil)
    annual_tehsil = []
    df_v = df[df["village"].notna() & (df["village"] != "")].copy()
    for (year, tehsil), g in df_v.groupby(["year", "tehsil"]):
        mean_cdi = g["composite_drought_score"].mean()
        if pd.notna(mean_cdi):
            annual_tehsil.append({
                "year": int(year),
                "tehsil": str(tehsil),
                "cdi": round(float(mean_cdi), 3),
            })

    # 3. Correlation Matrix across indices
    cols = ["monthly_rainfall_mm", "SPI_1", "SPI_3", "SPI_6", "NDVI", "VCI", "VHI", "composite_drought_score"]
    corr_df = df[cols].corr().round(3)
    corr_matrix = []
    labels = {
        "monthly_rainfall_mm": "Rainfall",
        "SPI_1": "SPI-1",
        "SPI_3": "SPI-3",
        "SPI_6": "SPI-6",
        "NDVI": "NDVI",
        "VCI": "VCI",
        "VHI": "VHI",
        "composite_drought_score": "CDI",
    }
    for c1 in cols:
        row = {"index": labels.get(c1, c1)}
        for c2 in cols:
            val = corr_df.loc[c1, c2]
            row[labels.get(c2, c2)] = float(val) if pd.notna(val) else 0.0
        corr_matrix.append(row)

    payload = {
        "latest_period": latest_p,
        "tehsil_ranking": tehsil_ranking,
        "annual_tehsil": annual_tehsil,
        "correlation_matrix": corr_matrix,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Successfully generated {OUT_JSON} with {len(tehsil_ranking)} tehsils ranking and correlation matrix.")


if __name__ == "__main__":
    build()
