"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { type Locale, LOCALE_LABEL, t as translate } from "@/lib/i18n";

interface Ctx {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
}

const LocaleCtx = createContext<Ctx>({
  locale: "en",
  setLocale: () => undefined,
  t: (k) => k,
});

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");

  useEffect(() => {
    try {
      const stored = localStorage.getItem("latur:locale");
      if (stored === "en" || stored === "hi" || stored === "mr") setLocale(stored);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    try { localStorage.setItem("latur:locale", locale); } catch { /* ignore */ }
    document.documentElement.lang = locale;
  }, [locale]);

  return (
    <LocaleCtx.Provider value={{ locale, setLocale, t: (k) => translate(locale, k) }}>
      {children}
    </LocaleCtx.Provider>
  );
}

export const useLocale = () => useContext(LocaleCtx);

export function LocaleSwitcher() {
  const { locale, setLocale, t } = useLocale();
  return (
    <label className="flex items-center gap-1 text-xs text-slate-600 dark:text-slate-300">
      <span className="sr-only">{t("header.language")}</span>
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        aria-label={t("header.language")}
        className="rounded border border-slate-300 bg-transparent px-1 py-0.5 text-xs
                   dark:border-slate-700"
      >
        {(["en", "hi", "mr"] as const).map((l) => (
          <option key={l} value={l}>{LOCALE_LABEL[l]}</option>
        ))}
      </select>
    </label>
  );
}
