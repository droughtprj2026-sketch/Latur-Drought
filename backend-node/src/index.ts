// Latur Drought Monitoring — Node.js API server.
//
// Serves all drought-monitoring endpoints (indices, CDI, time-series,
// village data) from a local SQLite database and Dashboard JSON files.
// Also handles Supabase auth pass-through and GeoJSON uploads.
import "dotenv/config";
import cors from "cors";
import express from "express";
import pinoHttp from "pino-http";
import pino from "pino";
import { authRouter } from "./routes/auth.js";
import { uploadRouter } from "./routes/upload.js";
import { aoiRouter } from "./routes/aoi.js";
import { apiRouter } from "./routes/api.js";

const PORT = Number(process.env.PORT ?? 4000);

const logger = pino({ level: process.env.LOG_LEVEL ?? "info" });
const app = express();

app.use(pinoHttp({ logger }));
app.use(
  cors({
    origin: (process.env.ALLOWED_ORIGINS ?? "http://localhost:3000").split(","),
    credentials: true,
  })
);
app.use(express.json({ limit: "2mb" }));

// --- health ----------------------------------------------------------
app.get("/health", (_req, res) => res.json({ status: "ok" }));

// --- auth (Supabase pass-through) ------------------------------------
app.use("/auth", authRouter);

// --- uploads: processed GeoJSON into Supabase storage ----------------
app.use("/upload", uploadRouter);

// --- AOI upload: pipeline input (shapefile zip or GeoJSON) -----------
app.use("/upload", aoiRouter);

// --- API routes -------------------------------------------------------
app.use("/api/v1", apiRouter);

app.use((req, res) => res.status(404).json({ error: { code: "NOT_FOUND", message: `no route for ${req.path}` } }));

app.listen(PORT, () => {
  logger.info({ port: PORT }, "API server listening");
});
