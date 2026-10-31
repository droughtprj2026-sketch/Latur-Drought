# -*- coding: utf-8 -*-
"""
Build the id-keyed lookup files the dashboard needs:

  frontend/public/data/villages_by_tehsil.json
      { "<Tehsil>": [ {"id": 1, "name": "Ahmadpur (M Cl)"}, ... ] }
      One entry per polygon (954), sorted by name. Same-named villages
      stay distinct because the dropdown selects by id, not by name.

  frontend/public/data/village_baselines.json
      { "district": { "<month>": {...} },
        "villages": { "<id>": { "<month>": {ndvi_mean, ndvi_std, vci_mean,
                                             vci_std, rain_mean, rain_std,
                                             spi3_mean, spi3_std} } } }
      Calendar-month climatology (mu, sigma) per village over the
      2016-2026 record, exactly as defined in baseline_drought_architecture.md
      section 2.1.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "frontend" / "public" / "data"
BASE_CSV = ROOT / "data" / "processed" / "csv" / "village_with_baseline.csv"


def main():
    gj = json.loads((PUB / "latur_villages_latest.geojson").read_text(encoding="utf-8"))
    by_tehsil: dict[str, list[dict]] = {}
    for f in gj["features"]:
        p = f["properties"]
        by_tehsil.setdefault(p["tehsil"].strip(), []).append(
            {"id": int(p["id"]), "name": p["village"].strip()})
    for t in by_tehsil:
        by_tehsil[t].sort(key=lambda v: (v["name"].lower(), v["id"]))
    total = sum(len(v) for v in by_tehsil.values())
    assert total == len(gj["features"]) == len({v["id"] for l in by_tehsil.values() for v in l})
    (PUB / "villages_by_tehsil.json").write_text(
        json.dumps(by_tehsil, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"villages_by_tehsil.json: {total} villages, {len(by_tehsil)} tehsils")

    df = pd.read_csv(BASE_CSV, keep_default_na=False, na_values=[""])
    df["id"] = df["village_idx"].astype(int)
    spec = {"ndvi": "NDVI", "vci": "VCI", "rain": "Rain_mm", "spi3": "SPI3"}

    def stats(g: pd.DataFrame) -> dict:
        out = {}
        for k, col in spec.items():
            m, s = g[col].mean(), g[col].std()
            out[f"{k}_mean"] = None if pd.isna(m) else round(float(m), 3 if k in ("ndvi", "spi3") else 1)
            out[f"{k}_std"] = None if pd.isna(s) else round(float(s), 3 if k in ("ndvi", "spi3") else 1)
        return out

    villages = {}
    for vid, g in df.groupby("id"):
        villages[str(vid)] = {str(m): stats(gm) for m, gm in g.groupby("month")}
    district = {str(m): stats(g) for m, g in df.groupby("month")}
    (PUB / "village_baselines.json").write_text(
        json.dumps({"district": district, "villages": villages}, separators=(",", ":")),
        encoding="utf-8")
    print(f"village_baselines.json: {len(villages)} villages")


if __name__ == "__main__":
    main()
