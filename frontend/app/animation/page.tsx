"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { IndexDropdown, type IndexName } from "@/components/ui/IndexDropdown";

const AnimationPlayer = dynamic(
  () => import("@/components/animation/AnimationPlayer").then((m) => m.AnimationPlayer),
  { ssr: false },
);

export default function AnimationPage() {
  const [index, setIndex] = useState<IndexName>("cdi");
  const [from, setFrom] = useState("2016-01");
  const [to, setTo] = useState("2026-10");

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-200 bg-white p-4
                      dark:border-slate-800 dark:bg-slate-900">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <IndexDropdown value={index} onChange={setIndex} />
          <label className="text-xs text-slate-500">
            From (YYYY-MM)
            <input value={from} onChange={(e) => setFrom(e.target.value)}
                   className="mt-1 w-full rounded border border-slate-300 bg-transparent
                              px-2 py-1 text-sm dark:border-slate-700" />
          </label>
          <label className="text-xs text-slate-500">
            To (YYYY-MM)
            <input value={to} onChange={(e) => setTo(e.target.value)}
                   className="mt-1 w-full rounded border border-slate-300 bg-transparent
                              px-2 py-1 text-sm dark:border-slate-700" />
          </label>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Each frame is read live from the API — no values are faked when a period is missing.
        </p>
      </div>
      <AnimationPlayer index={index} from={from} to={to} />
    </div>
  );
}
