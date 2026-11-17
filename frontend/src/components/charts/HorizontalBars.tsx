export interface SignedBarItem {
  label: string;
  value: number;
  /** Tooltip text (defaults to "label: value"). */
  hint?: string;
}

export interface HorizontalBarsProps {
  items: SignedBarItem[];
  valueFormatter?: (v: number) => string;
  /** Legend text for positive / negative directions. */
  positiveLabel?: string;
  negativeLabel?: string;
  positiveColor?: string;
  negativeColor?: string;
  /** Sort by |value| descending (default true). */
  sortByMagnitude?: boolean;
  maxItems?: number;
  /** CSS grid width for the label column, e.g. "minmax(0, 40%)". */
  labelWidth?: string;
  ariaLabel: string;
}

/**
 * Diverging bars around a zero axis — SHAP/LIME contributions, deltas, signed effects.
 * When all values share a sign the axis sits at the edge and bars use the full width.
 */
export function HorizontalBars({
  items,
  valueFormatter = (v) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(3)),
  positiveLabel = "Pushes toward prediction",
  negativeLabel = "Pushes away",
  positiveColor = "var(--chart-pos)",
  negativeColor = "var(--chart-neg)",
  sortByMagnitude = true,
  maxItems,
  labelWidth,
  ariaLabel,
}: HorizontalBarsProps) {
  const rows = (sortByMagnitude ? [...items].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)) : items).slice(
    0,
    maxItems ?? items.length
  );
  const hasNeg = rows.some((r) => r.value < 0);
  const hasPos = rows.some((r) => r.value > 0);
  const maxAbs = Math.max(1e-12, ...rows.map((r) => Math.abs(r.value)));
  // Zero position as a % of the track.
  const zero = hasNeg && hasPos ? 50 : hasNeg ? 100 : 0;
  const span = hasNeg && hasPos ? 50 : 100;
  const style = labelWidth ? { ["--hb-label-w" as string]: labelWidth } : undefined;

  return (
    <figure className="hbars" style={{ margin: 0, ...style }} aria-label={ariaLabel} role="group">
      <div className="legend" style={{ marginBottom: 4 }}>
        {hasPos && (
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: positiveColor }} aria-hidden />
            {positiveLabel}
          </span>
        )}
        {hasNeg && (
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: negativeColor }} aria-hidden />
            {negativeLabel}
          </span>
        )}
      </div>
      <ul className="list-plain hbars">
        {rows.map((r) => {
          const w = (Math.abs(r.value) / maxAbs) * span;
          const left = r.value >= 0 ? zero : zero - w;
          const sign = r.value > 0 ? "+" : r.value < 0 ? "−" : "";
          return (
            <li className="hbar" key={r.label} title={r.hint ?? `${r.label}: ${valueFormatter(r.value)}`}>
              <span className="hbar-label">{r.label}</span>
              <span className="hbar-track" aria-hidden>
                <span className="hbar-zero" style={{ left: `${zero}%` }} />
                <span
                  className="hbar-fill"
                  style={{
                    left: `${left}%`,
                    width: `max(${w}%, 2px)`,
                    background: r.value >= 0 ? positiveColor : negativeColor,
                  }}
                />
              </span>
              <span className="hbar-value">
                <span className="sr-only">{r.value >= 0 ? "positive " : "negative "}</span>
                {sign}
                {valueFormatter(Math.abs(r.value))}
              </span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}
