import { useMemo, useState } from "react";
import { api, ExplainResult, PredictResult } from "../services/api";

const ATTACK_OPTIONS = ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot", "BENIGN"];

export function DetectionPage() {
  const [attackHint, setAttackHint] = useState("DDoS");
  const [label, setLabel] = useState<string | null>(null);
  const [features, setFeatures] = useState<Record<string, number> | null>(null);
  const [result, setResult] = useState<PredictResult | null>(null);
  const [explain, setExplain] = useState<ExplainResult | null>(null);
  const [lime, setLime] = useState<ExplainResult | null>(null);
  const [xaiTab, setXaiTab] = useState<"shap" | "lime">("shap");
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
    setExplain(null);
    setLime(null);
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
    try {
      const pred = await api.predict(features);
      setResult(pred);
      if (pred.is_attack) {
        const [ex, lx] = await Promise.all([
          api.explain(features, "shap"),
          api.explain(features, "lime"),
        ]);
        setExplain(ex);
        setLime(lx);
        setXaiTab("shap");
      } else {
        setExplain(null);
        setLime(null);
      }
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
          <p>Two-stage ML: binary detection → attack-family classification → risk → recommendation.</p>
        </div>
      </div>

      <div className="panel row" style={{ marginBottom: "1rem" }}>
        <label className="muted">Demo flow type</label>
        <select className="select" value={attackHint} onChange={(e) => setAttackHint(e.target.value)}>
          {ATTACK_OPTIONS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <button className="btn btn-secondary" onClick={loadDemo} disabled={busy}>
          {busy && !features ? "Loading…" : "Load sample flow"}
        </button>
        <button className="btn btn-primary" onClick={runDetect} disabled={busy || !features}>
          {busy && features ? "Detecting…" : "Detect & classify"}
        </button>
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

      <div className="split">
        <section className="panel stack">
          <h3 style={{ marginTop: 0 }}>Prediction</h3>
          {!result && <p className="muted">Load a CICIDS2017 sample flow, then run detection.</p>}
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
              {result.incident_id && (
                <p className="mono muted">Logged as {result.incident_id}</p>
              )}
              <div>
                <h4>Recommended defense</h4>
                <p style={{ marginTop: 0 }}>{result.recommendation.primary}</p>
                <ul>
                  {result.recommendation.actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  {result.recommendation.disclaimer ??
                    "Advisory only — the platform does not execute network changes."}
                </p>
              </div>
            </>
          )}
        </section>

        <section className="panel">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <h3 style={{ margin: 0 }}>Why?</h3>
            <div className="row">
              <button
                className={`btn ${xaiTab === "shap" ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "0.35rem 0.7rem" }}
                onClick={() => setXaiTab("shap")}
                disabled={!explain}
              >
                SHAP
              </button>
              <button
                className={`btn ${xaiTab === "lime" ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "0.35rem 0.7rem" }}
                onClick={() => setXaiTab("lime")}
                disabled={!lime}
              >
                LIME
              </button>
            </div>
          </div>
          {!activeExplain && <p className="muted">Explanations appear for attack predictions.</p>}
          {activeExplain && (
            <>
              <p className="muted mono" style={{ fontSize: "0.78rem" }}>
                Method: {(activeExplain.method ?? xaiTab).toUpperCase()}
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
    </div>
  );
}
