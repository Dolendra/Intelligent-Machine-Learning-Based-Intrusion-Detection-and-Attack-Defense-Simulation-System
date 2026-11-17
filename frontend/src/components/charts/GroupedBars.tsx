import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartLegend, ChartTooltipBox } from "./ChartTooltip";
import type { SeriesDef } from "./TimeSeriesArea";
import { usePrefersReducedMotion, useChartTheme } from "./theme";

export interface GroupedBarsProps<T extends object> {
  data: T[];
  /** Property holding the category label (x axis). */
  categoryKey: keyof T & string;
  series: SeriesDef[];
  height?: number;
  yFormatter?: (v: number) => string;
  categoryFormatter?: (v: unknown) => string;
  yDomain?: [number | "auto" | "dataMin" | "dataMax", number | "auto" | "dataMin" | "dataMax"];
  ariaLabel: string;
}

/** Vertical grouped bars — compare a few metrics across a few categories (e.g. models × recall/F1). */
export function GroupedBars<T extends object>({
  data,
  categoryKey,
  series,
  height = 260,
  yFormatter = (v) => String(v),
  categoryFormatter = (v) => String(v),
  yDomain,
  ariaLabel,
}: GroupedBarsProps<T>) {
  const theme = useChartTheme();
  const reduced = usePrefersReducedMotion();
  const colors = series.map((s, i) => s.color ?? theme.series[i % theme.series.length]);
  const axis = { stroke: theme.axis, tick: { fill: theme.muted, fontSize: 11 }, tickLine: false, axisLine: { stroke: theme.grid } } as const;
  return (
    <figure className="chart" role="img" aria-label={ariaLabel} style={{ margin: 0 }}>
      {series.length > 1 && (
        <div style={{ marginBottom: 8 }}>
          <ChartLegend items={series.map((s, i) => ({ label: s.label, color: colors[i] }))} />
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }} barGap={2} barCategoryGap="22%">
          <CartesianGrid stroke={theme.grid} vertical={false} />
          <XAxis dataKey={categoryKey as string} {...axis} tickFormatter={categoryFormatter} interval={0} />
          <YAxis {...axis} tickFormatter={yFormatter} domain={yDomain} width={52} />
          <Tooltip
            cursor={{ fill: theme.grid }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <ChartTooltipBox
                  title={categoryFormatter(label)}
                  rows={payload.map((p) => {
                    const idx = series.findIndex((s) => s.key === p.dataKey);
                    return { label: series[idx]?.label ?? String(p.name), value: yFormatter(Number(p.value)), color: colors[idx] };
                  })}
                />
              ) : null
            }
          />
          {series.map((s, i) => (
            <Bar key={s.key} dataKey={s.key} name={s.label} fill={colors[i]} radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={!reduced} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}
