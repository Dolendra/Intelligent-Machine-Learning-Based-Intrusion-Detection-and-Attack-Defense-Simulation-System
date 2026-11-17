import { useMemo } from "react";

export type HeatmapNormalize = "none" | "row" | "column" | "all";

export interface HeatmapProps {
  /** Row labels (e.g. actual class). */
  rows: string[];
  /** Column labels (e.g. predicted class). */
  cols: string[];
  /** values[r][c] */
  values: number[][];
  /**
   * Colour/label normalisation: "row" shows per-row share (recall view for confusion matrices),
   * "column" per-column share (precision view), "all" share of total, "none" raw counts.
   */
  normalize?: HeatmapNormalize;
  rowAxisLabel?: string;
  colAxisLabel?: string;
  /** Format the displayed cell value (receives the normalised value when normalising). */
  valueFormatter?: (v: number, raw: number) => string;
  showValues?: boolean;
  /** Outline the diagonal (confusion matrices). */
  highlightDiagonal?: boolean;
  /** Minimum cell width in px (grid scrolls horizontally on narrow screens). */
  minCellWidth?: number;
  /**
   * Colour scale for raw values: "log" (default for normalize="none", good for counts) or
   * "linear" (good for rates already in [0, 1] — pass `domain` to fix the range).
   */
  scale?: "log" | "linear";
  /** Value range for the linear scale (default [0, max]). */
  domain?: [number, number];
  ariaLabel: string;
}

/**
 * Generic matrix heatmap (confusion matrices, correlation, per-class metrics).
 * Sequential single-hue scale from --seq-lo to --seq-hi; text flips to stay legible.
 */
export function Heatmap({
  rows,
  cols,
  values,
  normalize = "none",
  rowAxisLabel,
  colAxisLabel,
  valueFormatter,
  showValues = true,
  highlightDiagonal,
  minCellWidth = 56,
  scale,
  domain,
  ariaLabel,
}: HeatmapProps) {
  const norm = useMemo(() => {
    const total = values.flat().reduce((s, v) => s + v, 0) || 1;
    const rowSums = values.map((r) => r.reduce((s, v) => s + v, 0) || 1);
    const colSums = cols.map((_, c) => values.reduce((s, r) => s + (r[c] ?? 0), 0) || 1);
    return values.map((r, ri) =>
      r.map((v, ci) =>
        normalize === "row" ? v / rowSums[ri] : normalize === "column" ? v / colSums[ci] : normalize === "all" ? v / total : v
      )
    );
  }, [values, cols, normalize]);

  // For raw counts use a log-ish scale so one dominant cell doesn't wash out the rest.
  const max = Math.max(1e-12, ...norm.flat());
  const linear = scale === "linear";
  const [lo, hi] = domain ?? [0, max];
  const intensity = (v: number) => {
    if (linear) return Math.max(0, Math.min(1, (v - lo) / (hi - lo || 1)));
    if (normalize !== "none") return Math.max(0, Math.min(1, v / (normalize === "all" ? max : 1)));
    return Math.log1p(Math.max(0, v)) / Math.log1p(max);
  };
  const fmt =
    valueFormatter ??
    ((v: number, raw: number) => (normalize === "none" ? raw.toLocaleString() : `${(v * 100).toFixed(v < 0.1 && v > 0 ? 1 : 0)}%`));
  const scaleLabels =
    linear && domain ? [fmt(lo, lo), fmt(hi, hi)] : normalize === "none" ? ["fewer", linear ? "more" : "more (log scale)"] : ["0%", normalize === "all" ? "max" : "100%"];

  const gridTemplate = `minmax(72px, auto) repeat(${cols.length}, minmax(${minCellWidth}px, 1fr))`;

  return (
    <figure style={{ margin: 0, minWidth: 0 }} aria-label={ariaLabel} role="group">
      <div style={{ overflowX: "auto" }}>
        {colAxisLabel && (
          <div className="heatmap-axis" style={{ textAlign: "center", marginBottom: 6, paddingLeft: 72 }}>
            {colAxisLabel} →
          </div>
        )}
        <div className="heatmap" role="table" aria-label={ariaLabel} style={{ gridTemplateColumns: gridTemplate }}>
          <div role="row" style={{ display: "contents" }}>
            <div className="heatmap-axis" role="columnheader" style={{ alignSelf: "end", paddingBottom: 4 }}>
              {rowAxisLabel ? `${rowAxisLabel} ↓` : ""}
            </div>
            {cols.map((c) => (
              <div className="heatmap-head" role="columnheader" key={c} title={c}>
                {c}
              </div>
            ))}
          </div>
          {rows.map((r, ri) => (
            <div role="row" style={{ display: "contents" }} key={r}>
              <div className="heatmap-rowhead" role="rowheader" title={r}>
                {r}
              </div>
              {cols.map((c, ci) => {
                const raw = values[ri]?.[ci] ?? 0;
                const v = norm[ri]?.[ci] ?? 0;
                const t = intensity(v);
                const pct = Math.round(t * 100);
                return (
                  <div
                    key={c}
                    role="cell"
                    className="heatmap-cell"
                    data-diag={highlightDiagonal && ri === ci ? "true" : undefined}
                    title={`${rowAxisLabel ?? "Row"} ${r} · ${colAxisLabel ?? "Column"} ${c}: ${raw.toLocaleString()}${
                      normalize !== "none" ? ` (${(v * 100).toFixed(2)}%)` : ""
                    }`}
                    style={{
                      background: `color-mix(in oklab, var(--seq-hi) ${pct}%, var(--seq-lo))`,
                      color: t > 0.55 ? "#ffffff" : "var(--text)",
                    }}
                  >
                    {showValues ? fmt(v, raw) : <span className="sr-only">{fmt(v, raw)}</span>}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="row" style={{ marginTop: 10, gap: 8, fontSize: "0.72rem" }}>
        <span className="muted">{scaleLabels[0]}</span>
        <span className="heatmap-scale" style={{ flex: "0 1 160px" }} aria-hidden />
        <span className="muted">{scaleLabels[1]}</span>
      </div>
    </figure>
  );
}
