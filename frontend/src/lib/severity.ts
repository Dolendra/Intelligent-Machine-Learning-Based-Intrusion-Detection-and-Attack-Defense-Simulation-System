import type { SeverityLevel } from "../services/api";

export const SEVERITY_ORDER: SeverityLevel[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

/** Backend mixes "HIGH" and "High" — normalise to the upper-case enum. Unknown → INFO. */
export function normalizeSeverity(value: unknown): SeverityLevel {
  const s = String(value ?? "").trim().toUpperCase();
  if (s === "CRITICAL" || s === "HIGH" || s === "MEDIUM" || s === "LOW") return s;
  if (s === "BENIGN" || s === "NONE" || s === "INFO") return "INFO";
  return "INFO";
}

/** Merge case-variant severity buckets: {HIGH: 14, High: 97} → {HIGH: 111}. */
export function mergeSeverityCounts(bySeverity: Record<string, number> | undefined | null): Record<SeverityLevel, number> {
  const out: Record<SeverityLevel, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
  for (const [k, v] of Object.entries(bySeverity ?? {})) out[normalizeSeverity(k)] += Number(v) || 0;
  return out;
}

/** CSS custom property holding the colour for a severity. */
export function severityVar(sev: unknown): string {
  return `var(--sev-${normalizeSeverity(sev).toLowerCase()})`;
}

/**
 * Some seeded incidents store risk on a 0–1 scale while the live pipeline uses 0–100.
 * Use for aggregates/charts only; tables show the stored value.
 */
export function normalizeRisk(value: unknown): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return n > 0 && n <= 1 ? n * 100 : Math.max(0, Math.min(100, n));
}

/** Map a 0–100 risk onto a severity band (for colouring gauges). */
export function riskToSeverity(risk: number): SeverityLevel {
  if (risk >= 85) return "CRITICAL";
  if (risk >= 65) return "HIGH";
  if (risk >= 40) return "MEDIUM";
  if (risk > 0) return "LOW";
  return "INFO";
}
