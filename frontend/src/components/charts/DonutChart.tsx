import { useState, type ReactNode } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ChartTooltipBox } from "./ChartTooltip";
import { usePrefersReducedMotion, useChartTheme } from "./theme";

export interface DonutDatum {
  name: string;
  value: number;
  /** Resolved colour; defaults to the categorical palette by index. */
  color?: string;
  /** Optional legend icon/badge before the name. */
  icon?: ReactNode;
}

export interface DonutChartProps {
  data: DonutDatum[];
  /** Big number in the hole (defaults to the total). */
  centerValue?: ReactNode;
  centerLabel?: string;
  valueFormatter?: (v: number) => string;
  /** Makes legend rows/slices toggle buttons. */
  onSelect?: (name: string) => void;
  /** Currently selected slice (others dim). */
  activeName?: string | null;
  ariaLabel: string;
  /** Hide the side legend. */
  hideLegend?: boolean;
}

/** Donut with a centred total and an interactive legend (name · value · share). */
export function DonutChart({
  data,
  centerValue,
  centerLabel = "Total",
  valueFormatter = (v) => v.toLocaleString(),
  onSelect,
  activeName,
  ariaLabel,
  hideLegend,
}: DonutChartProps) {
  const theme = useChartTheme();
  const reduced = usePrefersReducedMotion();
  const [hover, setHover] = useState<string | null>(null);
  const rows = data.filter((d) => d.value > 0);
  const total = rows.reduce((s, d) => s + d.value, 0);
  const color = (d: DonutDatum, i: number) => d.color ?? theme.series[i % theme.series.length];
  const focus = hover ?? activeName ?? null;

  return (
    <div className="donut">
      <figure className="donut-figure" role="img" aria-label={ariaLabel} style={{ margin: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={rows.length ? rows : [{ name: "none", value: 1 }]}
              dataKey="value"
              nameKey="name"
              innerRadius="68%"
              outerRadius="96%"
              paddingAngle={rows.length > 1 ? 2 : 0}
              cornerRadius={4}
              stroke={theme.surface}
              strokeWidth={2}
              startAngle={90}
              endAngle={-270}
              isAnimationActive={!reduced}
              onMouseEnter={(_, i) => rows[i] && setHover(rows[i].name)}
              onMouseLeave={() => setHover(null)}
              onClick={(_, i) => rows[i] && onSelect?.(rows[i].name)}
              style={{ cursor: onSelect ? "pointer" : undefined, outline: "none" }}
            >
              {rows.length ? (
                rows.map((d, i) => (
                  <Cell key={d.name} fill={color(d, i)} fillOpacity={focus && focus !== d.name ? 0.3 : 1} />
                ))
              ) : (
                <Cell fill={theme.surface3} />
              )}
            </Pie>
            {rows.length > 0 && (
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const p = payload[0];
                  const v = Number(p.value);
                  const idx = rows.findIndex((r) => r.name === p.name);
                  return (
                    <ChartTooltipBox
                      rows={[
                        {
                          label: String(p.name),
                          value: `${valueFormatter(v)} · ${total ? Math.round((v / total) * 100) : 0}%`,
                          color: idx >= 0 ? color(rows[idx], idx) : undefined,
                        },
                      ]}
                    />
                  );
                }}
              />
            )}
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <span className="donut-center-value">{centerValue ?? valueFormatter(total)}</span>
          <span className="donut-center-label">{centerLabel}</span>
        </div>
      </figure>

      {!hideLegend && (
        <ul className="donut-legend">
          {rows.length === 0 && <li className="muted small">No data yet</li>}
          {rows.map((d, i) => {
            const pct = total ? Math.round((d.value / total) * 100) : 0;
            const dim = activeName != null && activeName !== d.name;
            const content = (
              <>
                <span className="legend-swatch" style={{ background: color(d, i) }} aria-hidden />
                {d.icon}
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.name}</span>
                <span className="val">{valueFormatter(d.value)}</span>
                <span className="pct">{pct}%</span>
              </>
            );
            return (
              <li key={d.name}>
                {onSelect ? (
                  <button
                    type="button"
                    aria-pressed={activeName === d.name}
                    data-dim={dim || undefined}
                    onClick={() => onSelect(d.name)}
                    onMouseEnter={() => setHover(d.name)}
                    onMouseLeave={() => setHover(null)}
                  >
                    {content}
                  </button>
                ) : (
                  <div className="donut-legend-row" data-dim={dim || undefined}>
                    {content}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
