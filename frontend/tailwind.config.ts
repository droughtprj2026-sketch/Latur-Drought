import type { Config } from "tailwindcss";

// Palette: survey-sheet paper, deep field-green ink, and a terracotta accent
// taken from Marathwada's black-cotton-soil and baked-earth landscape.
// `slate` and `amber` are remapped so every existing utility class
// (text-slate-700, bg-amber-600 ...) picks up the new identity.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F1E7",
        ink: "#1D2B25",
        clay: "#B4532A",
        teal: { DEFAULT: "#0B6E6E" },
        // drought classes, shared with lib/classify.ts
        d0: "#F2E26B", d1: "#F6BC63", d2: "#E9822F", d3: "#C23B22", d4: "#6E1423",
        slate: {
          50: "#F8F5EE", 100: "#F0EBDF", 200: "#E1DAC8", 300: "#CBC3AC", 400: "#A39B84",
          500: "#7A7462", 600: "#5A5646", 700: "#403F34", 800: "#2A2E27", 900: "#1D2B25", 950: "#121A16",
        },
        amber: {
          50: "#FBF0E6", 100: "#F6DFC8", 200: "#EFC3A0", 300: "#E5A173", 400: "#D77F4B",
          500: "#C4642F", 600: "#A9501F", 700: "#8A3F17", 800: "#6B3114", 900: "#4F2410",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 rgba(29,43,37,.06), 0 6px 18px -8px rgba(29,43,37,.28)",
      },
    },
  },
  plugins: [],
};
export default config;
