"use client";

import { useCallback, useEffect, useState } from "react";
import type { FeatureCollection } from "geojson";
import { analyseAoi, clearAoi, loadSavedAoi, parseAoi, saveAoi, type AoiResult } from "@/lib/aoi";
import { loadTimeseries, loadVillages } from "@/lib/data";

/** Holds the uploaded AOI, and re-scores it whenever the month changes. */
export function useAoi(period: string) {
  const [aoi, setAoi] = useState<FeatureCollection | null>(null);
  const [name, setName] = useState("");
  const [result, setResult] = useState<AoiResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const s = loadSavedAoi();
    if (s) { setAoi(s.fc); setName(s.name); }
  }, []);

  useEffect(() => {
    if (!aoi) { setResult(null); return; }
    let alive = true;
    setBusy(true);
    Promise.all([loadVillages(), loadTimeseries()])
      .then(([v, ts]) => {
        // let the spinner paint before the (CPU-bound) intersection
        setTimeout(() => {
          if (!alive) return;
          try { setResult(analyseAoi(aoi, v, ts, period)); setError(null); }
          catch (e) { setError(String((e as Error).message ?? e)); }
          setBusy(false);
        }, 30);
      })
      .catch((e) => { if (alive) { setError(String(e)); setBusy(false); } });
    return () => { alive = false; };
  }, [aoi, period]);

  const upload = useCallback(async (file: File) => {
    setError(null);
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error("File is larger than 20 MB.");
      if (/\.(zip|shp)$/i.test(file.name)) throw new Error("Shapefiles are not read in the browser. Convert to GeoJSON (ogr2ogr -f GeoJSON -t_srs EPSG:4326 out.geojson in.shp) and upload that.");
      const fc = parseAoi(await file.text());
      saveAoi(fc, file.name);
      setAoi(fc); setName(file.name);
    } catch (e) { setError(String((e as Error).message ?? e)); }
  }, []);

  const clear = useCallback(() => { clearAoi(); setAoi(null); setResult(null); setName(""); setError(null); }, []);
  return { aoi, name, result, busy, error, upload, clear };
}
