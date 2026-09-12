import type { CSSProperties } from "react";

type Step = { stage: string; title: string; detail: string; timestamp?: string };

export function DecisionTraceTimeline({
  title,
  steps,
}: {
  title?: string;
  steps: Step[];
}) {
  if (!steps?.length) return null;
  return (
    <div>
      {title ? <h4 style={{ marginBottom: "0.5rem" }}>{title}</h4> : null}
      <ol className="decision-trace">
        {steps.map((s, i) => (
          <li key={`${s.stage}-${i}`}>
            <div className="decision-trace-dot" />
            <div>
              <strong>{s.title}</strong>
              <div className="muted">{s.detail}</div>
              {s.timestamp ? <div className="mono muted" style={{ fontSize: "0.75rem" }}>{s.timestamp}</div> : null}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function reductionPct(before: number, after: number): string {
  if (!Number.isFinite(before) || before === 0) return "—";
  const pct = ((before - after) / Math.abs(before)) * 100;
  return `${pct.toFixed(1)}%`;
}

export function CompareTable({
  without,
  withDefense,
  recoveryS,
}: {
  without: { peak_traffic: number; server_stress: number; risk: number; threat?: string };
  withDefense: {
    peak_traffic: number;
    server_stress: number;
    risk: number;
    traffic_blocked?: number;
    threat?: string;
  };
  recoveryS?: number | null;
}) {
  const rows: Array<{ label: string; a: string; b: string; style?: CSSProperties }> = [
    {
      label: "Peak traffic",
      a: `${Math.round(without.peak_traffic * 100)}%`,
      b: `${Math.round(withDefense.peak_traffic * 100)}%`,
    },
    {
      label: "Server stress",
      a: `${Math.round(without.server_stress * 100)}%`,
      b: `${Math.round(withDefense.server_stress * 100)}%`,
    },
    { label: "Risk", a: String(without.risk), b: String(withDefense.risk) },
    {
      label: "Recovery",
      a: "—",
      b: recoveryS != null ? `${recoveryS}s` : "—",
    },
  ];
  return (
    <div className="panel">
      <h4 style={{ marginTop: 0 }}>Before vs after defense</h4>
      <table className="table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Without defense</th>
            <th>With defense</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td>{r.label}</td>
              <td className="mono">{r.a}</td>
              <td className="mono">{r.b}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mono muted" style={{ marginBottom: 0 }}>
        Risk reduction: {reductionPct(Number(without.risk), Number(withDefense.risk))} · Traffic reduction:{" "}
        {reductionPct(Number(without.peak_traffic), Number(withDefense.peak_traffic))}
      </p>
    </div>
  );
}
