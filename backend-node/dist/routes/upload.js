import { Router } from "express";
import multer from "multer";
import { requireAdmin, requireUser, supabaseAdmin } from "../middleware/supabase.js";
export const uploadRouter = Router();
const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 50 * 1024 * 1024 }, // 50 MB per file
});
// POST /upload/geojson?index=cdi&year=2026
//
// Accepts a GeoJSON produced by the Python pipeline and stores it in the
// Supabase bucket "processed". The Go ingest CLI can then be re-run.
uploadRouter.post("/geojson", requireUser, requireAdmin, upload.single("file"), async (req, res) => {
    if (!supabaseAdmin) {
        return res
            .status(503)
            .json({ error: { code: "NO_ADMIN", message: "SUPABASE_SERVICE_ROLE_KEY not configured" } });
    }
    if (!req.file) {
        return res.status(400).json({ error: { code: "NO_FILE", message: "attach a 'file' field" } });
    }
    const index = String(req.query.index ?? "").toLowerCase();
    const year = Number(req.query.year ?? 0);
    if (!index || !year) {
        return res
            .status(400)
            .json({ error: { code: "BAD_QUERY", message: "index and year are required" } });
    }
    const path = `${index}/${index.toUpperCase()}_Latur_${year}.geojson`;
    const { error } = await supabaseAdmin.storage
        .from("processed")
        .upload(path, req.file.buffer, {
        contentType: "application/geo+json",
        upsert: true,
    });
    if (error) {
        return res
            .status(500)
            .json({ error: { code: "UPLOAD_FAILED", message: error.message } });
    }
    return res.status(201).json({ ok: true, path });
});
