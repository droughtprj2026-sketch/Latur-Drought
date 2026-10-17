"use client";

import { useLocale } from "@/components/i18n/LocaleProvider";

/**
 * The 10 Latur tehsils. Keep this list stable — the master CSV joins on
 * exactly these names.
 */
export const LATUR_TEHSILS = [
  "Latur", "Ausa", "Nilanga", "Renapur", "Chakur",
  "Ahmadpur", "Udgir", "Jalkot", "Deoni", "Shirur-Anantpal",
] as const;

export type TehsilName = typeof LATUR_TEHSILS[number] | "All";

interface Props {
  value: TehsilName;
  onChange: (next: TehsilName) => void;
}

export function TehsilSelector({ value, onChange }: Props) {
  const { t } = useLocale();
  return (
    <div>
      <label htmlFor="tehsil-select" className="block text-xs font-medium text-slate-500">
        {t("controls.tehsil")}
      </label>
      <select
        id="tehsil-select"
        value={value}
        onChange={(e) => onChange(e.target.value as TehsilName)}
        className="mt-1 w-full rounded border border-slate-300 bg-transparent
                   px-2 py-1.5 text-sm dark:border-slate-700"
      >
        <option value="All">— {t("controls.district")} —</option>
        {LATUR_TEHSILS.map((th) => (
          <option key={th} value={th}>{th}</option>
        ))}
      </select>
    </div>
  );
}
