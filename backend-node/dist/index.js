// Latur Drought Monitoring — Node.js gateway.
//
// Purpose: authenticate requests against Supabase, accept processed
// GeoJSON uploads, and proxy everything else to the Go API.
//
// The Go service is the source of truth for drought data; this process
// exists so the frontend has one URL to talk to and so Supabase JWTs
// never have to touch the Go code.
import "dotenv/config";
import cors from "cors";
import express from "express";
import pinoHttp from "pino-http";
import pino from "pino";
import { createProxyMiddleware } from "http-proxy-middleware";
import { authRouter } from "./routes/auth.js";
import { uploadRouter } from "./routes/upload.js";
import { aoiRouter } from "./routes/aoi.js";
import { apiRouter } from "./routes/api.js";
const PORT = Number(process.env.NODE_GATEWAY_PORT ?? 4000);
const GO_API_URL = process.env.GO_API_URL ?? "http://localhost:8080";
const logger = pino({ level: process.env.LOG_LEVEL ?? "info" });
const app = express();
app.use(pinoHttp({ logger }));
app.use(cors({
    origin: (process.env.ALLOWED_ORIGINS ?? "http://localhost:3000").split(","),
    credentials: true,
}));
app.use(express.json({ limit: "2mb" }));
// --- health ----------------------------------------------------------
app.get("/health", (_req, res) => res.json({ status: "ok" }));
// --- auth (Supabase pass-through) ------------------------------------
app.use("/auth", authRouter);
// --- uploads: processed GeoJSON into Supabase storage ----------------
app.use("/upload", uploadRouter);
// --- AOI upload: pipeline input (shapefile zip or GeoJSON) -----------
app.use("/upload", aoiRouter);
// --- database-backed API routes ---------------------------------------
app.use("/api/v1", apiRouter);
// --- everything else proxies to the Go API ---------------------------
app.use("/api", createProxyMiddleware({
    target: GO_API_URL,
    changeOrigin: true,
    pathRewrite: (path) => path,
    on: {
        proxyReq: (proxyReq, req) => {
            const auth = req.headers.authorization;
            if (auth)
                proxyReq.setHeader("authorization", auth);
        },
    },
}));
app.use((req, res) => res.status(404).json({ error: { code: "NOT_FOUND", message: `no route for ${req.path}` } }));
app.listen(PORT, () => {
    logger.info({ port: PORT, goApi: GO_API_URL }, "gateway listening");
});
