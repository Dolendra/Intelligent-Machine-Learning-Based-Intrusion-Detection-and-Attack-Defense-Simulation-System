/** Format helpers used by dashboard/simulation presentations. */
export function formatPct(value: unknown): string {
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return `${Math.round(n * 100)}%`;
}

export function formatRisk(value: unknown): string {
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return String(Math.round(n));
}
