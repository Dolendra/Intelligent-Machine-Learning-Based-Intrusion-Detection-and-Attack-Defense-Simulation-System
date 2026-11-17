import { ChartLegend } from "./ChartTooltip";

export interface StackSegment {
  label: string;
  value: number;
  color: string;
}

export interface StackBarProps {
  segments: StackSegment[];
  /** Scale total; defaults to the sum (use 100 for a 0–100 score). */
  total?: number;
  valueFormatter?: (v: number) => string;
  ariaLabel: string;
}

/** Single 100% composition bar with a legend — e.g. how risk components add up to the score. */
export function StackBar({ segments, total, valueFormatter = (v) => v.toFixed(1), ariaLabel }: StackBarProps) {
  const rows = segments.filter((s) => s.value > 0);
  const sum = total ?? rows.reduce((s, x) => s + x.value, 0);
  return (
    <figure style={{ margin: 0 }} className="stack-sm" aria-label={ariaLabel} role="group">
      <div className="stackbar" aria-hidden>
        {rows.map((s) => (
          <span key={s.label} title={`${s.label}: ${valueFormatter(s.value)}`} style={{ width: `${(s.value / (sum || 1)) * 100}%`, background: s.color }} />
        ))}
      </div>
      <ChartLegend items={rows.map((s) => ({ label: `${s.label} · ${valueFormatter(s.value)}`, color: s.color }))} />
    </figure>
  );
}
