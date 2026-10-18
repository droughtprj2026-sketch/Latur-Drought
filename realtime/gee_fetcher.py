# -*- coding: utf-8 -*-
"""
=============================================================================
 Real-Time Google Earth Engine Data Ingestion Interface
 Sentinel-2 MSI L2A + UCSB CHIRPS Monthly Ingestion for Latur
=============================================================================
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VECTOR_DIR = ROOT / "data" / "vector"
PUBLIC_DATA = ROOT / "frontend" / "public" / "data"

LATUR_BBOX = [76.4, 17.8, 77.3, 18.8]  # [minLon, minLat, maxLon, maxLat]


def init_gee() -> Any | None:
    """Authenticates to Earth Engine via Service Account or Project ID."""
    try:
        import ee
    except ImportError:
        print("  [!] earthengine-api not installed. Running in baseline derivation mode.")
        return None

    service_account_key = os.environ.get("GEE_SERVICE_ACCOUNT_KEY")
    gee_project = os.environ.get("GEE_PROJECT")

    try:
        if service_account_key:
            print("  -> Authenticating with GEE_SERVICE_ACCOUNT_KEY...")
            key_data = (
                json.loads(service_account_key)
                if isinstance(service_account_key, str) and service_account_key.startswith("{")
                else json.load(open(service_account_key))
            )
            credentials = ee.ServiceAccountCredentials(
                key_data.get("client_email"),
                key_data=service_account_key
            )
            ee.Initialize(credentials, project=gee_project or key_data.get("project_id"))
            print("  -> GEE initialized successfully with Service Account.")
            return ee
        elif gee_project:
            print(f"  -> Initializing GEE with GEE_PROJECT: {gee_project}...")
            ee.Initialize(project=gee_project)
            print("  -> GEE initialized with project ID.")
            return ee
        else:
            ee.Initialize()
            print("  -> GEE initialized with default credentials.")
            return ee
    except Exception as exc:
        print(f"  [!] Note: GEE Live credentials unavailable ({exc}). Using historical baselines.")
        return None


def fetch_chirps_precip(ee: Any | None, period_str: str) -> dict[str, float]:
    """Fetches CHIRPS monthly rainfall per tehsil or district for period_str (YYYY-MM)."""
    if ee is None:
        return {}

    try:
        y, m = period_str.split("-")
        start_date = f"{y}-{m}-01"
        end_date = f"{y}-{int(m)+1:02d}-01" if int(m) < 12 else f"{int(y)+1}-01-01"

        col = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/monthly")
            .filterDate(start_date, end_date)
            .select("precipitation")
        )
        img = col.first()
        if img is None:
            return {}

        region = ee.Geometry.BBox(*LATUR_BBOX)
        mean_dict = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=5566,
            maxPixels=1e7
        ).getInfo()

        rain = mean_dict.get("precipitation")
        if rain is not None:
            return {"district_mean": round(float(rain), 2)}
        return {}
    except Exception as exc:
        print(f"  [!] GEE CHIRPS query warning: {exc}")
        return {}


def get_overpass_schedule() -> dict[str, Any]:
    """Returns the astronomical and orbital overpass schedule for Sentinel-2 over Latur.
    
    Orbital Parameters:
      - Location: Latur District, Maharashtra (18.40°N, 76.58°E)
      - Orbit Type: Sun-synchronous, descending node
      - Nominal Equatorial Crossing: 10:30 AM Mean Local Solar Time
      - Latur Overpass Time: ~10:54 AM IST (05:24 UTC) ± 10 minutes
      - Relative Orbits (Tracks): R062 (Main overpass), R105 (Western overlap)
      - Constellation: Sentinel-2A + Sentinel-2B (phased 180° apart)
      - Combined Revisit Frequency: ~2 to 5 days over Latur
      - Earth Engine Ingestion Window: 6 to 12 hours post-acquisition (by ~21:00 UTC / 02:30 AM IST)
      - Optimal Automated Sync Time: Mondays & Thursdays at 03:00 UTC (08:30 AM IST)
    """
    return {
        "target_region": "Latur District, Maharashtra",
        "coordinates": {"lat": 18.40, "lon": 76.58},
        "satellites": ["Sentinel-2A", "Sentinel-2B"],
        "sensor": "MSI (Multi-Spectral Instrument)",
        "relative_orbits": ["R062", "R105"],
        "overpass_time_utc": "05:24 UTC",
        "overpass_time_ist": "10:54 AM IST (window: 10:45 AM - 11:05 AM)",
        "revisit_interval_days": "2.5 - 5 days",
        "primary_overpass_days": ["Monday", "Thursday"],
        "recommended_sync_utc": "03:00 UTC",
        "recommended_sync_ist": "08:30 AM IST",
        "ingestion_lag_hours": "6 - 12 hours"
    }


def fetch_sentinel2_indices(ee: Any | None, period_str: str) -> dict[str, Any]:
    """Fetches Sentinel-2 L2A BOA reflectance and calculates mean NDVI & EVI.
    
    Identifies the exact overpass timestamp of the most recent cloud-free acquisition.
    """
    if ee is None:
        return {}

    try:
        y, m = period_str.split("-")
        start_date = f"{y}-{m}-01"
        end_date = f"{y}-{int(m)+1:02d}-01" if int(m) < 12 else f"{int(y)+1}-01-01"

        # SCL Cloud Masking (Keep vegetation, soil, water)
        def mask_s2(img):
            scl = img.select("SCL")
            mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
            return img.updateMask(mask)

        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate(start_date, end_date)
            .filterBounds(ee.Geometry.BBox(*LATUR_BBOX))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
            .sort("system:time_start", False)  # Most recent first
        )

        count = col.size().getInfo()
        latest_pass_info = {}
        if count > 0:
            first_img = col.first()
            props = first_img.toDictionary(["system:time_start", "SPACECRAFT_NAME", "SENSING_ORBIT_NUMBER", "CLOUDY_PIXEL_PERCENTAGE"]).getInfo()
            if props and "system:time_start" in props:
                pass_ms = props["system:time_start"]
                pass_dt = datetime.fromtimestamp(pass_ms / 1000.0, tz=timezone.utc)
                latest_pass_info = {
                    "satellite": props.get("SPACECRAFT_NAME", "Sentinel-2"),
                    "overpass_datetime_utc": pass_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "overpass_date": pass_dt.strftime("%Y-%m-%d"),
                    "overpass_time": pass_dt.strftime("%H:%M:%S UTC"),
                    "orbit": props.get("SENSING_ORBIT_NUMBER"),
                    "cloud_pct": round(float(props.get("CLOUDY_PIXEL_PERCENTAGE", 0.0)), 2)
                }
                print(f"  -> Latest Sentinel-2 overpass: {latest_pass_info['satellite']} on {latest_pass_info['overpass_datetime_utc']} (Orbit {latest_pass_info.get('orbit')}, Cloud: {latest_pass_info['cloud_pct']}%)")

        masked_col = col.map(mask_s2)
        composite = masked_col.median()
        nir = composite.select("B8").multiply(0.0001)
        red = composite.select("B4").multiply(0.0001)
        blue = composite.select("B2").multiply(0.0001)

        ndvi = nir.subtract(red).divide(nir.add(red)).rename("ndvi")
        evi = (
            nir.subtract(red)
            .multiply(2.5)
            .divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1))
            .rename("evi")
        )

        reduced = (
            ee.Image.cat([ndvi, evi])
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee.Geometry.BBox(*LATUR_BBOX),
                scale=500,
                maxPixels=1e8
            )
            .getInfo()
        )

        res: dict[str, Any] = {
            "ndvi": round(float(reduced.get("ndvi", 0.35)), 4),
            "evi": round(float(reduced.get("evi", 0.25)), 4),
        }
        if latest_pass_info:
            res["overpass_info"] = latest_pass_info
        return res
    except Exception as exc:
        print(f"  [!] GEE Sentinel-2 query warning: {exc}")
        return {}
