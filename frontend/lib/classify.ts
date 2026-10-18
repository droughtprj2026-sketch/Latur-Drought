// Drought legend. Two scales, same colour ramp:
//   - SPI value scale (McKee 1993; negative = dry)
//   - Composite CDI scale (0..1 drought intensity; from config/composite.yaml)
// Must match scripts/common/classify.py.

export const D_CODES  = ["None", "D0", "D1", "D2", "D3", "D4"] as const;
export const D_LABELS = [
  "No drought / Normal",
  "D0 — Abnormally dry",
  "D1 — Moderate drought",
  "D2 — Severe drought",
  "D3 — Extreme drought",
  "D4 — Exceptional drought",
] as const;
export const D_COLORS = [
  "#22c55e", "#eab308", "#f59e0b", "#ea580c", "#dc2626", "#7f1d1d",
] as const;

export const SPI_CODES  = D_CODES;
export const SPI_LABELS = D_LABELS;
export const SPI_COLORS = D_COLORS;

// ---- SPI value scale (negative = drought) ------------------------------
export function codeForSPI(v: number | null | undefined): typeof D_CODES[number] | "ND" {
  if (v == null || Number.isNaN(v)) return "ND";
  if (v >= -0.5) return "None";
  if (v >= -0.8) return "D0";
  if (v >= -1.3) return "D1";
  if (v >= -1.6) return "D2";
  if (v >= -2.0) return "D3";
  return "D4";
}

// ---- Composite CDI scale (0..1 drought intensity) ----------------------
export function codeForCDI(v: number | null | undefined): typeof D_CODES[number] | "ND" {
  if (v == null || Number.isNaN(v)) return "ND";
  if (v < 0.20) return "None";
  if (v < 0.35) return "D0";
  if (v < 0.50) return "D1";
  if (v < 0.65) return "D2";
  if (v < 0.80) return "D3";
  return "D4";
}

export function colorForCode(code: string): string {
  const idx = D_CODES.indexOf(code as any);
  return idx >= 0 ? D_COLORS[idx] : "#e5e7eb";
}

// Generic classify for a map pixel: supports CDI, SPI, NDVI, EVI, VCI, VHI, Rain
export function classifyValue(v: number | null | undefined, layer = "spi"): string {
  if (v == null || Number.isNaN(v)) return "No data";
  const l = layer.toLowerCase();
  if (l.startsWith("cdi")) {
    const code = codeForCDI(v);
    const idx = D_CODES.indexOf(code as any);
    return idx >= 0 ? D_LABELS[idx] : "No data";
  }
  if (l.startsWith("spi")) {
    const code = codeForSPI(v);
    const idx = D_CODES.indexOf(code as any);
    return idx >= 0 ? D_LABELS[idx] : "No data";
  }
  if (l === "ndvi" || l === "evi") {
    if (v < 0.15) return "Extremely Dry / Desiccated";
    if (v < 0.25) return "Severe Vegetation Stress";
    if (v < 0.35) return "Moderate Vegetation Stress";
    if (v < 0.45) return "Normal / Moderate Canopy";
    return "Lush / Bumper Vegetation";
  }
  if (l === "vci" || l === "vhi") {
    if (v < 10) return "Extreme Condition Deficit";
    if (v < 20) return "Severe Condition Deficit";
    if (v < 35) return "Moderate Condition Deficit";
    if (v < 50) return "Mild / Abnormally Dry";
    return "Normal / Optimal Condition";
  }
  if (l === "rain" || l === "pci") {
    if (v < 20) return "Severe Rainfall Deficit";
    if (v < 50) return "Moderate Rainfall";
    return "Adequate / Heavy Rainfall";
  }
  const code = codeForSPI(v);
  const idx = D_CODES.indexOf(code as any);
  return idx >= 0 ? D_LABELS[idx] : "No data";
}

export function colorForValue(v: number | null | undefined, layer = "spi"): string {
  if (v == null || Number.isNaN(v)) return "#94a3b8"; // Slate-400 no-data grey
  const l = layer.toLowerCase();

  // 1. CDI Composite
  if (l.startsWith("cdi")) {
    const code = codeForCDI(v);
    return colorForCode(code);
  }

  // 2. SPI scales (McKee 1993 standard)
  if (l.startsWith("spi")) {
    if (v <= -2.0) return "#7f1d1d"; // Extremely Dry
    if (v <= -1.5) return "#dc2626"; // Severely Dry
    if (v <= -1.0) return "#ea580c"; // Moderately Dry
    if (v <= -0.5) return "#eab308"; // Abnormally Dry
    if (v < 1.0)  return "#cbd5e1"; // Near Normal
    if (v < 2.0)  return "#38bdf8"; // Moderately Wet
    return "#1d4ed8";               // Extremely Wet
  }

  // 3. Vegetation Canopy Greenness (NDVI, EVI)
  if (l === "ndvi" || l === "evi") {
    if (v < 0.15) return "#854d0e"; // Extremely dry / bare soil
    if (v < 0.25) return "#ca8a04"; // Stressed vegetation
    if (v < 0.35) return "#a3e635"; // Moderate greenness
    if (v < 0.45) return "#4ade80"; // Good vegetation canopy
    return "#15803d";               // Dense / Lush canopy
  }

  // 4. Condition Indices (VCI, VHI: 0–100 scale)
  if (l === "vci" || l === "vhi") {
    if (v < 10) return "#7f1d1d";   // Extreme drought
    if (v < 20) return "#dc2626";   // Severe drought
    if (v < 35) return "#ea580c";   // Moderate drought
    if (v < 50) return "#eab308";   // Abnormally dry
    return "#22c55e";               // Normal / Optimal
  }

  // 5. Rainfall Volume (mm)
  if (l === "rain" || l === "pci") {
    if (v < 20) return "#f59e0b";   // Low rainfall deficit
    if (v < 50) return "#38bdf8";   // Moderate rainfall
    return "#0284c7";               // Good / Heavy rainfall
  }

  const code = codeForSPI(v);
  return colorForCode(code);
}

// ---- Historical Marathwada drought years (markers in time-series) ------
export const HISTORICAL_DROUGHTS = [
  { year: 2012, label: "2012 drought" },
  { year: 2015, label: "2015–16 drought" },
  { year: 2016, label: "2015–16 drought" },
  { year: 2018, label: "2018–19 drought" },
  { year: 2019, label: "2018–19 drought" },
];
