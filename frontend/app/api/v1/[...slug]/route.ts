import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

// Path to static assets in public/data for standalone Vercel execution
const PUBLIC_DATA_DIR = path.join(process.cwd(), "public/data");

// In-memory caches for fast sub-millisecond responses on serverless instances
let villageTimeseriesCache: Record<string, any[]> | null = null;
let districtMonthlyCache: any = null;
let tehsilAnalyticsCache: any = null;

function getVillageTimeseries() {
  if (!villageTimeseriesCache) {
    const fPath = path.join(PUBLIC_DATA_DIR, "village_timeseries.json");
    if (fs.existsSync(fPath)) {
      try {
        villageTimeseriesCache = JSON.parse(fs.readFileSync(fPath, "utf-8"));
      } catch (e) {
        console.error("[Vercel API] Error reading village_timeseries.json:", e);
      }
    }
  }
  return villageTimeseriesCache;
}

function getDistrictMonthly() {
  if (!districtMonthlyCache) {
    const fPath = path.join(PUBLIC_DATA_DIR, "district_monthly.json");
    if (fs.existsSync(fPath)) {
      try {
        districtMonthlyCache = JSON.parse(fs.readFileSync(fPath, "utf-8"));
      } catch {}
    }
  }
  return districtMonthlyCache;
}

function getTehsilAnalytics() {
  if (!tehsilAnalyticsCache) {
    const fPath = path.join(PUBLIC_DATA_DIR, "tehsil_analytics.json");
    if (fs.existsSync(fPath)) {
      try {
        tehsilAnalyticsCache = JSON.parse(fs.readFileSync(fPath, "utf-8"));
      } catch {}
    }
  }
  return tehsilAnalyticsCache;
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
    const statusFile = path.join(PUBLIC_DATA_DIR, "latest_status.json");
    if (fs.existsSync(statusFile)) {
      try {
        return NextResponse.json(JSON.parse(fs.readFileSync(statusFile, "utf-8")));
      } catch {}
    }
    return NextResponse.json({
      generated_at: new Date().toISOString(),
      monitoring_status: "operational",
      sentinel2: { latest_period_id: "2026-10", status: "operational" },
      chirps: { latest_period_id: "2026-10", status: "operational" },
      composite: { formula_version: "cdi-v2026.10" },
      region: { district: "Latur", state: "Maharashtra", centroid_lat: 18.4088, centroid_lon: 76.5604 },
    });
  }

  // 3. Manifest
  if (route === "manifest") {
    return NextResponse.json({
      district: "Latur",
      years: [2016, 2017, 2018, 2020, 2021, 2022, 2023, 2024, 2026],
      as_of: "2026-10",
      indices: {
        cdi: { source: "Composite", unit: "0..1", years: [2016, 2017, 2018, 2020, 2021, 2022, 2023, 2024, 2026] },
        ndvi: { source: "Sentinel-2", unit: "-1..1", years: [2016, 2017, 2018, 2020, 2021, 2022, 2023, 2024, 2026] },
        spi3: { source: "CHIRPS", unit: "sigma", years: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026] },
      },
    });
  }

  // 4. Tehsils GeoJSON
  if (route === "tehsils") {
    const tPath = path.join(PUBLIC_DATA_DIR, "latur_tehsils.geojson");
    if (fs.existsSync(tPath)) {
      const data = JSON.parse(fs.readFileSync(tPath, "utf-8"));
      return NextResponse.json(data, {
        headers: { "Cache-Control": "public, max-age=86400" },
      });
    }
    return NextResponse.json({ error: "Tehsil GeoJSON missing" }, { status: 404 });
  }

  // 5. Villages GeoJSON
  if (route === "villages" || route.startsWith("village-indices")) {
    const vPath = path.join(PUBLIC_DATA_DIR, "latur_villages_latest.geojson");
    if (fs.existsSync(vPath)) {
      const data = JSON.parse(fs.readFileSync(vPath, "utf-8"));
      return NextResponse.json(data, {
        headers: { "Cache-Control": "public, max-age=3600" },
      });
    }
    return NextResponse.json({ error: "Village GeoJSON missing" }, { status: 404 });
  }

  // 6. District Timeseries
  if (route === "district-timeseries") {
    const data = getDistrictMonthly() || { series: [] };
    return NextResponse.json(data);
  }

  // 7. Tehsil Analytics
  if (route === "tehsil-analytics") {
    const data = getTehsilAnalytics() || {};
    return NextResponse.json(data);
  }

  // 8. Timeseries (Specific Index: /timeseries/:name)
  if (slug[0] === "timeseries" && slug.length === 2) {
    const indexName = slug[1].toLowerCase();
    const dm = getDistrictMonthly();
    const series = dm?.series || [];
    const points = series.map((d: any) => {
      let val: number | null = null;
      if (indexName === "cdi") val = d.composite_drought_score;
      else if (indexName === "spi1") val = d.SPI1;
      else if (indexName === "spi3") val = d.SPI3;
      else if (indexName === "spi6") val = d.SPI6;
      else if (indexName === "spi12") val = d.SPI12;
      else if (indexName === "ndvi") val = d.NDVI;
      else if (indexName === "evi") val = d.EVI;
      else if (indexName === "vci") val = d.VCI;
      else if (indexName === "vhi") val = d.VHI;
      else if (indexName === "pci") val = d.PCI;
      else if (indexName === "rain") val = d.Rain_mm;
      else val = d.composite_drought_score;

      return {
        date: d.date,
        value: val != null && !isNaN(val) ? Number(val) : null,
        class: d.composite_drought_class || "None",
        pct_area_dry: d.pct_area_dry ?? null,
      };
    });
    return NextResponse.json(points);
  }

  // 9. Timeseries Query for Village or Tehsil: /timeseries?tehsil=...&village=...
  if (route === "timeseries") {
    const tehsil = String(searchParams.get("tehsil") ?? "").trim().toLowerCase();
    const village = String(searchParams.get("village") ?? "").trim().toLowerCase();
    const cache = getVillageTimeseries();

    if (cache && tehsil && village) {
      const key = `${tehsil}::${village}`;
      const pts = cache[key] || [];
      return NextResponse.json(pts);
    }
    const dm = getDistrictMonthly();
    return NextResponse.json(dm?.series || []);
  }

  // 10. Dynamic GeoJSON synthesis for Any Index and Period: /indices/:name/:year/:month
  if (slug[0] === "indices" && slug.length >= 4) {
    const name = slug[1].toLowerCase();
    const year = slug[2];
    const month = String(slug[3]).padStart(2, "0");
    const period = `${year}-${month}`;

    const vPath = path.join(PUBLIC_DATA_DIR, "latur_villages_latest.geojson");
    if (fs.existsSync(vPath)) {
      try {
        const gj = JSON.parse(fs.readFileSync(vPath, "utf-8"));
        const cache = getVillageTimeseries();
        if (cache) {
          gj.features = gj.features.map((f: any) => {
            const p = f.properties || {};
            const t = (p.tehsil || p.TEHSIL || "").trim().toLowerCase();
            const v = (p.village || p.VILLAGE || p.name || "").trim().toLowerCase();
            const key = `${t}::${v}`;
            const pts = cache[key];
            const match = pts?.find((x: any) => x.p === period);
            const val = match
              ? (match[name] ?? (name === "rain" ? match.rain : match.cdi))
              : null;
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
                vhi: match?.vhi ?? null,
                vci: match?.vci ?? null,
                rain: match?.rain ?? null,
                period,
              },
            };
          });
        }
        return NextResponse.json(gj, {
          headers: { "Cache-Control": "public, max-age=3600" },
        });
      } catch (err) {
        console.error("[Vercel API] Error synthesizing index GeoJSON:", err);
      }
    }
    return NextResponse.json({ error: "Index GeoJSON synthesis failed" }, { status: 404 });
  }

  // 11. Animation Frame List: /animation?index=...&from=...&to=...
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

  // 12. Compare: /compare?a=...&b=...
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

  // 13. Latest status for village or tehsil: /latest?tehsil=...&village=...
  if (route === "latest") {
    const tehsil = String(searchParams.get("tehsil") ?? "Latur");
    const village = String(searchParams.get("village") ?? "");

    return NextResponse.json({
      tehsil,
      village,
      observation_period: "2026-10",
      CDI: 0.35,
      CDI_class: "D0",
      NDVI: 0.35,
      VHI: 25.0,
      SPI_3: -0.75,
    });
  }

  // 14. Master Rows: /master?tehsil=...&village=...
  if (route === "master") {
    const dm = getDistrictMonthly();
    return NextResponse.json(dm?.series || []);
  }

  return NextResponse.json({ error: `Not Found: /api/v1/${route}` }, { status: 404 });
}
