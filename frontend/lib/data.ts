// Shared, module-cached loaders for the static dashboard data. Every
// consumer (map, sidebar, drawer, charts) goes through here, so the
// 20 MB village history is downloaded once per page load, not once per
// click.

import type { ActiveVillage } from "./metrics";
import { fetchData } from "./dataSource";

export interface TsPoint {
  p: string;
  cdi: number | null; cls: string;
  ndvi: number | null; evi: number | null; vci: number | null; vhi: number | null; pci: number | null;
  tci?: number | null; smi?: number | null; lst?: number | null; vv?: number | null;
  rain: number | null;
  spi1: number | null; spi3: number | null; spi6: number | null; spi12: number | null;
}
export type TimeseriesById = Record<string, TsPoint[]>;

export interface BaselineStats {
  ndvi_mean?: number | null; ndvi_std?: number | null;
  vci_mean?: number | null;  vci_std?: number | null;
  rain_mean?: number | null; rain_std?: number | null;
  spi3_mean?: number | null; spi3_std?: number | null;
}
export interface Baselines {
  district: Record<string, BaselineStats>;
  villages: Record<string, Record<string, BaselineStats>>;
}

export interface VillageRef { id: number; name: string }
export type VillagesByTehsil = Record<string, VillageRef[]>;

export interface VillageFeatureProps {
  id: number; village: string; tehsil: string; AREA_SQKM?: number;
  [k: string]: unknown;
}

const memo = new Map<string, Promise<any>>();
function load<T>(name: string): Promise<T> {
  let p = memo.get(name);
  if (!p) {
    p = fetchData<T>(name).catch((e) => { memo.delete(name); throw e; });
    memo.set(name, p);
  }
  return p as Promise<T>;
}

export const loadTimeseries   = () => load<TimeseriesById>("village_timeseries.json");
export const loadBaselines    = () => load<Baselines>("village_baselines.json");
export const loadVillageIndex = () => load<VillagesByTehsil>("villages_by_tehsil.json");
export const loadVillages     = () => load<GeoJSON.FeatureCollection>("latur_villages_latest.geojson");
export const loadTehsils      = () => load<GeoJSON.FeatureCollection>("latur_tehsils.geojson");
export const loadDistrict     = () => load<GeoJSON.FeatureCollection>("latur_district.geojson");
export const loadDistrictMonthly = () => load<any>("district_monthly.json");
export const loadTehsilAnalytics = () => load<any>("tehsil_analytics.json");
// Status is always read through the API route so it reflects the newest pipeline run.
export const loadStatus = () => fetch("/api/v1/status").then((r) => {
  if (!r.ok) throw new Error(`status: ${r.status}`);
  return r.json();
});

export function activeVillage(
  props: VillageFeatureProps,
  ts: TimeseriesById | null,
  baselines: Baselines | null,
  period: string,
): ActiveVillage {
  const id = Number(props.id);
  const pt = ts?.[String(id)]?.find((x) => x.p === period);
  const month = String(parseInt(period.split("-")[1] ?? "0", 10));
  return {
    id,
    village: String(props.village ?? props.VILLAGE ?? props.name ?? ""),
    tehsil: String(props.tehsil ?? props.TEHSIL ?? ""),
    period,
    area_sqkm: props.AREA_SQKM,
    cdi: pt?.cdi, cls: pt?.cls,
    ndvi: pt?.ndvi, evi: pt?.evi, vci: pt?.vci, vhi: pt?.vhi, pci: pt?.pci,
    tci: pt?.tci, smi: pt?.smi, lst: pt?.lst, vv: pt?.vv,
    rain: pt?.rain,
    spi1: pt?.spi1, spi3: pt?.spi3, spi6: pt?.spi6, spi12: pt?.spi12,
    base: baselines?.villages?.[String(id)]?.[month] ?? null,
  };
}

/** Latest period for which at least `minShare` of villages have a CDI. */
export function latestCoveredPeriod(ts: TimeseriesById, minShare = 0.5): string | null {
  const counts = new Map<string, number>();
  const ids = Object.keys(ts);
  for (const id of ids) for (const pt of ts[id]) if (pt.cdi != null) counts.set(pt.p, (counts.get(pt.p) ?? 0) + 1);
  const ok = [...counts.entries()].filter(([, n]) => n >= minShare * ids.length).map(([p]) => p).sort();
  return ok.length ? ok[ok.length - 1] : null;
}

/** Shape expected by the sidebar / drawer panels. */
export function toVillageProperties(a: ActiveVillage): any {
  return {
    id: a.id, village_id: a.id, village: a.village, tehsil: a.tehsil, AREA_SQKM: a.area_sqkm,
    period: a.period, date: a.period,
    CDI: a.cdi ?? null, CDI_class: a.cls ?? "ND", class: a.cls ?? "ND",
    TCI: a.tci ?? null, SMI: a.smi ?? null, LST: a.lst ?? null,
    NDVI: a.ndvi ?? null, EVI: a.evi ?? null, VCI: a.vci ?? null, VHI: a.vhi ?? null, PCI: a.pci ?? null,
    Rain_mm: a.rain ?? null,
    SPI1: a.spi1 ?? null, SPI3: a.spi3 ?? null, SPI6: a.spi6 ?? null, SPI12: a.spi12 ?? null,
    baseline_ndvi: a.base?.ndvi_mean ?? null,
  };
}


/** Tehsil names exactly as in the data (no hand-typed list). */
export const tehsilNames = (v: VillagesByTehsil) => Object.keys(v).sort((a, b) => a.localeCompare(b));

/** Mean CDI of the district per month, for months where at least half the villages have a score. */
export function districtCdiByPeriod(ts: TimeseriesById): { p: string; cdi: number }[] {
  const acc = new Map<string, { s: number; n: number }>();
  const ids = Object.keys(ts);
  for (const id of ids) for (const pt of ts[id]) {
    if (pt.cdi == null) continue;
    const a = acc.get(pt.p) ?? { s: 0, n: 0 };
    a.s += pt.cdi; a.n++; acc.set(pt.p, a);
  }
  return [...acc].filter(([, a]) => a.n >= 0.5 * ids.length).map(([p, a]) => ({ p, cdi: a.s / a.n })).sort((x, y) => x.p.localeCompare(y.p));
}

/** Data-derived jump targets for the timeline: the worst and the mildest scored month on record. */
export function recordMarkers(ts: TimeseriesById): { p: string; label: string }[] {
  const d = districtCdiByPeriod(ts);
  if (d.length < 2) return [];
  const worst = d.reduce((a, b) => (b.cdi > a.cdi ? b : a));
  const mild = d.reduce((a, b) => (b.cdi < a.cdi ? b : a));
  return [{ p: worst.p, label: `Highest CDI on record · ${worst.p}` }, { p: mild.p, label: `Lowest CDI on record · ${mild.p}` }];
}
