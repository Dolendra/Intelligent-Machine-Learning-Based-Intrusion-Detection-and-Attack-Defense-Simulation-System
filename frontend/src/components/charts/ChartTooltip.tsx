import type { ReactNode } from "react";

export interface TooltipRow {
  label: ReactNode;
  value: ReactNode;
  color?: string;
}

/** Shared tooltip body used by every chart (recharts `content` and the HTML charts). */
export function ChartTooltipBox({ title, rows }: { title?: ReactNode; rows: TooltipRow[] }) {
  return (
    <div className="chart-tooltip">
      {title != null ? <div className="chart-tooltip-title">{title}</div> : null}
      {rows.map((r, i) => (
        <div className="chart-tooltip-row" key={i}>
          {r.color ? <span className="legend-swatch" style={{ background: r.color }} aria-hidden /> : null}
          <span>{r.label}</span>
          <strong>{r.value}</strong>
        </div>
      ))}
    </div>
  );
}

export interface LegendItem {
  label: ReactNode;
  color: string;
  variant?: "box" | "line" | "dashed";
}

export function ChartLegend({ items }: { items: LegendItem[] }) {
  return (
    <div className="legend" role="list">
      {items.map((it, i) => (
        <span className="legend-item" role="listitem" key={i}>
          <span
            className={`legend-swatch${it.variant && it.variant !== "box" ? " line" : ""}`}
            style={
              it.variant === "dashed"
                ? { background: `repeating-linear-gradient(90deg, ${it.color} 0 4px, transparent 4px 7px)` }
                : { background: it.color }
            }
            aria-hidden
          />
          {it.label}
        </span>
      ))}
    </div>
  );
}
