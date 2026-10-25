# -*- coding: utf-8 -*-
"""
Publish the dashboard data to Supabase (Storage + Postgres). Standard library only.

  Storage  bucket `drought-data` (public read): the JSON/GeoJSON files the site loads
  Postgres public.villages        one row per polygon (polygon_id, tehsil, name, centroid, area)
           public.village_monthly one row per village and month (the history, keyed on polygon id)
           public.pipeline_runs   one row per pipeline run

Credentials (never in git):
  SUPABASE_URL                 https://<project>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    server side only

Usage
  python scripts/publish_supabase.py                  # files + the months passed with --period
  python scripts/publish_supabase.py --full           # files + the entire history (first load / repair)
  python scripts/publish_supabase.py --period 2026-09 --period 2026-10
  python scripts/publish_supabase.py --files-only

Run `supabase/migrations/0002_polygon_ids_storage_publishing.sql` once first.
Every request is retried with backoff; any request that still fails raises, so the caller
(realtime_update.py / the workflow) fails instead of reporting a publish that did not happen.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PUB = ROOT / "frontend" / "public" / "data"
BUCKET = os.environ.get("SUPABASE_BUCKET", "drought-data")
BATCH = 1000

# file name in the bucket -> (local path, content type)
ARTIFACTS = {
    "village_timeseries.json": "application/json",
    "village_baselines.json": "application/json",
    "villages_by_tehsil.json": "application/json",
    "district_monthly.json": "application/json",
    "tehsil_analytics.json": "application/json",
    "latest_status.json": "application/json",
    "zonal_latest.json": "application/json",
    "latur_villages_latest.geojson": "application/geo+json",
    "latur_villages.geojson": "application/geo+json",
    "latur_tehsils.geojson": "application/geo+json",
    "latur_district.geojson": "application/geo+json",
}


class PublishError(RuntimeError):
    pass


class Client:
    def __init__(self, url: str, key: str, retries: int = 4, sleep=time.sleep):
        self.url = url.rstrip("/")
        self.key = key
        self.retries = retries
        self.sleep = sleep

    def _request(self, method: str, path: str, body: bytes | None, headers: dict) -> bytes:
        h = {"apikey": self.key, "Authorization": f"Bearer {self.key}", **headers}
        last: Exception | None = None
        for attempt in range(self.retries):
            req = urllib.request.Request(self.url + path, data=body, method=method, headers=h)
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                last = PublishError(f"{method} {path} -> {e.code}: {detail}")
                if e.code < 500 and e.code != 429:   # client error: retrying cannot help
                    raise last
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = PublishError(f"{method} {path} -> {e}")
            self.sleep(2 ** attempt)
        raise last  # type: ignore[misc]

    # -- Storage ------------------------------------------------------------
    def upload(self, name: str, data: bytes, content_type: str) -> None:
        self._request("POST", f"/storage/v1/object/{BUCKET}/{urllib.parse.quote(name)}", data, {
            "Content-Type": content_type,
            "x-upsert": "true",
            "cache-control": "max-age=300",
        })

    # -- Postgres (PostgREST) -------------------------------------------------
    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            self._request(
                "POST", f"/rest/v1/{table}?on_conflict={on_conflict}",
                json.dumps(chunk, separators=(",", ":")).encode(),
                {"Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
            )

    def insert(self, table: str, row: dict) -> None:
        self._request("POST", f"/rest/v1/{table}", json.dumps(row).encode(),
                      {"Content-Type": "application/json", "Prefer": "return=minimal"})


def client_from_env() -> Client:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise PublishError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return Client(url, key)


# ---------------------------------------------------------------------------
def village_rows(pub: Path = PUB) -> list[dict]:
    gj = json.loads((pub / "latur_villages_latest.geojson").read_text(encoding="utf-8"))
    rows = []
    for f in gj["features"]:
        p = f["properties"]
        ring = f["geometry"]["coordinates"]
        while isinstance(ring[0][0], list):      # first ring of first polygon
            ring = ring[0]
        n = len(ring)
        rows.append({
            "polygon_id": int(p["id"]),
            "tehsil": str(p["tehsil"]).strip(),
            "village": str(p["village"]).strip(),
            "area_km2": p.get("AREA_SQKM"),
            "centroid_lon": round(sum(c[0] for c in ring) / n, 6),
            "centroid_lat": round(sum(c[1] for c in ring) / n, 6),
        })
    ids = [r["polygon_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise PublishError("duplicate polygon ids in latur_villages_latest.geojson")
    return rows


def monthly_rows(periods: list[str] | None, pub: Path = PUB) -> list[dict]:
    ts = json.loads((pub / "village_timeseries.json").read_text(encoding="utf-8"))
    want = set(periods) if periods is not None else None
    out = []
    for vid, pts in ts.items():
        for x in pts:
            if want is not None and x["p"] not in want:
                continue
            out.append({
                "village_id": int(vid), "period": x["p"],
                "cdi": x.get("cdi"),
                "cdi_class": x.get("cls") if x.get("cdi") is not None else "ND",
                "ndvi": x.get("ndvi"), "evi": x.get("evi"), "vci": x.get("vci"),
                "vhi": x.get("vhi"), "pci": x.get("pci"), "rain_mm": x.get("rain"),
                "tci": x.get("tci"), "smi": x.get("smi"), "lst_c": x.get("lst"), "vv_db": x.get("vv"),
                "spi1": x.get("spi1"), "spi3": x.get("spi3"),
                "spi6": x.get("spi6"), "spi12": x.get("spi12"),
            })
    return out


def git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def publish(c: Client, periods: list[str] | None, files: bool = True, tables: bool = True,
            pub: Path = PUB, log=print) -> dict:
    """periods=None publishes the whole history; [] publishes none (files only)."""
    done = {"files": [], "villages": 0, "monthly": 0}
    if files:
        for name, ctype in ARTIFACTS.items():
            p = pub / name
            if not p.exists():
                log(f"  skip {name} (not found)")
                continue
            c.upload(name, p.read_bytes(), ctype)
            done["files"].append(name)
            log(f"  uploaded {name} ({p.stat().st_size / 1e6:.2f} MB)")
    if tables:
        v = village_rows(pub)
        c.upsert("villages", v, "polygon_id")
        done["villages"] = len(v)
        if periods is None or periods:
            m = monthly_rows(periods, pub)
            c.upsert("village_monthly", m, "village_id,period")
            done["monthly"] = len(m)
        log(f"  upserted {done['villages']} villages, {done['monthly']} village-month rows")
    return done


def log_run(c: Client, status_path: Path) -> None:
    """Record the run described by latest_status.json (pipeline_run block)."""
    st = json.loads(status_path.read_text(encoding="utf-8"))
    run = st.get("pipeline_run") or {}
    if not run:
        return
    c.insert("pipeline_runs", {
        "started_at": run.get("started_at"), "finished_at": run.get("finished_at"),
        "ok": bool(run.get("ok")), "ingested": run.get("ingested", []),
        "steps": run.get("steps", []), "git_sha": git_sha(),
    })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", action="append", help="YYYY-MM whose rows to upsert (repeatable)")
    ap.add_argument("--full", action="store_true", help="upsert the entire history")
    ap.add_argument("--files-only", action="store_true")
    args = ap.parse_args()
    try:
        c = client_from_env()
        periods = None if args.full else (args.period or [])
        publish(c, periods, tables=not args.files_only)
        log_run(c, PUB / "latest_status.json")
    except PublishError as e:
        print(f"publish failed: {e}", file=sys.stderr)
        return 1
    print("published")
    return 0


if __name__ == "__main__":
    sys.exit(main())
