# -*- coding: utf-8 -*-
"""
Build the compact per-village history served to the dashboard.

Output: frontend/public/data/village_timeseries.json
        { "<village_id>": [ {p, cdi, cls, ndvi, evi, vci, vhi, pci,
                             rain, spi1, spi3, spi6, spi12}, ... ] }

Keyed by the numeric `id` carried by every polygon in
latur_villages*.geojson. The previous build keyed by
"tehsil::village-name", which collapsed three pairs of same-named
villages (Anandwadi, Hatkarwadi, Kamshetwadi) into one series, so 954
polygons showed only 951 distinct histories.

Sources (all village-id aware):
  data/processed/csv/village_with_baseline.csv   Sentinel-2 indices, PCI, CDI
  output/spi/csv/SPI{1,3,6,12}_village_monthly.csv   SPI (vid = id - 1)
  output/spi/extra/csv/village_monthly_rainfall_wide.csv  CHIRPS rain (vid = id - 1)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE_CSV = ROOT / "data" / "processed" / "csv" / "village_with_baseline.csv"
SPI_DIR = ROOT / "output" / "spi" / "csv"
RAIN_CSV = ROOT / "output" / "spi" / "extra" / "csv" / "village_monthly_rainfall_wide.csv"
OUT_JSON = ROOT / "frontend" / "public" / "data" / "village_timeseries.json"

SPI_FILES = {"spi1": "SPI1", "spi3": "SPI3", "spi6": "SPI6", "spi12": "SPI12"}


def _wide(path: Path) -> pd.DataFrame:
    """Wide (vid x period) CSV -> long frame indexed by (id, period)."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    periods = [c for c in df.columns if len(c) == 7 and c[4] == "-"]
    long = df.melt(id_vars=["vid"], value_vars=periods,
                   var_name="p", value_name="v")
    long["id"] = long["vid"].astype(int) + 1
    return long.set_index(["id", "p"])["v"]


def _r(v, n):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), n)


def _thermal_frame():
    """(village_idx, date) -> LST, VV, TCI, SMI from output/thermal, or None before any thermal data exists."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common.thermal import add_thermal_indices, load_thermal
    from common.village_cdi import _load_cfg
    th = load_thermal()
    if th.empty:
        return None
    t = th[["village_idx", "date"]].copy()
    t["VCI"] = np.nan                       # TCI / SMI do not need it; VHI is not taken from here
    t = add_thermal_indices(t, th, _load_cfg("config/composite_thermal.yaml")["thermal"])
    t["village_idx"] = t["village_idx"].astype(int)
    return t.set_index(["village_idx", "date"])[["LST", "VV", "TCI", "SMI"]]


def build() -> dict:
    # keep_default_na=False so the class label "None" is not parsed as NaN.
    base = pd.read_csv(BASE_CSV, keep_default_na=False, na_values=[""],
                       dtype={"composite_drought_class": "string"})
    base["id"] = base["village_idx"].astype(int)
    base["p"] = base["date"].astype(str)
    s2 = base.set_index(["id", "p"])

    series = {"rain": _wide(RAIN_CSV)}
    for key, stem in SPI_FILES.items():
        series[key] = _wide(SPI_DIR / f"{stem}_village_monthly.csv")

    # LST / Sentinel-1 VV and the TCI / SMI derived from them come straight from the thermal table, so they
    # appear for every month fetched, whichever composite formula (and panel) is active.
    thx = _thermal_frame()

    ids = sorted(base["id"].unique())
    periods = sorted(set(base["p"]) | {p for s in series.values() for p in s.index.get_level_values("p")}
                     | (set(thx.index.get_level_values("date")) if thx is not None else set()))

    out: dict[str, list[dict]] = {}
    for vid in ids:
        pts = []
        for p in periods:
            row = s2.loc[(vid, p)] if (vid, p) in s2.index else None
            pt = {"p": p}
            cdi = row["composite_drought_score"] if row is not None else None
            cls = row["composite_drought_class"] if row is not None else None
            has_cdi = cdi is not None and pd.notna(cdi)
            pt["cdi"] = _r(cdi, 3) if has_cdi else None
            pt["cls"] = str(cls) if has_cdi and pd.notna(cls) else "ND"
            for k, col, nd in (("ndvi", "NDVI", 3), ("evi", "EVI", 3), ("vci", "VCI", 1),
                               ("vhi", "VHI", 1), ("pci", "PCI", 1), ("tci", "TCI", 1),
                               ("smi", "SMI", 1), ("lst", "LST", 1), ("vv", "VV", 2)):
                pt[k] = _r(row[col], nd) if row is not None and col in row.index else None
            for k, ser in series.items():
                v = ser.get((vid, p))
                if k == "rain" and row is not None and pd.notna(row["Rain_mm"]):
                    v = row["Rain_mm"]   # same zonal run the CDI/PCI were built from
                pt[k] = _r(v, 1 if k == "rain" else 3) if v is not None else None
            if thx is not None and (vid, p) in thx.index:
                tr = thx.loc[(vid, p)]
                for k, col, nd in (("lst", "LST", 1), ("vv", "VV", 2), ("tci", "TCI", 1), ("smi", "SMI", 1)):
                    if pt.get(k) is None and pd.notna(tr[col]):
                        pt[k] = _r(tr[col], nd)
            if any(pt[k] is not None for k in pt if k not in ("p", "cls")):
                pts.append(pt)
        out[str(vid)] = pts
    return out


def main():
    data = build()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size / 1e6:.1f} MB), "
          f"{len(data)} villages")


if __name__ == "__main__":
    main()
