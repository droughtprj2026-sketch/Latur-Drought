# -*- coding: utf-8 -*-
"""
Supabase Data Seeder Generator
Exports verified tables from SQLite (drought.db) into PostgreSQL/PostGIS SQL format
for instant execution in Supabase SQL editor or via psql.
"""

import json
import sqlite3
from pathlib import Path

WORKSPACE = Path(r"d:\Droughtprj@2026")
PROJ_ROOT = WORKSPACE / "drought-monitoring (1)" / "drought-monitoring"
DB_PATH = PROJ_ROOT / "data" / "drought.db"
TEHSILS_GEOJSON = PROJ_ROOT / "frontend" / "public" / "data" / "latur_tehsils.geojson"
VILLAGES_GEOJSON = PROJ_ROOT / "frontend" / "public" / "data" / "latur_villages.geojson"
OUT_SQL = PROJ_ROOT / "supabase" / "seed_data.sql"

OUT_SQL.parent.mkdir(parents=True, exist_ok=True)

def escape_sql(val):
    if val is None or val == "":
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"'{s}'"

def main():
    print(f"Reading database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    lines = [
        "-- Auto-generated Supabase Seed Data for Latur Drought Monitoring",
        "-- Run this in Supabase SQL editor after running schema.sql",
        "BEGIN;\n"
    ]

    # 1. Tehsils
    if TEHSILS_GEOJSON.exists():
        with open(TEHSILS_GEOJSON, "r", encoding="utf-8") as f:
            gj = json.load(f)
        lines.append("-- Seeding Tehsils with PostGIS Geometries")
        for feat in gj.get("features", []):
            name = feat["properties"].get("TEHSIL") or feat["properties"].get("name")
            geom_str = json.dumps(feat["geometry"]).replace("'", "''")
            lines.append(f"""INSERT INTO public.tehsils (name, geom) VALUES ('{name}', ST_SetSRID(ST_GeomFromGeoJSON('{geom_str}'), 4326)) ON CONFLICT (name) DO NOTHING;""")
        lines.append("")

    # 2. Villages (Top 100 sample or full)
    if VILLAGES_GEOJSON.exists():
        with open(VILLAGES_GEOJSON, "r", encoding="utf-8") as f:
            vgj = json.load(f)
        lines.append(f"-- Seeding {len(vgj.get('features', []))} Villages with PostGIS Geometries")
        for feat in vgj.get("features", []):
            props = feat.get("properties", {})
            vname = (props.get("VILLAGE") or props.get("name") or props.get("village") or "").replace("'", "''")
            tname = (props.get("TEHSIL") or props.get("tehsil") or "").replace("'", "''")
            area = props.get("AREA_SQKM")
            vcode = props.get("village_code") or props.get("VILL_CODE")
            geom_str = json.dumps(feat["geometry"]).replace("'", "''")
            if not vname:
                continue
            lines.append(f"""INSERT INTO public.villages (tehsil, village, village_code, geom, area_km2) VALUES ('{tname}', '{vname}', {escape_sql(vcode)}, ST_SetSRID(ST_GeomFromGeoJSON('{geom_str}'), 4326), {escape_sql(area)}) ON CONFLICT (tehsil, village) DO NOTHING;""")
        lines.append("")

    # 3. Monthly Index (District SPI)
    cur.execute("SELECT index_name, year, month, value, class_label, pct_area_dry FROM monthly_index WHERE value IS NOT NULL;")
    rows = cur.fetchall()
    lines.append(f"-- Seeding {len(rows)} Monthly District Indices")
    for r in rows:
        lines.append(f"""INSERT INTO public.monthly_index (index_name, year, month, value, class_label, pct_area_dry) VALUES ({escape_sql(r[0])}, {r[1]}, {r[2]}, {escape_sql(r[3])}, {escape_sql(r[4])}, {escape_sql(r[5])}) ON CONFLICT (index_name, year, month) DO NOTHING;""")
    lines.append("")

    # 4. Master Row (Tehsil level)
    cur.execute("SELECT district, tehsil, village, observation_period, year, month, monthly_rainfall_mm, chirps_data_through, spi_1, spi_3, spi_6, spi_12, spi_reference_period, data_quality_status FROM master_row WHERE village = '';")
    mrows = cur.fetchall()
    lines.append(f"-- Seeding {len(mrows)} Verified Master Tehsil Records")
    for r in mrows:
        lines.append(f"""INSERT INTO public.master_row (district, tehsil, village, observation_period, year, month, monthly_rainfall_mm, chirps_data_through, spi_1, spi_3, spi_6, spi_12, spi_reference_period, data_quality_status) VALUES ({escape_sql(r[0])}, {escape_sql(r[1])}, {escape_sql(r[2])}, {escape_sql(r[3])}, {r[4]}, {r[5]}, {escape_sql(r[6])}, {escape_sql(r[7])}, {escape_sql(r[8])}, {escape_sql(r[9])}, {escape_sql(r[10])}, {escape_sql(r[11])}, {escape_sql(r[12])}, {escape_sql(r[13])}) ON CONFLICT (tehsil, village, observation_period) DO NOTHING;""")
    lines.append("")

    lines.append("COMMIT;")

    with open(OUT_SQL, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated Supabase seed SQL: {OUT_SQL} ({len(lines)} statements)")

if __name__ == "__main__":
    main()
