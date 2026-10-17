import { Router } from "express";
import multer from "multer";
import { requireAdmin, requireUser } from "../middleware/supabase.js";
export const aoiRouter = Router();
const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 20 * 1024 * 1024 }, // 20 MB per spec
});
// POST /upload/aoi
//
// Validates the upload (shapefile zip or GeoJSON FeatureCollection) and
// forwards it to the Go admin endpoint, which writes it under
// data/vector/ and kicks off scripts/pipeline_gee.py against the AOI.
aoiRouter.post("/aoi", requireUser, requireAdmin, upload.single("file"), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({
            error: { code: "NO_FILE", message: "attach a 'file' field" },
        });
    }
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
    const goURL = (process.env.GO_API_URL ?? "http://localhost:8080") +
        "/api/v1/admin/aoi";
    const contentType = req.file.mimetype.includes("zip")
        ? "application/zip"
        : "application/geo+json";
    const res2 = await fetch(goURL, {
        method: "POST",
        headers: {
            "Content-Type": contentType,
            Authorization: `Bearer ${serviceKey ?? ""}`,
        },
        body: req.file.buffer,
    });
    const body = await res2.text();
    res.status(res2.status).type("application/json").send(body);
});
