import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { NextFunction, Request, Response } from "express";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_ANON = process.env.SUPABASE_ANON_KEY;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;

export const supabase: SupabaseClient | null = (SUPABASE_URL && SUPABASE_ANON)
  ? createClient(SUPABASE_URL, SUPABASE_ANON)
  : null;
export const supabaseAdmin: SupabaseClient | null = (SUPABASE_URL && SUPABASE_SERVICE)
  ? createClient(SUPABASE_URL, SUPABASE_SERVICE, { auth: { persistSession: false } })
  : null;

/** Attach Supabase user to `req.user` from the Bearer token. 401 on failure. */
export async function requireUser(req: Request, res: Response, next: NextFunction): Promise<void> {
  if (!supabase) {
    (req as Request & { user: any }).user = { id: "local-dev", role: "admin", app_metadata: { role: "admin" } };
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
  (req as Request & { user: typeof data.user }).user = data.user;
  next();
}

/** 403 unless the authenticated user has the "admin" role claim. */
export function requireAdmin(req: Request, res: Response, next: NextFunction): void {
  const user = (req as Request & { user?: { role?: string; app_metadata?: { role?: string } } }).user;
  const role = user?.app_metadata?.role ?? user?.role;
  if (role !== "admin") {
    res.status(403).json({ error: { code: "FORBIDDEN", message: "admin role required" } });
    return;
  }
  next();
}
