// Manual light/dark override on top of the OS preference.
// theme:  null  = follow the system (prefers-color-scheme)
//         'light' | 'dark' = user pinned it (persisted, wins over the OS)
// The <html data-theme> attribute is what index.css keys off; a no-flash
// script in index.html sets it before first paint, this provider keeps it in
// sync and exposes what's actually resolved on screen right now.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

const KEY = "vault-theme";
type Pinned = "light" | "dark" | null;

function stored(): Pinned {
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" ? v : null;
}

function apply(v: Pinned) {
  const el = document.documentElement;
  if (v) el.dataset.theme = v;
  else delete el.dataset.theme;
}

function systemDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
    : false;
}

interface ThemeCtx {
  theme: Pinned;
  resolved: "light" | "dark";
  toggleTheme: () => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Pinned>(() => stored());
  const [isSystemDark, setIsSystemDark] = useState(() => systemDark());

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = (e: MediaQueryListEvent) => setIsSystemDark(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  useEffect(() => {
    if (theme) localStorage.setItem(KEY, theme);
    else localStorage.removeItem(KEY);
    apply(theme);
  }, [theme]);

  const resolved = theme ?? (isSystemDark ? "dark" : "light");

  const value = useMemo<ThemeCtx>(
    () => ({
      theme,
      resolved,
      toggleTheme: () => setTheme((v) => (((v ?? (isSystemDark ? "dark" : "light")) === "dark") ? "light" : "dark")),
    }),
    [theme, resolved, isSystemDark],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
