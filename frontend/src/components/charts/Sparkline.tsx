import { useId } from "react";

export interface SparklineProps {
  data: number[];
  /** Any CSS colour (var() works — this is inline SVG with style). */
  color?: string;
  width?: number;
  height?: number;
  /** Accessible summary; defaults to "Trend: first → last". */
  label?: string;
}

/** Tiny dependency-free trend line with a soft fill. */
export function Sparkline({ data, color = "var(--accent)", width = 96, height = 28, label }: SparklineProps) {
  const gid = useId().replace(/:/g, "");
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = 2;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (width - pad * 2);
    const y = pad + (1 - (v - min) / span) * (height - pad * 2);
    return [x, y] as const;
  });
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${pts[pts.length - 1][0].toFixed(1)},${height} L${pts[0][0].toFixed(1)},${height} Z`;
  const last = pts[pts.length - 1];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label ?? `Trend: ${data[0]} → ${data[data.length - 1]}`}>
      <defs>
        <linearGradient id={`spark-${gid}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" style={{ stopColor: color, stopOpacity: 0.28 }} />
          <stop offset="100%" style={{ stopColor: color, stopOpacity: 0 }} />
        </linearGradient>
      </defs>
      <path d={area} style={{ fill: `url(#spark-${gid})` }} />
      <path d={line} style={{ fill: "none", stroke: color, strokeWidth: 1.6, strokeLinejoin: "round", strokeLinecap: "round" }} />
      <circle cx={last[0]} cy={last[1]} r={2.4} style={{ fill: color }} />
    </svg>
  );
}
