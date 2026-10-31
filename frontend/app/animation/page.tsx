"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { loadDistrictMonthly } from "@/lib/data";
import { IndexDropdown, type IndexName } from "@/components/ui/IndexDropdown";

const AnimationPlayer = dynamic(
  () => import("@/components/animation/AnimationPlayer").then((m) => m.AnimationPlayer),
  { ssr: false },
);

export default function AnimationPage() {
  const [index, setIndex] = useState<IndexName>("cdi");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [record, setRecord] = useState<string[]>([]);

  // Range comes from the months that exist in the data, not from typed-in dates.
  useEffect(() => {
    loadDistrictMonthly().then((d) => {
      const ps: string[] = (d.series || []).map((x: any) => x.date).filter(Boolean).sort();
      if (!ps.length) return;
      setRecord(ps); setFrom(ps[0]); setTo(ps[ps.length - 1]);
    }).catch(() => null);
  }, []);
  const lastN = (n: number) => { if (record.length) { setFrom(record[Math.max(0, record.length - n)]); setTo(record[record.length - 1]); } };

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 space-y-6 text-slate-900">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
              Decadal Timelapse Engine
            </span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900">
            Historical Spatiotemporal Animation
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Continuous monthly map player stepping sequentially through Latur district's satellite index and drought severity records.
          </p>
        </div>

        {/* Range presets computed from the record */}
        <div className="flex items-center gap-1.5 text-xs font-semibold">
          <button onClick={() => lastN(record.length)} className="px-2.5 py-1 rounded-lg border border-amber-300 bg-amber-100 text-amber-900 shadow-2xs font-bold">
            Full record{record.length ? ` (${record[0]} to ${record[record.length - 1]})` : ""}
          </button>
          <button onClick={() => lastN(36)} className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs">Last 36 months</button>
          <button onClick={() => lastN(12)} className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs">Last 12 months</button>
        </div>
      </div>

      {/* Control Strip */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <IndexDropdown value={index} onChange={setIndex} />
          <div>
            <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1">
              Start Period (YYYY-MM)
            </label>
            <input
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              placeholder="2016-01"
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-mono font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1">
              End Period (YYYY-MM)
            </label>
            <input
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="YYYY-MM"
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-mono font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
          </div>
        </div>
      </div>

      {/* Animation Player Map Viewport */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
        {from && to && <AnimationPlayer index={index} from={from} to={to} />}
      </div>
    </div>
  );
}
