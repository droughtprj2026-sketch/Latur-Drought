# -*- coding: utf-8 -*-
"""
Raw village zonal statistics from Earth Engine, kept for every month the pipeline ingests, whichever composite
formula is active:

    NDVI, EVI      Sentinel-2 monthly median, village mean
    LST            Landsat 8/9 surface temperature, village mean (deg C)
    VV             Sentinel-1 VV backscatter, village mean (dB)   (the input of the soil moisture index)

One row per (village_idx, date). Sources arrive independently, so a row may hold only some columns; a later
fetch fills the rest. Values are exactly what Earth Engine returned: nothing is estimated or filled.
`zonal_latest.json` is the dashboard-facing summary written from this table.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
ZONAL_CSV = ROOT / "output" / "zonal" / "village_monthly_zonal.csv"
COLUMNS = ["village_idx", "date", "NDVI", "EVI", "LST", "VV", "s2_scenes", "lst_images", "vv_images", "fetched_at"]
VARS = ("NDVI", "EVI", "LST", "VV")


def load_zonal(path: Path = ZONAL_CSV) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=COLUMNS)
    z = pd.read_csv(path)
    z["date"] = z["date"].astype(str)
    return z.reindex(columns=COLUMNS)


def save_zonal(z: pd.DataFrame, path: Path = ZONAL_CSV) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    z.sort_values(["village_idx", "date"]).to_csv(path, index=False, columns=COLUMNS)


def upsert_period(z: pd.DataFrame, period: str, s2: dict | None = None, thermal: dict | None = None) -> pd.DataFrame:
    """Merge one month's fetched values into the table. `s2` / `thermal` are the dicts the fetchers return
    ({"values": {id: {...}}, "scenes"|"lst_images"|"vv_images": n}); either may be None."""
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    rest = z[z["date"] != period]
    rows: dict[int, dict] = {int(r["village_idx"]): dict(r) for r in z[z["date"] == period].to_dict("records")}

    def row(i: int) -> dict:
        return rows.setdefault(i, {"village_idx": i, "date": period})

    if s2 and s2.get("values"):
        for pid, v in s2["values"].items():
            r = row(int(pid))
            r["NDVI"], r["EVI"], r["s2_scenes"] = v.get("ndvi"), v.get("evi"), s2.get("scenes")
            r["fetched_at"] = now
    if thermal and thermal.get("values"):
        for pid, v in thermal["values"].items():
            r = row(int(pid))
            r["LST"], r["VV"] = v.get("lst"), v.get("vv")
            r["lst_images"], r["vv_images"] = thermal.get("lst_images"), thermal.get("vv_images")
            r["fetched_at"] = now
    new = pd.DataFrame(list(rows.values())).reindex(columns=COLUMNS)
    new["village_idx"] = new["village_idx"].astype(int)
    new["date"] = period
    return pd.concat([rest, new], ignore_index=True)


def write_latest_json(z: pd.DataFrame, path: Path, regional: dict | None = None) -> dict:
    """Latest available value of each variable for every village, with the month it comes from.
    Sources have different latency, so each variable reports its own newest month."""
    out: dict = {"generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                 "latest": {}, "villages": {}}
    if regional:
        out["region"] = regional
    for var in VARS:
        have = z[z[var].notna()]
        if have.empty:
            out["latest"][var.lower()] = None
            continue
        month = have["date"].max()
        out["latest"][var.lower()] = month
        for vid, val in have[have["date"] == month].set_index("village_idx")[var].items():
            out["villages"].setdefault(str(int(vid)), {})[var.lower()] = round(float(val), 4)
    Path(path).write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return out
