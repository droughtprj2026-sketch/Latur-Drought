// Where the dashboard's data files come from.
//
// With NEXT_PUBLIC_SUPABASE_URL set, files are read from the public Supabase Storage bucket
// (published by scripts/publish_supabase.py). If that request fails, or Supabase is not
// configured, the copy bundled in /public/data is used and `usingFallback()` turns true so
// the UI can say it is showing a snapshot instead of live data.

const URL_ = process.env.NEXT_PUBLIC_SUPABASE_URL;
const BUCKET = process.env.NEXT_PUBLIC_SUPABASE_BUCKET || "drought-data";

export const remoteBase: string | null =
  URL_ && process.env.NEXT_PUBLIC_DATA_SOURCE !== "static"
    ? `${URL_.replace(/\/$/, "")}/storage/v1/object/public/${BUCKET}`
    : null;

let fallbackUsed = false;
const listeners = new Set<() => void>();
export const usingFallback = () => fallbackUsed;
export const onFallback = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn); }; };

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

export async function fetchData<T>(name: string): Promise<T> {
  if (remoteBase) {
    try {
      return await getJson<T>(`${remoteBase}/${name}`);
    } catch (e) {
      console.warn(`[data] Supabase read of ${name} failed, using bundled snapshot`, e);
      if (!fallbackUsed) { fallbackUsed = true; listeners.forEach((f) => f()); }
    }
  }
  return getJson<T>(`/data/${name}`);
}
