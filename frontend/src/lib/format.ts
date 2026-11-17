/** Formatting helpers shared by every page. All are null/NaN safe and return "—" for missing values. */
const DASH = "—";

function num(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** 0.84 → "84%" */
export function formatPct(value: unknown, digits = 0): string {
  const n = num(value);
  if (n === null) return DASH;
  return `${(n * 100).toFixed(digits)}%`;
}

/** 91.4 → "91"; small fractional values keep one decimal (0.8 → "0.8") so 0–1 scaled risks stay honest. */
export function formatRisk(value: unknown): string {
  const n = num(value);
  if (n === null) return DASH;
  if (Math.abs(n) < 10 && !Number.isInteger(n)) return n.toFixed(1);
  return String(Math.round(n));
}

/** Locale-grouped number with fixed max fraction digits. */
export function formatNumber(value: unknown, maxDigits = 0): string {
  const n = num(value);
  if (n === null) return DASH;
  return n.toLocaleString(undefined, { maximumFractionDigits: maxDigits });
}

/** 0.99047 → "0.990" — model metrics. */
export function formatMetric(value: unknown, digits = 3): string {
  const n = num(value);
  if (n === null) return DASH;
  return n.toFixed(digits);
}

/** 1234567 → "1.2M" */
export function formatCompact(value: unknown): string {
  const n = num(value);
  if (n === null) return DASH;
  return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

/** Seconds → "4.1 s" / "12 min" / "3 h 5 min" */
export function formatDuration(seconds: unknown): string {
  const n = num(seconds);
  if (n === null) return DASH;
  if (n < 60) return `${n < 10 ? n.toFixed(1) : Math.round(n)} s`;
  const m = Math.floor(n / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h} h ${m % 60} min`;
  return `${Math.floor(h / 24)} d ${h % 24} h`;
}

/**
 * Parse backend timestamps. SQLite drops tz info, so naive ISO strings are UTC by contract
 * (backend writes datetime.now(timezone.utc)).
 */
export function parseTimestamp(value: unknown): Date | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value === "number") return new Date(value);
  const s = String(value).trim();
  const naive = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(s);
  const d = new Date(naive ? `${s.replace(" ", "T")}Z` : s);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "14 Sep 2026, 19:58" */
export function formatDateTime(value: unknown): string {
  const d = parseTimestamp(value);
  if (!d) return DASH;
  return d.toLocaleString(undefined, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** "19:58:41" */
export function formatTime(value: unknown): string {
  const d = parseTimestamp(value);
  if (!d) return DASH;
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** "15 Sep, 01:28" (year added when not the current year). */
export function formatShortDate(value: unknown): string {
  const d = parseTimestamp(value);
  if (!d) return DASH;
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    ...(sameYear ? {} : { year: "numeric" }),
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "3 min ago" / "in 2 h" / falls back to a short date after 30 days. */
export function formatRelative(value: unknown, now: number = Date.now()): string {
  const d = parseTimestamp(value);
  if (!d) return DASH;
  const diff = (d.getTime() - now) / 1000;
  const abs = Math.abs(diff);
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (abs < 45) return "just now";
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  if (abs < 86400 * 30) return rtf.format(Math.round(diff / 86400), "day");
  return formatShortDate(d);
}

const ACRONYMS: Record<string, string> = {
  ids: "IDS",
  pcap: "PCAP",
  csv: "CSV",
  api: "API",
  ip: "IP",
  shap: "SHAP",
  lime: "LIME",
  ddos: "DDoS",
  dos: "DoS",
  edr: "EDR",
  waf: "WAF",
  rbac: "RBAC",
  psi: "PSI",
  xgboost: "XGBoost",
};

/** "DefenseApplied" → "Defense applied", "pcap_extractor" → "PCAP extractor", "ids_alert" → "IDS alert" */
export function humanize(value: unknown): string {
  if (value === null || value === undefined || value === "") return DASH;
  const s = String(value)
    .replace(/[_-]+/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .trim()
    .toLowerCase()
    .replace(/[a-z]+/g, (w) => ACRONYMS[w] ?? w);
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Truncate a long string with an ellipsis. */
export function truncate(value: unknown, max = 60): string {
  const s = value == null ? "" : String(value);
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

/** Mean with 95% CI: "69.6% [65.1–72.3]", or "69.6% (n=1)" when the interval is degenerate. */
export function formatCI(ci: { mean: number; low: number | null; high: number | null; n: number | null } | null | undefined, digits = 1): string {
  if (!ci || ci.mean == null || !Number.isFinite(ci.mean)) return DASH;
  const f = (v: number) => (v * 100).toFixed(digits);
  if (ci.low != null && ci.high != null && ci.high > ci.low) return `${f(ci.mean)}% [${f(ci.low)}–${f(ci.high)}]`;
  return `${f(ci.mean)}%${ci.n ? ` (n=${ci.n})` : ""}`;
}
