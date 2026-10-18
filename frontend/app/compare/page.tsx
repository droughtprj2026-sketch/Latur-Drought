"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { IndexDropdown, type IndexName } from "@/components/ui/IndexDropdown";

const ComparisonSlider = dynamic(
  () => import("@/components/compare/ComparisonSlider").then((m) => m.ComparisonSlider),
  { ssr: false },
);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

export default function ComparePage() {
  const [index, setIndex] = useState<IndexName>("cdi");
  const [ay, setAY] = useState(2018);
  const [am, setAM] = useState(5);
  const [by, setBY] = useState(2026);
  const [bm, setBM] = useState(10);

  const setPreset = (y1: number, m1: number, y2: number, m2: number) => {
    setAY(y1);
    setAM(m1);
    setBY(y2);
    setBM(m2);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 space-y-6 text-slate-900">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
              Bi-Temporal Spatial Analysis
            </span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900">
            Drought Comparison Curtain Slider
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Interactively wipe between any two historical observation periods to visually evaluate spatial drought spread and recovery.
          </p>
        </div>

        {/* Quick Presets */}
        <div className="flex items-center gap-1.5 text-xs font-semibold">
          <span className="text-slate-400 mr-1 text-[11px]">Presets:</span>
          <button
            onClick={() => setPreset(2018, 5, 2020, 9)}
            className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs"
          >
            '18 Drought vs '20 Monsoon
          </button>
          <button
            onClick={() => setPreset(2024, 5, 2026, 10)}
            className="px-2.5 py-1 rounded-lg border border-amber-200 bg-amber-50 text-amber-900 shadow-2xs"
          >
            '24 El Niño vs '26 Current
          </button>
        </div>
      </div>

      {/* Control Strip */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-5 items-end">
          <div className="md:col-span-1">
            <IndexDropdown value={index} onChange={setIndex} />
          </div>
          <PeriodPicker label="Underlying Layer (Period A)" y={ay} m={am} setY={setAY} setM={setAM} />
          <PeriodPicker label="Overlying Layer (Period B)" y={by} m={bm} setY={setBY} setM={setBM} />
        </div>
      </div>

      {/* Main Curtain Wipe Slider Map */}
      <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-xs overflow-hidden">
        <div className="flex items-center justify-between px-2 pb-2 text-xs font-bold text-slate-700">
          <span className="text-amber-800">
            ◀ Period A: {MONTHS[am - 1]} {ay}
          </span>
          <span className="text-slate-400 text-[11px] font-normal">
            Drag the center dividing bar left and right to reveal layers
          </span>
          <span className="text-blue-800">
            Period B: {MONTHS[bm - 1]} {by} ▶
          </span>
        </div>
        <ComparisonSlider index={index} a={{ year: ay, month: am }} b={{ year: by, month: bm }} />
      </div>
    </div>
  );
}

function PeriodPicker({
  label, y, m, setY, setM,
}: { label: string; y: number; m: number;
     setY: (n: number) => void; setM: (n: number) => void }) {
  return (
    <div className="md:col-span-2">
      <div className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-1">{label}</div>
      <div className="flex gap-2">
        <select
          value={y}
          onChange={(e) => setY(Number(e.target.value))}
          className="flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
        >
          {YEARS.map((yy) => <option key={yy} value={yy}>{yy}</option>)}
        </select>
        <select
          value={m}
          onChange={(e) => setM(Number(e.target.value))}
          className="flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
        >
          {MONTHS.map((mm, i) => <option key={mm} value={i + 1}>{mm}</option>)}
        </select>
      </div>
    </div>
  );
}
