import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { readStorage, writeStorage } from "../lib/storage";

export type ThemeName = "dark" | "light";
export const THEME_STORAGE_KEY = "aegis_theme";

interface ThemeContextValue {
  /** Theme currently applied to <html data-theme>. */
  theme: ThemeName;
  /** True when the user picked a theme explicitly (otherwise we follow the OS). */
  explicit: boolean;
  setTheme: (t: ThemeName) => void;
  toggleTheme: () => void;
  /** Forget the explicit choice and follow prefers-color-scheme again. */
  useSystemTheme: () => void;
}

function systemTheme(): ThemeName {
  try {
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: light)").matches) return "light";
  } catch {
    /* ignore */
  }
  return "dark";
}

function storedTheme(): ThemeName | null {
  const v = readStorage(THEME_STORAGE_KEY);
  return v === "dark" || v === "light" ? v : null;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [explicitTheme, setExplicitTheme] = useState<ThemeName | null>(() => storedTheme());
  const [osTheme, setOsTheme] = useState<ThemeName>(() => systemTheme());
  const theme = explicitTheme ?? osTheme;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    let mql: MediaQueryList | undefined;
    try {
      mql = window.matchMedia?.("(prefers-color-scheme: light)");
    } catch {
      mql = undefined;
    }
    if (!mql) return;
    const onChange = () => setOsTheme(mql!.matches ? "light" : "dark");
    mql.addEventListener?.("change", onChange);
    return () => mql!.removeEventListener?.("change", onChange);
  }, []);

  const setTheme = useCallback((t: ThemeName) => {
    setExplicitTheme(t);
    writeStorage(THEME_STORAGE_KEY, t);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      explicit: explicitTheme !== null,
      setTheme,
      toggleTheme: () => setTheme(theme === "dark" ? "light" : "dark"),
      useSystemTheme: () => {
        setExplicitTheme(null);
        writeStorage(THEME_STORAGE_KEY, null);
      },
    }),
    [theme, explicitTheme, setTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}

/** Optional variant for leaf components (charts) that should still render outside the provider. */
export function useThemeName(): ThemeName {
  return useContext(ThemeContext)?.theme ?? "dark";
}
