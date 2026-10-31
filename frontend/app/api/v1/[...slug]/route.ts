import { NextRequest, NextResponse } from "next/server";
import { readData } from "@/lib/serverData";


const getVillageTimeseries = () => readData<Record<string, any[]>>("village_timeseries.json");
const getDistrictMonthly = () => readData<any>("district_monthly.json");
const getTehsilAnalytics = () => readData<any>("tehsil_analytics.json");
const getVillageGeo = () => readData<any>("latur_villages_latest.geojson");
const readStatus = () => readData<any>("latest_status.json");

/** Resolve ?id=, or fall back to ?tehsil=&village= (first match; names are not unique). */
async function resolveVillageId(sp: URLSearchParams): Promise<string | null> {
  const id = sp.get("id");
  if (id) return id;
  const t = String(sp.get("tehsil") ?? "").trim().toLowerCase();
  const v = String(sp.get("village") ?? "").trim().toLowerCase();
  if (!t || !v) return null;
  const gj = await getVillageGeo();
  const f = (gj?.features ?? []).find(
    (x: any) =>
      String(x.properties?.tehsil ?? "").trim().toLowerCase() === t &&
      String(x.properties?.village ?? "").trim().toLowerCase() === v,
  );
  return f ? String(f.properties.id) : null;
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

  // 2. Status — never fabricate "operational" when no real data exists
  if (route === "status") {
    const st = await readStatus();
    if (st) return NextResponse.json(st);
    return NextResponse.json({
      generated_at: new Date().toISOString(),
      monitoring_status: "degraded",
      sentinel2: { latest_period_id: null, status: "no_data" },
      chirps: { latest_period_id: null, status: "no_data" },
      composite: { formula_version: "cdi-v2026.10" },
      region: { district: "Latur", state: "Maharashtra", centroid_lat: 18.4088, centroid_lon: 76.5604 },
    });
  }

  // 3. Manifest — derived from the data actually shipped
  if (route === "manifest") {
    const cache = await getVillageTimeseries() || {};
    const periods = new Set<string>();
    const have: Record<string, Set<number>> = {};
    for (const pts of Object.values(cache)) {
      for (const x of pts as any[]) {
        periods.add(x.p);
        for (const k of ["cdi", "ndvi", "vci", "vhi", "pci", "rain", "spi1", "spi3", "spi6", "spi12"]) {
          if (x[k] != null) (have[k] ||= new Set()).add(Number(String(x.p).slice(0, 4)));
        }
      }
    }
    const sorted = [...periods].sort();
    const indices: Record<string, any> = {};
    for (const [k, ys] of Object.entries(have)) {
      indices[k] = {
        source: k.startsWith("spi") || k === "rain" || k === "pci" ? "CHIRPS" : k === "cdi" ? "Composite" : "Sentinel-2",
        years: [...ys].sort(),
      };
    }
    return NextResponse.json({
      district: "Latur",
      years: [...new Set(sorted.map((p) => Number(p.slice(0, 4))))],
      as_of: sorted[sorted.length - 1] ?? null,
      indices,
    });
  }

  // 4. Tehsils GeoJSON
  if (route === "tehsils") {
    const data = await readData("latur_tehsils.geojson");
    if (data) {
      return NextResponse.json(data, { headers: { "Cache-Control": "public, max-age=86400" } });
    }
    return NextResponse.json({ error: "Tehsil GeoJSON missing" }, { status: 404 });
  }

  // 5. Villages GeoJSON
  if (route === "villages" || route.startsWith("village-indices")) {
    const data = await getVillageGeo();
    if (data) {
      return NextResponse.json(data, { headers: { "Cache-Control": "public, max-age=3600" } });
    }
    return NextResponse.json({ error: "Village GeoJSON missing" }, { status: 404 });
  }

  // 6. District Timeseries
  if (route === "district-timeseries") {
    const data = await getDistrictMonthly() || { series: [] };
    return NextResponse.json(data);
  }

  // 7. Tehsil Analytics
  if (route === "tehsil-analytics") {
    const data = await getTehsilAnalytics() || {};
    return NextResponse.json(data);
  }

  // 8. Timeseries (Specific Index: /timeseries/:name)
  if (slug[0] === "timeseries" && slug.length === 2) {
    const indexName = slug[1].toLowerCase();
    const dm = await getDistrictMonthly();
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

  // 9. Village history: /timeseries?id=123  (or ?tehsil=&village= — resolved to the first matching id)
  if (route === "timeseries") {
    const cache = await getVillageTimeseries();
    const vid = await resolveVillageId(searchParams);
    if (cache && vid) return NextResponse.json(cache[vid] || []);
    const dm = await getDistrictMonthly();
    return NextResponse.json(dm?.series || []);
  }

  // 10. Village GeoJSON for any index and month: /indices/:name/:year/:month
  if (slug[0] === "indices" && slug.length >= 4) {
    const name = slug[1].toLowerCase();
    const period = `${slug[2]}-${String(slug[3]).padStart(2, "0")}`;
    const base = await getVillageGeo();
    const cache = await getVillageTimeseries();
    if (!base || !cache) {
      return NextResponse.json({ error: "Village data missing" }, { status: 404 });
    }
    const field = name === "cdi_class" ? "cdi" : name;
    const features = base.features.map((f: any) => {
      const p = f.properties || {};
      const m = cache[String(p.id)]?.find((x: any) => x.p === period);
      const val = m ? m[field] : null;
      return {
        ...f,
        properties: {
          ...p,
          value: val != null && !isNaN(val) ? Number(val) : null,
          class: m?.cdi != null ? m.cls : "ND",
          cdi: m?.cdi ?? null, spi1: m?.spi1 ?? null, spi3: m?.spi3 ?? null,
          spi6: m?.spi6 ?? null, spi12: m?.spi12 ?? null, ndvi: m?.ndvi ?? null,
          vhi: m?.vhi ?? null, vci: m?.vci ?? null, pci: m?.pci ?? null, rain: m?.rain ?? null,
          period,
        },
      };
    });
    return NextResponse.json(
      { type: "FeatureCollection", features },
      { headers: { "Cache-Control": "public, max-age=3600" } },
    );
  }

  // 11. Animation Frame List: /animation?index=...&from=...&to=...
  if (route === "animation") {
    const index = String(searchParams.get("index") ?? "cdi").toLowerCase();
    const from = String(searchParams.get("from") ?? "2016-01");
    const to = String(searchParams.get("to") ?? "2026-10");

    const dm = await getDistrictMonthly();
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
    const dm = await getDistrictMonthly();
    const matchA = (dm?.series || []).find((s: any) => s.date === a);
    const matchB = (dm?.series || []).find((s: any) => s.date === b);

    return NextResponse.json({
      a: { period: a, rows: matchA ? [matchA] : [] },
      b: { period: b, rows: matchB ? [matchB] : [] },
    });
  }

  // 13. Latest status for village or tehsil: /latest?tehsil=...&village=...
  // Never return hardcoded fake CDI values when no data exists.
  if (route === "latest") {
    const tehsil = String(searchParams.get("tehsil") ?? "Latur");
    const village = String(searchParams.get("village") ?? "");

    // Newest scored month of the requested village (resolved by id, or by tehsil + name).
    const cache = await getVillageTimeseries();
    const vid = await resolveVillageId(new URLSearchParams({ tehsil, village, ...(searchParams.get("id") ? { id: searchParams.get("id")! } : {}) }));
    const pts = cache && vid ? cache[vid] : null;
    const last = pts ? [...pts].reverse().find((x: any) => x.cdi != null) : null;
    if (last) return NextResponse.json({ village_id: Number(vid), tehsil, village, observation_period: last.p, ...last });

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

  // 14. Master Rows: /master?tehsil=...&village=...
  if (route === "master") {
    const dm = await getDistrictMonthly();
    return NextResponse.json(dm?.series || []);
  }

  // 15. Pipeline telemetry — everything below is read from the status file the
  // pipeline writes; nothing here is a constant.
  if (route === "realtime" || route === "realtime/status") {
    const st = await readStatus();
    return NextResponse.json({
      status: st?.monitoring_status ?? "no_data",
      sentinel2: st?.sentinel2 ?? null,
      chirps: st?.chirps ?? null,
      generated_at: st?.generated_at ?? null,
      pipeline_run: st?.pipeline_run ?? null,
      monitored_villages: (await getVillageGeo())?.features?.length ?? null,
    });
  }

  // 16. Data checks computed from the files being served (no canned results)
  if (route === "realtime/validate") {
    const geo = await getVillageGeo();
    const cache = await getVillageTimeseries();
    const st = await readStatus();
    const checks: { name: string; status: "PASS" | "WARN" | "FAIL"; detail: string }[] = [];
    const add = (name: string, status: "PASS" | "WARN" | "FAIL", detail: string) => checks.push({ name, status, detail });

    if (!geo || !cache) {
      add("Data files present", "FAIL", "latur_villages_latest.geojson or village_timeseries.json is missing");
    } else {
      const ids = geo.features.map((f: any) => String(f.properties?.id));
      const uniq = new Set(ids).size;
      add("Polygon ids unique", uniq === ids.length ? "PASS" : "FAIL", `${uniq} unique ids across ${ids.length} polygons`);
      const missing = ids.filter((i: string) => !cache[i]).length;
      add("Every polygon has a history", missing === 0 ? "PASS" : "FAIL", `${ids.length - missing}/${ids.length} polygons matched to a time series`);

      let latest = "";
      for (const pts of Object.values(cache)) for (const x of pts as any[]) if (x.cdi != null && x.p > latest) latest = x.p;
      let n = 0, rain = 0, spi = 0;
      for (const id of ids) {
        const m = cache[id]?.find((x: any) => x.p === latest);
        if (m?.cdi != null) n++;
        if (m?.rain != null) rain++;
        if (m?.spi3 != null) spi++;
      }
      add(`Composite coverage in ${latest || "latest month"}`, n / ids.length > 0.9 ? "PASS" : n / ids.length > 0.5 ? "WARN" : "FAIL", `${n}/${ids.length} villages have a CDI`);
      add(`CHIRPS rainfall in ${latest || "latest month"}`, rain / ids.length > 0.9 ? "PASS" : "FAIL", `${rain}/${ids.length} villages have rainfall; ${spi}/${ids.length} have SPI-3`);
    }

    const now = new Date();
    const curIdx = now.getUTCFullYear() * 12 + now.getUTCMonth();
    const age = (p?: string | null) => (p ? curIdx - (Number(p.slice(0, 4)) * 12 + Number(p.slice(5, 7)) - 1) : null);
    const a2 = age(st?.sentinel2?.latest_period_id), ac = age(st?.chirps?.latest_period_id);
    add("Sentinel-2 freshness", a2 == null ? "FAIL" : a2 <= 1 ? "PASS" : "WARN", st?.sentinel2?.latest_period_id ? `latest period ${st.sentinel2.latest_period_id} (${a2} month(s) old)` : "no Sentinel-2 period recorded");
    add("CHIRPS freshness", ac == null ? "FAIL" : ac <= 2 ? "PASS" : "WARN", st?.chirps?.latest_period_id ? `latest period ${st.chirps.latest_period_id} (${ac} month(s) old)` : "no CHIRPS period recorded");

    const worst = checks.some((c) => c.status === "FAIL") ? "FAIL" : checks.some((c) => c.status === "WARN") ? "WARN" : "PASS";
    return NextResponse.json({ validation_status: worst, timestamp: new Date().toISOString(), checks });
  }

  return NextResponse.json({ error: `Not Found: /api/v1/${route}` }, { status: 404 });
}
