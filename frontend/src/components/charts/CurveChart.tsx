import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartLegend, ChartTooltipBox } from "./ChartTooltip";
import { usePrefersReducedMotion, useChartTheme } from "./theme";

export interface CurvePoint {
  x: number;
  y: number;
  /** e.g. the threshold that produced this point. */
  meta?: string | number;
}

export interface CurveSeries {
  label: string;
  points: CurvePoint[];
  color?: string;
  /** Shown in the legend, e.g. AUC. */
  summary?: string;
}

export interface CurveChartProps {
  series: CurveSeries[];
  xLabel?: string;
  yLabel?: string;
  /** Draw the y = x chance diagonal (ROC). */
  diagonal?: boolean;
  /** Horizontal baseline (PR prevalence). */
  baselineY?: number;
  domain?: { x?: [number, number]; y?: [number, number] };
  height?: number;
  digits?: number;
  /** Mark an operating point. */
  marker?: { x: number; y: number; label?: string };
  ariaLabel: string;
}

/** Generic x/y curve plot — ROC, precision-recall, calibration, threshold sweeps. */
export function CurveChart({
  series,
  xLabel,
  yLabel,
  diagonal,
  baselineY,
  domain,
  height = 280,
  digits = 3,
  marker,
  ariaLabel,
}: CurveChartProps) {
  const theme = useChartTheme();
  const reduced = usePrefersReducedMotion();
  const colors = series.map((s, i) => s.color ?? theme.series[i % theme.series.length]);
  const xDomain = domain?.x ?? [0, 1];
  const yDomain = domain?.y ?? [0, 1];
  const fmt = (v: number) => (Number.isFinite(v) ? v.toFixed(digits <= 2 ? digits : 2) : "—");
  const axis = { stroke: theme.axis, tick: { fill: theme.muted, fontSize: 11 }, tickLine: false, axisLine: { stroke: theme.grid } } as const;

  return (
    <figure className="chart" role="img" aria-label={ariaLabel} style={{ margin: 0 }}>
      {series.length > 1 || series.some((s) => s.summary) ? (
        <div style={{ marginBottom: 8 }}>
          <ChartLegend items={series.map((s, i) => ({ label: s.summary ? `${s.label} · ${s.summary}` : s.label, color: colors[i], variant: "line" }))} />
        </div>
      ) : null}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart margin={{ top: 8, right: 12, bottom: xLabel ? 18 : 0, left: yLabel ? 4 : -12 }}>
          <CartesianGrid stroke={theme.grid} />
          <XAxis
            type="number"
            dataKey="x"
            domain={xDomain}
            {...axis}
            tickFormatter={fmt}
            label={xLabel ? { value: xLabel, position: "insideBottom", offset: -10, fill: theme.muted, fontSize: 11 } : undefined}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={yDomain}
            {...axis}
            tickFormatter={fmt}
            width={48}
            label={yLabel ? { value: yLabel, angle: -90, position: "insideLeft", fill: theme.muted, fontSize: 11 } : undefined}
          />
          {diagonal && (
            <ReferenceLine
              segment={[
                { x: xDomain[0], y: yDomain[0] },
                { x: xDomain[1], y: yDomain[1] },
              ]}
              stroke={theme.axis}
              strokeDasharray="4 4"
            />
          )}
          {baselineY != null && <ReferenceLine y={baselineY} stroke={theme.axis} strokeDasharray="4 4" />}
          <Tooltip
            cursor={{ stroke: theme.axis, strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload as CurvePoint;
              return (
                <ChartTooltipBox
                  title={p.meta != null ? `Point ${p.meta}` : undefined}
                  rows={[
                    { label: xLabel ?? "x", value: p.x.toFixed(digits) },
                    { label: yLabel ?? "y", value: p.y.toFixed(digits) },
                  ]}
                />
              );
            }}
          />
          {series.map((s, i) => (
            <Line
              key={s.label}
              data={s.points}
              dataKey="y"
              name={s.label}
              type="linear"
              stroke={colors[i]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: theme.surface, strokeWidth: 2 }}
              isAnimationActive={!reduced}
            />
          ))}
          {marker && (
            <ReferenceLine
              segment={[
                { x: marker.x, y: yDomain[0] },
                { x: marker.x, y: marker.y },
              ]}
              stroke={theme.accent}
              strokeDasharray="2 3"
              label={marker.label ? { value: marker.label, fill: theme.text2, fontSize: 11, position: "top" } : undefined}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
}
