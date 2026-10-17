import { Router } from "express";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const { DatabaseSync } = require("node:sqlite");
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.resolve(__dirname, "../../../data");
const DASH_DIR = path.resolve(__dirname, "../../../outputs/Dashboard");
const DB_PATH = path.join(DATA_DIR, "drought.db");
let db = null;
try {
    if (fs.existsSync(DB_PATH)) {
        db = new DatabaseSync(DB_PATH);
    }
}
catch (err) {
    console.error("Failed to open SQLite database:", err);
}
export const apiRouter = Router();
const TEHSIL_GEOJSON_PATH = path.resolve(__dirname, "../../../frontend/public/data/latur_tehsils.geojson");
const tehsilPolygonMap = new Map();
try {
    if (fs.existsSync(TEHSIL_GEOJSON_PATH)) {
        const raw = JSON.parse(fs.readFileSync(TEHSIL_GEOJSON_PATH, "utf-8"));
        for (const f of raw.features || []) {
            const name = f.properties?.TEHSIL || f.properties?.name;
            if (name) {
                tehsilPolygonMap.set(String(name).trim().toLowerCase(), f.geometry);
            }
        }
    }
}
catch (e) {
    console.error("Failed to load tehsil polygons:", e);
}
function parseGeometry(geomStr, fallbackName) {
    if (fallbackName && tehsilPolygonMap.has(fallbackName.trim().toLowerCase())) {
        return tehsilPolygonMap.get(fallbackName.trim().toLowerCase());
    }
    if (!geomStr)
        return null;
    const trimmed = geomStr.trim();
    if (trimmed.startsWith("{")) {
        try {
            return JSON.parse(trimmed);
        }
        catch {
            // ignore
        }
    }
    const pointMatch = trimmed.match(/POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)/i);
    if (pointMatch && pointMatch[1] && pointMatch[2]) {
        return {
            type: "Point",
            coordinates: [parseFloat(pointMatch[1]), parseFloat(pointMatch[2])],
        };
    }
    return null;
}
const VALID_INDICES = new Set([
    "spi1", "spi3", "spi6", "spi12",
    "ndvi", "evi", "pci", "vci", "vhi", "cdi", "cdi_class"
]);
function getIndexColumn(name) {
    switch (name.toLowerCase()) {
        case "spi1": return "spi_1";
        case "spi3": return "spi_3";
        case "spi6": return "spi_6";
        case "spi12": return "spi_12";
        case "ndvi": return "ndvi";
        case "evi": return "evi";
        case "vci": return "vci";
        case "vhi": return "vhi";
        case "pci": return "pci";
        case "cdi": return "composite_drought_score";
        case "cdi_class": return "composite_drought_class";
        default: return name;
    }
}
// GET /api/v1/health
apiRouter.get("/health", (_req, res) => {
    res.json({ status: "ok", db: db !== null });
});
// GET /api/v1/manifest
apiRouter.get("/manifest", (_req, res) => {
    const manifestPath = path.join(DATA_DIR, "processed/json/manifest.json");
    if (fs.existsSync(manifestPath)) {
        try {
            const data = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
            return res.json(data);
        }
        catch {
            // fallback
        }
    }
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const yearsRows = db.prepare("SELECT DISTINCT year FROM monthly_index ORDER BY year").all();
    const years = yearsRows.map((r) => r.year);
    res.json({
        district: "Latur",
        years,
        as_of: new Date().toISOString(),
        indices: {
            spi1: { source: "CHIRPS v2.0", unit: "z", years },
            spi3: { source: "CHIRPS v2.0", unit: "z", years },
            spi6: { source: "CHIRPS v2.0", unit: "z", years },
            spi12: { source: "CHIRPS v2.0", unit: "z", years },
            ndvi: { source: "Sentinel-2 L2A", unit: "0..1", years },
            evi: { source: "Sentinel-2 L2A", unit: "0..1", years },
            vci: { source: "Sentinel-2 L2A", unit: "%", years },
            vhi: { source: "VCI + TCI proxy", unit: "%", years },
            pci: { source: "CHIRPS (normalized)", unit: "0..1", years },
            cdi: { source: "Composite Drought Index", unit: "0..1", years },
        },
    });
});
// GET /api/v1/tehsils
apiRouter.get("/tehsils", (_req, res) => {
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const rows = db.prepare("SELECT name, geom FROM tehsils ORDER BY name").all();
    const features = rows.map((r) => ({
        type: "Feature",
        properties: { TEHSIL: r.name, name: r.name },
        geometry: parseGeometry(r.geom, r.name),
    }));
    res.setHeader("Content-Type", "application/geo+json");
    res.json({
        type: "FeatureCollection",
        features,
    });
});
// GET /api/v1/villages?tehsil=
apiRouter.get("/villages", (req, res) => {
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const tehsil = req.query.tehsil ? String(req.query.tehsil).trim() : "";
    let sql = "SELECT DISTINCT village, tehsil FROM village_spi WHERE village != ''";
    const params = [];
    if (tehsil && tehsil.toLowerCase() !== "all") {
        sql += " AND LOWER(tehsil) = LOWER(?)";
        params.push(tehsil);
    }
    sql += " ORDER BY village ASC";
    const rows = db.prepare(sql).all(...params);
    res.json(rows.map((r) => r.village));
});
// GET /api/v1/indices/:name/:year/:month  (tehsil-level polygons)
apiRouter.get("/indices/:name/:year/:month", (req, res) => {
    const name = String(req.params.name ?? "").toLowerCase();
    if (!VALID_INDICES.has(name)) {
        return res.status(400).json({ error: { code: "BAD_INDEX", message: `unknown index: ${name}` } });
    }
    const yearStr = req.params.year ?? "";
    const monthStr = req.params.month ?? "";
    const year = parseInt(yearStr, 10);
    const month = parseInt(monthStr, 10);
    if (isNaN(year) || isNaN(month) || month < 1 || month > 12) {
        return res.status(400).json({ error: { code: "BAD_DATE", message: "Invalid year or month" } });
    }
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const period = `${year}-${String(month).padStart(2, "0")}`;
    const col = getIndexColumn(name);
    const tehsils = db.prepare("SELECT name, geom FROM tehsils ORDER BY name").all();
    const masterRows = db.prepare("SELECT tehsil, " + col + " AS val, composite_drought_class AS dclass FROM master_row WHERE observation_period = ? AND village = ''").all(period);
    const valMap = new Map();
    for (const m of masterRows) {
        const isNum = m.val !== null && m.val !== "" && !isNaN(Number(m.val));
        valMap.set(m.tehsil.toLowerCase(), {
            val: isNum ? Number(m.val) : null,
            dclass: isNum ? (m.dclass || "None") : "ND",
        });
    }
    const features = tehsils.map((t) => {
        const info = valMap.get(t.name.toLowerCase()) || { val: null, dclass: "ND" };
        return {
            type: "Feature",
            properties: {
                TEHSIL: t.name,
                name: t.name,
                index: name,
                period,
                value: info.val,
                class: info.dclass,
            },
            geometry: parseGeometry(t.geom, t.name),
        };
    });
    res.setHeader("Content-Type", "application/geo+json");
    res.setHeader("Cache-Control", "public, max-age=86400");
    res.json({
        type: "FeatureCollection",
        features,
    });
});
// GET /api/v1/village-indices/:name/:year/:month  (village-level points)
apiRouter.get("/village-indices/:name/:year/:month", (req, res) => {
    const name = String(req.params.name ?? "").toLowerCase();
    if (!VALID_INDICES.has(name)) {
        return res.status(400).json({ error: { code: "BAD_INDEX", message: `unknown index: ${name}` } });
    }
    const year = parseInt(req.params.year ?? "", 10);
    const month = parseInt(req.params.month ?? "", 10);
    if (isNaN(year) || isNaN(month) || month < 1 || month > 12) {
        return res.status(400).json({ error: { code: "BAD_DATE", message: "Invalid year or month" } });
    }
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const period = `${year}-${String(month).padStart(2, "0")}`;
    const col = getIndexColumn(name);
    const rows = db.prepare(`SELECT village, tehsil, lon, lat, ${col} AS val, composite_drought_class AS dclass, composite_drought_score AS score
     FROM master_row
     WHERE observation_period = ? AND village != '' AND lon IS NOT NULL AND lat IS NOT NULL`).all(period);
    const features = rows.map((r) => {
        const isNum = r.val !== null && r.val !== "" && !isNaN(Number(r.val));
        const scoreNum = r.score !== null && r.score !== "" && !isNaN(Number(r.score));
        return {
            type: "Feature",
            properties: {
                VILLAGE: r.village,
                TEHSIL: r.tehsil,
                name: r.village,
                index: name,
                period,
                value: isNum ? Number(r.val) : null,
                class: isNum ? (r.dclass || "None") : "ND",
                score: scoreNum ? Number(r.score) : null,
                cdi_class: r.dclass || "ND",
            },
            geometry: {
                type: "Point",
                coordinates: [Number(r.lon), Number(r.lat)],
            },
        };
    });
    res.setHeader("Content-Type", "application/geo+json");
    res.setHeader("Cache-Control", "public, max-age=300");
    res.json({
        type: "FeatureCollection",
        features,
    });
});
// GET /api/v1/timeseries/:name
apiRouter.get("/timeseries/:name", (req, res) => {
    const name = String(req.params.name ?? "").toLowerCase();
    if (!VALID_INDICES.has(name)) {
        return res.status(400).json({ error: { code: "BAD_INDEX", message: `unknown index: ${name}` } });
    }
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const from = req.query.from ? String(req.query.from) : "";
    const to = req.query.to ? String(req.query.to) : "";
    const sql = `
    SELECT year, month, value, class_label, pct_area_dry
    FROM monthly_index
    WHERE index_name = ?
    ORDER BY year, month
  `;
    const rows = db.prepare(sql).all(name);
    const points = rows
        .map((r) => {
        const date = `${r.year}-${String(r.month).padStart(2, "0")}`;
        return {
            date,
            value: r.value !== null ? Number(r.value) : null,
            class: r.class_label || "No data",
            pct_area_dry: r.pct_area_dry !== null ? Number(r.pct_area_dry) : null,
        };
    })
        .filter((p) => (!from || p.date >= from) && (!to || p.date <= to));
    res.json(points);
});
// GET /api/v1/cdi/:year/:month
apiRouter.get("/cdi/:year/:month", (req, res) => {
    const yearStr = req.params.year ?? "";
    const monthStr = req.params.month ?? "";
    const year = parseInt(yearStr, 10);
    const month = parseInt(monthStr, 10);
    if (isNaN(year) || isNaN(month) || month < 1 || month > 12) {
        return res.status(400).json({ error: { code: "BAD_DATE", message: "Invalid year or month" } });
    }
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const period = `${year}-${String(month).padStart(2, "0")}`;
    const meanRow = db.prepare("SELECT value, class_label FROM monthly_index WHERE index_name = 'cdi' AND year = ? AND month = ?").get(year, month);
    const tehsilRows = db.prepare("SELECT tehsil, composite_drought_score, composite_drought_class FROM master_row WHERE observation_period = ? AND village = ''").all(period);
    const tehsils = tehsilRows.map((r) => ({
        name: r.tehsil,
        mean: r.composite_drought_score !== null ? Number(r.composite_drought_score) : 0,
        class: r.composite_drought_class || "ND",
    }));
    res.json({
        year,
        month,
        mean: meanRow?.value ?? null,
        class: meanRow?.class_label ?? "ND",
        tehsils,
        weights: { SPI: 0.3, VHI: 0.2, VCI: 0.15, NDVI: 0.15, EVI: 0.1, PCI: 0.1 },
    });
});
// GET /api/v1/status
apiRouter.get("/status", (_req, res) => {
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
        sentinel2: { latest_period_id: "2026-08", status: "success" },
        chirps: { latest_period_id: "2026-08", status: "success" },
        composite: { formula_version: "cdi-v2026.10" },
        region: { district: "Latur", state: "Maharashtra", centroid_lat: 18.4088, centroid_lon: 76.5604 },
    });
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
        sentinel2: ["2026-08"],
        chirps: ["2026-08"],
        composite: ["2026-08"],
    });
});
// GET /api/v1/master
apiRouter.get("/master", (req, res) => {
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const tehsil = req.query.tehsil ? String(req.query.tehsil).trim() : "";
    const village = req.query.village ? String(req.query.village).trim() : "";
    const from = req.query.from ? String(req.query.from) : "";
    const to = req.query.to ? String(req.query.to) : "";
    let sql = "SELECT * FROM master_row WHERE 1=1";
    const params = [];
    if (tehsil && tehsil.toLowerCase() !== "all") {
        sql += " AND LOWER(tehsil) = LOWER(?)";
        params.push(tehsil);
    }
    if (village) {
        sql += " AND LOWER(village) = LOWER(?)";
        params.push(village);
    }
    else {
        sql += " AND village = ''";
    }
    if (from) {
        sql += " AND observation_period >= ?";
        params.push(from);
    }
    if (to) {
        sql += " AND observation_period <= ?";
        params.push(to);
    }
    sql += " ORDER BY observation_period ASC";
    const rows = db.prepare(sql).all(...params);
    const formatted = rows.map((r) => {
        const obj = {};
        for (const [k, v] of Object.entries(r)) {
            if (k === "id")
                continue;
            if (k === "spi_1")
                obj["SPI_1"] = v !== null ? String(v) : "";
            else if (k === "spi_3")
                obj["SPI_3"] = v !== null ? String(v) : "";
            else if (k === "spi_6")
                obj["SPI_6"] = v !== null ? String(v) : "";
            else if (k === "spi_12")
                obj["SPI_12"] = v !== null ? String(v) : "";
            else if (k === "ndvi")
                obj["NDVI"] = v !== null ? String(v) : "";
            else if (k === "evi")
                obj["EVI"] = v !== null ? String(v) : "";
            else if (k === "vci")
                obj["VCI"] = v !== null ? String(v) : "";
            else if (k === "vhi")
                obj["VHI"] = v !== null ? String(v) : "";
            else if (k === "pci")
                obj["PCI"] = v !== null ? String(v) : "";
            else
                obj[k] = v !== null ? String(v) : "";
        }
        return obj;
    });
    res.json(formatted);
});
// GET /api/v1/latest
apiRouter.get("/latest", (req, res) => {
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const tehsil = req.query.tehsil ? String(req.query.tehsil).trim() : "Latur";
    const village = req.query.village ? String(req.query.village).trim() : "";
    let sql = "SELECT * FROM master_row WHERE LOWER(tehsil) = LOWER(?)";
    const params = [tehsil];
    if (village) {
        sql += " AND LOWER(village) = LOWER(?)";
        params.push(village);
    }
    else {
        sql += " AND village = ''";
    }
    sql += " ORDER BY observation_period DESC LIMIT 1";
    const row = db.prepare(sql).get(...params);
    if (!row) {
        return res.status(404).json({ error: { code: "NO_DATA", message: `no data for ${tehsil}` } });
    }
    const formatted = {};
    for (const [k, v] of Object.entries(row)) {
        if (k === "id")
            continue;
        if (k === "spi_1")
            formatted["SPI_1"] = v !== null ? String(v) : "";
        else if (k === "spi_3")
            formatted["SPI_3"] = v !== null ? String(v) : "";
        else if (k === "spi_6")
            formatted["SPI_6"] = v !== null ? String(v) : "";
        else if (k === "spi_12")
            formatted["SPI_12"] = v !== null ? String(v) : "";
        else if (k === "ndvi")
            formatted["NDVI"] = v !== null ? String(v) : "";
        else if (k === "evi")
            formatted["EVI"] = v !== null ? String(v) : "";
        else if (k === "vci")
            formatted["VCI"] = v !== null ? String(v) : "";
        else if (k === "vhi")
            formatted["VHI"] = v !== null ? String(v) : "";
        else if (k === "pci")
            formatted["PCI"] = v !== null ? String(v) : "";
        else
            formatted[k] = v !== null ? String(v) : "";
    }
    res.json(formatted);
});
// GET /api/v1/compare
apiRouter.get("/compare", (req, res) => {
    const a = String(req.query.a || "");
    const b = String(req.query.b || "");
    if (!a || !b) {
        return res.status(400).json({ error: { code: "BAD_INPUT", message: "a and b are required (YYYY-MM)" } });
    }
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const rowsA = db.prepare("SELECT * FROM master_row WHERE observation_period = ? AND village = ''").all(a);
    const rowsB = db.prepare("SELECT * FROM master_row WHERE observation_period = ? AND village = ''").all(b);
    res.json({
        a: { period: a, rows: rowsA },
        b: { period: b, rows: rowsB },
    });
});
// GET /api/v1/animation
apiRouter.get("/animation", (req, res) => {
    const name = String(req.query.index || "cdi").toLowerCase();
    if (!VALID_INDICES.has(name)) {
        return res.status(400).json({ error: { code: "BAD_INDEX", message: `unknown index: ${name}` } });
    }
    const from = req.query.from ? String(req.query.from) : "";
    const to = req.query.to ? String(req.query.to) : "";
    if (!db) {
        return res.status(503).json({ error: { code: "DB_UNAVAILABLE", message: "Database not loaded" } });
    }
    const periodsRows = db.prepare("SELECT DISTINCT observation_period FROM master_row ORDER BY observation_period ASC").all();
    const frames = periodsRows
        .map((r) => r.observation_period)
        .filter((p) => (!from || p >= from) && (!to || p <= to))
        .map((p) => {
        const [year, month] = p.split("-");
        return {
            period: p,
            geojson_url: `/api/v1/indices/${name}/${year}/${parseInt(month ?? "1", 10)}`,
        };
    });
    res.json({
        index: name,
        count: frames.length,
        frames,
    });
});
// POST /api/v1/admin/ingest
apiRouter.post("/admin/ingest", (_req, res) => {
    res.status(202).json({ status: "accepted" });
});
// POST /api/v1/admin/aoi
apiRouter.post("/admin/aoi", (_req, res) => {
    res.status(202).json({ status: "accepted" });
});
