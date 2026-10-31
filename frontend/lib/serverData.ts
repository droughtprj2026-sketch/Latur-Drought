// Server-side reads for the /api/v1 routes: Supabase Storage first (when configured),
// otherwise the bundled /public/data copy. Results are memoised for a few minutes because
// Next's fetch cache refuses bodies over 2 MB and the village history is ~20 MB.

import fs from "node:fs";
import path from "node:path";

const BASE = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const BUCKET = process.env.NEXT_PUBLIC_SUPABASE_BUCKET || "drought-data";
const TTL_MS = 5 * 60 * 1000;
const LOCAL = path.join(process.cwd(), "public/data");

const memo = new Map<string, { at: number; data: unknown }>();

export async function readData<T = any>(name: string): Promise<T | null> {
  const hit = memo.get(name);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.data as T;

  let data: unknown = null;
  if (BASE && process.env.NEXT_PUBLIC_DATA_SOURCE !== "static") {
    try {
      const r = await fetch(`${BASE.replace(/\/$/, "")}/storage/v1/object/public/${BUCKET}/${name}`, { cache: "no-store" });
      if (r.ok) data = await r.json();
      else console.warn(`[data] ${name}: Supabase answered ${r.status}`);
    } catch (e) {
      console.warn(`[data] ${name}: Supabase unreachable`, e);
    }
  }
  if (data === null) {
    const f = path.join(LOCAL, name);
    try {
      if (fs.existsSync(f)) data = JSON.parse(fs.readFileSync(f, "utf-8"));
    } catch (e) {
      console.error(`[data] cannot read ${f}`, e);
    }
  }
  if (data !== null) memo.set(name, { at: Date.now(), data });
  else if (hit) return hit.data as T;      // serve stale rather than nothing
  return data as T | null;
}
