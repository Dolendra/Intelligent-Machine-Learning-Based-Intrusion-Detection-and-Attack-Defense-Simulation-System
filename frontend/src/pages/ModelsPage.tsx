import { useEffect, useState } from "react";
import { api } from "../services/api";

export function ModelsPage() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [cmp, setCmp] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.models(), api.modelsComparison().catch(() => null)])
      .then(([m, c]) => {
        setInfo(m);
        setCmp(c);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const meta = (info?.metadata as Record<string, unknown> | undefined) ?? {};
  const binaryRows = (cmp?.binary_validation as Array<Record<string, unknown>> | undefined) ?? [];
  const multiRows = (cmp?.multiclass_validation as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Model Lab</h2>
          <p>Health, versions, and validation comparison from training artifacts (research view).</p>
        </div>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      <div className="grid-stats">
        <div className="stat">
          <div className="label">Status</div>
          <div className="value" style={{ fontSize: "1.1rem" }}>
            {info?.models_loaded ? "ONLINE" : "OFFLINE"}
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
        </p>
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
