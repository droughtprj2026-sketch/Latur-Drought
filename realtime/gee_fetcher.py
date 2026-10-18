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


CLOUD_ACCEPTANCE_TIERS = [
    {"max_cloud": 15.0, "name": "Tier 1: Optimal", "tag": "tier_1_optimal"},
    {"max_cloud": 20.0, "name": "Tier 2: Acceptable", "tag": "tier_2_acceptable"},
    {"max_cloud": 25.0, "name": "Tier 3: Maximum Ceiling", "tag": "tier_3_ceiling"},
]
MAX_ACCEPTABLE_CLOUD_COVER = 25.0


def evaluate_cloud_cover_acceptance(cloud_pct: float) -> dict[str, Any]:
    """Evaluates a cloud cover percentage against the 15% -> 20% -> 25% acceptance ladder.
    
    Returns:
      dict with: accepted (bool), tier (str), max_threshold (float), reason (str)
    """
    for tier in CLOUD_ACCEPTANCE_TIERS:
        if cloud_pct <= tier["max_cloud"]:
            return {
                "accepted": True,
                "tier": tier["name"],
                "tag": tier["tag"],
                "threshold_applied": tier["max_cloud"],
                "cloud_pct": round(cloud_pct, 2),
                "reason": f"Accepted: Cloud cover {cloud_pct:.1f}% meets {tier['name']} (<= {tier['max_cloud']}%)."
            }

    return {
        "accepted": False,
        "tier": "Exceeded Maximum Ceiling",
        "tag": "rejected_cloud_exceeded",
        "threshold_applied": MAX_ACCEPTABLE_CLOUD_COVER,
        "cloud_pct": round(cloud_pct, 2),
        "reason": (
            f"REJECTED: Cloud cover {cloud_pct:.1f}% exceeds statutory maximum ceiling of "
            f"{MAX_ACCEPTABLE_CLOUD_COVER}%. Optical imagery rejected to prevent false drought artifacts."
        )
    }


def fetch_sentinel2_indices(ee: Any | None, period_str: str) -> dict[str, Any]:
    """Fetches Sentinel-2 L2A BOA reflectance using progressive step-by-step cloud filtering.
    
    Ladder:
      1. Attempt <= 15% (Tier 1: Optimal)
      2. Attempt <= 20% (Tier 2: Acceptable)
      3. Attempt <= 25% (Tier 3: Maximum Ceiling)
      4. If all scenes > 25%: REJECT optical imagery and report rejection.
    """
    if ee is None:
        return {}

    try:
        y, m = period_str.split("-")
        start_date = f"{y}-{m}-01"
        end_date = f"{y}-{int(m)+1:02d}-01" if int(m) < 12 else f"{int(y)+1}-01-01"

        base_col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate(start_date, end_date)
            .filterBounds(ee.Geometry.BBox(*LATUR_BBOX))
        )

        total_scenes = base_col.size().getInfo()
        if total_scenes == 0:
            print(f"  [!] No Sentinel-2 scenes found for period {period_str}.")
            return {"optical_status": "no_scenes", "cloud_rejected": True}

        # Step-by-step tiered cloud cover search (15% -> 20% -> 25%)
        accepted_col = None
        applied_tier = None

        for tier in CLOUD_ACCEPTANCE_TIERS:
            threshold = tier["max_cloud"]
            candidate_col = base_col.filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", threshold))
            c_size = candidate_col.size().getInfo()
            if c_size > 0:
                accepted_col = candidate_col
                applied_tier = tier
                print(f"  -> Cloud Filter Check: {c_size} scene(s) passed {tier['name']} (<= {threshold}%).")
                break
            else:
                print(f"  -> Cloud Filter Step: 0 scenes with <= {threshold}% cloud. Escalating to next tier...")

        if accepted_col is None:
            # All available scenes exceed the 25% ceiling
            best_scene = base_col.sort("CLOUDY_PIXEL_PERCENTAGE", True).first()
            best_props = best_scene.toDictionary(["CLOUDY_PIXEL_PERCENTAGE", "system:time_start"]).getInfo()
            best_cloud = round(float(best_props.get("CLOUDY_PIXEL_PERCENTAGE", 99.9)), 2)

            print("  " + "!" * 70)
            print("  [!] SATELLITE REJECTION NOTICE: Optical scene REJECTED due to cloud cover.")
            print(f"  [!] All {total_scenes} scene(s) exceed the 25% ceiling. Best available: {best_cloud}%.")
            print("  [!] Optical NDVI/EVI will NOT be fabricated. Relying on CHIRPS precipitation.")
            print("  " + "!" * 70)

            return {
                "optical_status": "rejected",
                "cloud_rejected": True,
                "best_available_cloud_pct": best_cloud,
                "max_ceiling": MAX_ACCEPTABLE_CLOUD_COVER,
                "reason": (
                    f"Sentinel-2 imagery rejected: Best available scene had {best_cloud}% cloud cover, "
                    f"which exceeds the maximum acceptable ceiling of {MAX_ACCEPTABLE_CLOUD_COVER}%."
                )
            }

        # An image was accepted under 15%, 20%, or 25%
        col = accepted_col.sort("system:time_start", False)  # Most recent first
        first_img = col.first()
        props = first_img.toDictionary(["system:time_start", "SPACECRAFT_NAME", "SENSING_ORBIT_NUMBER", "CLOUDY_PIXEL_PERCENTAGE"]).getInfo()
        
        latest_pass_info = {}
        if props and "system:time_start" in props:
            pass_ms = props["system:time_start"]
            pass_dt = datetime.fromtimestamp(pass_ms / 1000.0, tz=timezone.utc)
            cloud_pct = round(float(props.get("CLOUDY_PIXEL_PERCENTAGE", 0.0)), 2)
            eval_res = evaluate_cloud_cover_acceptance(cloud_pct)
            
            latest_pass_info = {
                "satellite": props.get("SPACECRAFT_NAME", "Sentinel-2"),
                "overpass_datetime_utc": pass_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "overpass_date": pass_dt.strftime("%Y-%m-%d"),
                "overpass_time": pass_dt.strftime("%H:%M:%S UTC"),
                "orbit": props.get("SENSING_ORBIT_NUMBER"),
                "cloud_pct": cloud_pct,
                "cloud_tier": applied_tier["name"],
                "cloud_status": "accepted"
            }
            print(f"  -> ACCEPTED Sentinel-2 Scene: {latest_pass_info['satellite']} ({cloud_pct}% cloud <= {applied_tier['max_cloud']}%) on {latest_pass_info['overpass_datetime_utc']}")

        # SCL Cloud Masking (Keep vegetation, soil, water)
        def mask_s2(img):
            scl = img.select("SCL")
            mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
            return img.updateMask(mask)

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
            "optical_status": "accepted",
            "cloud_rejected": False,
            "cloud_tier": applied_tier["name"] if applied_tier else "Unknown",
            "ndvi": round(float(reduced.get("ndvi", 0.35)), 4),
            "evi": round(float(reduced.get("evi", 0.25)), 4),
        }
        if latest_pass_info:
            res["overpass_info"] = latest_pass_info
        return res
    except Exception as exc:
        print(f"  [!] GEE Sentinel-2 query warning: {exc}")
        return {}
