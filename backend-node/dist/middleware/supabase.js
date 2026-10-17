import { createClient } from "@supabase/supabase-js";
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_ANON = process.env.SUPABASE_ANON_KEY;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;
export const supabase = (SUPABASE_URL && SUPABASE_ANON)
    ? createClient(SUPABASE_URL, SUPABASE_ANON)
    : null;
export const supabaseAdmin = (SUPABASE_URL && SUPABASE_SERVICE)
    ? createClient(SUPABASE_URL, SUPABASE_SERVICE, { auth: { persistSession: false } })
    : null;
/** Attach Supabase user to `req.user` from the Bearer token. 401 on failure. */
export async function requireUser(req, res, next) {
    if (!supabase) {
        req.user = { id: "local-dev", role: "admin", app_metadata: { role: "admin" } };
        return next();
    }
    const auth = req.headers.authorization ?? "";
    const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
    if (!token) {
        res.status(401).json({ error: { code: "NO_TOKEN", message: "Bearer token required" } });
        return;
    }
    const { data, error } = await supabase.auth.getUser(token);
    if (error || !data.user) {
        res.status(401).json({ error: { code: "BAD_TOKEN", message: "invalid or expired token" } });
        return;
    }
    req.user = data.user;
    next();
}
/** 403 unless the authenticated user has the "admin" role claim. */
export function requireAdmin(req, res, next) {
    const user = req.user;
    const role = user?.app_metadata?.role ?? user?.role;
    if (role !== "admin") {
        res.status(403).json({ error: { code: "FORBIDDEN", message: "admin role required" } });
        return;
    }
    next();
}
