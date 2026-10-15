#!/usr/bin/env python3
"""
latur_s2_chirps_download.py
===========================
Downloads Sentinel-2 and CHIRPS data for Latur district directly to the local folder:
D:\\Droughtprj@2026\\output

Features:
- Uses local shapefile (Latur.shp) for the district boundary.
- For Sentinel-2 (large ~1 GB composites): Uses Earth Engine batch export to Google Drive,
  then AUTOMATICALLY downloads the GeoTIFF directly to your local output folder.
- For CHIRPS (small ~3 KB rasters): Downloads directly to local disk in seconds.
- Automatically detects already completed files on Google Drive and downloads them.
- Prevents duplicate Earth Engine tasks by tracking existing task statuses.
- Supports resuming from a specific year/month and dry-run mode.

Usage:
    python latur_s2_chirps_download.py                    # Normal run
    python latur_s2_chirps_download.py --sync-drive       # Download all files currently on Drive
    python latur_s2_chirps_download.py --resume 2021 11   # Resume from Nov 2021
    python latur_s2_chirps_download.py --dry-run          # Show planned actions
"""

import argparse
import calendar
import datetime as dt
import io
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import ee
import geemap
import geopandas as gpd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# =============================================================================
# SETTINGS
# =============================================================================
GEE_PROJECT = "igneous-effort-511512-c8"

YEARS  = list(range(2016, 2027))
MONTHS = list(range(1, 13))

MAX_CLOUD_PERCENT = 15

DOWNLOAD_S2     = True
DOWNLOAD_CHIRPS = True

# Local output folder (root)
OUTPUT_DIR = r"D:\Droughtprj@2026\output"

# Subfolders for organized storage
S2_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "sentinel")
CHIRPS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "chirps")

# Google Drive folder for large batch exports
DRIVE_FOLDER = "Latur_Drought"

# Local shapefile for Latur boundary
SHAPEFILE_PATH = r"D:\Droughtprj@2026\Latur.shp"

S2_BANDS  = ["B2", "B3", "B4", "B8", "B11", "B12"]
S2_NAMES  = ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]
S2_SCALE  = 10
CRS       = "EPSG:32643"
NODATA    = -9999

PAUSE_AFTER_YEAR = False  # Disabled by default so scripts do not hang indefinitely

# Task monitoring
TASK_POLL_INTERVAL = 30  # seconds
TASK_TIMEOUT = 3600 * 6  # 6 hours max per task
# =============================================================================


def init_ee():
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)


# ----------------------------------------------------------------------------- Google Drive API
def get_drive_service():
    """Build an authenticated Google Drive API service using existing EE credentials."""
    creds_path = os.path.expanduser(r"~/.config/earthengine/credentials")
    if not os.path.exists(creds_path):
        return None
    try:
        with open(creds_path, "r", encoding="utf-8") as f:
            c = json.load(f)
        import ee.oauth
        creds = Credentials(
            None,
            refresh_token=c["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=ee.oauth.CLIENT_ID,
            client_secret=ee.oauth.CLIENT_SECRET,
            scopes=c.get("scopes", ["https://www.googleapis.com/auth/drive"]),
        )
        creds.refresh(Request())
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"  [Warning] Could not initialize Google Drive API: {e}")
        return None


def get_drive_folder_id(drive_service, folder_name=DRIVE_FOLDER):
    """Find the folder ID for the target Drive folder."""
    if not drive_service:
        return None
    try:
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = drive_service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]
    except Exception as e:
        print(f"  [Warning] Error locating folder '{folder_name}' in Drive: {e}")
    return None


def list_drive_files_in_folder(drive_service, folder_id):
    """Returns a dict mapping filename -> file metadata for files inside the Drive folder."""
    if not drive_service or not folder_id:
        return {}
    drive_files = {}
    page_token = None
    try:
        while True:
            res = drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                pageSize=100,
                fields="nextPageToken, files(id, name, size)",
                pageToken=page_token,
            ).execute()
            for f in res.get("files", []):
                drive_files[f["name"]] = f
            page_token = res.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        print(f"  [Warning] Error listing files in Drive folder: {e}")
    return drive_files


def download_file_from_drive(drive_service, file_id, file_name, out_dir):
    """Downloads a file directly from Google Drive into the local folder with progress."""
    out_path = os.path.join(out_dir, file_name)
    temp_path = out_path + ".tmp"
    print(f"      downloading from Google Drive -> {out_path}...")
    try:
        request = drive_service.files().get_media(fileId=file_id)
        with open(temp_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024 * 10)
            done = False
            last_pct = 0
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    if pct - last_pct >= 20 or done:
                        print(f"        {pct}% downloaded...")
                        last_pct = pct
        if os.path.exists(out_path):
            os.remove(out_path)
        os.rename(temp_path, out_path)
        print(f"      [OK] Saved locally: {file_name} ({os.path.getsize(out_path)/(1024*1024):.1f} MB)")
        return True
    except Exception as e:
        print(f"      [Error] Download from Drive failed: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False


def sync_all_drive_files(drive_service, s2_root, chirps_root, folder_name=DRIVE_FOLDER):
    """Downloads all files from the Drive folder to the local output folders organized by year."""
    folder_id = get_drive_folder_id(drive_service, folder_name)
    if not folder_id:
        print(f"Drive folder '{folder_name}' not found.")
        return
    drive_files = list_drive_files_in_folder(drive_service, folder_id)
    print(f"\nFound {len(drive_files)} files in Google Drive '{folder_name}'.")
    downloaded = 0
    for name, f in sorted(drive_files.items()):
        # Determine dataset and year from filename
        if name.startswith("S2_Latur_"):
            # S2_Latur_2016_03.tif -> year=2016
            parts = name.split("_")
            if len(parts) >= 3:
                year = parts[2]
                out_dir = os.path.join(s2_root, year)
            else:
                out_dir = s2_root
        elif name.startswith("CHIRPS_Latur_"):
            # CHIRPS_Latur_2016_01_mm.tif -> year=2016
            parts = name.split("_")
            if len(parts) >= 3:
                year = parts[2]
                out_dir = os.path.join(chirps_root, year)
            else:
                out_dir = chirps_root
        else:
            out_dir = OUTPUT_DIR
        
        os.makedirs(out_dir, exist_ok=True)
        local_path = os.path.join(out_dir, name)
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            print(f"  {name} already exists locally, skipping.")
            continue
        ok = download_file_from_drive(drive_service, f["id"], name, out_dir)
        if ok:
            downloaded += 1
    print(f"Sync complete. Downloaded {downloaded} new files to organized folders.\n")


def get_s2_output_dir(year):
    """Get the Sentinel-2 output directory for a specific year."""
    path = os.path.join(S2_OUTPUT_DIR, str(year))
    os.makedirs(path, exist_ok=True)
    return path


def get_chirps_output_dir(year):
    """Get the CHIRPS output directory for a specific year."""
    path = os.path.join(CHIRPS_OUTPUT_DIR, str(year))
    os.makedirs(path, exist_ok=True)
    return path


# ----------------------------------------------------------------------------- Task Management
def get_existing_tasks():
    """Fetch all existing EE tasks and return a dict mapping description -> state."""
    print("  Querying existing Earth Engine tasks...")
    try:
        tasks = ee.data.getTaskList()
        task_map = {}
        for t in tasks:
            desc = t.get("description", "")
            state = t.get("state", "")
            task_map[desc] = state
        print(f"  Found {len(task_map)} existing tasks on Earth Engine")
        return task_map
    except Exception as e:
        print(f"  [Warning] Could not list EE tasks: {e}")
        return {}


def is_task_submitted(task_map, name):
    state = task_map.get(name)
    if state in ("READY", "RUNNING", "COMPLETED"):
        return True, state
    return False, state


def file_exists_locally(name, out_dir):
    """Check if file exists in the given directory."""
    path = os.path.join(out_dir, f"{name}.tif")
    return os.path.exists(path) and os.path.getsize(path) > 0


def s2_file_exists_locally(name, year):
    """Check if Sentinel-2 file exists in year-specific folder."""
    out_dir = get_s2_output_dir(year)
    return file_exists_locally(name, out_dir)


def chirps_file_exists_locally(name, year):
    """Check if CHIRPS file exists in year-specific folder."""
    out_dir = get_chirps_output_dir(year)
    return file_exists_locally(name, out_dir)


def wait_for_task(task, description, timeout=TASK_TIMEOUT):
    """Wait for EE batch task to complete. Returns True if successful."""
    print(f"      waiting for EE task: {description}...")
    start = time.time()
    while time.time() - start < timeout:
        status = task.status()
        state = status["state"]
        if state == "COMPLETED":
            print(f"      EE task completed: {description}")
            return True
        if state in ("FAILED", "CANCELLED"):
            err = status.get("error_message", "unknown error")
            print(f"      EE task FAILED: {description} - {err}")
            return False
        if state == "RUNNING":
            elapsed = int(time.time() - start)
            print(f"      running... ({elapsed}s)")
        time.sleep(TASK_POLL_INTERVAL)
    print(f"      EE task TIMEOUT: {description}")
    return False


def export_s2_to_drive(image, name, region, scale, crs, drive_folder):
    """Start batch export to Google Drive for large Sentinel-2 images."""
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=name,
        folder=drive_folder,
        fileNamePrefix=name,
        region=region,
        scale=scale,
        crs=crs,
        maxPixels=1e13,
        fileFormat="GeoTIFF",
        formatOptions={"cloudOptimized": True, "noData": NODATA},
    )
    task.start()
    return task


# ----------------------------------------------------------------------------- Geometry & Dates
def load_aoi():
    """Load Latur boundary from local shapefile and convert to EE geometry."""
    gdf = gpd.read_file(SHAPEFILE_PATH)
    gdf = gdf.to_crs("EPSG:4326")
    fc = geemap.gdf_to_ee(gdf)
    return fc.geometry()


def month_range(year, month):
    start = dt.date(year, month, 1)
    end = dt.date(year + (month == 12), (month % 12) + 1, 1)
    return start.isoformat(), end.isoformat()


def week_windows(year, month):
    _, month_end = month_range(year, month)
    starts = [1, 8, 15, 22]
    weeks = []
    for i, d in enumerate(starts):
        ws = dt.date(year, month, d).isoformat()
        we = dt.date(year, month, starts[i + 1]).isoformat() if i < 3 else month_end
        weeks.append((ws, we))
    return weeks


def months_to_process(year, resume_year=None, resume_month=None):
    today = dt.date.today()
    if year > today.year:
        return []
    if year == today.year:
        months = [m for m in MONTHS if m < today.month]
    else:
        months = MONTHS

    if resume_year is not None:
        if year < resume_year:
            return []
        if year == resume_year and resume_month is not None:
            months = [m for m in months if m >= resume_month]
    return months


def s2_name(year, month):
    return f"S2_Latur_{year}_{month:02d}"


def chirps_name(year, month):
    return f"CHIRPS_Latur_{year}_{month:02d}_mm"


# ----------------------------------------------------------------------------- Sentinel-2
def s2_collection(start, end, aoi, year):
    if year >= 2019:
        cid, has_scl = "COPERNICUS/S2_SR_HARMONIZED", True
    else:
        cid, has_scl = "COPERNICUS/S2_HARMONIZED", False

    cloud_score = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    col = (
        ee.ImageCollection(cid)
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
        .linkCollection(cloud_score, ["cs_cdf"])
    )

    def mask_clouds(img):
        clear = img.select("cs_cdf").gte(0.60)
        if has_scl:
            scl = img.select("SCL")
            for v in (1, 3, 8, 9, 10, 11):
                clear = clear.And(scl.neq(v))
        bands = img.select(S2_BANDS).resample("bilinear")
        return bands.updateMask(clear).copyProperties(img, ["system:time_start"])

    return col.map(mask_clouds)


def s2_month(year, month, aoi):
    weekly = []
    for ws, we in week_windows(year, month):
        col = s2_collection(ws, we, aoi, year)
        weekly.append(col.median().set({"n_scenes": col.size()}))
    weekly_col = ee.ImageCollection.fromImages(weekly)
    scenes_per_week = weekly_col.aggregate_array("n_scenes").getInfo()
    weekly_col = weekly_col.filter(ee.Filter.gt("n_scenes", 0))
    return weekly_col, scenes_per_week


def run_s2(year, months, aoi, s2_root, drive_folder, drive_service, drive_files, dry_run=False, task_map=None):
    product = "L2A" if year >= 2019 else "L1C"
    print(f"  Sentinel-2 {product}, cloud < {MAX_CLOUD_PERCENT}%")
    for m in months:
        name = s2_name(year, m)
        tif_filename = f"{name}.tif"
        s2_dir = get_s2_output_dir(year)

        # 1. Already exists locally
        if s2_file_exists_locally(name, year):
            print(f"    {year}-{m:02d}  already exists locally in sentinel/{year}/, skipping")
            continue

        # 2. Already completed on Google Drive -> Download immediately!
        if drive_service and tif_filename in drive_files:
            print(f"    {year}-{m:02d}  found in Google Drive '{drive_folder}', downloading locally...")
            if not dry_run:
                f_meta = drive_files[tif_filename]
                download_file_from_drive(drive_service, f_meta["id"], tif_filename, s2_dir)
            else:
                print(f"      [DRY-RUN] Would download {tif_filename} from Drive")
            continue

        # 3. Check existing EE tasks
        if task_map:
            submitted, state = is_task_submitted(task_map, name)
            if submitted:
                if state == "COMPLETED":
                    print(f"    {year}-{m:02d}  EE task completed on server. Searching Drive for file...")
                    if drive_service and not dry_run:
                        # Re-check Drive in case it just appeared
                        folder_id = get_drive_folder_id(drive_service, drive_folder)
                        latest_files = list_drive_files_in_folder(drive_service, folder_id)
                        if tif_filename in latest_files:
                            download_file_from_drive(drive_service, latest_files[tif_filename]["id"], tif_filename, s2_dir)
                            continue
                elif state in ("READY", "RUNNING"):
                    print(f"    {year}-{m:02d}  EE task is currently {state}, waiting for it...")
                    # Let it run in background or wait
                    continue

        if dry_run:
            print(f"    {year}-{m:02d}  [DRY-RUN] Would submit EE batch export for {name}.tif and auto-download to sentinel/{year}/")
            continue

        weekly_col, spw = s2_month(year, m, aoi)
        usable = sum(1 for n in spw if n > 0)
        print(f"    {year}-{m:02d}  scenes per week {spw}  -> {usable} weeks used")
        if usable == 0:
            print(f"      !! no scenes under {MAX_CLOUD_PERCENT}% cloud - month skipped")
            continue

        monthly = (
            weekly_col.select(S2_BANDS)
            .median()
            .rename(S2_NAMES)
            .round()
            .toInt16()
            .unmask(NODATA)
            .clip(aoi)
        )
        task = export_s2_to_drive(monthly, name, aoi.bounds(), S2_SCALE, CRS, drive_folder)
        ok = wait_for_task(task, name)
        if ok and drive_service:
            # Auto-download from Drive now
            folder_id = get_drive_folder_id(drive_service, drive_folder)
            latest_files = list_drive_files_in_folder(drive_service, folder_id)
            if tif_filename in latest_files:
                download_file_from_drive(drive_service, latest_files[tif_filename]["id"], tif_filename, s2_dir)
            else:
                print(f"      [Notice] Task completed, file should appear shortly in Drive.")


# ----------------------------------------------------------------------------- CHIRPS
def run_chirps(year, months, aoi, chirps_root, dry_run=False, task_map=None):
    """Directly downloads CHIRPS monthly rainfall (mm/month) to local disk."""
    print("  CHIRPS monthly rainfall (mm/month)")
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation")
    region = aoi.buffer(6000)
    for m in months:
        name = chirps_name(year, m)
        chirps_dir = get_chirps_output_dir(year)
        file_path = os.path.join(chirps_dir, f"{name}.tif")

        if chirps_file_exists_locally(name, year):
            print(f"    {year}-{m:02d}  already exists locally in chirps/{year}/, skipping")
            continue

        if dry_run:
            print(f"    {year}-{m:02d}  [DRY-RUN] Would download: {name}.tif directly to chirps/{year}/")
            continue

        start, end = month_range(year, m)
        daily = chirps.filterDate(start, end)
        n_days = daily.size().getInfo()
        days_in_month = calendar.monthrange(year, m)[1]
        if n_days < days_in_month:
            print(f"    {year}-{m:02d}  only {n_days}/{days_in_month} days published - skipped")
            continue
        print(f"    {year}-{m:02d}  {n_days} days summed")

        rain = daily.sum().rename("rainfall_mm").toFloat().unmask(NODATA).clip(region)
        print(f"      downloading directly to {file_path}...")
        try:
            geemap.ee_export_image(
                rain,
                filename=file_path,
                scale=5566,
                crs="EPSG:4326",
                region=region.bounds(),
                file_per_band=False,
                verbose=False,
            )
            print(f"      [OK] Saved locally: chirps/{year}/{name}.tif")
        except Exception as e:
            print(f"      !! CHIRPS export failed for {name}: {e}")


# ----------------------------------------------------------------------------- Main
def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Sentinel-2 and CHIRPS data for Latur directly to your local folder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without submitting tasks")
    parser.add_argument("--sync-drive", action="store_true", help="Download all completed files from Google Drive to local output folder and exit")
    parser.add_argument(
        "--resume",
        nargs="+",
        type=int,
        metavar=("YEAR", "MONTH"),
        help="Resume from a specific year and optional month (e.g. --resume 2021 11)",
    )
    parser.add_argument("--pause", action="store_true", help="Prompt to press Enter after each year finishes")
    return parser.parse_args()


def main():
    args = parse_args()
    dry_run = args.dry_run

    if dry_run:
        print("=" * 60)
        print("DRY-RUN MODE - No downloads or tasks will be submitted")
        print("=" * 60)

    init_ee()
    os.makedirs(S2_OUTPUT_DIR, exist_ok=True)
    os.makedirs(CHIRPS_OUTPUT_DIR, exist_ok=True)

    drive_service = get_drive_service()
    if drive_service:
        print(f"Connected to Google Drive API successfully.")
    else:
        print(f"[Warning] Google Drive API connection not available.")

    # If --sync-drive flag is passed, just download all existing files from Drive
    if args.sync_drive:
        if drive_service:
            sync_all_drive_files(drive_service, S2_OUTPUT_DIR, CHIRPS_OUTPUT_DIR, DRIVE_FOLDER)
        else:
            print("Google Drive service unavailable.")
        return

    # Parse resume parameters
    resume_year = None
    resume_month = None
    if args.resume:
        resume_year = args.resume[0]
        if len(args.resume) > 1:
            resume_month = args.resume[1]
        print(f"Resume point: year={resume_year}, month={resume_month or 1}")

    task_map = get_existing_tasks()

    # Pre-fetch files in Google Drive folder so we can download immediately
    drive_files = {}
    if drive_service:
        folder_id = get_drive_folder_id(drive_service, DRIVE_FOLDER)
        if folder_id:
            drive_files = list_drive_files_in_folder(drive_service, folder_id)
            print(f"Found {len(drive_files)} existing GeoTIFF files in Google Drive '{DRIVE_FOLDER}'.")

    aoi = load_aoi()
    area_km2 = round(aoi.area(100).getInfo() / 1e6)
    print(f"Study area: Latur district, {area_km2} km2")
    print(f"Local output folders: {S2_OUTPUT_DIR} (sentinel), {CHIRPS_OUTPUT_DIR} (chirps)")

    for year in YEARS:
        months = months_to_process(year, resume_year, resume_month)
        print(f"\n========== {year}  (months {months}) ==========")
        if not months:
            print("  nothing to download")
            continue

        if DOWNLOAD_S2:
            run_s2(year, months, aoi, S2_OUTPUT_DIR, DRIVE_FOLDER, drive_service, drive_files, dry_run, task_map)

        if DOWNLOAD_CHIRPS:
            run_chirps(year, months, aoi, CHIRPS_OUTPUT_DIR, dry_run, task_map)

        if args.pause and year != YEARS[-1]:
            input(f"\nYear {year} done. Press Enter to continue to next year...")

    print(f"\nProcessing complete! Files saved in:")
    print(f"  Sentinel-2: {S2_OUTPUT_DIR}/<year>/")
    print(f"  CHIRPS:     {CHIRPS_OUTPUT_DIR}/<year>/")


if __name__ == "__main__":
    main()