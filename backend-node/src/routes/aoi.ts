import { Router } from "express";
import multer from "multer";
import path from "node:path";
import fs from "node:fs";
import { requireAdmin, requireUser } from "../middleware/supabase.js";

export const aoiRouter = Router();

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 20 * 1024 * 1024 },
});

const VECTOR_DIR = path.resolve(__dirname, "../../../data/vector");

aoiRouter.post(
  "/aoi",
  requireUser,
  requireAdmin,
  upload.single("file"),
  async (req, res) => {
    if (!req.file) {
      return res.status(400).json({
        error: { code: "NO_FILE", message: "attach a 'file' field" },
      });
    }

    const ext = req.file.mimetype.includes("zip") ? ".zip" : ".geojson";
    const dest = path.join(VECTOR_DIR, `custom_aoi${ext}`);

    try {
      fs.mkdirSync(VECTOR_DIR, { recursive: true });
      fs.writeFileSync(dest, req.file.buffer);
      res.status(202).json({ status: "accepted", path: dest });
    } catch (err: any) {
      res.status(500).json({
        error: { code: "WRITE_FAILED", message: err.message },
      });
    }
  }
);
