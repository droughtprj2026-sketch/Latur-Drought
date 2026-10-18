import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LocaleProvider, LocaleSwitcher } from "@/components/i18n/LocaleProvider";

export const metadata: Metadata = {
  title: "Latur Drought Intelligence Platform · 2016–2026",
  description:
    "Real-time and near-real-time drought monitoring for Latur district, Marathwada. High-resolution Sentinel-2 and CHIRPS spectral indices, village-level PostGIS choropleth, and composite drought classification.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased bg-slate-50 text-slate-900 min-h-screen flex flex-col">
        <LocaleProvider>
          {/* Main Top Navigation Header — Crisp White Theme with Gold Accents */}
          <header className="border-b border-slate-200 bg-white shadow-sm px-6 py-2.5 flex items-center justify-between z-30">
            <div className="flex items-center gap-3">
              <Link href="/" className="flex items-center gap-2 group">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-amber-600 to-amber-400 flex items-center justify-center font-black text-white text-base shadow-md shadow-amber-500/20 group-hover:scale-105 transition-transform">
                  LD
                </div>
                <div>
                  <div className="text-sm font-bold tracking-tight text-slate-900 group-hover:text-amber-600 transition-colors">
                    Latur Drought Intelligence
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono leading-none">
                    Marathwada · Sentinel-2 + CHIRPS (2016–2026)
                  </div>
                </div>
              </Link>
            </div>

            <nav className="flex items-center gap-5 text-xs font-semibold text-slate-600">
              <Link href="/" className="text-amber-700 font-bold hover:text-amber-800 transition-colors">
                Live Dashboard
              </Link>
              <Link href="/timeseries" className="hover:text-amber-700 transition-colors">
                Time Series
              </Link>
              <Link href="/compare" className="hover:text-amber-700 transition-colors">
                Comparative
              </Link>
              <Link href="/animation" className="hover:text-amber-700 transition-colors">
                Timelapse
              </Link>
              <Link href="/upload" className="hover:text-amber-700 transition-colors">
                Upload AOI
              </Link>
              <Link href="/sources" className="hover:text-amber-700 transition-colors">
                Sources
              </Link>
              <div className="border-l border-slate-200 pl-4 flex items-center">
                <LocaleSwitcher />
              </div>
            </nav>
          </header>

          {/* Full-bleed Content Area */}
          <main className="flex-1 w-full relative overflow-hidden">{children}</main>
        </LocaleProvider>
      </body>
    </html>
  );
}
