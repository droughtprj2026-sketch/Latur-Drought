import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LocaleProvider, LocaleSwitcher } from "@/components/i18n/LocaleProvider";
import { StatusHeader } from "@/components/header/StatusHeader";

export const metadata: Metadata = {
  title: "Near-Real Time Drought Monitoring System for Latur District",
  description:
    "Near-real-time drought monitoring for Latur district, Marathwada — Sentinel-2 + CHIRPS, indices NDVI, SPI, VCI, VHI, EVI, PCI; a validated Random Forest classifier; D0–D4 drought scale.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <LocaleProvider>
          <header className="border-b border-slate-200 bg-slate-50/80 backdrop-blur
                             dark:border-slate-800 dark:bg-slate-900/80">
            <div className="mx-auto max-w-7xl px-4 py-3">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h1 className="text-xl font-semibold tracking-tight">
                    Near-Real Time Drought Monitoring System
                  </h1>
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    Latur District · Marathwada, Maharashtra
                  </p>
                </div>
                <nav className="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-300">
                  <Link href="/"            className="hover:text-blue-600">Dashboard</Link>
                  <Link href="/map"         className="hover:text-blue-600">Map</Link>
                  <Link href="/timeseries"  className="hover:text-blue-600">Time series</Link>
                  <Link href="/compare"     className="hover:text-blue-600">Compare</Link>
                  <Link href="/animation"   className="hover:text-blue-600">Animation</Link>
                  <Link href="/upload"      className="hover:text-blue-600">Upload AOI</Link>
                  <Link href="/sources"     className="hover:text-blue-600">Sources</Link>
                  <Link href="/about"       className="hover:text-blue-600">About</Link>
                  <LocaleSwitcher />
                </nav>
              </div>
              <div className="mt-3 border-t border-slate-200 pt-2 dark:border-slate-800">
                <StatusHeader />
              </div>
            </div>
          </header>
          <main className="mx-auto max-w-7xl p-4">{children}</main>
          <footer className="mx-auto max-w-7xl px-4 py-6 text-xs text-slate-500">
            © 2026 Latur Drought Monitoring Project · Data: Copernicus Sentinel-2 (ESA),
            CHIRPS (UCSB CHG) · See <Link href="/sources" className="underline">Sources</Link>.
          </footer>
        </LocaleProvider>
      </body>
    </html>
  );
}
