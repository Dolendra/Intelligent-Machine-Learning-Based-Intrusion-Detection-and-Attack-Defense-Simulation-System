import type { ReactNode } from "react";

export interface BarListItem {
  /** Identity (key + value passed to onSelect). */
  label: string;
  /** Optional rendered label (e.g. humanised); defaults to `label`. */
  display?: ReactNode;
  value: number;
  /** CSS colour (tokens like "var(--chart-2)" work). */
  color?: string;
  /** Leading icon / badge. */
  icon?: ReactNode;
  /** Tooltip text. */
  hint?: string;
}

export interface BarListProps {
  items: BarListItem[];
  valueFormatter?: (v: number) => string;
  /** Scale maximum; defaults to the largest value. */
  max?: number;
  /** Makes rows toggle buttons (e.g. click-to-filter). */
  onSelect?: (label: string) => void;
  activeLabel?: string | null;
  /** Sort descending by value (default true). */
  sort?: boolean;
  limit?: number;
  ariaLabel?: string;
}

/** Ranked horizontal bars with the label inside the bar and the value right-aligned. */
export function BarList({
  items,
  valueFormatter = (v) => v.toLocaleString(),
  max,
  onSelect,
  activeLabel,
  sort = true,
  limit,
  ariaLabel,
}: BarListProps) {
  const rows = (sort ? [...items].sort((a, b) => b.value - a.value) : items).slice(0, limit ?? items.length);
  const top = max ?? Math.max(1e-9, ...rows.map((r) => Math.abs(r.value)));
  return (
    <ul className="barlist" aria-label={ariaLabel}>
      {rows.map((r, i) => {
        const pct = Math.max(0, Math.min(100, (Math.abs(r.value) / top) * 100));
        const color = r.color ?? `var(--chart-${(i % 8) + 1})`;
        const dim = activeLabel != null && activeLabel !== r.label;
        const inner = (
          <>
            <span className="barlist-fill" style={{ width: `max(${pct}%, 6px)`, ["--bar-color" as string]: color }} aria-hidden />
            <span className="barlist-label">
              {r.icon}
              {r.display ?? r.label}
            </span>
            <span className="barlist-value">{valueFormatter(r.value)}</span>
          </>
        );
        return (
          <li key={r.label} title={r.hint}>
            {onSelect ? (
              <button
                type="button"
                className="barlist-row"
                aria-pressed={activeLabel === r.label}
                data-dim={dim || undefined}
                onClick={() => onSelect(r.label)}
              >
                {inner}
              </button>
            ) : (
              <div className="barlist-row" data-dim={dim || undefined}>
                {inner}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
