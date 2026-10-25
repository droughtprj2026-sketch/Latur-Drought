"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import type { MetricName } from "@/lib/metrics";
import { LayerSelect } from "@/components/dashboard/LayerSelect";
import { MonthlyTimelineScrubber } from "@/components/map/MonthlyTimelineScrubber";
import { VillageIntelligenceDrawer } from "@/components/panels/VillageIntelligenceDrawer";
import { activeVillage, latestCoveredPeriod, loadVillageIndex, recordMarkers, tehsilNames, loadBaselines, loadTimeseries, toVillageProperties, type Baselines, type TimeseriesById } from "@/lib/data";
import type { ActiveVillage } from "@/lib/metrics";

const LaturMap = dynamic(() => import("@/components/map/LaturMap"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center font-mono text-xs text-ink/60">Loading map…</div>,
});

export default function FullscreenMapPage() {
  const [metric, setMetric] = useState<MetricName>("cdi");
  const [tehsil, setTehsil] = useState("All");
  const [period, setPeriod] = useState("");
  const [picked, setPicked] = useState<ActiveVillage | null>(null);
  const [ts, setTs] = useState<TimeseriesById | null>(null);
  const [baselines, setBaselines] = useState<Baselines | null>(null);
  const [tehsils, setTehsils] = useState<string[]>(["All"]);

  useEffect(() => { loadVillageIndex().then((v) => setTehsils(["All", ...tehsilNames(v)])).catch(() => null); }, []);
  useEffect(() => {
    Promise.all([loadTimeseries(), loadBaselines()]).then(([t, b]) => {
      setTs(t); setBaselines(b); setPeriod((p) => p || latestCoveredPeriod(t) || "");
    }).catch(() => null);
  }, []);

  const periods = useMemo(() => {
    const s = new Set<string>();
    if (ts) for (const pts of Object.values(ts)) for (const x of pts) s.add(x.p);
    return [...s].sort();
  }, [ts]);

  // keep the drawer in step with the month being scrubbed
  const drawerVillage = useMemo(() => {
    if (!picked || !period) return null;
    return toVillageProperties(activeVillage(
      { id: picked.id, village: picked.village, tehsil: picked.tehsil, AREA_SQKM: picked.area_sqkm }, ts, baselines, period));
  }, [picked, ts, baselines, period]);

  return (
    <div className="relative h-[calc(100dvh-3.5rem)] w-full">
      {period && (
        <LaturMap
          metric={metric} tehsil={tehsil} currentPeriod={period}
          selectedVillageId={picked?.id ?? null} onSelectVillage={setPicked} onPeriodChange={setPeriod}
          rightInset={picked ? 512 : 0}
          topLeft={
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-ink/15 bg-paper/95 p-2 shadow-card backdrop-blur">
              <LayerSelect value={metric} onChange={setMetric} />
              <select value={tehsil} onChange={(e) => setTehsil(e.target.value)} aria-label="Tehsil"
                className="cursor-pointer rounded border border-ink/20 bg-paper px-2 py-1.5 text-xs font-medium">
                {tehsils.map((t) => <option key={t} value={t}>{t === "All" ? "All 10 tehsils" : t}</option>)}
              </select>
            </div>
          }
        >
          {periods.length > 0 && <MonthlyTimelineScrubber periods={periods} currentPeriod={period} onPeriodChange={setPeriod} markers={ts ? recordMarkers(ts) : []} />}
        </LaturMap>
      )}
      <VillageIntelligenceDrawer village={drawerVillage} onClose={() => setPicked(null)} />
    </div>
  );
}
