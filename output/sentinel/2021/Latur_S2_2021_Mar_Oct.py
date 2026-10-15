# ============================================================
# Sentinel-2 monthly composites for Latur (built from weekly composites)
# Bands: B2, B3, B4, B8, B11, B12
# Cloud filter: starts at 15 %, steps +5 % until the month has scenes
# Output: /content/Latur_S2/<YEAR>/Latur_S2_<YEAR>_<MM>.tif
# Paste each "# %%" block into its own Colab cell and run them in order.
# Cell 5 is the download cell for 2021 - run it when you want it.
# ============================================================

# %% Cell 1 - install & imports
!pip -q install geopandas "rasterio>=1.4" requests

import os, csv, shutil, zipfile, time, calendar, requests
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from shapely.geometry import box
import ee

# %% Cell 2 - Earth Engine login
ee.Authenticate()
ee.Initialize(project='ee-shital')

# %% Cell 3 - read the shapefile (upload Latur.zip to /content first)
ZIP_PATH = '/content/Latur.zip'
SHP_DIR  = '/content/Latur_shp'

os.makedirs(SHP_DIR, exist_ok=True)
with zipfile.ZipFile(ZIP_PATH) as z:
    z.extractall(SHP_DIR)

shp = [os.path.join(r, f) for r, _, fs in os.walk(SHP_DIR)
       for f in fs if f.lower().endswith('.shp')][0]
gdf = gpd.read_file(shp)
if gdf.crs is None:
    gdf = gdf.set_crs(4326)
gdf = gdf.to_crs(4326)

geom_shp = gdf.unary_union
roi  = ee.Geometry(geom_shp.simplify(0.001).__geo_interface__)
minx, miny, maxx, maxy = gdf.total_bounds
bbox = ee.Geometry.Rectangle([minx, miny, maxx, maxy])

area_km2 = gdf.to_crs(32643).unary_union.area / 1e6
print('Using', shp)
print(f'Bounds: {minx:.4f}, {miny:.4f}, {maxx:.4f}, {maxy:.4f}')
print(f'Area from shapefile: {area_km2:,.0f} sq km (expected ~7,157)')

# %% Cell 4 - settings + functions
OUT_ROOT     = '/content/Latur_S2'
LOG_CSV      = os.path.join(OUT_ROOT, 'cloud_threshold_log.csv')
BANDS        = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12']
SCALE_M      = 10                 # B11/B12 (20 m native) are resampled to 10 m
OUT_CRS      = 'EPSG:32643'       # UTM 43N

CLOUD_START  = 15                 # first scene-level cloud cover limit (%)
CLOUD_STEP   = 5                  # increase by this much if no scene is found
CLOUD_MAX    = 60                 # never go above this (set 100 to allow anything)
PIXEL_CS     = 0.60               # pixel-level Cloud Score+ mask (cs_cdf >= 0.6)

TILE_DEG     = 0.15               # ~16 km tiles: 6 bands x uint16 ~ 32 MB (< 48 MB EE limit)
N_WORKERS    = 4                  # parallel tile downloads

# L1C (TOA) harmonized is used because it covers 2016-2018 over India
# (L2A is only global from ~Dec 2018).
S2  = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
CSP = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')

def month_collection(y, m, max_cloud):
    start = f'{y}-{m:02d}-01'
    end   = date(y + (m == 12), (m % 12) + 1, 1).isoformat()
    return (S2.filterBounds(bbox)
              .filterDate(start, end)
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud))
              .linkCollection(CSP, ['cs_cdf'])
              .map(lambda im: im.updateMask(im.select('cs_cdf').gte(PIXEL_CS))
                                .select(BANDS)))

def find_collection(y, m):
    """Try 15 %, 20 %, 25 % ... until scenes are found. Returns (col, threshold, n)."""
    thr = CLOUD_START
    while thr <= CLOUD_MAX:
        col = month_collection(y, m, thr + 1e-6)   # '<=' thr
        n = col.size().getInfo()
        if n > 0:
            return col, thr, n
        print(f'   {y}-{m:02d}: no scenes with cloud <= {thr}%')
        thr += CLOUD_STEP
    return None, None, 0

def week_windows(y, m):
    """Days 1-7, 8-14, 15-21, 22-28, 29-end (end date exclusive)."""
    n = calendar.monthrange(y, m)[1]
    edges = [1, 8, 15, 22, 29, n + 1]
    wins = []
    for a, b in zip(edges[:-1], edges[1:]):
        if a > n:
            continue
        wins.append((date(y, m, a).isoformat(),
                     (date(y, m, 1) + timedelta(days=b - 1)).isoformat()))
    return wins

def monthly_from_weekly(y, m):
    col, thr, n_scenes = find_collection(y, m)
    if col is None:
        return None, 0, None, 0
    weekly = []
    for s, e in week_windows(y, m):
        wc = col.filterDate(s, e)
        if wc.size().getInfo() > 0:
            weekly.append(wc.median())
    img = (ee.ImageCollection.fromImages(weekly).median()
             .clip(roi).unmask(0).toUint16())
    return img, len(weekly), thr, n_scenes

def make_tiles():
    out = []
    for x in np.arange(minx, maxx, TILE_DEG):
        for yv in np.arange(miny, maxy, TILE_DEG):
            b = box(x, yv, min(x + TILE_DEG, maxx), min(yv + TILE_DEG, maxy))
            if b.intersects(geom_shp):          # skip tiles fully outside the district
                out.append(b.bounds)
    return out

TILES = make_tiles()
print('Tiles per image:', len(TILES))

def download_tile(img, b, path, tries=4):
    region = ee.Geometry.Rectangle(list(b))
    for k in range(tries):
        try:
            url = img.getDownloadURL({'region': region, 'scale': SCALE_M,
                                      'crs': OUT_CRS, 'format': 'GEO_TIFF'})
            r = requests.get(url, timeout=900)
            r.raise_for_status()
            with open(path, 'wb') as f:
                f.write(r.content)
            return path
        except Exception:
            time.sleep(5 * (k + 1))
    return None

def log_row(y, m, thr, n_scenes, n_weeks):
    os.makedirs(OUT_ROOT, exist_ok=True)
    new = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['year', 'month', 'cloud_limit_used_pct', 'n_scenes', 'n_weekly_composites'])
        w.writerow([y, m, thr, n_scenes, n_weeks])

def download_month(y, m):
    year_dir = os.path.join(OUT_ROOT, str(y))
    os.makedirs(year_dir, exist_ok=True)
    out_tif = os.path.join(year_dir, f'Latur_S2_{y}_{m:02d}.tif')
    if os.path.exists(out_tif):
        print(f'{y}-{m:02d}: exists, skipped')
        return

    img, n_weeks, thr, n_scenes = monthly_from_weekly(y, m)
    if img is None:
        print(f'{y}-{m:02d}: no scenes even at {CLOUD_MAX}% cloud, skipped')
        log_row(y, m, 'none', 0, 0)
        return
    print(f'{y}-{m:02d}: cloud limit {thr}% | {n_scenes} scenes | '
          f'{n_weeks} weekly composites -> 1 monthly | {len(TILES)} tiles')

    tmp = os.path.join('/content/_tiles', f'{y}_{m:02d}')
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)

    paths, failed = [], []
    with ThreadPoolExecutor(N_WORKERS) as ex:
        futs = {ex.submit(download_tile, img, b, os.path.join(tmp, f't{i:03d}.tif')): i
                for i, b in enumerate(TILES)}
        for f in as_completed(futs):
            res = f.result()
            if res: paths.append(res)
            else:   failed.append(futs[f])
    if failed:
        print('   FAILED tiles (month not saved, re-run this cell):', sorted(failed))
        shutil.rmtree(tmp, ignore_errors=True)
        return

    srcs = [rasterio.open(p) for p in sorted(paths)]
    merge(srcs, nodata=0, dst_path=out_tif,
          dst_kwds={'compress': 'lzw', 'tiled': True, 'BIGTIFF': 'IF_SAFER'})
    for s in srcs: s.close()
    with rasterio.open(out_tif, 'r+') as dst:
        dst.descriptions = tuple(BANDS)
        dst.update_tags(CLOUD_LIMIT_PCT=str(thr), N_SCENES=str(n_scenes),
                        N_WEEKLY_COMPOSITES=str(n_weeks))
    shutil.rmtree(tmp, ignore_errors=True)
    log_row(y, m, thr, n_scenes, n_weeks)
    print('   saved', out_tif)

def run_year(y, months):
    for m in months:
        download_month(y, m)

# %% Cell 5 - 2021 (months 3, 4, 5, 6, 7, 8, 9, 10)
run_year(2021, [3, 4, 5, 6, 7, 8, 9, 10])

# %% Cell 6 (optional) - copy to Drive
# from google.colab import drive
# drive.mount('/content/drive')
# !cp -r /content/Latur_S2 /content/drive/MyDrive/