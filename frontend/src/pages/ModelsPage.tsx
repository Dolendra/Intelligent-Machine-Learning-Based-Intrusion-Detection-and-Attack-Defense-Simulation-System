import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

function ImportanceList({
  title,
  items,
}: {
  title: string;
  items: Array<{ feature: string; importance?: number; mean_abs_contribution?: number }>;
}) {
  if (!items.length) return <p className="muted">No rankings yet.</p>;
  const max = Math.max(
    ...items.map((i) => Number(i.importance ?? i.mean_abs_contribution ?? 0)),
    1e-9
  );
  return (
    <div>
      <h4 style={{ marginBottom: "0.5rem" }}>{title}</h4>
      {items.map((it) => {
        const v = Number(it.importance ?? it.mean_abs_contribution ?? 0);
        const pct = Math.min(100, (v / max) * 100);
        return (
          <div className="feature-bar" key={it.feature}>
            <span title={it.feature}>{it.feature}</span>
            <div className="track">
              <div className="fill" style={{ width: `${pct}%` }} />
            </div>
            <span className="mono muted">{v.toFixed(3)}</span>
          </div>
        );
      })}
    </div>
  );
}

export function ModelsPage() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [cmp, setCmp] = useState<Record<string, unknown> | null>(null);
  const [shap, setShap] = useState<Record<string, unknown> | null>(null);
  const [drift, setDrift] = useState<Record<string, unknown> | null>(null);
  const [experiments, setExperiments] = useState<Array<Record<string, unknown>>>([]);
  const [attackKey, setAttackKey] = useState<string>("");
  const [labTab, setLabTab] = useState<"overview" | "xai" | "ops">("overview");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.models(),
      api.modelsHealth().catch(() => null),
      api.modelsComparison().catch(() => null),
      api.globalShap().catch(() => null),
      api.drift().catch(() => null),
      api.experiments().catch(() => null),
    ])
      .then(([m, h, c, s, d, e]) => {
        setInfo(m);
        setHealth(h);
        setCmp(c);
        setShap(s);
        setDrift(d);
        setExperiments((e?.experiments as Array<Record<string, unknown>>) ?? []);
        const attacks = ((s?.attack_specific as Record<string, unknown> | undefined)?.attacks as string[]) ?? [];
        if (attacks.length) setAttackKey(attacks[0]);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const meta = (info?.metadata as Record<string, unknown> | undefined) ?? {};
  const binaryRows = (cmp?.binary_validation as Array<Record<string, unknown>> | undefined) ?? [];
  const multiRows = (cmp?.multiclass_validation as Array<Record<string, unknown>> | undefined) ?? [];
  const globalBin =
    ((shap?.global as Record<string, unknown> | undefined)?.binary_top as Array<{
      feature: string;
      importance: number;
    }>) ?? [];
  const globalMulti =
    ((shap?.global as Record<string, unknown> | undefined)?.multiclass_top as Array<{
      feature: string;
      importance: number;
    }>) ?? [];
  const byAttack =
    ((shap?.attack_specific as Record<string, unknown> | undefined)?.by_attack as Record<
      string,
      { top_features: Array<{ feature: string; mean_abs_contribution: number }> }
    >) ?? {};
  const attackOptions = Object.keys(byAttack);
  const online = Boolean(
    info?.models_loaded ||
      String(health?.status ?? "").toLowerCase() === "ok" ||
      String(health?.status ?? "").toUpperCase() === "ONLINE"
  );

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Model Lab</h2>
          <p>Inspect frozen artifacts — health, global SHAP, drift, and experiment index.</p>
        </div>
        <div className="row">
          <span className={`live-chip ${online ? "" : "off"}`}>
            <span className={`status-dot ${online ? "on" : ""}`} />
            {online ? "Artifacts online" : "Artifacts offline"}
          </span>
          <Link className="btn btn-secondary" to="/research">
            Research results
          </Link>
        </div>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      <div className="tab-row" style={{ marginBottom: "1rem" }} role="tablist" aria-label="Model lab sections">
        {(
          [
            ["overview", "Overview"],
            ["xai", "Global XAI"],
            ["ops", "Drift & experiments"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            className={`tab-btn ${labTab === id ? "active" : ""}`}
            aria-selected={labTab === id}
            onClick={() => setLabTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid-stats">
        <div className="stat">
          <div className="label">Health</div>
          <div className="value" style={{ fontSize: "1.1rem", color: online ? "var(--ok)" : "var(--amber)" }}>
            {String(health?.status ?? (info?.models_loaded ? "ONLINE" : "OFFLINE")).toUpperCase()}
          </div>
        </div>
        <div className="stat">
          <div className="label">App</div>
          <div className="value" style={{ fontSize: "1.1rem" }}>
            {String(info?.application_version ?? "—")}
          </div>
        </div>
        <div className="stat">
          <div className="label">Model</div>
          <div className="value" style={{ fontSize: "1.1rem" }}>
            {String(info?.model_version ?? "—")}
          </div>
        </div>
        <div className="stat">
          <div className="label">Threshold</div>
          <div className="value" style={{ fontSize: "1.1rem" }}>
            {String(info?.binary_threshold ?? "—")}
          </div>
        </div>
      </div>

      <div className="panel panel-interactive" style={{ marginBottom: "1rem" }}>
        <p className="mono muted" style={{ margin: 0 }}>
          Binary: {String(meta.binary_model ?? cmp?.binary_best ?? "—")} · Multiclass:{" "}
          {String(meta.multiclass_model ?? cmp?.multiclass_best ?? "—")} · Calibration active:{" "}
          {String(info?.calibrated_binary_active ?? false)} · Dataset: {String(meta.dataset ?? "CICIDS2017")}
          {health?.drift_summary ? ` · Drift flags: ${JSON.stringify(health.drift_summary)}` : ""}
        </p>
      </div>

      {labTab === "xai" && (
        <>
          <div className="split" style={{ marginBottom: "1rem" }}>
            <section className="panel panel-interactive">
              <ImportanceList title="Global binary importance" items={globalBin} />
            </section>
            <section className="panel panel-interactive">
              <ImportanceList title="Global multiclass importance" items={globalMulti} />
            </section>
          </div>

          <div className="panel panel-interactive" style={{ marginBottom: "1rem" }}>
            <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
              <h3 style={{ margin: 0 }}>Attack-specific drivers</h3>
              <div className="tab-row" role="tablist" aria-label="Attack family">
                {attackOptions.length === 0 && (
                  <span className="muted" style={{ padding: "0.45rem 0.85rem" }}>
                    Run script 24 / refresh SHAP
                  </span>
                )}
                {attackOptions.map((a) => (
                  <button
                    key={a}
                    type="button"
                    role="tab"
                    className={`tab-btn ${attackKey === a ? "active" : ""}`}
                    aria-selected={attackKey === a}
                    onClick={() => setAttackKey(a)}
                  >
                    {a}
                  </button>
                ))}
              </div>
            </div>
            {attackKey && byAttack[attackKey] ? (
              <ImportanceList title={attackKey} items={byAttack[attackKey].top_features ?? []} />
            ) : (
              <div className="empty-state">
                <strong>No attack-specific SHAP cache</strong>
                <p className="muted" style={{ margin: 0 }}>Generate global SHAP artifacts to populate this view.</p>
              </div>
            )}
          </div>
        </>
      )}

      {labTab === "ops" && (
        <div className="split" style={{ marginBottom: "1rem" }}>
          <section className="panel panel-interactive">
            <h3 style={{ marginTop: 0 }}>Drift</h3>
            {!drift?.available ? (
              <div className="empty-state">
                <strong>No drift report</strong>
                <p className="muted" style={{ margin: 0 }}>{String(drift?.message ?? "Artifact missing.")}</p>
              </div>
            ) : (
              <>
                <p className="mono muted">
                  Status: {String(drift.retrain_recommendation ? "review" : "monitor")} · Ref=
                  {String(drift.ref)} → {String(drift.current)} · Flagged PSI≥0.2:{" "}
                  {JSON.stringify(
                    (drift.feature_drift as Record<string, unknown> | undefined)?.["flagged_psi_ge_0.2"] ?? []
                  )}
                </p>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>PSI</th>
                      <th>|z| shift</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      ((drift.feature_drift as Record<string, unknown> | undefined)?.top_psi as Array<
                        Record<string, unknown>
                      >) ?? []
                    )
                      .slice(0, 8)
                      .map((row) => (
                        <tr key={String(row.feature)}>
                          <td>{String(row.feature)}</td>
                          <td className="mono">{Number(row.psi ?? 0).toFixed(3)}</td>
                          <td className="mono">{Math.abs(Number(row.mean_shift_z ?? 0)).toFixed(3)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  {String(drift.note ?? "Prototype drift monitoring only.")}
                </p>
              </>
            )}
          </section>
          <section className="panel panel-interactive">
            <h3 style={{ marginTop: 0 }}>Experiments</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Artifact</th>
                  <th>Present</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((ex) => (
                  <tr key={String(ex.experiment_id)}>
                    <td className="mono">{String(ex.experiment_id)}</td>
                    <td>{String(ex.name)}</td>
                    <td className="mono muted">{String(ex.artifact)}</td>
                    <td>
                      <span className={`badge ${ex.present ? "low" : "medium"}`}>
                        {ex.present ? "yes" : "no"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}

      {labTab === "overview" && (
        <>
          <section className="panel panel-interactive" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginTop: 0 }}>Experiment conclusions</h3>
            <div className="quick-launch" style={{ marginBottom: 0 }}>
              <div className="launch-tile" style={{ cursor: "default" }}>
                <span className="kicker">EXP-004</span>
                <strong>Threshold 0.85</strong>
                <span>Max F1 under recall ≥ 0.95 after freeze retrain.</span>
              </div>
              <div className="launch-tile" style={{ cursor: "default" }}>
                <span className="kicker">EXP-003</span>
                <strong>Calibration off</strong>
                <span>Isotonic worsened Brier and reduced recall.</span>
              </div>
              <div className="launch-tile" style={{ cursor: "default" }}>
                <span className="kicker">EXP-005</span>
                <strong>Risk stable</strong>
                <span>Severity labels held across weight configurations.</span>
              </div>
              <div className="launch-tile" style={{ cursor: "default" }}>
                <span className="kicker">EXP-008</span>
                <strong>Drift clear</strong>
                <span>No feature exceeded PSI ≥ 0.2 on IID test.</span>
              </div>
            </div>
          </section>

          <div className="split">
            <section className="panel panel-interactive">
              <h3 style={{ marginTop: 0 }}>Binary validation</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Recall</th>
                    <th>F1</th>
                    <th>PR-AUC</th>
                    <th>FPR</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {binaryRows.map((r) => (
                    <tr key={String(r.model)}>
                      <td>{String(r.model)}</td>
                      <td className="mono">{Number(r.recall ?? 0).toFixed(3)}</td>
                      <td className="mono">{Number(r.f1 ?? 0).toFixed(3)}</td>
                      <td className="mono">{r.pr_auc == null ? "—" : Number(r.pr_auc).toFixed(3)}</td>
                      <td className="mono">{Number(r.fpr ?? 0).toFixed(3)}</td>
                      <td className="mono">{r.selection_score == null ? "—" : Number(r.selection_score).toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="panel panel-interactive">
              <h3 style={{ marginTop: 0 }}>Multiclass validation</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Macro-F1</th>
                    <th>Weighted-F1</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {multiRows.map((r) => (
                    <tr key={String(r.model)}>
                      <td>{String(r.model)}</td>
                      <td className="mono">{Number(r.f1_macro ?? 0).toFixed(3)}</td>
                      <td className="mono">{Number(r.f1_weighted ?? 0).toFixed(3)}</td>
                      <td className="mono">{r.selection_score == null ? "—" : Number(r.selection_score).toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="muted" style={{ fontSize: "0.85rem" }}>
                Selection criteria are project-justified (see training report). Stage-2 is attack-only.
              </p>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
