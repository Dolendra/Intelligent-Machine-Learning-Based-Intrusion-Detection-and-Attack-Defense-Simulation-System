import { useCallback, useEffect, useState } from "react";
import { Blocks, FlaskConical, Scale } from "lucide-react";
import { api, ApiError, type FrameworkModules, type R3Hypothesis, type R3Results } from "../../services/api";
import { Badge, type BadgeTone } from "../ui/Badge";
import { Callout, Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";

const HYPOTHESES: { id: string; title: string }[] = [
  { id: "A1", title: "LOAFO: does fusion beat the classifier alone, for every evidence model?" },
  { id: "A2", title: "Does the choice of evidence model matter inside Aegis-OSR?" },
  { id: "A4", title: "Validity: is the realised FPR within [0.8, 1.2] % at α = 1 %?" },
  { id: "A5", title: "Cross-network (2018, recal@2000): does Fisher fusion fall below the classifier?" },
  { id: "A6", title: "Design-free test (cross-dataset LOAFO): does the LOAFO gain transfer?" },
  { id: "A7", title: "Is max fusion non-inferior to the classifier after the shift?" },
];

function verdictTone(v: string | null | undefined): BadgeTone {
  if (!v) return "neutral";
  if (v === "supported" || v === "LOAFO gain transfers") return "ok";
  if (v === "rejected" || v === "reverses") return "danger";
  return "warn";
}

const fmt = (x: number | null | undefined, d = 3) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(d));
const fmtSigned = (x: number | null | undefined) => (x == null ? "—" : `${x >= 0 ? "+" : ""}${x.toFixed(3)}`);

function HypothesisTable({ id, h }: { id: string; h: R3Hypothesis }) {
  const rows = Object.entries(h.per_model);
  const isValidity = id === "A4";
  return (
    <table className="table table-dense" aria-label={`${id} per model`}>
      <thead>
        <tr>
          <th scope="col">{isValidity ? "Model | method" : "Evidence model"}</th>
          {isValidity ? (
            <>
              <th scope="col">FPR (smoothed)</th>
              <th scope="col">FPR (deterministic)</th>
              <th scope="col">In band</th>
            </>
          ) : (
            <>
              <th scope="col">Mean Δ</th>
              <th scope="col">95 % CI (folds/days → seeds)</th>
              <th scope="col">Holm p</th>
              <th scope="col">Seeds</th>
            </>
          )}
        </tr>
      </thead>
      <tbody>
        {rows.map(([m, r]) => (
          <tr key={m}>
            <td>{m}</td>
            {isValidity ? (
              <>
                <td>{r.realised_fpr_smoothed == null ? "—" : `${(r.realised_fpr_smoothed * 100).toFixed(2)} %`}</td>
                <td>{r.realised_fpr_deterministic == null ? "—" : `${(r.realised_fpr_deterministic * 100).toFixed(2)} %`}</td>
                <td>{r.in_band ? "yes" : "no"}</td>
              </>
            ) : (
              <>
                <td>{fmtSigned(r.mean)}</td>
                <td>
                  {r.hierarchical_bootstrap_95ci ? `[${fmtSigned(r.hierarchical_bootstrap_95ci[0])}, ${fmtSigned(r.hierarchical_bootstrap_95ci[1])}]` : "—"}
                </td>
                <td>{fmt(r.holm_p ?? r.noninferiority_p ?? r.t_p, 4)}</td>
                <td>{r.n_seeds ?? "—"}</td>
              </>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function R3Panel() {
  const [r3, setR3] = useState<R3Results | null>(null);
  const [notRun, setNotRun] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [fw, setFw] = useState<FrameworkModules | null>(null);

  const load = useCallback(() => {
    setError(null);
    api
      .researchR3()
      .then((d) => {
        setR3(d);
        setNotRun(false);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) setNotRun(true);
        else setError(e);
      });
    api.frameworkModules().then(setFw).catch(() => setFw(null));
  }, []);
  useEffect(load, [load]);

  return (
    <div className="stack">
      <Callout tone="info" icon={Scale} title="Pre-registered, matched false-alarm rate">
        Effects are the difference in detection rate at exactly 1 % benign FPR (Δ = Fisher fusion − classifier alone unless
        stated). Hypotheses and pass/fail rules were committed before any campaign run (docs/research/R3_AMENDMENT.md). Seeds
        are the unit of analysis; intervals resample folds or days, then seeds.
      </Callout>

      {error ? <ErrorState error={error} title="Could not load R3 results" onRetry={load} /> : null}
      {notRun ? (
        <EmptyState icon={FlaskConical} title="R3 analysis not generated yet" description="Run scripts/74_r3_analysis.py after the campaign." />
      ) : null}

      {r3 ? (
        <>
          <p className="muted">
            Analysis <code>{r3.analysis}</code> · models {(r3.meta.models ?? []).join(", ")} · seeds {(r3.meta.seeds ?? []).join(", ")}
          </p>
          {HYPOTHESES.map(({ id, title }) => {
            const h = r3.hypotheses[id];
            if (!h) return null;
            return (
              <Card
                key={id}
                title={`${id}: ${title}`}
                subtitle={h.description ?? undefined}
                actions={
                  <Badge tone={verdictTone(h.verdict)} dot>
                    {h.verdict ?? "not run"}
                  </Badge>
                }
              >
                <HypothesisTable id={id} h={h} />
              </Card>
            );
          })}
          <Card title="Evidence-reliability study (RS1, RS2)" subtitle="Can benign-only target data tell when a stream has gone stale?">
            <ul>
              {(["RS1", "RS2"] as const).map((k) => {
                const r = r3.reliability[k];
                return (
                  <li key={k}>
                    <strong>{k}</strong>: Spearman ρ = {fmt(r.rho)}{" "}
                    {r.day_cluster_ci95 ? `[${fmt(r.day_cluster_ci95[0])}, ${fmt(r.day_cluster_ci95[1])}]` : ""} (n = {r.n ?? "—"}){" "}
                    <Badge tone={verdictTone(r.verdict)} size="sm">
                      {r.verdict ?? "—"}
                    </Badge>
                  </li>
                );
              })}
            </ul>
            <p className="muted">
              Phase 7 gate (build a reliability-gated method only if RS1 and RS2 are both supported):{" "}
              <strong>{r3.reliability.phase7_gate_open ? "open" : "closed"}</strong>
            </p>
          </Card>
        </>
      ) : null}

      {fw ? (
        <Card title="Framework modules" icon={Blocks} subtitle="Interchangeable modules behind typed interfaces (framework/)">
          <table className="table table-dense" aria-label="framework modules">
            <thead>
              <tr>
                <th scope="col">Role</th>
                <th scope="col">Active</th>
                <th scope="col">Available</th>
              </tr>
            </thead>
            <tbody>
              {(Object.keys(fw.modules) as (keyof FrameworkModules["modules"])[]).map((kind) => (
                <tr key={kind}>
                  <td>{kind.replace("_", "-")}</td>
                  <td>{fw.active[kind] ?? "—"}</td>
                  <td>
                    {fw.modules[kind].map((m) => (
                      <span key={m.name} title={`${m.description} (${m.status})`} style={{ marginRight: 8 }}>
                        <code>{m.name}</code>
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  );
}
