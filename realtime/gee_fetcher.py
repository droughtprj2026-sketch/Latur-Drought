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


def fetch_sentinel2_indices(ee: Any | None, period_str: str) -> dict[str, float]:
    """Fetches Sentinel-2 L2A BOA reflectance and calculates mean NDVI & EVI."""
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
            .map(mask_s2)
        )

        composite = col.median()
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

        return {
            "ndvi": round(float(reduced.get("ndvi", 0.35)), 4),
            "evi": round(float(reduced.get("evi", 0.25)), 4),
        }
    except Exception as exc:
        print(f"  [!] GEE Sentinel-2 query warning: {exc}")
        return {}
