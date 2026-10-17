import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        drought: {
          extreme:   "#7f0000",
          severe:    "#d7301f",
          moderate:  "#fdae61",
          normal:    "#f7f7f7",
          "wet-mod": "#a6d96a",
          "wet-high":"#1a9850",
          "wet-ext": "#00441b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
