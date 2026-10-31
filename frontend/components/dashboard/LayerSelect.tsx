"use client";

import { METRICS, METRIC_GROUPS, type MetricName } from "@/lib/metrics";

type Group = typeof METRIC_GROUPS[number];

/** `exclude` hides groups: the home dashboard leaves out "Long-term" (SPI-3/6/12), which only
 *  change monthly and are shown on the map and history pages instead. */
export function LayerSelect({ value, onChange, exclude = [] }: {
  value: MetricName; onChange: (m: MetricName) => void; exclude?: Group[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as MetricName)}
      aria-label="Map layer"
      className="cursor-pointer rounded border border-ink/20 bg-paper px-2 py-1.5 text-xs font-medium text-ink"
    >
      {METRIC_GROUPS.filter((g) => !exclude.includes(g)).map((g) => (
        <optgroup key={g} label={g === "Long-term" ? "Long-term accumulation (monthly)" : g}>
          {Object.values(METRICS).filter((m) => m.group === g).map((m) => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
