"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MetricName } from "@/lib/metrics";
import { METRICS } from "@/lib/metrics";
import { PermanentSidebar } from "@/components/panels/PermanentSidebar";
import { MonthlyTimelineScrubber } from "@/components/map/MonthlyTimelineScrubber";
import { LayerSelect } from "@/components/dashboard/LayerSelect";
import { StatusRibbon } from "@/components/dashboard/StatusRibbon";
import { AoiCard } from "@/components/aoi/AoiCard";
import { useAoi } from "@/components/aoi/useAoi";
import { codeForCDI } from "@/lib/classify";
import {
  activeVillage, latestCoveredPeriod, recordMarkers, tehsilNames, loadBaselines, loadTimeseries, loadVillageIndex, loadVillages,
  toVillageProperties, type Baselines, type TimeseriesById, type VillageFeatureProps, type VillagesByTehsil,
} from "@/lib/data";

const LaturMap = dynamic(() => import("@/components/map/LaturMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-paper font-mono text-xs text-ink/60">Loading map…</div>
  ),
});

export default function HomePage() {
  const [metric, setMetric] = useState<MetricName>("cdi");
  const [tehsil, setTehsil] = useState("All");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [period, setPeriod] = useState("");
  const [satellite, setSatellite] = useState(false);

  const [ts, setTs] = useState<TimeseriesById | null>(null);
  const [vIndex, setVIndex] = useState<VillagesByTehsil | null>(null);
  const [baselines, setBaselines] = useState<Baselines | null>(null);
  const [props, setProps] = useState<Map<number, VillageFeatureProps>>(new Map());
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([loadTimeseries(), loadVillageIndex(), loadBaselines(), loadVillages()])
      .then(([t, v, b, g]) => {
        setTs(t); setVIndex(v); setBaselines(b);
        setProps(new Map(g.features.map((f) => [Number((f.properties as any).id), f.properties as unknown as VillageFeatureProps])));
        setPeriod((p) => p || latestCoveredPeriod(t) || "");
      })
      .catch((e) => setLoadError(String(e)));
  }, []);

  const periods = useMemo(() => {
    if (!ts) return [];
    const set = new Set<string>();
    for (const pts of Object.values(ts)) for (const x of pts) set.add(x.p);
    return [...set].sort();
  }, [ts]);
  const markers = useMemo(() => (ts ? recordMarkers(ts) : []), [ts]);
  const tehsils = useMemo(() => ["All", ...(vIndex ? tehsilNames(vIndex) : [])], [vIndex]);
  const latest = useMemo(() => (ts ? latestCoveredPeriod(ts) ?? periods[periods.length - 1] : undefined), [ts, periods]);

  const aoiState = useAoi(period || "2000-01");

  // ---- Summary for the villages on screen (same rules as the map legend) ----
  const summary = useMemo(() => {
    if (!ts || !vIndex || !period) return null;
    let total = 0, assessed = 0, inDrought = 0, d2plus = 0, sum = 0, hasNdvi = 0, hasRain = 0, hasSpi = 0;
    const KEYS = ["ndvi", "vci", "vhi", "rain", "spi1", "spi3", "spi6", "spi12", "tci", "smi", "lst"] as const;
    const acc: Record<string, { s: number; n: number }> = Object.fromEntries(KEYS.map((k) => [k, { s: 0, n: 0 }]));
    for (const [t, vs] of Object.entries(vIndex)) {
      if (tehsil !== "All" && t !== tehsil) continue;
      for (const v of vs) {
        total++;
        const pt = ts[String(v.id)]?.find((x) => x.p === period);
        if (!pt) continue;
        for (const k of KEYS) { const v = (pt as any)[k]; if (v != null) { acc[k].s += v; acc[k].n++; } }
        if (pt.ndvi != null) hasNdvi++;
        if (pt.rain != null) hasRain++;
        if (pt.spi1 != null) hasSpi++;
        if (pt.cdi == null) continue;
        assessed++; sum += pt.cdi;
        const c = codeForCDI(pt.cdi);
        if (c !== "None") inDrought++;
        if (c === "D2" || c === "D3" || c === "D4") d2plus++;
      }
    }
    const means: Record<string, number | null> = Object.fromEntries(KEYS.map((k) => [k, acc[k].n ? acc[k].s / acc[k].n : null]));
    return { total, assessed, inDrought, d2plus, mean: assessed ? sum / assessed : null, hasNdvi, hasRain, hasSpi, means };
  }, [ts, vIndex, period, tehsil]);

  const selected = useMemo(() => {
    if (selectedId == null || !period) return null;
    const p = props.get(selectedId);
    return p ? toVillageProperties(activeVillage(p, ts, baselines, period)) : null;
  }, [selectedId, props, ts, baselines, period]);

  const onPick = useCallback((id: number) => {
    setSelectedId(id);
    const p = props.get(id);
    if (p && tehsil !== "All" && String(p.tehsil) !== tehsil) setTehsil("All");
  }, [props, tehsil]);

  const fileRef = useRef<HTMLInputElement>(null);
  const villageOptions = useMemo(() => {
    if (!vIndex) return [];
    return Object.entries(vIndex).filter(([t]) => tehsil === "All" || t === tehsil).sort(([a], [b]) => a.localeCompare(b));
  }, [vIndex, tehsil]);

  const pct = (n: number, d: number) => (d ? Math.round((100 * n) / d) : 0);

  return (
    <div className="flex flex-col lg:h-[calc(100dvh-3.5rem)] lg:flex-row">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-ink/15 bg-paper px-4 py-2">
          <Field label="Tehsil">
            <select aria-label="Tehsil" value={tehsil} onChange={(e) => { setTehsil(e.target.value); setSelectedId(null); }}
              className="cursor-pointer rounded border border-ink/20 bg-paper px-2 py-1.5 text-xs font-medium">
              {tehsils.map((t) => <option key={t} value={t}>{t === "All" ? "All 10 tehsils" : t}</option>)}
            </select>
          </Field>
          <Field label="Village">
            <select aria-label="Village" value={selectedId ?? ""} onChange={(e) => (e.target.value ? onPick(Number(e.target.value)) : setSelectedId(null))}
              className="max-w-[210px] cursor-pointer rounded border border-ink/20 bg-paper px-2 py-1.5 text-xs font-medium">
              <option value="">{summary ? `Choose from ${summary.total}` : "Loading…"}</option>
              {villageOptions.map(([t, vs]) => (
                <optgroup key={t} label={t}>
                  {vs.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                </optgroup>
              ))}
            </select>
          </Field>
          <Field label="Layer"><LayerSelect value={metric} onChange={setMetric} exclude={["Long-term"]} /></Field>
          <label className="flex cursor-pointer items-center gap-1.5 text-xs">
            <input type="checkbox" checked={satellite} onChange={(e) => setSatellite(e.target.checked)} className="accent-clay" />
            Satellite underlay
          </label>
          <input ref={fileRef} type="file" accept=".geojson,.json,application/geo+json" className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) aoiState.upload(f); e.target.value = ""; }} />
          <button type="button" onClick={() => fileRef.current?.click()}
            className="rounded border border-teal px-2.5 py-1.5 font-mono text-[11px] font-semibold text-teal hover:bg-teal/10">
            {aoiState.aoi ? "Replace AOI" : "Upload AOI (GeoJSON)"}
          </button>
          <div className="ml-auto"><StatusRibbon /></div>
        </div>

        {aoiState.error && (
          <p role="alert" className="border-b border-d3/40 bg-d3/10 px-4 py-1.5 text-xs text-ink">{aoiState.error}</p>
        )}
        {loadError && <p role="alert" className="border-b border-d3/40 bg-d3/10 px-4 py-1.5 text-xs">Data failed to load: {loadError}</p>}

        {/* Headline numbers */}
        <dl className="grid grid-cols-2 gap-px border-b border-ink/15 bg-ink/15 sm:grid-cols-5">
          <Kpi label="Villages assessed" value={summary ? `${summary.assessed}` : "–"} note={summary ? `of ${summary.total} polygons` : ""} />
          <Kpi label="In drought · D0–D4" value={summary ? `${summary.inDrought}` : "–"} note={summary ? `${pct(summary.inDrought, summary.assessed)}% of assessed` : ""} />
          <Kpi label="Severe or worse · D2–D4" value={summary ? `${summary.d2plus}` : "–"} note={summary ? `${pct(summary.d2plus, summary.assessed)}% of assessed` : ""} tone="alert" />
          <Kpi label="Mean CDI" value={summary?.mean != null ? summary.mean.toFixed(3) : "–"} note={summary?.mean != null ? METRICS.cdi.bins[METRICS.cdi.bins.findIndex((b) => summary.mean! < b.hi)]?.label ?? "" : ""} />
          <div className="col-span-2 bg-paper px-3 py-1.5 sm:col-span-1">
            <div className="font-mono text-[10px] uppercase tracking-wider text-ink/55">Inputs present · {period}</div>
            {summary ? (
              <div className="mt-1 space-y-0.5">
                <Bar label="Sentinel-2" n={summary.hasNdvi} d={summary.total} />
                <Bar label="CHIRPS rain" n={summary.hasRain} d={summary.total} />
                <Bar label="SPI-1" n={summary.hasSpi} d={summary.total} />
              </div>
            ) : <div className="text-xs">–</div>}
          </div>
        </dl>

        <div className="relative h-[72dvh] min-h-[420px] lg:h-auto lg:min-h-0 lg:flex-1">
          {period && (
            <LaturMap
              metric={metric} tehsil={tehsil} currentPeriod={period} selectedVillageId={selectedId}
              onSelectVillage={(v) => setSelectedId(v.id)} onPeriodChange={setPeriod} aoi={aoiState.aoi} showSatellite={satellite}
              topLeft={aoiState.result ? (
                <AoiCard name={aoiState.name} result={aoiState.result} period={period} onClear={aoiState.clear} onSelect={onPick} />
              ) : aoiState.busy ? (
                <div className="rounded border border-teal/50 bg-paper/95 px-3 py-2 font-mono text-xs text-teal shadow-card">Intersecting AOI with 954 villages…</div>
              ) : null}
            >
              {periods.length > 0 && (
                <MonthlyTimelineScrubber periods={periods} currentPeriod={period} onPeriodChange={setPeriod} latestPeriod={latest} markers={markers} />
              )}
            </LaturMap>
          )}
        </div>
      </div>

      <div className="w-full flex-shrink-0 lg:h-full lg:w-[430px] xl:w-[470px]">
        <PermanentSidebar
          village={selected}
          selectedTehsil={tehsil}
          selectedPeriod={period || "2000-01"}
          summary={summary}
          onSelectTehsil={(t) => { setTehsil(t); setSelectedId(null); }}
        />
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex items-center gap-1.5">
      <span className="font-mono text-[10px] uppercase tracking-wider text-ink/55">{label}</span>
      {children}
    </label>
  );
}

function Kpi({ label, value, note, tone }: { label: string; value: string; note?: string; tone?: "alert" }) {
  return (
    <div className="bg-paper px-3 py-1.5">
      <dt className="font-mono text-[10px] uppercase tracking-wider text-ink/55">{label}</dt>
      <dd className={`font-display text-2xl leading-tight ${tone === "alert" ? "text-d3" : "text-ink"}`}>{value}</dd>
      <div className="truncate text-[10px] text-ink/60">{note}</div>
    </div>
  );
}

function Bar({ label, n, d }: { label: string; n: number; d: number }) {
  const p = d ? (100 * n) / d : 0;
  return (
    <div className="flex items-center gap-1.5 text-[10px]">
      <span className="w-[62px] flex-none text-ink/70">{label}</span>
      <span className="relative h-1.5 flex-1 overflow-hidden rounded-sm bg-ink/10">
        <span className={`absolute inset-y-0 left-0 ${p < 50 ? "bg-d3" : "bg-teal"}`} style={{ width: `${p}%` }} />
      </span>
      <span className="w-8 flex-none text-right font-mono text-ink/70">{Math.round(p)}%</span>
    </div>
  );
}
