"use client";

import { useEffect, useState } from "react";
import { useLocale } from "@/components/i18n/LocaleProvider";

interface Props {
  tehsil: string;             // "All" or a tehsil name
  value: string;              // "" = all villages
  onChange: (v: string) => void;
}

/**
 * Dependent dropdown. Reads /data/latur_villages.geojson once, groups
 * village names by their TEHSIL property, and shows the subset for the
 * selected tehsil. Falls back to "All villages" when the file is absent
 * or no tehsil is picked.
 */
export function VillageSelector({ tehsil, value, onChange }: Props) {
  const { t } = useLocale();
  const [byTehsil, setByTehsil] = useState<Record<string, string[]>>({});

  useEffect(() => {
    fetch("/data/latur_villages.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .then((fc: GeoJSON.FeatureCollection | null) => {
        if (!fc) return;
        const grouped: Record<string, string[]> = {};
        for (const f of fc.features ?? []) {
          const p = (f.properties ?? {}) as Record<string, string>;
          const th = p.TEHSIL ?? p.tehsil ?? "";
          const v  = p.VILLAGE ?? p.village ?? p.name ?? "";
          if (!v) continue;
          (grouped[th] = grouped[th] || []).push(v);
        }
        for (const k of Object.keys(grouped)) {
          grouped[k] = Array.from(new Set(grouped[k])).sort();
        }
        setByTehsil(grouped);
      })
      .catch(() => undefined);
  }, []);

  const villages = (tehsil && tehsil !== "All") ? (byTehsil[tehsil] ?? []) : [];
  const disabled = tehsil === "All" || villages.length === 0;

  return (
    <div>
      <label htmlFor="village-select" className="block text-xs font-medium text-slate-500">
        Village
      </label>
      <select
        id="village-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        title={disabled ? "Select a tehsil first (or upload latur_villages.geojson)" : ""}
        className="mt-1 w-full rounded border border-slate-300 bg-transparent px-2 py-1.5
                   text-sm disabled:opacity-40 dark:border-slate-700"
      >
        <option value="">— All villages —</option>
        {villages.map((v) => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>
    </div>
  );
}
