# -*- coding: utf-8 -*-
"""
SPI Village Data Converter & High-Performance Database Loader
Converts wide SPI CSVs (SPI1, SPI3, SPI6, SPI12) and Latur_Tehsil_Villages.shp
into fast, consolidated formats:
  1. data/drought.db (table `village_spi` with indexes + populated `master_row`)
  2. output/spi/csv/SPI_village_monthly_tidy.csv
  3. frontend/public/data/latur_villages.geojson
  4. frontend/public/data/villages_by_tehsil.json
"""

import csv
import json
import math
import os
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import shapefile

WORKSPACE = Path(r"d:\Droughtprj@2026")
PROJ_ROOT = WORKSPACE / "drought-monitoring (1)" / "drought-monitoring"
DATA_DIR = PROJ_ROOT / "data"
PUBLIC_DATA_DIR = PROJ_ROOT / "frontend" / "public" / "data"
OUTPUT_SPI_DIR = WORKSPACE / "output" / "spi" / "csv"
DB_PATH = DATA_DIR / "drought.db"

PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_SPI_DIR.mkdir(parents=True, exist_ok=True)

TEHSIL_MAP = {
    "AHMADPUR": "Ahmadpur",
    "AUSA": "Ausa",
    "CHAKUR": "Chakur",
    "DEONI": "Deoni",
    "JALKOT": "Jalkot",
    "LATUR": "Latur",
    "NILANGA": "Nilanga",
    "RENAPUR": "Renapur",
    "SHIRUR-ANANTPAL": "Shirur-Anantpal",
    "UDGIR": "Udgir"
}

def clean_tehsil(name):
    clean = str(name).strip().upper()
    return TEHSIL_MAP.get(clean, str(name).strip().title())

def to_float(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def get_drought_code(score):
    if score is None or math.isnan(score):
        return "ND"
    if score <= 0.20:
        return "None"
    elif score <= 0.35:
        return "D0"
    elif score <= 0.50:
        return "D1"
    elif score <= 0.65:
        return "D2"
    elif score <= 0.80:
        return "D3"
    else:
        return "D4"

def step1_export_villages_geojson():
    print("Step 1: Exporting latur_villages.geojson and villages_by_tehsil.json...")
    zip_path = WORKSPACE / "Latur_Tehsil_Villages.zip"
    if not zip_path.exists():
        print(f"Warning: {zip_path} not found.")
        return

    by_tehsil = {}
    features = []

    with zipfile.ZipFile(zip_path) as z:
        sf = shapefile.Reader(
            shp=z.open("Latur_Tehsil_Villages.shp"),
            dbf=z.open("Latur_Tehsil_Villages.dbf"),
            shx=z.open("Latur_Tehsil_Villages.shx")
        )
        fields = [f[0] for f in sf.fields[1:]]

        for shape_rec in sf.shapeRecords():
            rec = dict(zip(fields, shape_rec.record))
            geom = shape_rec.shape.__geo_interface__

            v_name = str(rec.get("VILLAGE", "")).strip()
            t_name = clean_tehsil(rec.get("TEHSIL", ""))
            area = to_float(rec.get("AREA_SQKM"))

            if not v_name or not t_name:
                continue

            by_tehsil.setdefault(t_name, set()).add(v_name)

            features.append({
                "type": "Feature",
                "properties": {
                    "VILLAGE": v_name,
                    "TEHSIL": t_name,
                    "DISTRICT": "Latur",
                    "AREA_SQKM": area,
                    "name": v_name,
                    "tehsil": t_name
                },
                "geometry": geom
            })

    # Sort village names
    by_tehsil_sorted = {k: sorted(list(v)) for k, v in sorted(by_tehsil.items())}

    geojson_out = PUBLIC_DATA_DIR / "latur_villages.geojson"
    with open(geojson_out, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    print(f"  -> Wrote {len(features)} village features to {geojson_out}")

    json_out = PUBLIC_DATA_DIR / "villages_by_tehsil.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(by_tehsil_sorted, f, indent=2)
    print(f"  -> Wrote village index to {json_out}")

def step2_consolidate_spi_data():
    print("Step 2: Consolidating SPI-1, 3, 6, 12 village CSVs...")
    spi_files = {
        "spi1": OUTPUT_SPI_DIR / "SPI1_village_monthly.csv",
        "spi3": OUTPUT_SPI_DIR / "SPI3_village_monthly.csv",
        "spi6": OUTPUT_SPI_DIR / "SPI6_village_monthly.csv",
        "spi12": OUTPUT_SPI_DIR / "SPI12_village_monthly.csv",
    }

    # Consolidated structure: (tehsil, village, date) -> dict
    combined = {}

    for scale, path in spi_files.items():
        if not path.exists():
            print(f"Warning: {path} not found")
            continue
        print(f"  Processing {path.name}...")
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            date_cols = [c for c in reader.fieldnames if len(c) == 7 and c[4] == "-"]
            for row in reader:
                t_name = clean_tehsil(row.get("TEHSIL", ""))
                v_name = str(row.get("VILLAGE", "")).strip()
                if not v_name or not t_name:
                    continue

                for d in date_cols:
                    val = to_float(row.get(d))
                    key = (t_name, v_name, d)
                    if key not in combined:
                        y, m = d.split("-")
                        combined[key] = {
                            "tehsil": t_name,
                            "village": v_name,
                            "date": d,
                            "year": int(y),
                            "month": int(m),
                            "spi1": None,
                            "spi3": None,
                            "spi6": None,
                            "spi12": None,
                        }
                    combined[key][scale] = val

    print(f"  Consolidated {len(combined)} village-month observation cells.")

    # Merge with village_monthly_indices.csv (which has NDVI, Rain, VCI, CDI if available)
    v_indices_path = WORKSPACE / "output" / "indices" / "zonal" / "village" / "village_monthly_indices.csv"
    if v_indices_path.exists():
        print(f"  Enriching from {v_indices_path.name}...")
        with open(v_indices_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                t_name = clean_tehsil(r.get("tehsil", ""))
                v_name = str(r.get("village", "")).strip()
                d = r.get("date")
                if not d or not v_name or not t_name:
                    continue
                key = (t_name, v_name, d)
                if key in combined:
                    combined[key]["rain_mm"] = to_float(r.get("Rain_mm"))
                    combined[key]["ndvi"] = to_float(r.get("NDVI"))
                    combined[key]["evi"] = to_float(r.get("EVI"))
                    combined[key]["vci"] = to_float(r.get("VCI"))
                    combined[key]["vhi"] = to_float(r.get("VHI"))
                    combined[key]["pci"] = to_float(r.get("PCI"))
                    combined[key]["cdi"] = to_float(r.get("CDI"))
                    combined[key]["cdi_class"] = r.get("CDI_class")

    return combined

def step3_save_tidy_csv_and_database(combined):
    print("Step 3: Writing tidy CSV and updating SQLite database...")
    tidy_csv_out = OUTPUT_SPI_DIR / "SPI_village_monthly_tidy.csv"
    fields = [
        "tehsil", "village", "date", "year", "month",
        "SPI1", "SPI3", "SPI6", "SPI12",
        "Rain_mm", "NDVI", "EVI", "VCI", "VHI", "PCI",
        "CDI", "composite_drought_score", "composite_drought_class"
    ]

    tidy_rows = []
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS village_spi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tehsil TEXT NOT NULL,
        village TEXT NOT NULL,
        observation_period TEXT NOT NULL,
        year INT NOT NULL,
        month INT NOT NULL,
        spi_1 REAL,
        spi_3 REAL,
        spi_6 REAL,
        spi_12 REAL,
        monthly_rainfall_mm REAL,
        ndvi REAL,
        evi REAL,
        vci REAL,
        vhi REAL,
        pci REAL,
        composite_drought_score REAL,
        composite_drought_class TEXT,
        UNIQUE (tehsil, village, observation_period)
    );
    CREATE INDEX IF NOT EXISTS idx_village_spi_lookup ON village_spi (tehsil, village, observation_period);
    CREATE INDEX IF NOT EXISTS idx_village_spi_period ON village_spi (observation_period);
    CREATE INDEX IF NOT EXISTS idx_village_spi_tehsil ON village_spi (tehsil);
    """)

    db_rows = []
    master_village_rows = []

    for item in combined.values():
        t_name = item["tehsil"]
        v_name = item["village"]
        d = item["date"]
        y = item["year"]
        m = item["month"]
        s1 = item.get("spi1")
        s3 = item.get("spi3")
        s6 = item.get("spi6")
        s12 = item.get("spi12")
        rain = item.get("rain_mm")
        ndvi = item.get("ndvi")
        evi = item.get("evi")
        vci = item.get("vci")
        vhi = item.get("vhi")
        pci = item.get("pci")
        raw_cdi = item.get("cdi")

        # Normalize CDI (0..1)
        cdi_norm = None
        if raw_cdi is not None:
            cdi_norm = max(0.0, min(1.0, 1.0 - (raw_cdi / 100.0)))
        elif s3 is not None:
            cdi_norm = max(0.0, min(1.0, -s3 / 3.0))

        d_code = get_drought_code(cdi_norm)

        tidy_rows.append({
            "tehsil": t_name,
            "village": v_name,
            "date": d,
            "year": y,
            "month": m,
            "SPI1": round(s1, 3) if s1 is not None else "",
            "SPI3": round(s3, 3) if s3 is not None else "",
            "SPI6": round(s6, 3) if s6 is not None else "",
            "SPI12": round(s12, 3) if s12 is not None else "",
            "Rain_mm": round(rain, 2) if rain is not None else "",
            "NDVI": round(ndvi, 3) if ndvi is not None else "",
            "EVI": round(evi, 3) if evi is not None else "",
            "VCI": round(vci, 2) if vci is not None else "",
            "VHI": round(vhi, 2) if vhi is not None else "",
            "PCI": round(pci, 2) if pci is not None else "",
            "CDI": round(raw_cdi, 2) if raw_cdi is not None else "",
            "composite_drought_score": round(cdi_norm, 3) if cdi_norm is not None else "",
            "composite_drought_class": d_code
        })

        db_rows.append((
            t_name, v_name, d, y, m,
            s1, s3, s6, s12, rain, None, None, None, None, None,
            None, None
        ))

        # Also prepare for master_row table (village level - Sentinel pending)
        master_village_rows.append((
            "Latur", t_name, v_name, d, y, m,
            rain, f"{d}-28", s1, s3, s6, s12, "2016-2026",
            None, None, None, None, None,
            None, None, "{}", "cdi-v2026.10",
            None, None, None, None, None, "spi_verified_sentinel_pending", now_iso, "run-spi-converter"
        ))

    with open(tidy_csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(tidy_rows)
    print(f"  -> Wrote tidy long CSV: {tidy_csv_out} ({len(tidy_rows)} rows)")

    print("  -> Wiping old village records to remove stale mock values...")
    cur.execute("DELETE FROM village_spi;")
    cur.execute("DELETE FROM master_row WHERE village != '';")
    conn.commit()

    print(f"  -> Inserting {len(db_rows)} records into village_spi table...")
    cur.executemany("""
        INSERT INTO village_spi (
            tehsil, village, observation_period, year, month,
            spi_1, spi_3, spi_6, spi_12, monthly_rainfall_mm,
            ndvi, evi, vci, vhi, pci, composite_drought_score, composite_drought_class
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tehsil, village, observation_period) DO UPDATE SET
            spi_1=excluded.spi_1,
            spi_3=excluded.spi_3,
            spi_6=excluded.spi_6,
            spi_12=excluded.spi_12,
            monthly_rainfall_mm=excluded.monthly_rainfall_mm,
            ndvi=excluded.ndvi,
            evi=excluded.evi,
            vci=excluded.vci,
            vhi=excluded.vhi,
            pci=excluded.pci,
            composite_drought_score=excluded.composite_drought_score,
            composite_drought_class=excluded.composite_drought_class;
    """, db_rows)

    print(f"  -> Upserting {len(master_village_rows)} records into master_row table...")
    cur.executemany("""
        INSERT INTO master_row (
            district, tehsil, village, observation_period, year, month,
            monthly_rainfall_mm, chirps_data_through, spi_1, spi_3, spi_6, spi_12,
            spi_reference_period, ndvi, evi, vci, vhi, pci,
            composite_drought_score, composite_drought_class, component_contributions,
            composite_formula_version, drought_area_km2, drought_percentage,
            total_polygon_area_km2, sentinel2_observation_date, sentinel2_cloud_percentage,
            data_quality_status, processing_timestamp, processing_run_id
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(tehsil, village, observation_period) DO UPDATE SET
            district=excluded.district,
            year=excluded.year,
            month=excluded.month,
            monthly_rainfall_mm=excluded.monthly_rainfall_mm,
            chirps_data_through=excluded.chirps_data_through,
            spi_1=excluded.spi_1,
            spi_3=excluded.spi_3,
            spi_6=excluded.spi_6,
            spi_12=excluded.spi_12,
            spi_reference_period=excluded.spi_reference_period,
            ndvi=excluded.ndvi,
            evi=excluded.evi,
            vci=excluded.vci,
            vhi=excluded.vhi,
            pci=excluded.pci,
            composite_drought_score=excluded.composite_drought_score,
            composite_drought_class=excluded.composite_drought_class,
            component_contributions=excluded.component_contributions,
            composite_formula_version=excluded.composite_formula_version,
            drought_area_km2=excluded.drought_area_km2,
            drought_percentage=excluded.drought_percentage,
            total_polygon_area_km2=excluded.total_polygon_area_km2,
            sentinel2_observation_date=excluded.sentinel2_observation_date,
            sentinel2_cloud_percentage=excluded.sentinel2_cloud_percentage,
            data_quality_status=excluded.data_quality_status,
            processing_timestamp=excluded.processing_timestamp,
            processing_run_id=excluded.processing_run_id;
    """, master_village_rows)

    conn.commit()
    conn.close()
    print("  -> Database update complete!")

def main():
    step1_export_villages_geojson()
    combined = step2_consolidate_spi_data()
    step3_save_tidy_csv_and_database(combined)
    print("\nAll SPI data successfully converted and indexed!")

if __name__ == "__main__":
    main()
