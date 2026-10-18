"use client";

import React, { useEffect, useState, useRef } from "react";

interface Props {
  periods: string[];
  currentPeriod: string;
  onPeriodChange: (period: string) => void;
}

export function MonthlyTimelineScrubber({
  periods,
  currentPeriod,
  onPeriodChange,
}: Props) {
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const currentIndex = Math.max(0, periods.indexOf(currentPeriod));

  // Animation player loop (1.2 seconds per step)
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        onPeriodChange(periods[(currentIndex + 1) % periods.length]);
      }, 1200);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, currentIndex, periods, onPeriodChange]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = Number(e.target.value);
    if (periods[idx]) {
      onPeriodChange(periods[idx]);
    }
  };

  const stepPrev = () => {
    if (currentIndex > 0) {
      onPeriodChange(periods[currentIndex - 1]);
    }
  };

  const stepNext = () => {
    if (currentIndex < periods.length - 1) {
      onPeriodChange(periods[currentIndex + 1]);
    }
  };

  // Format YYYY-MM to human readable (e.g. "October 2026")
  const formatPeriod = (p: string) => {
    if (!p) return "—";
    const [y, m] = p.split("-");
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const mIdx = parseInt(m, 10) - 1;
    return `${monthNames[mIdx] || m} ${y}`;
  };

  return (
    <div className="bg-white/95 backdrop-blur-md border border-slate-200 rounded-2xl p-3 shadow-md text-slate-800">
      {/* Top Controls Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        {/* Play/Pause & Step Buttons */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`px-3 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all shadow-xs ${
              isPlaying
                ? "bg-amber-600 text-white ring-2 ring-amber-300"
                : "bg-amber-500 text-white hover:bg-amber-600"
            }`}
          >
            {isPlaying ? "⏸ Pause" : "▶ Play 10-Yr Evolution"}
          </button>

          <button
            onClick={stepPrev}
            disabled={currentIndex === 0}
            className="p-1 px-2.5 rounded-lg border border-slate-200 bg-slate-50 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-40 transition-colors"
            title="Previous Month"
          >
            ◀
          </button>

          <button
            onClick={stepNext}
            disabled={currentIndex === periods.length - 1}
            className="p-1 px-2.5 rounded-lg border border-slate-200 bg-slate-50 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-40 transition-colors"
            title="Next Month"
          >
            ▶
          </button>
        </div>

        {/* Current Active Period Badge */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Observation Period:
          </span>
          <span className="px-2.5 py-0.5 rounded-lg bg-amber-100 text-amber-900 border border-amber-300 font-mono font-extrabold text-xs shadow-2xs">
            {formatPeriod(currentPeriod)} <span className="text-[10px] text-amber-700 font-medium">({currentPeriod})</span>
          </span>
          <span className="text-[10px] text-slate-400 font-mono">
            [{currentIndex + 1} / {periods.length}]
          </span>
        </div>

        {/* Historical Benchmark Quick-Jump Buttons */}
        <div className="hidden lg:flex items-center gap-1 text-[10px] font-bold text-slate-600">
          <span className="text-slate-400 font-semibold mr-1">Benchmarks:</span>
          <button
            onClick={() => onPeriodChange("2016-01")}
            className="px-2 py-0.5 rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors"
          >
            '16 Baseline
          </button>
          <button
            onClick={() => onPeriodChange("2018-05")}
            className="px-2 py-0.5 rounded border border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100 transition-colors"
          >
            '18 Drought
          </button>
          <button
            onClick={() => onPeriodChange("2020-09")}
            className="px-2 py-0.5 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 transition-colors"
          >
            '20 Recovery
          </button>
          <button
            onClick={() => onPeriodChange("2024-05")}
            className="px-2 py-0.5 rounded border border-orange-200 bg-orange-50 text-orange-800 hover:bg-orange-100 transition-colors"
          >
            '24 El Niño
          </button>
          <button
            onClick={() => onPeriodChange("2026-10")}
            className="px-2 py-0.5 rounded border border-amber-300 bg-amber-100 text-amber-900 font-extrabold hover:bg-amber-200 transition-colors"
          >
            Latest ('26)
          </button>
        </div>
      </div>

      {/* Main Scrubber Slider */}
      <div className="relative flex flex-col gap-1">
        <input
          type="range"
          min={0}
          max={periods.length - 1}
          value={currentIndex}
          onChange={handleSliderChange}
          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600 focus:outline-none"
        />

        {/* Year Ticks */}
        <div className="flex justify-between text-[9px] font-mono font-semibold text-slate-400 px-1">
          <span>2016</span>
          <span>2017</span>
          <span>2018</span>
          <span>2019</span>
          <span>2020</span>
          <span>2021</span>
          <span>2022</span>
          <span>2023</span>
          <span>2024</span>
          <span>2025</span>
          <span className="text-amber-700 font-bold">2026</span>
        </div>
      </div>
    </div>
  );
}
