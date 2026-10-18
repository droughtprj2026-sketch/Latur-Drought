import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";
export const dynamicParams = true;

// Path resolution - works from both repo root and frontend/
const POSSIBLE_DASH_DIRS = [
  path.join(process.cwd(), "data", "dashboard"),
  path.join(process.cwd(), "..", "data", "dashboard"),
];
let DASH_DIR = POSSIBLE_DASH_DIRS[0];
if (!fs.existsSync(DASH_DIR)) {
  DASH_DIR = POSSIBLE_DASH_DIRS[1];
}
const PROCESSED_JSON_DIR = path.join(DASH_DIR, "json");
const POSSIBLE_PUBLIC_DIRS = [
  path.join(process.cwd(), "frontend", "public", "data"),
  path.join(process.cwd(), "public", "data"),
];
let PUBLIC_DATA_DIR = POSSIBLE_PUBLIC_DIRS[0];
if (!fs.existsSync(PUBLIC_DATA_DIR)) {
  PUBLIC_DATA_DIR = POSSIBLE_PUBLIC_DIRS[1];
}

// In-memory caches invalidated on file mtime change
let latestStatusCache: any = null;
let latestStatusCacheMtime: number | null = null;
let dataAvailabilityCache: any = null;
let dataAvailabilityCacheMtime: number | null = null;
let processingManifestCache: any = null;
let processingManifestCacheMtime: number | null = null;
let districtMonthlyCache: any = null;
let districtMonthlyCacheMtime: number | null = null;
let villageTimeseriesCache: Record<string, any[]> | null = null;
let villageTimeseriesCacheMtime: number | null = null;
let tehsilAnalyticsCache: any = null;
let tehsilAnalyticsCacheMtime: number | null = null;
let villageLatestCache: any = null;
let villageLatestCacheMtime: number | null = null;
let villageGeojsonCache: any = null;
let villageGeojsonCacheMtime: number | null = null;

function _readJsonIfChanged(fPath: string, cache: any, mtime: number | null): { data: any; mtime: number } | null {
  if (!fs.existsSync(fPath)) return null;
  const stat = fs.statSync(fPath);
  if (cache !== null && mtime !== null && stat.mtimeMs === mtime) {
    return { data: cache, mtime };
  }
  try {
    const data = JSON.parse(fs.readFileSync(fPath, "utf8"));
    return { data, mtime: stat.mtimeMs };
  } catch (e) {
    console.error(`[Vercel API] Error reading ${fPath}:`, e);
    return null;
  }
}

function getLatestStatus() {
  const result = _readJsonIfChanged(
    path.join(DASH_DIR, "latest_status.json"),
    latestStatusCache,
    latestStatusCacheMtime,
  );
  if (result) {
    latestStatusCache = result.data;
    latestStatusCacheMtime = result.mtime;
    return result.data;
  }
  const fallback = _readJsonIfChanged(
    path.join(PUBLIC_DATA_DIR, "latest_status.json"),
    latestStatusCache,
    latestStatusCacheMtime,
  );
  if (fallback) {
    latestStatusCache = fallback.data;
    latestStatusCacheMtime = fallback.mtime;
    return fallback.data;
  }
  return null;
}

function getDataAvailability() {
  const result = _readJsonIfChanged(
    path.join(DASH_DIR, "data_availability.json"),
    dataAvailabilityCache,
    dataAvailabilityCacheMtime,
  );
  if (result) {
    dataAvailabilityCache = result.data;
    dataAvailabilityCacheMtime = result.mtime;
    return result.data;
  }
  return null;
}

function getProcessingManifest() {
  const result = _readJsonIfChanged(
    path.join(DASH_DIR, "processing_manifest.json"),
    processingManifestCache,
    processingManifestCacheMtime,
  );
  if (result) {
    processingManifestCache = result.data;
    processingManifestCacheMtime = result.mtime;
    return result.data;
  }
  return null;
}

function getDistrictMonthly() {
  const result = _readJsonIfChanged(
    path.join(PROCESSED_JSON_DIR, "district_monthly.json"),
    districtMonthlyCache,
    districtMonthlyCacheMtime,
  );
  if (result) {
    districtMonthlyCache = result.data;
    districtMonthlyCacheMtime = result.mtime;
    return result.data;
  }
  const fallback = _readJsonIfChanged(
    path.join(PUBLIC_DATA_DIR, "district_monthly.json"),
    districtMonthlyCache,
    districtMonthlyCacheMtime,
  );
  if (fallback) {
    districtMonthlyCache = fallback.data;
    districtMonthlyCacheMtime = fallback.mtime;
    return fallback.data;
  }
  return null;
}

function getVillageTimeseries() {
  const result = _readJsonIfChanged(
    path.join(PUBLIC_DATA_DIR, "village_timeseries.json"),
    villageTimeseriesCache,
    villageTimeseriesCacheMtime,
  );
  if (result) {
    villageTimeseriesCache = result.data;
    villageTimeseriesCacheMtime = result.mtime;
  }
  return villageTimeseriesCache;
}

function getTehsilAnalytics() {
  const result = _readJsonIfChanged(
    path.join(PUBLIC_DATA_DIR, "tehsil_analytics.json"),
    tehsilAnalyticsCache,
    tehsilAnalyticsCacheMtime,
  );
  if (result) {
    tehsilAnalyticsCache = result.data;
    tehsilAnalyticsCacheMtime = result.mtime;
  }
  return tehsilAnalyticsCache;
}

function getVillageLatest() {
  const result = _readJsonIfChanged(
    path.join(PROCESSED_JSON_DIR, "village_latest.json"),
    villageLatestCache,
    villageLatestCacheMtime,
  );
  if (result) {
    villageLatestCache = result.data;
    villageLatestCacheMtime = result.mtime;
    return result.data;
  }
  const fallback = _readJsonIfChanged(
    path.join(PUBLIC_DATA_DIR, "village_latest.json"),
    villageLatestCache,
    villageLatestCacheMtime,
  );
  if (fallback) {
    villageLatestCache = fallback.data;
    villageLatestCacheMtime = fallback.mtime;
    return fallback.data;
  }
  return null;
}

function getVillageBaselines() {
  const result = _readJsonIfChanged(
    path.join(PUBLIC_DATA_DIR, "village_baselines.json"),
    villageLatestCache,
    villageLatestCacheMtime,
  );
  if (result) {
    villageLatestCache = result.data;
    villageLatestCacheMtime = result.mtime;
    return result.data;
  }
  return null;
}

function getVillagesGeojson() {
  const result = _readJsonIfChanged(
    path.join(PUBLIC_DATA_DIR, "latur_villages_latest.geojson"),
    villageGeojsonCache,
    villageGeojsonCacheMtime,
  );
  if (result) {
    villageGeojsonCache = result.data;
    villageGeojsonCacheMtime = result.mtime;
    return result.data;
  }
  return null;
}

function parseMasterCsv(): any[] {
  const result = _readCsvIfChanged(path.join(DASH_DIR, "drought_monitoring_master.csv"));
  if (!result) return [];
  const raw = result.data;
  const lines = raw.split(/\r?\n/).filter(Boolean);
  if (!lines.length) return [];
  const headers = lines[0].split(",").map((h) => h.trim());
  const rows: Record<string, string>[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",");
    const row: Record<string, string> = {};
    for (let j = 0; j < headers.length; j++) {
      row[headers[j]] = parts[j] ?? "";
    }
    rows.push(row);
  }
  return rows;
}

function _readCsvIfChanged(fPath: string): { data: string; mtime: number } | null {
  if (!fs.existsSync(fPath)) return null;
  const stat = fs.statSync(fPath);
  try {
    const data = fs.readFileSync(fPath, "utf8");
    return { data, mtime: stat.mtimeMs };
  } catch (e) {
    console.error(`[Vercel API] Error reading ${fPath}:`, e);
    return null;
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { slug: string[] } }
) {
  const slug = params.slug || [];
  const route = slug.join("/");
  const { searchParams } = new URL(request.url);

  // 1. Health check
  if (route === "health") {
    return NextResponse.json({
      status: "ok",
      platform: "vercel-native",
      timestamp: new Date().toISOString(),
    });
  }

  // 2. Status
  if (route === "status") {
    const data = getLatestStatus();
    if (data) return NextResponse.json(data);
    return NextResponse.json({
      generated_at: new Date().toISOString(),
      monitoring_status: "degraded",
      sentinel2: { latest_period_id: null, status: "no_data" },
      chirps: { latest_period_id: null, status: "no_data" },
      composite: { formula_version: "cdi-v2026.10" },
      region: { district: "Latur", state: "Maharashtra", centroid_lat: 18.4088, centroid_lon: 76.5604 },
    });
  }

  // 3. Manifest
  if (route === "manifest") {
    const data = getProcessingManifest();
    if (data) return NextResponse.json(data);
    return NextResponse.json({
      district: "Latur",
      years: [],
      as_of: new Date().toISOString(),
      indices: {},
    });
  }

  // 4. Availability
  if (route === "availability") {
    const data = getDataAvailability();
    if (data) return NextResponse.json(data);
    return NextResponse.json({ sentinel2: [], chirps: [], composite: [] });
  }

  // 5. Tehsils GeoJSON
  if (route === "tehsils") {
    const tPath = path.join(PUBLIC_DATA_DIR, "latur_tehsils.geojson");
    if (fs.existsSync(tPath)) {
      const data = JSON.parse(fs.readFileSync(tPath, "utf8"));
      return NextResponse.json(data, {
        headers: { "Cache-Control": "public, max-age=86400" },
      });
    }
    return NextResponse.json({ error: "Tehsil GeoJSON missing" }, { status: 404 });
  }

  // 6. Villages GeoJSON
  if (route === "villages" || route.startsWith("village-indices")) {
    const data = getVillagesGeojson();
    if (data) {
      return NextResponse.json(data, {
        headers: { "Cache-Control": "public, max-age=3600" },
      });
    }
    return NextResponse.json({ error: "Village GeoJSON missing" }, { status: 404 });
  }

  // 6b. Village Timeseries
  if (route === "timeseries") {
    const tehsil = String(searchParams.get("tehsil") ?? "").trim().toLowerCase();
    const village = String(searchParams.get("village") ?? "").trim().toLowerCase();
    const cache = getVillageTimeseries();
    if (cache && tehsil && village) {
      const key = `${tehsil}::${village}`;
      if (cache[key]) {
        return NextResponse.json(cache[key]);
      }
      for (const [k, pts] of Object.entries(cache)) {
        const [t, v] = k.split("::");
        if (t === tehsil && (v === village || v.includes(village) || village.includes(v))) {
          return NextResponse.json(pts);
        }
      }
    }
    return NextResponse.json([]);
  }

  // 7. District Timeseries
  if (route === "district-timeseries") {
    const data = getDistrictMonthly() || { series: [] };
    return NextResponse.json(data);
  }

  // 8. Tehsil Analytics
  if (route === "tehsil-analytics") {
    const data = getTehsilAnalytics() || {};
    return NextResponse.json(data);
  }

  // 9. Stats endpoint for period + tehsil aggregation
  if (route === "stats") {
    const period = String(searchParams.get("period") ?? "2026-10");
    const tehsilParam = String(searchParams.get("tehsil") ?? "All").trim();
    const isAll = !tehsilParam || tehsilParam.toLowerCase() === "all";

    const cache = getVillageTimeseries();
    if (!cache) {
      return NextResponse.json({
        period,
        tehsil: tehsilParam,
        total: 954,
        droughtCount: 0,
        d2PlusCount: 0,
        avgCdi: 0,
        pctDrought: 0,
        tehsil_ranking: [],
        classes_count: { None: 0, D0: 0, D1: 0, D2: 0, D3: 0, D4: 0 },
      });
    }

    const tehsilStats: Record<string, { tehsil: string; villages: number; sumCdi: number; cdiCount: number; droughtCount: number; d2Plus: number }> = {};
    let totalVillages = 0;
    let totalDrought = 0;
    let totalD2Plus = 0;
    let sumCdi = 0;
    let cdiCount = 0;
    const classesCount: Record<string, number> = { None: 0, D0: 0, D1: 0, D2: 0, D3: 0, D4: 0 };

    for (const [key, pts] of Object.entries(cache)) {
      const [tName] = key.split("::");
      const normalizedTehsil = tName.toLowerCase();

      if (!tehsilStats[normalizedTehsil]) {
        tehsilStats[normalizedTehsil] = {
          tehsil: tName.charAt(0).toUpperCase() + tName.slice(1),
          villages: 0,
          sumCdi: 0,
          cdiCount: 0,
          droughtCount: 0,
          d2Plus: 0,
        };
      }

      const pt = pts.find((x: any) => (x.p || x.date) === period);
      if (pt) {
        tehsilStats[normalizedTehsil].villages++;
        const cdi = pt.cdi != null ? Number(pt.cdi) : null;
        const cls = pt.cls || "None";

        if (cdi != null) {
          tehsilStats[normalizedTehsil].sumCdi += cdi;
          tehsilStats[normalizedTehsil].cdiCount++;
          if (cdi >= 0.20 || (cls && cls !== "None" && cls !== "ND")) {
            tehsilStats[normalizedTehsil].droughtCount++;
          }
          if (["D2", "D3", "D4"].includes(cls) || cdi >= 0.50) {
            tehsilStats[normalizedTehsil].d2Plus++;
          }
        }

        if (isAll || normalizedTehsil === tehsilParam.toLowerCase()) {
          totalVillages++;
          if (cdi != null) {
            sumCdi += cdi;
            cdiCount++;
            if (cdi >= 0.20 || (cls && cls !== "None" && cls !== "ND")) {
              totalDrought++;
            }
            if (["D2", "D3", "D4"].includes(cls) || cdi >= 0.50) {
              totalD2Plus++;
            }
            if (classesCount[cls] !== undefined) {
              classesCount[cls]++;
            } else {
              classesCount["None"]++;
            }
          }
        }
      }
    }

    const tehsilRanking = Object.values(tehsilStats)
      .map((t) => ({
        tehsil: t.tehsil,
        villages: t.villages,
        avg_cdi: t.cdiCount ? Number((t.sumCdi / t.cdiCount).toFixed(3)) : 0,
        drought_pct: t.villages ? Number(((t.droughtCount / t.villages) * 100).toFixed(1)) : 0,
        d2_plus: t.d2Plus,
      }))
      .sort((a, b) => b.avg_cdi - a.avg_cdi);

    return NextResponse.json({
      period,
      tehsil: tehsilParam,
      total: totalVillages,
      droughtCount: totalDrought,
      d2PlusCount: totalD2Plus,
      avgCdi: cdiCount > 0 ? Number((sumCdi / cdiCount).toFixed(3)) : 0,
      pctDrought: totalVillages > 0 ? Number(((totalDrought / totalVillages) * 100).toFixed(1)) : 0,
      classes_count: classesCount,
      tehsil_ranking: tehsilRanking,
    });
  }

  // 10. Latest village/tehsil data
  if (route === "latest") {
    const tehsil = String(searchParams.get("tehsil") ?? "Latur");
    const village = String(searchParams.get("village") ?? "");

    const vl = getVillageLatest();
    if (vl && vl.villages) {
      const villages = vl.villages as Record<string, any>;
      for (const v of Object.values(villages)) {
        if (
          v.tehsil?.toLowerCase() === tehsil.toLowerCase() &&
          (!village || v.village?.toLowerCase() === village.toLowerCase())
        ) {
          return NextResponse.json(v);
        }
      }
    }

    return NextResponse.json({
      tehsil,
      village,
      observation_period: null,
      CDI: null,
      CDI_class: null,
      NDVI: null,
      VHI: null,
      SPI_3: null,
      monitoring_status: "degraded",
      message: "No latest observation data available",
    });
  }

  // 11. Master rows
  if (route === "master") {
    const tehsil = String(searchParams.get("tehsil") ?? "").trim().toLowerCase();
    const village = String(searchParams.get("village") ?? "").trim().toLowerCase();
    const from = String(searchParams.get("from") ?? "");
    const to = String(searchParams.get("to") ?? "");

    const rows = parseMasterCsv();
    let filtered = rows;

    if (tehsil) {
      filtered = filtered.filter((r) => (r.tehsil || "").toLowerCase() === tehsil);
    }
    if (village) {
      filtered = filtered.filter((r) => (r.village || "").toLowerCase() === village);
    } else if (tehsil && !searchParams.get("village")) {
      filtered = filtered.filter((r) => !r.village || r.village.trim() === "");
    }
    if (from) filtered = filtered.filter((r) => (r.observation_period || "") >= from);
    if (to) filtered = filtered.filter((r) => (r.observation_period || "") <= to);

    return NextResponse.json(filtered);
  }

  // 12. Indices GeoJSON
  if (slug[0] === "indices" && slug.length >= 4) {
    const name = slug[1].toLowerCase();
    const year = slug[2];
    const month = String(slug[3]).padStart(2, "0");
    const period = `${year}-${month}`;

    const rawGj = getVillagesGeojson();
    if (rawGj && rawGj.features) {
      try {
        const cache = getVillageTimeseries();
        const features = rawGj.features.map((f: any) => {
          const p = f.properties || {};
          const t = (p.tehsil || p.TEHSIL || "").trim().toLowerCase();
          const v = (p.village || p.VILLAGE || p.name || "").trim().toLowerCase();
          const key = `${t}::${v}`;
          const pts = cache ? cache[key] : null;
          const match = pts?.find((x: any) => (x.p || x.date) === period);

          let val: number | null = null;
          if (match) {
            switch (name) {
              case "cdi":
              case "cdi_class":
                val = match.cdi ?? null;
                break;
              case "ndvi":
                val = match.ndvi ?? null;
                break;
              case "evi":
                val = match.evi ?? match.ndvi ?? null;
                break;
              case "vci":
                val = match.vci ?? null;
                break;
              case "vhi":
                val = match.vhi ?? null;
                break;
              case "spi":
              case "spi3":
                val = match.spi3 ?? match.spi1 ?? null;
                break;
              case "spi1":
                val = match.spi1 ?? null;
                break;
              case "spi6":
                val = match.spi6 ?? null;
                break;
              case "spi12":
                val = match.spi12 ?? null;
                break;
              case "rain":
              case "pci":
                val = match.rain ?? match.pci ?? null;
                break;
              default:
                val = match[name] != null ? match[name] : (match.cdi ?? null);
            }
          }

          return {
            ...f,
            properties: {
              ...p,
              value: val != null && !isNaN(val) ? Number(val) : null,
              class: match?.cls || "None",
              cdi: match?.cdi ?? null,
              spi1: match?.spi1 ?? null,
              spi3: match?.spi3 ?? null,
              spi6: match?.spi6 ?? null,
              spi12: match?.spi12 ?? null,
              ndvi: match?.ndvi ?? null,
              evi: match?.evi ?? match?.ndvi ?? null,
              vci: match?.vci ?? null,
              vhi: match?.vhi ?? null,
              pci: match?.pci ?? match?.rain ?? null,
              rain: match?.rain ?? null,
              period,
            },
          };
        });

        return NextResponse.json(
          { type: "FeatureCollection", features },
          { headers: { "Cache-Control": "public, max-age=3600" } }
        );
      } catch (err) {
        console.error("[Vercel API] Error synthesizing index GeoJSON:", err);
      }
    }
    return NextResponse.json({ error: "Index GeoJSON synthesis failed" }, { status: 404 });
  }

  // 13. Animation frames
  if (route === "animation") {
    const index = String(searchParams.get("index") ?? "cdi").toLowerCase();
    const from = String(searchParams.get("from") ?? "2016-01");
    const to = String(searchParams.get("to") ?? "2026-10");

    const dm = getDistrictMonthly();
    const periods: string[] = (dm?.series || []).map((s: any) => s.date).filter(Boolean);
    const filtered = periods.filter((p) => p >= from && p <= to);
    const frames = filtered.map((p) => {
      const [y, m] = p.split("-");
      return {
        period: p,
        geojson_url: `/api/v1/indices/${index}/${y}/${m}`,
      };
    });

    return NextResponse.json({
      index,
      count: frames.length,
      frames,
    });
  }

  // 14. Compare
  if (route === "compare") {
    const a = String(searchParams.get("a") ?? "2018-05");
    const b = String(searchParams.get("b") ?? "2026-10");
    const dm = getDistrictMonthly();
    const matchA = (dm?.series || []).find((s: any) => s.date === a);
    const matchB = (dm?.series || []).find((s: any) => s.date === b);

    return NextResponse.json({
      a: { period: a, rows: matchA ? [matchA] : [] },
      b: { period: b, rows: matchB ? [matchB] : [] },
    });
  }

  // 15. Village Baselines
  if (route === "baselines") {
    const bPath = path.join(PUBLIC_DATA_DIR, "village_baselines.json");
    if (fs.existsSync(bPath)) {
      try {
        const data = JSON.parse(fs.readFileSync(bPath, "utf8"));
        return NextResponse.json(data);
      } catch (e) {
        console.error("[Vercel API] Error reading baselines:", e);
      }
    }
    return NextResponse.json({ baselines: {} });
  }

  return NextResponse.json({ error: `Not Found: /api/v1/${route}` }, { status: 404 });
}
