// Client-side AOI analysis: parse an uploaded GeoJSON, intersect it with the
// 954 village polygons, and summarise drought for the overlapped area.
// Runs entirely in the browser; nothing is uploaded.

import intersect from "@turf/intersect";
import area from "@turf/area";
import { featureCollection } from "@turf/helpers";
import type { Feature, FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { codeForCDI } from "./classify";
import type { TimeseriesById } from "./data";

export interface AoiVillageRow {
  id: number; village: string; tehsil: string;
  overlap_km2: number; share_of_village: number;
  cdi: number | null; cls: string;
  rain: number | null; ndvi: number | null; spi3: number | null;
}
export interface AoiResult {
  features: number;
  aoi_km2: number;
  covered_km2: number;          // part of the AOI that lies inside Latur villages
  rows: AoiVillageRow[];        // sorted by overlap, largest first
  weighted_cdi: number | null; // area-weighted over villages that have a score
  weighted_class: string;
  scored_share: number;         // share of overlap area that has a score
  by_class: Record<string, number>; // km2 by D-class
}

type Poly = Feature<Polygon | MultiPolygon>;

export function parseAoi(text: string): FeatureCollection {
  let gj: any;
  try { gj = JSON.parse(text); } catch { throw new Error("File is not valid JSON/GeoJSON."); }
  const feats: Feature[] =
    gj.type === "FeatureCollection" ? gj.features :
    gj.type === "Feature" ? [gj] :
    gj.type && gj.coordinates ? [{ type: "Feature", properties: {}, geometry: gj }] : [];
  const polys = feats.filter((f) => f?.geometry && (f.geometry.type === "Polygon" || f.geometry.type === "MultiPolygon"));
  if (!polys.length) throw new Error("No Polygon or MultiPolygon features found. Points and lines cannot define an area.");
  // Coordinates must look like lon/lat degrees (EPSG:4326).
  const sample = firstCoord(polys[0].geometry as any);
  if (!sample || Math.abs(sample[0]) > 180 || Math.abs(sample[1]) > 90) {
    throw new Error("Coordinates are not lon/lat degrees. Re-export the layer in EPSG:4326 (WGS 84).");
  }
  return { type: "FeatureCollection", features: polys };
}

function firstCoord(g: any): number[] | null {
  let c = g.coordinates;
  while (Array.isArray(c) && Array.isArray(c[0])) c = c[0];
  return Array.isArray(c) && typeof c[0] === "number" ? c : null;
}

function bboxOf(g: any): [number, number, number, number] {
  let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
  const walk = (c: any) => {
    if (typeof c[0] === "number") { x0 = Math.min(x0, c[0]); x1 = Math.max(x1, c[0]); y0 = Math.min(y0, c[1]); y1 = Math.max(y1, c[1]); }
    else c.forEach(walk);
  };
  walk(g.coordinates);
  return [x0, y0, x1, y1];
}
const overlaps = (a: number[], b: number[]) => a[0] <= b[2] && a[2] >= b[0] && a[1] <= b[3] && a[3] >= b[1];

export function analyseAoi(
  aoi: FeatureCollection, villages: FeatureCollection, ts: TimeseriesById, period: string,
): AoiResult {
  const aoiPolys = aoi.features as Poly[];
  const aoiBoxes = aoiPolys.map((f) => bboxOf(f.geometry));
  const aoi_m2 = aoiPolys.reduce((s, f) => s + area(f), 0);

  const rows: AoiVillageRow[] = [];
  let covered = 0;
  for (const vf of villages.features as Poly[]) {
    const vb = bboxOf(vf.geometry);
    let ov = 0;
    aoiPolys.forEach((a, i) => {
      if (!overlaps(vb, aoiBoxes[i])) return;
      try {
        const x = intersect(featureCollection([a, vf]));
        if (x) ov += area(x);
      } catch { /* degenerate ring: skip this pair */ }
    });
    if (ov <= 0) continue;
    covered += ov;
    const p: any = vf.properties;
    const pt = ts[String(p.id)]?.find((x) => x.p === period);
    const v_m2 = area(vf);
    rows.push({
      id: Number(p.id), village: p.village, tehsil: p.tehsil,
      overlap_km2: ov / 1e6, share_of_village: v_m2 ? ov / v_m2 : 0,
      cdi: pt?.cdi ?? null, cls: pt?.cdi != null ? codeForCDI(pt.cdi) : "ND",
      rain: pt?.rain ?? null, ndvi: pt?.ndvi ?? null, spi3: pt?.spi3 ?? null,
    });
  }
  rows.sort((a, b) => b.overlap_km2 - a.overlap_km2);

  const scored = rows.filter((r) => r.cdi != null);
  const wsum = scored.reduce((s, r) => s + r.overlap_km2, 0);
  const weighted = wsum ? scored.reduce((s, r) => s + r.overlap_km2 * (r.cdi as number), 0) / wsum : null;
  const by_class: Record<string, number> = {};
  rows.forEach((r) => { by_class[r.cls] = (by_class[r.cls] ?? 0) + r.overlap_km2; });
  const total = rows.reduce((s, r) => s + r.overlap_km2, 0);

  return {
    features: aoiPolys.length, aoi_km2: aoi_m2 / 1e6, covered_km2: covered / 1e6, rows,
    weighted_cdi: weighted, weighted_class: weighted != null ? codeForCDI(weighted) : "ND",
    scored_share: total ? wsum / total : 0, by_class,
  };
}

const KEY = "latur.aoi.v1";
export function saveAoi(fc: FeatureCollection, name: string) {
  try { sessionStorage.setItem(KEY, JSON.stringify({ name, fc })); } catch { /* storage unavailable */ }
}
export function loadSavedAoi(): { name: string; fc: FeatureCollection } | null {
  try { const s = sessionStorage.getItem(KEY); return s ? JSON.parse(s) : null; } catch { return null; }
}
export function clearAoi() { try { sessionStorage.removeItem(KEY); } catch { /* ignore */ } }

export function resultToCsv(r: AoiResult, period: string): string {
  const head = "village_id,village,tehsil,period,overlap_km2,share_of_village,cdi,class,rain_mm,ndvi,spi3";
  const q = (s: string) => `"${s.replace(/"/g, '""')}"`;
  const lines = r.rows.map((x) => [x.id, q(x.village), q(x.tehsil), period, x.overlap_km2.toFixed(3),
    x.share_of_village.toFixed(3), x.cdi ?? "", x.cls, x.rain ?? "", x.ndvi ?? "", x.spi3 ?? ""].join(","));
  return [head, ...lines].join("\n");
}
