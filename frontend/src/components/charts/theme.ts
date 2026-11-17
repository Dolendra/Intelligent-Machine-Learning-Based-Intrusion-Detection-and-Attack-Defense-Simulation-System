import { useEffect, useMemo, useState } from "react";
import { useThemeName } from "../../app/theme";
import type { SeverityLevel } from "../../services/api";

/** Fallbacks (dark theme values) for environments without computed styles (tests, SSR). */
const FALLBACK: Record<string, string> = {
  "--chart-1": "#3987e5",
  "--chart-2": "#d95926",
  "--chart-3": "#199e70",
  "--chart-4": "#c98500",
  "--chart-5": "#d55181",
  "--chart-6": "#2fa52f",
  "--chart-7": "#9085e9",
  "--chart-8": "#e66767",
  "--chart-grid": "rgba(148,170,196,0.12)",
  "--chart-axis": "#6b7a8d",
  "--chart-pos": "#3987e5",
  "--chart-neg": "#e66767",
  "--seq-lo": "#142133",
  "--seq-hi": "#5598e7",
  "--text": "#e7edf4",
  "--text-2": "#b5c1cf",
  "--muted": "#7f8ea1",
  "--surface": "#0f1620",
  "--surface-2": "#141d29",
  "--surface-3": "#1a2533",
  "--border": "rgba(148,170,196,0.13)",
  "--accent": "#2dd4bf",
  "--ok": "#22c55e",
  "--warn": "#f5b041",
  "--danger": "#f2555a",
  "--info": "#60a5fa",
  "--sev-critical": "#f2555a",
  "--sev-high": "#f0844f",
  "--sev-medium": "#f2b33d",
  "--sev-low": "#38bdf8",
  "--sev-info": "#8d9bb0",
};

/** Read a CSS custom property from <html>, falling back to the dark-theme default. */
export function readCssVar(name: string): string {
  try {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (v) return v;
  } catch {
    /* ignore */
  }
  return FALLBACK[name] ?? "#888888";
}

export interface ChartTheme {
  /** Categorical palette in fixed order — index by entity, never by rank. */
  series: string[];
  grid: string;
  axis: string;
  text: string;
  text2: string;
  muted: string;
  surface: string;
  surface2: string;
  surface3: string;
  border: string;
  accent: string;
  positive: string;
  negative: string;
  seqLo: string;
  seqHi: string;
  ok: string;
  warn: string;
  danger: string;
  info: string;
  severity: Record<SeverityLevel, string>;
}

function read(): ChartTheme {
  return {
    series: [1, 2, 3, 4, 5, 6, 7, 8].map((i) => readCssVar(`--chart-${i}`)),
    grid: readCssVar("--chart-grid"),
    axis: readCssVar("--chart-axis"),
    text: readCssVar("--text"),
    text2: readCssVar("--text-2"),
    muted: readCssVar("--muted"),
    surface: readCssVar("--surface"),
    surface2: readCssVar("--surface-2"),
    surface3: readCssVar("--surface-3"),
    border: readCssVar("--border"),
    accent: readCssVar("--accent"),
    positive: readCssVar("--chart-pos"),
    negative: readCssVar("--chart-neg"),
    seqLo: readCssVar("--seq-lo"),
    seqHi: readCssVar("--seq-hi"),
    ok: readCssVar("--ok"),
    warn: readCssVar("--warn"),
    danger: readCssVar("--danger"),
    info: readCssVar("--info"),
    severity: {
      CRITICAL: readCssVar("--sev-critical"),
      HIGH: readCssVar("--sev-high"),
      MEDIUM: readCssVar("--sev-medium"),
      LOW: readCssVar("--sev-low"),
      INFO: readCssVar("--sev-info"),
    },
  };
}

/**
 * Resolved chart colours for the active theme. Re-reads CSS variables whenever the theme flips,
 * so SVG presentation attributes (which cannot use var()) re-theme too.
 */
export function useChartTheme(): ChartTheme {
  const theme = useThemeName();
  const [tick, setTick] = useState(0);
  // data-theme is applied in an effect; read again after it lands.
  useEffect(() => {
    const id = window.requestAnimationFrame?.(() => setTick((t) => t + 1));
    return () => {
      if (id) window.cancelAnimationFrame?.(id);
    };
  }, [theme]);
  return useMemo(() => read(), [theme, tick]); // eslint-disable-line react-hooks/exhaustive-deps
}

/** Stable colour for a category given the full, ordered category list (colour follows entity, not rank). */
export function colorFor(theme: ChartTheme, category: string, allCategories: string[]): string {
  const idx = allCategories.indexOf(category);
  return theme.series[(idx < 0 ? 0 : idx) % theme.series.length];
}

/** Respect the OS reduced-motion setting for chart animations. */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => {
    try {
      return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    } catch {
      return false;
    }
  });
  useEffect(() => {
    let mql: MediaQueryList | undefined;
    try {
      mql = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    } catch {
      return;
    }
    if (!mql) return;
    const fn = () => setReduced(mql!.matches);
    mql.addEventListener?.("change", fn);
    return () => mql!.removeEventListener?.("change", fn);
  }, []);
  return reduced;
}

/** Fixed category order for the attack families the models know about (keeps colours stable across pages). */
export const ATTACK_FAMILIES = ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot", "BENIGN"];

export function attackColor(theme: ChartTheme, attack: string): string {
  const idx = ATTACK_FAMILIES.indexOf(attack);
  if (idx >= 0) return theme.series[idx % theme.series.length];
  // Unknown families take the last slot rather than a generated hue.
  return theme.series[7];
}
