// Drought legend. Two scales, same colour ramp:
//   - SPI value scale (McKee 1993; negative = dry)
//   - Composite CDI scale (0..1 drought intensity; from config/composite.yaml)
// Must match scripts/common/classify.py.

export const D_CODES  = ["None", "D0", "D1", "D2", "D3", "D4"] as const;
export const D_LABELS = [
  "Not in drought",
  "D0 — Abnormally dry",
  "D1 — Moderate drought",
  "D2 — Severe drought",
  "D3 — Extreme drought",
  "D4 — Exceptional drought",
] as const;
export const D_COLORS = [
  "#E2DED2", "#F2E26B", "#F6BC63", "#E9822F", "#C23B22", "#6E1423",
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

// Generic classify for a map pixel: SPI layers use codeForSPI;
// cdi/cdi_class/vci/vhi use codeForCDI-style; everything else uses SPI mapping.
export function classifyValue(v: number | null | undefined, layer = "spi"): string {
  const code = layer.startsWith("cdi") ? codeForCDI(v) : codeForSPI(v);
  if (code === "ND") return "No data";
  const idx = D_CODES.indexOf(code);
  return D_LABELS[idx];
}

export function colorForValue(v: number | null | undefined, layer = "spi"): string {
  const code = layer.startsWith("cdi") ? codeForCDI(v) : codeForSPI(v);
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
