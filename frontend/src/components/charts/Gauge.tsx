import type { ReactNode } from "react";
import { riskToSeverity } from "../../lib/severity";

export interface GaugeBand {
  /** Upper bound (inclusive) of this band on the 0..max scale. */
  to: number;
  color: string;
}

export interface GaugeProps {
  value: number;
  max?: number;
  label?: string;
  /** Replaces the numeric readout. */
  display?: ReactNode;
  /** Arc colour; defaults to the severity colour for value/max×100. */
  color?: string;
  /** Faint background bands (e.g. severity thresholds). */
  bands?: GaugeBand[];
  /** Max rendered width in px. */
  size?: number;
  ariaLabel?: string;
}

const START = -210;
const SWEEP = 240;

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arc(cx: number, cy: number, r: number, from: number, to: number) {
  const a = polar(cx, cy, r, from);
  const b = polar(cx, cy, r, to);
  const large = to - from > 180 ? 1 : 0;
  return `M${a.x.toFixed(2)},${a.y.toFixed(2)} A${r},${r} 0 ${large} 1 ${b.x.toFixed(2)},${b.y.toFixed(2)}`;
}

export const RISK_BANDS: GaugeBand[] = [
  { to: 40, color: "var(--sev-low)" },
  { to: 65, color: "var(--sev-medium)" },
  { to: 85, color: "var(--sev-high)" },
  { to: 100, color: "var(--sev-critical)" },
];

/** 240° radial gauge (risk 0–100 by default) exposed as an ARIA meter. */
export function Gauge({ value, max = 100, label = "Risk", display, color, bands = RISK_BANDS, size = 240, ariaLabel }: GaugeProps) {
  const v = Number.isFinite(value) ? Math.max(0, Math.min(max, value)) : 0;
  const frac = v / max;
  const arcColor = color ?? `var(--sev-${riskToSeverity(frac * 100).toLowerCase()})`;
  const cx = 100;
  const cy = 100;
  const r = 80;
  const track = arc(cx, cy, r, START, START + SWEEP);
  const length = (Math.PI * r * SWEEP) / 180;

  return (
    <div
      className="gauge"
      style={{ maxWidth: size, width: "100%" }}
      role="meter"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={Math.round(v)}
      aria-label={ariaLabel ?? label}
    >
      <svg viewBox="0 0 200 170" aria-hidden>
        {bands.map((b, i) => {
          const from = i === 0 ? 0 : bands[i - 1].to;
          return (
            <path
              key={i}
              d={arc(cx, cy, r + 13, START + (from / max) * SWEEP + 0.8, START + (b.to / max) * SWEEP - 0.8)}
              style={{ fill: "none", stroke: b.color, strokeOpacity: 0.55, strokeWidth: 3, strokeLinecap: "round" }}
            />
          );
        })}
        <path d={track} style={{ fill: "none", stroke: "var(--surface-3)", strokeWidth: 14, strokeLinecap: "round" }} />
        <path
          className="gauge-arc"
          d={track}
          style={{
            fill: "none",
            stroke: arcColor,
            strokeWidth: 14,
            strokeLinecap: "round",
            strokeDasharray: length,
            strokeDashoffset: length * (1 - frac),
            filter: `drop-shadow(0 0 6px color-mix(in srgb, ${arcColor} 45%, transparent))`,
          }}
        />
      </svg>
      <div className="gauge-value">
        <div className="gauge-number">{display ?? Math.round(v)}</div>
        <div className="gauge-label">{label}</div>
      </div>
    </div>
  );
}
