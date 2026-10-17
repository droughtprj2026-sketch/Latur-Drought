"use client";

export type IndexName =
  | "spi1" | "spi3" | "spi6" | "spi12"
  | "ndvi" | "evi"  | "ndmi" | "vci"
  | "vhi"  | "pci"
  | "cdi"           // composite multi-index drought score (continuous)
  | "cdi_class";    // composite drought class (categorical, D0..D4)

const LABELS: Record<IndexName, string> = {
  spi1:      "SPI-1  — Standardized Precipitation (1 mo)",
  spi3:      "SPI-3  — Standardized Precipitation (3 mo)",
  spi6:      "SPI-6  — Standardized Precipitation (6 mo)",
  spi12:     "SPI-12 — Standardized Precipitation (12 mo)",
  ndvi:      "NDVI   — Normalized Difference Vegetation",
  evi:       "EVI    — Enhanced Vegetation",
  ndmi:      "NDMI   — Normalized Difference Moisture",
  vci:       "VCI    — Vegetation Condition",
  vhi:       "VHI    — Vegetation Health",
  pci:       "PCI    — Precipitation Condition",
  cdi:       "CDI    — Composite Multi-Index Drought Score",
  cdi_class: "CDI    — Composite Drought Class (D0–D4)",
};

interface Props {
  value: IndexName;
  onChange: (next: IndexName) => void;
  available?: IndexName[];
}

export function IndexDropdown({ value, onChange, available }: Props) {
  const items = (available && available.length
    ? available
    : (Object.keys(LABELS) as IndexName[]));
  return (
    <div>
      <label htmlFor="index-select" className="block text-xs font-medium text-slate-500">
        Drought index
      </label>
      <select
        id="index-select"
        value={value}
        onChange={(e) => onChange(e.target.value as IndexName)}
        className="mt-1 w-full rounded border border-slate-300 bg-transparent
                   px-2 py-1.5 font-mono text-sm dark:border-slate-700"
      >
        {items.map((k) => (
          <option key={k} value={k}>{LABELS[k]}</option>
        ))}
      </select>
    </div>
  );
}
