import dotenv from "dotenv";
import path from "node:path";
dotenv.config();
dotenv.config({ path: path.resolve(process.cwd(), "../.env") });
dotenv.config({ path: path.resolve(process.cwd(), ".env") });
import cors from "cors";
import express from "express";
import pinoHttp from "pino-http";
import pino from "pino";
import { authRouter } from "./routes/auth.js";
import { uploadRouter } from "./routes/upload.js";
import { aoiRouter } from "./routes/aoi.js";
import { apiRouter } from "./routes/api.js";
const PORT = Number(process.env.NODE_GATEWAY_PORT ?? 4000);
const logger = pino({ level: process.env.LOG_LEVEL ?? "info" });
const app = express();
app.use(pinoHttp({ logger }));
app.use(cors({
    origin: (process.env.ALLOWED_ORIGINS ?? "http://localhost:3000,http://127.0.0.1:3000").split(","),
    credentials: true,
}));
app.use(express.json({ limit: "5mb" }));
// --- health ----------------------------------------------------------
app.get("/health", (_req, res) => res.json({ status: "ok", service: "latur-drought-backend-node" }));
// --- auth (Supabase pass-through) ------------------------------------
app.use("/auth", authRouter);
// --- uploads: processed GeoJSON into Supabase storage ----------------
app.use("/upload", uploadRouter);
// --- AOI upload: pipeline input (shapefile zip or GeoJSON) -----------
app.use("/upload", aoiRouter);
// --- Primary API routes (Supabase + Fast Cache Fallback) -------------
app.use("/api/v1", apiRouter);
// Fallback for /api queries
app.use("/api", apiRouter);
app.use((req, res) => res.status(404).json({ error: { code: "NOT_FOUND", message: `no route for ${req.path}` } }));
app.listen(PORT, () => {
    logger.info({ port: PORT }, "Standalone Node.js backend listening on port " + PORT);
});
