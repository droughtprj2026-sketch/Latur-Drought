import sqlite3
con = sqlite3.connect('D:/Droughtprj@2026/data/drought.db')
cur = con.cursor()

# Check tehsil-level row (village='') for latest period with full data
cur.execute("""
    SELECT observation_period, tehsil, village, spi_1, spi_3, spi_6, spi_12,
           ndvi, evi, vci, vhi, pci, composite_drought_score, composite_drought_class,
           data_quality_status
    FROM master_row
    WHERE village = '' AND observation_period = '2026-10'
    LIMIT 5
""")
print("=== Tehsil-level rows, 2026-10 ===")
for r in cur.fetchall():
    print(r)

# Count non-null per column for tehsil-level
print("\n=== Non-null counts (tehsil-level, village='') ===")
for col in ['spi_1','spi_3','spi_6','spi_12','ndvi','evi','vci','vhi','pci','composite_drought_score']:
    cur.execute(f"SELECT COUNT(*), COUNT({col}) FROM master_row WHERE village = ''")
    total, nonnull = cur.fetchone()
    print(f"  {col}: {nonnull}/{total}")

# Check village-level latest period
cur.execute("""
    SELECT observation_period, tehsil, village, composite_drought_score, composite_drought_class, pci, ndvi
    FROM master_row
    WHERE village != '' AND observation_period = '2026-10'
    LIMIT 5
""")
print("\n=== Village-level rows, 2026-10 ===")
for r in cur.fetchall():
    print(r)

# Check monthly_index timeseries
cur.execute("SELECT index_name, COUNT(*), MIN(year), MAX(year) FROM monthly_index GROUP BY index_name ORDER BY index_name")
print("\n=== monthly_index coverage ===")
for r in cur.fetchall():
    print(r)

con.close()
