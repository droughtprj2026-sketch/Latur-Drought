import sqlite3
con = sqlite3.connect('D:/Droughtprj@2026/data/drought.db')
cur = con.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
for name, sql in cur.fetchall():
    print(f'=== TABLE: {name} ===')
    print(sql)
    print()
for t in ['master_row', 'monthly_index', 'tehsils', 'village_spi']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'{t} count:', cur.fetchone()[0])
    except Exception as e:
        print(f'{t}: ERROR {e}')
print()
print('=== master_row sample columns ===')
cur.execute('PRAGMA table_info(master_row)')
for r in cur.fetchall():
    print(r)
print()
print('=== monthly_index sample columns ===')
cur.execute('PRAGMA table_info(monthly_index)')
for r in cur.fetchall():
    print(r)
print()
print('=== tehsils sample columns ===')
cur.execute('PRAGMA table_info(tehsils)')
for r in cur.fetchall():
    print(r)
print()
print('=== master_row sample rows ===')
cur.execute('SELECT * FROM master_row LIMIT 3')
cols = [d[0] for d in cur.description]
print(cols)
for r in cur.fetchall():
    print(r)
con.close()
