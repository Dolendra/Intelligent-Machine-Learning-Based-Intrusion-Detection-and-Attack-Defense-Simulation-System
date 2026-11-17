import { ShieldCheck } from "lucide-react";
import type { TraceStep } from "../services/api";
import { formatDateTime, formatPct } from "../lib/format";
import { GroupedBars } from "./charts/GroupedBars";
import { useChartTheme } from "./charts/theme";

const STAGE_COLOR: Record<string, string> = {
  ml: "var(--chart-1)",
  risk: "var(--sev-high)",
  recommendation: "var(--accent)",
  incident: "var(--chart-7)",
  response: "var(--ok)",
};

/** Backend sends "WHY DID AEGIS DO THIS?" — render in sentence case. */
function sentenceCase(s: string) {
  const lower = s.toLowerCase().replace(/aegis/g, "Aegis");
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/** Vertical timeline of the pipeline steps behind a decision ("why did Aegis do this?"). */
export function DecisionTraceTimeline({ title, steps }: { title?: string; steps: TraceStep[] }) {
  if (!steps?.length) return null;
  return (
    <div className="stack-sm">
      {title ? (
        <h4 className="row" style={{ gap: 8 }}>
          <ShieldCheck size={16} aria-hidden style={{ color: "var(--accent)" }} />
          {sentenceCase(title)}
        </h4>
      ) : null}
      <ol className="timeline">
        {steps.map((s, i) => (
          <li key={`${s.stage}-${i}`} style={{ ["--dot" as string]: STAGE_COLOR[s.stage] ?? "var(--accent)" }}>
            <div className="timeline-title">{s.title}</div>
            <div className="timeline-detail">{s.detail}</div>
            {s.timestamp ? <div className="timeline-meta">{formatDateTime(s.timestamp)}</div> : null}
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

type Side = { peak_traffic: number; server_stress: number; risk: number; traffic_blocked?: number; threat?: string };

/** Without- vs with-defense comparison: grouped bars + compact table. */
export function CompareTable({ without, withDefense, recoveryS }: { without: Side; withDefense: Side; recoveryS?: number | null }) {
  const theme = useChartTheme();
  const data = [
    { metric: "Peak traffic", without: without.peak_traffic * 100, with: withDefense.peak_traffic * 100 },
    { metric: "Server stress", without: without.server_stress * 100, with: withDefense.server_stress * 100 },
    { metric: "Risk", without: Number(without.risk), with: Number(withDefense.risk) },
  ];
  return (
    <div className="stack">
      <GroupedBars
        ariaLabel="Peak traffic, server stress and risk without versus with defense"
        data={data}
        categoryKey="metric"
        height={220}
        yDomain={[0, 100]}
        yFormatter={(v) => String(Math.round(v))}
        series={[
          { key: "without", label: "Without defense", color: theme.negative },
          { key: "with", label: "With defense", color: theme.positive },
        ]}
      />
      <div className="table-wrap">
        <table className="table dense">
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col" className="num">
                Without
              </th>
              <th scope="col" className="num">
                With defense
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Peak traffic</td>
              <td className="num mono">{formatPct(without.peak_traffic)}</td>
              <td className="num mono">{formatPct(withDefense.peak_traffic)}</td>
            </tr>
            <tr>
              <td>Server stress</td>
              <td className="num mono">{formatPct(without.server_stress)}</td>
              <td className="num mono">{formatPct(withDefense.server_stress)}</td>
            </tr>
            <tr>
              <td>Risk</td>
              <td className="num mono">{Math.round(Number(without.risk))}</td>
              <td className="num mono">{Math.round(Number(withDefense.risk))}</td>
            </tr>
            <tr>
              <td>Threat</td>
              <td className="num">{without.threat ?? "—"}</td>
              <td className="num">{withDefense.threat ?? "—"}</td>
            </tr>
            <tr>
              <td>Recovery</td>
              <td className="num mono">—</td>
              <td className="num mono">{recoveryS != null ? `${recoveryS}s` : "—"}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="mono small muted">
        Risk reduction {reductionPct(Number(without.risk), Number(withDefense.risk))} · Traffic reduction{" "}
        {reductionPct(Number(without.peak_traffic), Number(withDefense.peak_traffic))}
      </p>
    </div>
  );
}
