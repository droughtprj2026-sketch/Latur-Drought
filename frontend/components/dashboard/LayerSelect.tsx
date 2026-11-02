"use client";

import { METRICS, METRIC_GROUPS, type MetricName } from "@/lib/metrics";
import { useLocale } from "@/components/i18n/LocaleProvider";
import { slug } from "@/lib/i18n";

type Group = typeof METRIC_GROUPS[number];

/** `exclude` hides groups: the home dashboard leaves out "Long-term" (SPI-3/6/12), which only
 *  change monthly and are shown on the map and history pages instead. */
export function LayerSelect({ value, onChange, exclude = [] }: {
  value: MetricName; onChange: (m: MetricName) => void; exclude?: Group[];
}) {
  const { t, tf } = useLocale();
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as MetricName)}
      aria-label={t("controls.layer")}
      className="cursor-pointer rounded border border-ink/20 bg-paper px-2 py-1.5 text-xs font-medium text-ink"
    >
      {METRIC_GROUPS.filter((g) => !exclude.includes(g)).map((g) => (
        <optgroup key={g} label={g === "Long-term" ? t("group.long_term_accum") : tf(`group.${slug(g)}`, g)}>
          {Object.values(METRICS).filter((m) => m.group === g).map((m) => (
            <option key={m.id} value={m.id}>{tf(`metric.${m.id}.label`, m.label)}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
