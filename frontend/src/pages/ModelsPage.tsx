import { useEffect, useState } from "react";
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

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Model Lab</h2>
          <p>Health, global XAI, drift, and experiment tracking from training artifacts.</p>
        </div>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      <div className="grid-stats">
        <div className="stat">
          <div className="label">Health</div>
          <div className="value" style={{ fontSize: "1.1rem" }}>
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

      <div className="panel" style={{ marginBottom: "1rem" }}>
        <p className="mono muted" style={{ margin: 0 }}>
          Binary: {String(meta.binary_model ?? cmp?.binary_best ?? "—")} · Multiclass:{" "}
          {String(meta.multiclass_model ?? cmp?.multiclass_best ?? "—")} · Calibration active:{" "}
          {String(info?.calibrated_binary_active ?? false)} · Dataset: {String(meta.dataset ?? "CICIDS2017")}
          {health?.drift_summary ? ` · Drift flags: ${JSON.stringify(health.drift_summary)}` : ""}
        </p>
      </div>

      <div className="split" style={{ marginBottom: "1rem" }}>
        <section className="panel">
          <ImportanceList title="Global binary importance" items={globalBin} />
        </section>
        <section className="panel">
          <ImportanceList title="Global multiclass importance" items={globalMulti} />
        </section>
      </div>

      <div className="panel" style={{ marginBottom: "1rem" }}>
        <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
          <h3 style={{ margin: 0 }}>Attack-specific drivers</h3>
          <select
            className="select"
            value={attackKey}
            onChange={(e) => setAttackKey(e.target.value)}
            disabled={!attackOptions.length}
          >
            {attackOptions.length === 0 && <option value="">Run script 24 / refresh SHAP</option>}
            {attackOptions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        {attackKey && byAttack[attackKey] ? (
          <ImportanceList title={attackKey} items={byAttack[attackKey].top_features ?? []} />
        ) : (
          <p className="muted">No attack-specific sample explanations cached yet.</p>
        )}
      </div>

      <div className="split" style={{ marginBottom: "1rem" }}>
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Drift</h3>
          {!drift?.available ? <p className="muted">{String(drift?.message ?? "No drift report.")}</p> : null}
          {drift?.available ? (
            <p className="mono muted">
              Status: {String(drift.status ?? "ok")} · Flagged PSI≥0.2:{" "}
              {JSON.stringify(
                (drift.feature_drift as Record<string, unknown> | undefined)?.["flagged_psi_ge_0.2"] ?? []
              )}
            </p>
          ) : null}
        </section>
        <section className="panel">
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
                  <td>{ex.present ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <div className="split">
        <section className="panel">
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
        <section className="panel">
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
            Selection criteria are project-justified (see training report). Re-run training to refresh scores.
          </p>
        </section>
      </div>
    </div>
  );
}
