import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { DecisionTraceTimeline } from "../components/DecisionTrace";
import { api, BatchPredictResult, ExplainResult, PredictResult } from "../services/api";

const ATTACK_OPTIONS = ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot", "BENIGN"];

export function DetectionPage() {
  const navigate = useNavigate();
  const [attackHint, setAttackHint] = useState("DDoS");
  const [label, setLabel] = useState<string | null>(null);
  const [features, setFeatures] = useState<Record<string, number> | null>(null);
  const [result, setResult] = useState<PredictResult | null>(null);
  const [batch, setBatch] = useState<BatchPredictResult | null>(null);
  const [explain, setExplain] = useState<ExplainResult | null>(null);
  const [lime, setLime] = useState<ExplainResult | null>(null);
  const [xaiTab, setXaiTab] = useState<"shap" | "lime">("shap");
  const [counterfactual, setCounterfactual] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeExplain = xaiTab === "shap" ? explain : lime;
  const maxAbs = useMemo(() => {
    if (!activeExplain?.top_features?.length) return 1;
    return Math.max(...activeExplain.top_features.map((f) => Math.abs(f.contribution)), 1e-9);
  }, [activeExplain]);

  async function loadDemo() {
    setBusy(true);
    setError(null);
    setResult(null);
    setBatch(null);
    setExplain(null);
    setLime(null);
    setCounterfactual(null);
    try {
      const demo = await api.demoFlow(attackHint);
      setFeatures(demo.features);
      setLabel(demo.label);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runDetect() {
    if (!features) return;
    setBusy(true);
    setError(null);
    setBatch(null);
    try {
      const pred = await api.predict(features);
      setResult(pred);
      if (pred.is_attack) {
        const [ex, lx, cf] = await Promise.all([
          api.explain(features, "shap"),
          api.explain(features, "lime"),
          api.counterfactual(features).catch(() => null),
        ]);
        setExplain(ex);
        setLime(lx);
        setCounterfactual(cf);
        setXaiTab("shap");
      } else {
        setExplain(null);
        setLime(null);
        setCounterfactual(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runBatch() {
    setBusy(true);
    setError(null);
    setResult(null);
    setExplain(null);
    setLime(null);
    try {
      const demo = await api.demoFlows(attackHint === "BENIGN" ? "BENIGN" : attackHint, 12);
      if (!demo.items.length) throw new Error("No demo flows available — prepare processed data first.");
      const out = await api.predictBatch(
        demo.items.map((i) => i.features),
        false
      );
      setBatch(out);
      setLabel(`${demo.count} sample flows (${attackHint})`);
      setFeatures(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Detection Lab</h2>
          <p>Interactive two-stage pipeline: binary detection → attack-family classification → risk → recommendation.</p>
        </div>
      </div>

      <div className="panel panel-interactive row" style={{ marginBottom: "1rem" }}>
        <label className="muted">Demo flow type</label>
        <select className="select" value={attackHint} onChange={(e) => setAttackHint(e.target.value)}>
          {ATTACK_OPTIONS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <button className="btn btn-secondary" onClick={loadDemo} disabled={busy}>
          {busy && !features && !batch ? "Loading…" : "Load sample flow"}
        </button>
        <button className="btn btn-primary" onClick={runDetect} disabled={busy || !features}>
          {busy && features ? "Detecting…" : "Detect & classify"}
        </button>
        <button className="btn btn-amber" onClick={runBatch} disabled={busy}>
          Batch sample (12)
        </button>
        <label className="btn btn-secondary" style={{ cursor: busy ? "not-allowed" : "pointer" }}>
          Upload CSV
          <input
            type="file"
            accept=".csv,text/csv"
            hidden
            disabled={busy}
            onChange={async (e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (!file) return;
              setBusy(true);
              setError(null);
              setResult(null);
              setExplain(null);
              setLime(null);
              try {
                const out = await api.predictBatchCsv(file, false);
                setBatch(out);
                setLabel(`CSV upload (${out.total_flows} flows)`);
                setFeatures(null);
              } catch (err) {
                setError(err instanceof Error ? err.message : String(err));
              } finally {
                setBusy(false);
              }
            }}
          />
        </label>
        {busy && <span className="muted mono">Working…</span>}
        {label && (
          <span className="muted mono">
            Ground truth: <strong style={{ color: "var(--text)" }}>{label}</strong>
          </span>
        )}
      </div>

      {error && (
        <div className="panel" style={{ borderColor: "rgba(227,93,106,.4)", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {batch && (
        <section className="panel" style={{ marginBottom: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>Batch analytics</h3>
          <div className="grid-stats">
            <div className="stat">
              <div className="label">Flows</div>
              <div className="value">{batch.total_flows}</div>
            </div>
            <div className="stat">
              <div className="label">Attacks</div>
              <div className="value">{batch.attack_flows}</div>
            </div>
            <div className="stat">
              <div className="label">Attack %</div>
              <div className="value">{batch.attack_percentage}%</div>
            </div>
            <div className="stat">
              <div className="label">Highest risk</div>
              <div className="value" style={{ fontSize: "1rem" }}>
                {batch.highest_risk
                  ? `${batch.highest_risk.attack_type} (${batch.highest_risk.risk_score})`
                  : "—"}
              </div>
            </div>
          </div>
          <table className="table" style={{ marginTop: "1rem" }}>
            <thead>
              <tr>
                <th>#</th>
                <th>Verdict</th>
                <th>Confidence</th>
                <th>Risk</th>
                <th>Severity</th>
                <th>Confidence band</th>
              </tr>
            </thead>
            <tbody>
              {batch.results.map((r) => (
                <tr key={r.flow_index}>
                  <td className="mono">{r.flow_index}</td>
                  <td>{r.is_attack ? r.attack_type : "BENIGN"}</td>
                  <td className="mono">{(r.confidence * 100).toFixed(0)}%</td>
                  <td className="mono">{r.risk_score}</td>
                  <td>
                    <span className={`badge ${r.severity.toLowerCase()}`}>{r.severity}</span>
                  </td>
                  <td className="mono muted">{r.confidence_band_label ?? r.certainty ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <div className="split">
        <section className="panel stack">
          <h3 style={{ marginTop: 0 }}>Prediction</h3>
          {!result && !batch && <p className="muted">Load a CICIDS2017 sample flow, then run detection.</p>}
          {result && (
            <>
              <div className="grid-stats" style={{ marginBottom: 0 }}>
                <div className="stat">
                  <div className="label">Verdict</div>
                  <div className="value" style={{ fontSize: "1.25rem" }}>
                    {result.is_attack ? result.attack_type : "BENIGN"}
                  </div>
                </div>
                <div className="stat">
                  <div className="label">Confidence</div>
                  <div className="value">{(result.confidence * 100).toFixed(0)}%</div>
                </div>
                <div className="stat">
                  <div className="label">Risk</div>
                  <div className="value">{result.risk_score}</div>
                </div>
                <div className="stat">
                  <div className="label">Severity</div>
                  <div className="value" style={{ fontSize: "1.1rem" }}>
                    <span className={`badge ${result.severity.toLowerCase()}`}>{result.severity}</span>
                  </div>
                </div>
              </div>
              {(result.confidence_band_label || result.certainty) && (
                <div>
                  <p className="mono muted" style={{ marginBottom: "0.25rem" }}>
                    Confidence band: {result.confidence_band_label ?? result.certainty}
                    {(result.confidence_band ?? result.certainty) === "uncertain"
                      ? " — analyst review recommended"
                      : ""}
                  </p>
                  <p className="mono muted" style={{ fontSize: "0.78rem", marginTop: 0 }}>
                    Attack decision threshold: {result.threshold ?? "—"} · Band: [
                    {result.uncertainty_lower ?? "—"}, {result.uncertainty_upper ?? "—"}]
                  </p>
                  {result.threshold_note ? (
                    <p className="muted" style={{ fontSize: "0.8rem" }}>
                      {result.threshold_note}
                    </p>
                  ) : null}
                </div>
              )}
              {result.risk_why && (
                <div>
                  <h4 style={{ marginBottom: "0.35rem" }}>Why this risk?</h4>
                  <p style={{ marginTop: 0 }}>{result.risk_why}</p>
                  {result.risk_contributions && (
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Component</th>
                          <th>Contribution</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(result.risk_contributions).map(([k, v]) => (
                          <tr key={k}>
                            <td>{k}</td>
                            <td className="mono">{v}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
              {result.incident_id && (
                <p className="mono muted">
                  Logged as{" "}
                  <Link to={`/incidents/${encodeURIComponent(result.incident_id)}`}>{result.incident_id}</Link>
                </p>
              )}
              {result.is_attack && (
                <button
                  className="btn btn-amber"
                  onClick={async () => {
                    try {
                      const session = result.incident_id
                        ? await api.simulateIncident(result.incident_id)
                        : await api.startSim(result.attack_type, result.confidence, result.incident_id ?? undefined);
                      navigate(`/simulation?session=${encodeURIComponent(session.id)}`);
                    } catch (e) {
                      setError(e instanceof Error ? e.message : String(e));
                    }
                  }}
                >
                  Simulate this incident
                </button>
              )}
              <div>
                <h4>Recommended defense</h4>
                <p style={{ marginTop: 0 }}>{result.recommendation.primary}</p>
                <ul>
                  {result.recommendation.actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                {result.recommendation.rule_actions && result.recommendation.rule_actions.length > 0 && (
                  <p className="mono muted" style={{ fontSize: "0.8rem" }}>
                    Rules fired: {result.recommendation.rule_actions.join(", ")}
                  </p>
                )}
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  {result.recommendation.disclaimer ??
                    "Advisory only — the platform does not execute network changes."}
                </p>
              </div>
              {result.decision_trace ? (
                <DecisionTraceTimeline title={result.decision_trace.title} steps={result.decision_trace.steps} />
              ) : null}
            </>
          )}
        </section>

        <section className="panel">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <h3 style={{ margin: 0 }}>Why?</h3>
            <div className="tab-row" role="tablist" aria-label="Explanation method">
              <button
                type="button"
                role="tab"
                className={`tab-btn ${xaiTab === "shap" ? "active" : ""}`}
                onClick={() => setXaiTab("shap")}
                disabled={!explain}
                aria-selected={xaiTab === "shap"}
              >
                SHAP
              </button>
              <button
                type="button"
                role="tab"
                className={`tab-btn ${xaiTab === "lime" ? "active" : ""}`}
                onClick={() => setXaiTab("lime")}
                disabled={!lime}
                aria-selected={xaiTab === "lime"}
              >
                LIME
              </button>
            </div>
          </div>
          {!activeExplain && <p className="muted">Explanations appear for attack predictions.</p>}
          {activeExplain && (
            <>
              <p className="muted mono" style={{ fontSize: "0.78rem" }}>
                Method: {(activeExplain.actual_method ?? activeExplain.method ?? xaiTab).toUpperCase()}
                {activeExplain.fallback_used ? " (fallback — not pure SHAP)" : ""}
              </p>
              <p>{activeExplain.explanation}</p>
              {activeExplain.top_features.map((f) => (
                <div className="feature-bar" key={`${xaiTab}-${f.feature}`}>
                  <span title={f.feature}>{f.feature}</span>
                  <div className="track">
                    <div
                      className="fill"
                      style={{
                        width: `${(Math.abs(f.contribution) / maxAbs) * 100}%`,
                        background:
                          f.contribution >= 0
                            ? "linear-gradient(90deg, var(--cyan), #7ad7d3)"
                            : "linear-gradient(90deg, var(--danger), #f0a0a8)",
                      }}
                    />
                  </div>
                  <span className="mono muted">{f.contribution.toFixed(3)}</span>
                </div>
              ))}
            </>
          )}
        </section>
      </div>

      {counterfactual && (
        <section className="panel" style={{ marginTop: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>What-if counterfactual</h3>
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            {String(counterfactual.note ?? "Illustrative feature edits only.")}
          </p>
          <p className="mono muted">
            Baseline: {String((counterfactual.baseline as Record<string, unknown> | undefined)?.attack_type)} · p(attack)=
            {String((counterfactual.baseline as Record<string, unknown> | undefined)?.binary_proba_attack)}
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Edit</th>
                <th>New label</th>
                <th>p(attack)</th>
                <th>Flip?</th>
              </tr>
            </thead>
            <tbody>
              {((counterfactual.edits as Array<Record<string, unknown>>) ?? []).map((e) => (
                <tr key={String(e.feature)}>
                  <td>{String(e.feature)}</td>
                  <td className="mono">
                    {String(e.original_value)} → {String(e.counterfactual_value)}
                  </td>
                  <td>{String(e.new_attack_type)}</td>
                  <td className="mono">{String(e.new_binary_proba_attack)}</td>
                  <td>{e.flipped_to_benign ? "yes" : e.family_changed ? "family" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {counterfactual.combined != null ? (
            <p className="mono muted">
              Combined edit → {String((counterfactual.combined as Record<string, unknown>).new_attack_type)} · p=
              {String((counterfactual.combined as Record<string, unknown>).new_binary_proba_attack)}
              {(counterfactual.combined as Record<string, unknown>).flipped_to_benign ? " · flipped to BENIGN" : ""}
            </p>
          ) : null}
        </section>
      )}
    </div>
  );
}
