"use client";

import { useState } from "react";
import { SPIChart } from "@/components/charts/SPIChart";
import { CDIHeatmap } from "@/components/charts/CDIHeatmap";
import { IndexDropdown, type IndexName } from "@/components/ui/IndexDropdown";

export default function TimeseriesPage() {
  const [index, setIndex] = useState<IndexName>("spi3");
  const [overlay, setOverlay] = useState<IndexName | "">("ndvi");

  return (
    <div className="space-y-6">
      <div className="grid max-w-3xl grid-cols-1 gap-3 md:grid-cols-2">
        <IndexDropdown value={index} onChange={setIndex} />
        <div>
          <label className="block text-xs font-medium text-slate-500">
            Overlay (optional, dual axis)
          </label>
          <select
            value={overlay}
            onChange={(e) => setOverlay(e.target.value as IndexName | "")}
            className="mt-1 w-full rounded border border-slate-300 bg-transparent
                       px-2 py-1.5 font-mono text-sm dark:border-slate-700"
          >
            <option value="">— none —</option>
            {["spi1", "spi3", "spi6", "spi12", "ndvi", "evi", "vci", "vhi", "pci",
              "cdi", "cdi_class"].map((k) => (
              <option key={k} value={k}>{k.toUpperCase()}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="h-[400px] rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <SPIChart index={index} secondary={overlay || undefined} />
      </div>

      <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <h2 className="mb-2 text-sm font-medium">CDI year × month heatmap</h2>
        <CDIHeatmap />
      </div>
    </div>
  );
}
