import type { Metadata } from "next";
import "./globals.css";
import { LocaleProvider } from "@/components/i18n/LocaleProvider";
import { ClientHeader } from "@/components/header/ClientHeader";

export const metadata: Metadata = {
  title: "Near Real-Time Drought Monitoring System · Latur",
  description:
    "Near Real-Time Drought Monitoring System for Latur district, Marathwada. Developed by the Department of Geoinformatics, Shivaji University. Guide: Dr. Sachin S. Panhalkar. Village-level Sentinel-2, Sentinel-1, Landsat land-surface temperature and CHIRPS rainfall with a transparent composite index.",
};

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
          <ClientHeader />
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
