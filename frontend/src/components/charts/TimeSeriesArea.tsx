import { useId } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartLegend, ChartTooltipBox } from "./ChartTooltip";
import { usePrefersReducedMotion, useChartTheme } from "./theme";

export interface SeriesDef {
  /** Property name in each data row. */
  key: string;
  label: string;
  /** Resolved colour; defaults to the categorical palette by index. */
  color?: string;
  dashed?: boolean;
  /** In the "area" variant, draw this series as an unstacked line overlay (e.g. alert counts over traffic). */
  kind?: "area" | "line";
}

export interface ReferenceMark {
  y?: number;
  x?: string | number;
  label?: string;
  color?: string;
}

export interface TimeSeriesAreaProps<T extends object> {
  data: T[];
  /** Property used for the x axis (category labels or timestamps). */
  xKey: keyof T & string;
  series: SeriesDef[];
  /** "area" (default) fills under each series; "line" draws lines only. */
  variant?: "area" | "line";
  stacked?: boolean;
  height?: number;
  yFormatter?: (v: number) => string;
  xFormatter?: (v: unknown) => string;
  yDomain?: [number | "auto" | "dataMin" | "dataMax", number | "auto" | "dataMin" | "dataMax"];
  curve?: "monotone" | "linear" | "step";
  /** Defaults to true for ≥ 2 series. */
  showLegend?: boolean;
  referenceLines?: ReferenceMark[];
  /** Accessible description of the chart. */
  ariaLabel: string;
  /** Disable transitions (streaming data). Reduced-motion users never get animation. */
  animate?: boolean;
  /** Point markers on line series (default true). */
  dots?: boolean;
}

/** Area / line chart for ordered series (time buckets, simulation phases…). One y-axis only. */
export function TimeSeriesArea<T extends object>({
  data,
  xKey,
  series,
  variant = "area",
  stacked,
  height = 260,
  yFormatter = (v) => String(v),
  xFormatter = (v) => String(v),
  yDomain,
  curve = "monotone",
  showLegend,
  referenceLines,
  ariaLabel,
  animate = true,
  dots = true,
}: TimeSeriesAreaProps<T>) {
  const theme = useChartTheme();
  const reduced = usePrefersReducedMotion() || !animate;
  const gid = useId().replace(/:/g, "");
  const colors = series.map((s, i) => s.color ?? theme.series[i % theme.series.length]);
  const legend = showLegend ?? series.length > 1;

  const axisProps = {
    stroke: theme.axis,
    tick: { fill: theme.muted, fontSize: 11 },
    tickLine: false,
    axisLine: { stroke: theme.grid },
  } as const;

  const tooltip = (
    <Tooltip
      cursor={{ stroke: theme.axis, strokeDasharray: "3 3" }}
      content={({ active, payload, label }) =>
        active && payload?.length ? (
          <ChartTooltipBox
            title={xFormatter(label)}
            rows={payload.map((p) => {
              const idx = series.findIndex((s) => s.key === p.dataKey);
              return {
                label: series[idx]?.label ?? String(p.name),
                value: yFormatter(Number(p.value)),
                color: colors[idx] ?? String(p.color),
              };
            })}
          />
        ) : null
      }
    />
  );

  const refs = (referenceLines ?? []).map((r, i) => (
    <ReferenceLine
      key={`ref-${i}`}
      y={r.y}
      x={r.x}
      stroke={r.color ?? theme.axis}
      strokeDasharray="4 4"
      label={r.label ? { value: r.label, fill: theme.muted, fontSize: 11, position: "insideTopRight" } : undefined}
    />
  ));

  const common = { data, margin: { top: 8, right: 8, bottom: 0, left: -12 } };

  return (
    <figure className="chart" role="img" aria-label={ariaLabel} style={{ margin: 0 }}>
      {legend && (
        <div style={{ marginBottom: 8 }}>
          <ChartLegend
            items={series.map((s, i) => ({
              label: s.label,
              color: colors[i],
              variant: s.dashed ? "dashed" : variant === "line" || s.kind === "line" ? "line" : "box",
            }))}
          />
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {variant === "line" ? (
          <LineChart {...common}>
            <CartesianGrid stroke={theme.grid} vertical={false} />
            <XAxis dataKey={xKey as string} {...axisProps} tickFormatter={xFormatter} minTickGap={16} />
            <YAxis {...axisProps} tickFormatter={yFormatter} domain={yDomain} width={52} />
            {tooltip}
            {refs}
            {series.map((s, i) => (
              <Line
                key={s.key}
                type={curve}
                dataKey={s.key}
                name={s.label}
                stroke={colors[i]}
                strokeWidth={2}
                strokeDasharray={s.dashed ? "6 4" : undefined}
                dot={dots ? { r: 3, strokeWidth: 0, fill: colors[i] } : false}
                activeDot={{ r: 5, stroke: theme.surface, strokeWidth: 2 }}
                isAnimationActive={!reduced}
              />
            ))}
          </LineChart>
        ) : (
          <ComposedChart {...common}>
            <defs>
              {series.map((s, i) => (
                <linearGradient key={s.key} id={`ts-${gid}-${i}`} x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor={colors[i]} stopOpacity={stacked ? 0.55 : 0.32} />
                  <stop offset="100%" stopColor={colors[i]} stopOpacity={stacked ? 0.25 : 0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid stroke={theme.grid} vertical={false} />
            <XAxis dataKey={xKey as string} {...axisProps} tickFormatter={xFormatter} minTickGap={16} />
            <YAxis {...axisProps} tickFormatter={yFormatter} domain={yDomain} width={52} allowDecimals={false} />
            {tooltip}
            {refs}
            {series.map((s, i) =>
              s.kind === "line" ? (
                <Line
                  key={s.key}
                  type={curve}
                  dataKey={s.key}
                  name={s.label}
                  stroke={colors[i]}
                  strokeWidth={2}
                  strokeDasharray={s.dashed ? "6 4" : undefined}
                  dot={false}
                  activeDot={{ r: 4, stroke: theme.surface, strokeWidth: 2 }}
                  isAnimationActive={!reduced}
                />
              ) : (
                <Area
                  key={s.key}
                  type={curve}
                  dataKey={s.key}
                  name={s.label}
                  stackId={stacked ? "stack" : undefined}
                  stroke={colors[i]}
                  strokeWidth={2}
                  strokeDasharray={s.dashed ? "6 4" : undefined}
                  fill={`url(#ts-${gid}-${i})`}
                  activeDot={{ r: 4, stroke: theme.surface, strokeWidth: 2 }}
                  isAnimationActive={!reduced}
                />
              )
            )}
          </ComposedChart>
        )}
      </ResponsiveContainer>
    </figure>
  );
}
