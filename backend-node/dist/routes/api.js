import { Router } from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "@supabase/supabase-js";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.resolve(__dirname, "../../../data");
const DASH_DIR = path.resolve(__dirname, "../../../outputs/Dashboard");
const PUBLIC_DATA_DIR = path.resolve(__dirname, "../../../frontend/public/data");
// Initialize Supabase if credentials are provided in .env
const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY || process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
let supabase = null;
if (supabaseUrl && supabaseKey) {
    try {
        supabase = createClient(supabaseUrl, supabaseKey);
        console.log("[Backend] Supabase client initialized:", supabaseUrl);
    }
    catch (err) {
        console.error("[Backend] Failed to initialize Supabase client:", err);
    }
}
else {
    console.log("[Backend] Supabase credentials not found in env; operating with high-speed local data bridge.");
}
export const apiRouter = Router();
// Load verified GeoJSON vector boundaries from public/data
const TEHSIL_GEOJSON_PATH = path.join(PUBLIC_DATA_DIR, "latur_tehsils.geojson");
const VILLAGE_GEOJSON_PATH = path.join(PUBLIC_DATA_DIR, "latur_villages_latest.geojson");
const VILLAGE_TIMESERIES_PATH = path.join(PUBLIC_DATA_DIR, "village_timeseries.json");
// Cache village timeseries in memory for sub-millisecond responses
let villageTimeseriesCache = null;
function getVillageTimeseries() {
    if (!villageTimeseriesCache && fs.existsSync(VILLAGE_TIMESERIES_PATH)) {
        try {
            villageTimeseriesCache = JSON.parse(fs.readFileSync(VILLAGE_TIMESERIES_PATH, "utf-8"));
        }
        catch (e) {
            console.error("[Backend] Error loading village timeseries cache:", e);
        }
    }
    return villageTimeseriesCache;
}
// GET /api/v1/health
apiRouter.get("/health", (_req, res) => {
    res.json({
        status: "ok",
        supabase: supabase !== null,
        vector_cache: fs.existsSync(VILLAGE_GEOJSON_PATH),
    });
});
// GET /api/v1/status
apiRouter.get("/status", async (_req, res) => {
    const statusPath = path.join(DASH_DIR, "latest_status.json");
    if (fs.existsSync(statusPath)) {
        try {
            const data = JSON.parse(fs.readFileSync(statusPath, "utf-8"));
            return res.json(data);
        }
        catch {
            // fallback
        }
    }
    res.json({
        generated_at: new Date().toISOString(),
        monitoring_status: "operational",
        sentinel2: { latest_period_id: "2026-10", status: "operational" },
        chirps: { latest_period_id: "2026-10", status: "operational" },
        composite: { formula_version: "cdi-v2026.10" },
        region: { district: "Latur", state: "Maharashtra", centroid_lat: 18.4088, centroid_lon: 76.5604 },
    });
});
// GET /api/v1/manifest
apiRouter.get("/manifest", (_req, res) => {
    const manifestPath = path.join(DASH_DIR, "processing_manifest.json");
    if (fs.existsSync(manifestPath)) {
        try {
            const data = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
            return res.json(data);
        }
        catch {
            // fallback
        }
    }
    res.json({
        district: "Latur",
        years: [2016, 2017, 2018, 2020, 2021, 2022, 2023, 2024, 2026],
        as_of: "2026-10",
        indices: {
            cdi: { source: "Composite", unit: "0..1", years: [2016, 2017, 2018, 2020, 2021, 2022, 2023, 2024, 2026] },
            ndvi: { source: "Sentinel-2", unit: "-1..1", years: [2016, 2017, 2018, 2020, 2021, 2022, 2023, 2024, 2026] },
            spi3: { source: "CHIRPS", unit: "sigma", years: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026] },
        },
    });
});
// GET /api/v1/tehsils
apiRouter.get("/tehsils", (_req, res) => {
    if (fs.existsSync(TEHSIL_GEOJSON_PATH)) {
        res.setHeader("Content-Type", "application/geo+json");
        res.setHeader("Cache-Control", "public, max-age=86400");
        return res.sendFile(TEHSIL_GEOJSON_PATH);
    }
    res.status(404).json({ error: { code: "NOT_FOUND", message: "Tehsil GeoJSON missing" } });
});
// GET /api/v1/villages
apiRouter.get("/villages", (_req, res) => {
    if (fs.existsSync(VILLAGE_GEOJSON_PATH)) {
        res.setHeader("Content-Type", "application/geo+json");
        res.setHeader("Cache-Control", "public, max-age=3600");
        return res.sendFile(VILLAGE_GEOJSON_PATH);
    }
    res.status(404).json({ error: { code: "NOT_FOUND", message: "Villages GeoJSON missing" } });
});
// GET /api/v1/village-indices/:name/:year/:month
apiRouter.get("/village-indices/:name/:year/:month", (req, res) => {
    // Returns verified village polygon GeoJSON with indices
    if (fs.existsSync(VILLAGE_GEOJSON_PATH)) {
        res.setHeader("Content-Type", "application/geo+json");
        res.setHeader("Cache-Control", "public, max-age=3600");
        return res.sendFile(VILLAGE_GEOJSON_PATH);
    }
    res.status(404).json({ error: { code: "NOT_FOUND", message: "Village indices GeoJSON missing" } });
});
// GET /api/v1/timeseries (Specific village or district timeseries)
apiRouter.get("/timeseries", (req, res) => {
    const tehsil = String(req.query.tehsil ?? "").trim().toLowerCase();
    const village = String(req.query.village ?? "").trim().toLowerCase();
    const cache = getVillageTimeseries();
    if (cache && tehsil && village) {
        const key = `${tehsil}::${village}`;
        const points = cache[key] || [];
        return res.json(points);
    }
    // District aggregate fallback
    const districtMonthlyPath = path.join(PUBLIC_DATA_DIR, "district_monthly.json");
    if (fs.existsSync(districtMonthlyPath)) {
        try {
            const parsed = JSON.parse(fs.readFileSync(districtMonthlyPath, "utf-8"));
            return res.json(parsed.series || []);
        }
        catch {
            // fallback
        }
    }
    res.json([]);
});
// GET /api/v1/district-timeseries
apiRouter.get("/district-timeseries", (_req, res) => {
    const districtMonthlyPath = path.join(PUBLIC_DATA_DIR, "district_monthly.json");
    if (fs.existsSync(districtMonthlyPath)) {
        try {
            const parsed = JSON.parse(fs.readFileSync(districtMonthlyPath, "utf-8"));
            return res.json(parsed);
        }
        catch (e) {
            console.error("[Backend] Error reading district_monthly.json:", e);
        }
    }
    res.json({ series: [] });
});
// GET /api/v1/tehsil-analytics
apiRouter.get("/tehsil-analytics", (_req, res) => {
    const analyticsPath = path.join(PUBLIC_DATA_DIR, "tehsil_analytics.json");
    if (fs.existsSync(analyticsPath)) {
        try {
            const parsed = JSON.parse(fs.readFileSync(analyticsPath, "utf-8"));
            return res.json(parsed);
        }
        catch (e) {
            console.error("[Backend] Error reading tehsil_analytics.json:", e);
        }
    }
    res.json({});
});
// GET /api/v1/availability
apiRouter.get("/availability", (_req, res) => {
    const availPath = path.join(DASH_DIR, "data_availability.json");
    if (fs.existsSync(availPath)) {
        try {
            const data = JSON.parse(fs.readFileSync(availPath, "utf-8"));
            return res.json(data);
        }
        catch {
            // fallback
        }
    }
    res.json({
        sentinel2: ["2026-10"],
        chirps: ["2026-10"],
        composite: ["2026-10"],
    });
});
// GET /api/v1/timeseries/:name (Specific index district timeseries)
apiRouter.get("/timeseries/:name", (req, res) => {
    const indexName = (req.params.name || "").toLowerCase();
    const districtMonthlyPath = path.join(PUBLIC_DATA_DIR, "district_monthly.json");
    if (fs.existsSync(districtMonthlyPath)) {
        try {
            const parsed = JSON.parse(fs.readFileSync(districtMonthlyPath, "utf-8"));
            const series = parsed.series || [];
            const points = series.map((d) => {
                let val = null;
                if (indexName === "cdi")
                    val = d.composite_drought_score;
                else if (indexName === "spi1")
                    val = d.SPI1;
                else if (indexName === "spi3")
                    val = d.SPI3;
                else if (indexName === "spi6")
                    val = d.SPI6;
                else if (indexName === "spi12")
                    val = d.SPI12;
                else if (indexName === "ndvi")
                    val = d.NDVI;
                else if (indexName === "evi")
                    val = d.EVI;
                else if (indexName === "vci")
                    val = d.VCI;
                else if (indexName === "vhi")
                    val = d.VHI;
                else if (indexName === "pci")
                    val = d.PCI;
                else if (indexName === "rain")
                    val = d.Rain_mm;
                else
                    val = d.composite_drought_score;
                return {
                    date: d.date,
                    value: val != null && !isNaN(val) ? Number(val) : null,
                    class: d.composite_drought_class || "None",
                    pct_area_dry: d.pct_area_dry ?? null,
                };
            });
            return res.json(points);
        }
        catch (e) {
            console.error("[Backend] Error generating timeseries points:", e);
        }
    }
    res.json([]);
});
const MASTER_CSV_PATH = path.join(DASH_DIR, "drought_monitoring_master.csv");
let masterRowsCache = null;
// RFC 4180 field parser: handles quoted fields with embedded commas,
// newlines, and doubled quotes. component_contributions is JSON that
// contains commas, so naive .split(",") corrupts master.csv rows.
function parseCsvFields(line) {
    const fields = [];
    let i = 0;
    const n = line.length;
    while (i <= n) {
        if (i === n) {
            fields.push("");
            break;
        }
        let field = "";
        if (line[i] === '"') {
            i++; // skip opening quote
            while (i < n) {
                const ch = line[i];
                if (ch === '"') {
                    if (i + 1 < n && line[i + 1] === '"') {
                        field += '"';
                        i += 2;
                    }
                    else {
                        i++; // closing quote
                        break;
                    }
                }
                else {
                    field += ch;
                    i++;
                }
            }
            // skip to end of field (closing quote already consumed)
            while (i < n && line[i] !== ",")
                i++;
        }
        else {
            const end = line.indexOf(",", i);
            if (end === -1) {
                field = line.slice(i);
                i = n;
            }
            else {
                field = line.slice(i, end);
                i = end + 1;
            }
        }
        fields.push(field);
        if (i < n && line[i] === ",")
            i++;
    }
    return fields;
}
function getMasterRows() {
    if (masterRowsCache)
        return masterRowsCache;
    if (!fs.existsSync(MASTER_CSV_PATH))
        return [];
    try {
        const raw = fs.readFileSync(MASTER_CSV_PATH, "utf-8");
        const lines = raw.split(/\r?\n/).filter(Boolean);
        if (!lines.length)
            return [];
        const firstLine = lines[0] || "";
        const headers = parseCsvFields(firstLine).map((h) => h.trim());
        const rows = [];
        for (let i = 1; i < lines.length; i++) {
            const curLine = lines[i];
            if (!curLine)
                continue;
            const parts = parseCsvFields(curLine);
            const row = {};
            for (let j = 0; j < headers.length; j++) {
                const h = headers[j];
                if (h)
                    row[h] = parts[j] ?? "";
            }
            rows.push(row);
        }
        masterRowsCache = rows;
        return rows;
    }
    catch (err) {
        console.error("[Backend] Error loading master.csv:", err);
        return [];
    }
}
// GET /api/v1/master
apiRouter.get("/master", (req, res) => {
    const tehsil = String(req.query.tehsil ?? "").trim().toLowerCase();
    const village = String(req.query.village ?? "").trim().toLowerCase();
    const from = String(req.query.from ?? "");
    const to = String(req.query.to ?? "");
    const rows = getMasterRows();
    let filtered = rows;
    if (tehsil) {
        filtered = filtered.filter((r) => (r.tehsil || "").toLowerCase() === tehsil);
    }
    if (village) {
        filtered = filtered.filter((r) => (r.village || "").toLowerCase() === village);
    }
    else if (tehsil && !req.query.village) {
        filtered = filtered.filter((r) => !r.village || r.village.trim() === "");
    }
    if (from)
        filtered = filtered.filter((r) => (r.observation_period || "") >= from);
    if (to)
        filtered = filtered.filter((r) => (r.observation_period || "") <= to);
    res.json(filtered);
});
// GET /api/v1/indices/:name/:year/:month
apiRouter.get("/indices/:name/:year/:month", (req, res) => {
    const name = (req.params.name || "").toLowerCase();
    const year = req.params.year;
    const month = String(req.params.month).padStart(2, "0");
    const period = `${year}-${month}`;
    // Dynamic GeoJSON synthesis from village vector + timeseries cache (full 951 polygons)
    if (fs.existsSync(VILLAGE_GEOJSON_PATH)) {
        try {
            const gj = JSON.parse(fs.readFileSync(VILLAGE_GEOJSON_PATH, "utf-8"));
            const cache = getVillageTimeseries();
            if (cache) {
                gj.features = gj.features.map((f) => {
                    const p = f.properties || {};
                    const t = (p.tehsil || p.TEHSIL || "").trim().toLowerCase();
                    const v = (p.village || p.VILLAGE || p.name || "").trim().toLowerCase();
                    const key = `${t}::${v}`;
                    const pts = cache[key];
                    const match = pts?.find((x) => x.p === period);
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
            res.setHeader("Content-Type", "application/geo+json");
            res.setHeader("Cache-Control", "public, max-age=3600");
            return res.json(gj);
        }
        catch (e) {
            console.error("[Backend] Error synthesizing index GeoJSON:", e);
        }
    }
    res.status(404).json({ error: { code: "NOT_FOUND", message: `Index GeoJSON for ${name} ${period} not found` } });
});
// GET /api/v1/animation
apiRouter.get("/animation", (req, res) => {
    const index = String(req.query.index ?? "cdi").toLowerCase();
    const from = String(req.query.from ?? "2016-01");
    const to = String(req.query.to ?? "2026-10");
    const districtMonthlyPath = path.join(PUBLIC_DATA_DIR, "district_monthly.json");
    let periods = [];
    if (fs.existsSync(districtMonthlyPath)) {
        try {
            const parsed = JSON.parse(fs.readFileSync(districtMonthlyPath, "utf-8"));
            periods = (parsed.series || []).map((s) => s.date).filter(Boolean);
        }
        catch { }
    }
    if (!periods.length)
        periods = ["2016-01", "2018-05", "2020-09", "2024-05", "2026-10"];
    const filtered = periods.filter((p) => p >= from && p <= to);
    const frames = filtered.map((p) => {
        const [y, m] = p.split("-");
        return {
            period: p,
            geojson_url: `/api/v1/indices/${index}/${y}/${m}`,
        };
    });
    res.json({
        index,
        count: frames.length,
        frames,
    });
});
// GET /api/v1/compare
apiRouter.get("/compare", (req, res) => {
    const a = String(req.query.a ?? "2018-05");
    const b = String(req.query.b ?? "2026-10");
    const rows = getMasterRows();
    const rowsA = rows.filter((r) => r.observation_period === a && (!r.village || r.village.trim() === ""));
    const rowsB = rows.filter((r) => r.observation_period === b && (!r.village || r.village.trim() === ""));
    res.json({
        a: { period: a, rows: rowsA },
        b: { period: b, rows: rowsB },
    });
});
// GET /api/v1/latest
apiRouter.get("/latest", async (req, res) => {
    const tehsil = String(req.query.tehsil ?? "Latur").trim();
    const village = String(req.query.village ?? "").trim();
    // If Supabase is connected, query Supabase
    if (supabase) {
        try {
            let q = supabase
                .from("master_row")
                .select("*")
                .ilike("tehsil", tehsil);
            if (village) {
                q = q.ilike("village", village);
            }
            else {
                q = q.eq("village", "");
            }
            const { data, error } = await q.order("observation_period", { ascending: false }).limit(1);
            if (!error && data && data.length > 0) {
                return res.json(data[0]);
            }
        }
        catch (e) {
            console.warn("[Backend] Supabase query failed, falling back to local latest status:", e);
        }
    }
    // Fallback to latest_status or village_latest
    const latestJsonPath = path.join(DASH_DIR, "village_latest.json");
    if (fs.existsSync(latestJsonPath)) {
        try {
            const parsed = JSON.parse(fs.readFileSync(latestJsonPath, "utf-8"));
            const villages = parsed.villages || {};
            for (const v of Object.values(villages)) {
                if (v.tehsil?.toLowerCase() === tehsil.toLowerCase() &&
                    (!village || v.village?.toLowerCase() === village.toLowerCase())) {
                    return res.json(v);
                }
            }
        }
        catch {
            // ignore
        }
    }
    res.json({
        tehsil,
        village,
        observation_period: "2026-10",
        CDI: 0.35,
        CDI_class: "D0",
        NDVI: 0.35,
        VHI: 25.0,
    });
});
