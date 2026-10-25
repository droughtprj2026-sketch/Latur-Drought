import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LocaleProvider, LocaleSwitcher } from "@/components/i18n/LocaleProvider";

export const metadata: Metadata = {
  title: "Near Real-Time Drought Monitoring System · Latur",
  description:
    "Near Real-Time Drought Monitoring System for Latur district, Marathwada. Developed by the Department of Geoinformatics, Shivaji University. Guide: Dr. Sachin S. Panhalkar. Village-level Sentinel-2, Sentinel-1, Landsat land-surface temperature and CHIRPS rainfall with a transparent composite index.",
};

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/map", label: "Map" },
  { href: "/timeseries", label: "Village history" },
  { href: "/compare", label: "Compare" },
  { href: "/animation", label: "Timelapse" },
  { href: "/upload", label: "My area" },
  { href: "/sources", label: "Sources" },
  { href: "/about", label: "Method" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
        />
      </head>
      <body className="flex min-h-screen flex-col bg-paper font-sans text-ink antialiased">
        <LocaleProvider>
          <header className="relative z-[1200] flex h-14 flex-none items-center gap-6 border-b-2 border-ink bg-paper px-4">
            <Link href="/" className="flex flex-none items-baseline gap-2">
              <span className="font-display text-[19px] font-semibold leading-none tracking-tight">
                Near Real-Time Drought Monitoring
              </span>
              <span className="hidden font-mono text-[10px] uppercase leading-none tracking-[0.18em] text-ink/60 2xl:inline">
                Latur · Dept. of Geoinformatics, Shivaji University
              </span>
            </Link>
            <nav aria-label="Primary" className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto whitespace-nowrap text-[13px]">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href}
                  className="rounded px-2.5 py-1.5 text-ink/75 transition-colors hover:bg-ink/5 hover:text-ink">
                  {n.label}
                </Link>
              ))}
            </nav>
            <div className="flex-none"><LocaleSwitcher /></div>
          </header>
          <main className="relative w-full flex-1">{children}</main>
          <footer className="flex-none border-t border-ink/15 bg-paper px-4 py-1.5 font-mono text-[10px] text-ink/60">
            Near Real-Time Drought Monitoring System · Department of Geoinformatics, Shivaji University, Kolhapur ·
            Team: R. U. Kadam, A. B. Jagtap, P. S. Devkar, S. B. Gurav, T. U. Jadhav · Guide: Dr. S. S. Panhalkar ·
            Data: Copernicus Sentinel-1 and Sentinel-2, USGS Landsat 8/9, UCSB CHIRPS
          </footer>
        </LocaleProvider>
      </body>
    </html>
  );
}
