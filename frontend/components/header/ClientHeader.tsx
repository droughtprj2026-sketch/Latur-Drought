"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, LocaleSwitcher } from "@/components/i18n/LocaleProvider";

/** Route definitions — i18n key per label. */
const NAV = [
  { href: "/",          key: "nav.dashboard" },
  { href: "/map",       key: "nav.map" },
  { href: "/timeseries", key: "nav.timeseries" },
  { href: "/compare",   key: "nav.compare" },
  { href: "/animation", key: "nav.animation" },
  { href: "/upload",    key: "nav.upload" },
  { href: "/sources",   key: "nav.sources" },
  { href: "/about",     key: "nav.about" },
] as const;

/**
 * Responsive header with translated nav labels.
 * Desktop: inline horizontal nav.
 * Mobile: hamburger menu with a slide-down panel.
 */
export function ClientHeader() {
  const { t } = useLocale();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on route change.
  useEffect(() => { setOpen(false); }, [pathname]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <header ref={menuRef} className="relative z-[1200] flex h-14 flex-none items-center gap-3 border-b-2 border-ink bg-paper px-4 md:gap-6">
      {/* Hamburger — mobile only */}
      <button
        type="button"
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-ink/20 text-ink/70 transition-colors hover:bg-ink/5 hover:text-ink active:bg-ink/10 md:hidden"
      >
        {open ? (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="4" y1="4" x2="14" y2="14" />
            <line x1="14" y1="4" x2="4" y2="14" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="5" x2="15" y2="5" />
            <line x1="3" y1="9" x2="15" y2="9" />
            <line x1="3" y1="13" x2="15" y2="13" />
          </svg>
        )}
      </button>

      {/* Title */}
      <Link href="/" className="flex flex-none items-baseline gap-2" onClick={() => setOpen(false)}>
        <span className="font-display text-base font-semibold leading-none tracking-tight md:text-[19px]">
          {t("app.title")}
        </span>
        <span className="hidden font-mono text-[10px] uppercase leading-none tracking-[0.18em] text-ink/60 2xl:inline">
          {t("app.subtitle")}
        </span>
      </Link>

      {/* Desktop nav */}
      <nav aria-label="Primary" className="hidden min-w-0 flex-1 items-center gap-1 overflow-x-auto whitespace-nowrap text-[13px] md:flex">
        {NAV.map((n) => {
          const active = pathname === n.href;
          return (
            <Link key={n.href} href={n.href}
              className={`rounded px-2.5 py-1.5 transition-colors ${
                active
                  ? "bg-amber-100 text-amber-900 font-medium"
                  : "text-ink/75 hover:bg-ink/5 hover:text-ink"
              }`}>
              {t(n.key)}
            </Link>
          );
        })}
      </nav>

      <div className="ml-auto flex-none"><LocaleSwitcher /></div>

      {/* Mobile slide-down menu */}
      {open && (
        <>
          <div className="fixed inset-0 top-14 z-[1100] bg-black/20 backdrop-blur-[2px] md:hidden" aria-hidden onClick={() => setOpen(false)} />
          <nav
            aria-label="Mobile navigation"
            className="absolute left-0 right-0 top-full z-[1150] border-b-2 border-ink bg-paper shadow-lg md:hidden"
          >
            <div className="flex flex-col px-3 py-2">
              {NAV.map((n) => {
                const active = pathname === n.href;
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    onClick={() => setOpen(false)}
                    className={`rounded-lg px-3 py-2.5 text-[15px] font-medium transition-colors ${
                      active
                        ? "bg-amber-100 text-amber-900"
                        : "text-ink/75 hover:bg-ink/5 hover:text-ink active:bg-ink/10"
                    }`}
                  >
                    {t(n.key)}
                  </Link>
                );
              })}
            </div>
          </nav>
        </>
      )}
    </header>
  );
}
