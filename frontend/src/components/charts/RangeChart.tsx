import type { ReactNode } from "react";

export interface RangeItem {
  label: string;
  mean: number;
  /** CI bounds; omitted/null renders the point only. */
  low?: number | null;
  high?: number | null;
  /** Optional group header (rows are rendered in the given order; a header appears when it changes). */
  group?: string;
  color?: string;
  /** Bold label (e.g. the proposed method). */
  emphasize?: boolean;
  /** Extra tooltip text. */
  hint?: string;
}

export interface RangeChartProps {
  items: RangeItem[];
  /** Axis range (default [0, 1]). */
  domain?: [number, number];
  valueFormatter?: (v: number) => string;
  /** Dashed vertical reference (e.g. a baseline mean). */
  reference?: { value: number; label: string };
  /** Display names for group keys. */
  groupLabels?: Record<string, ReactNode>;
  ariaLabel: string;
}

/** Dot-and-whisker chart for means with confidence intervals (one row per item). */
export function RangeChart({
  items,
  domain = [0, 1],
  valueFormatter = (v) => `${(v * 100).toFixed(1)}%`,
  reference,
  groupLabels,
  ariaLabel,
}: RangeChartProps) {
  const [lo, hi] = domain;
  const pos = (v: number) => `${Math.max(0, Math.min(100, ((v - lo) / (hi - lo || 1)) * 100))}%`;
  let lastGroup: string | undefined;
  return (
    <figure className="range-chart" style={{ margin: 0 }} role="group" aria-label={ariaLabel}>
      {reference && (
        <div className="legend" style={{ marginBottom: 4 }}>
          <span className="legend-item">
            <span className="legend-swatch line" style={{ background: "var(--chart-axis)" }} aria-hidden />
            {reference.label} ({valueFormatter(reference.value)})
          </span>
          <span className="legend-item muted">Whiskers = 95% CI across seeds</span>
        </div>
      )}
      {items.map((it) => {
        const header = it.group !== undefined && it.group !== lastGroup ? it.group : null;
        lastGroup = it.group;
        const color = it.color ?? "var(--chart-1)";
        const hasCi = it.low != null && it.high != null && it.high > it.low;
        const ci = hasCi ? ` [${valueFormatter(it.low!)}, ${valueFormatter(it.high!)}]` : "";
        return (
          <div key={`${it.group ?? ""}-${it.label}`}>
            {header && <div className="range-group">{groupLabels?.[header] ?? header}</div>}
            <div className="range-row" data-emph={it.emphasize || undefined} title={it.hint ?? `${it.label}: ${valueFormatter(it.mean)}${ci}`}>
              <span className="range-label">{it.label}</span>
              <span className="range-track" aria-hidden>
                {reference && <span className="range-ref" style={{ left: pos(reference.value) }} />}
                {hasCi && (
                  <span
                    className="range-whisker"
                    style={{ left: pos(it.low!), width: `calc(${pos(it.high!)} - ${pos(it.low!)})`, background: color }}
                  />
                )}
                <span className="range-dot" style={{ left: pos(it.mean), background: color }} />
              </span>
              <span className="range-value">
                {valueFormatter(it.mean)}
                <span className="sr-only">{ci}</span>
              </span>
            </div>
          </div>
        );
      })}
      <div className="range-row" aria-hidden style={{ minHeight: 0 }}>
        <span />
        <span className="pmeter-scale">
          <span>{valueFormatter(lo)}</span>
          <span>{valueFormatter((lo + hi) / 2)}</span>
          <span>{valueFormatter(hi)}</span>
        </span>
        <span />
      </div>
    </figure>
  );
}
