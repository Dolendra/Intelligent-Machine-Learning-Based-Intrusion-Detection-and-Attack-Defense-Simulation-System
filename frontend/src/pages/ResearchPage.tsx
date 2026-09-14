import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

type Conclusion = { id: string; title: string; conclusion: string };

const STATIC_CONCLUSIONS: Conclusion[] = [
  {
    id: "EXP-004",
    title: "Threshold",
    conclusion:
      "0.85 selected because it maximized F1 under recall ≥ 0.95 after the freeze retrain (decision_tree binary).",
  },
  {
    id: "EXP-003",
    title: "Calibration",
    conclusion: "Disabled — isotonic improved ECE slightly but worsened Brier and reduced recall.",
  },
  {
    id: "EXP-005",
    title: "Risk sensitivity",
    conclusion: "Severity labels remained stable across A/B/C weight configurations.",
  },
  {
    id: "EXP-008",
    title: "Drift",
    conclusion:
      "No feature exceeded the selected PSI ≥ 0.2 flagging threshold between the training and IID test split.",
  },
];

export function ResearchPage() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [cmp, setCmp] = useState<Record<string, unknown> | null>(null);
  const [experiments, setExperiments] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"decisions" | "metrics" | "checklist">("decisions");

  useEffect(() => {
    Promise.all([api.models(), api.modelsComparison().catch(() => null), api.experiments().catch(() => null)])
      .then(([m, c, e]) => {
        setInfo(m);
        setCmp(c);
        setExperiments((e?.experiments as Array<Record<string, unknown>>) ?? []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const meta = (info?.metadata as Record<string, unknown> | undefined) ?? {};
  const binTest = (cmp?.binary_test as Record<string, unknown> | undefined) ?? {};
  const multiTest = (cmp?.multiclass_test as Record<string, unknown> | undefined) ?? {};
  const present = new Set(experiments.filter((x) => x.present).map((x) => String(x.experiment_id)));

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Research Results</h2>
          <p>Frozen experiment conclusions for the Aegis IDS v1.1 research/academic baseline.</p>
        </div>
        <Link className="btn btn-secondary" to="/models">
          Open Model Lab
        </Link>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      <div className="grid-stats">
        <div className="stat">
          <div className="label">Dataset</div>
          <div className="value" style={{ fontSize: "1.05rem" }}>
            {String(meta.dataset ?? "CICIDS2017")}
          </div>
        </div>
        <div className="stat">
          <div className="label">Threshold</div>
          <div className="value" style={{ fontSize: "1.05rem" }}>
            {String(info?.binary_threshold ?? meta.binary_threshold ?? "0.85")}
          </div>
        </div>
        <div className="stat">
          <div className="label">Confidence band</div>
          <div className="value" style={{ fontSize: "1.05rem" }}>
            [{String(meta.uncertainty_lower ?? "0.10")}, {String(meta.uncertainty_upper ?? "0.95")}]
          </div>
        </div>
        <div className="stat">
          <div className="label">Calibration</div>
          <div className="value" style={{ fontSize: "1.05rem" }}>
            {info?.calibrated_binary_active || meta.use_calibrated_binary ? "On" : "Off"}
          </div>
        </div>
      </div>

      <div className="tab-row" style={{ marginBottom: "1rem" }} role="tablist" aria-label="Research sections">
        {(
          [
            ["decisions", "Decisions"],
            ["metrics", "Test metrics"],
            ["checklist", "Experiment checklist"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            className={`tab-btn ${view === id ? "active" : ""}`}
            aria-selected={view === id}
            onClick={() => setView(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {view === "metrics" && (
        <div className="split" style={{ marginBottom: "1rem" }}>
          <section className="panel panel-interactive">
            <h3 style={{ marginTop: 0 }}>Binary model</h3>
            <p className="mono muted">Selected: {String(meta.binary_model ?? cmp?.binary_best ?? "—")}</p>
            <table className="table">
              <tbody>
                {["precision", "recall", "f1", "pr_auc", "fpr", "fnr", "mcc"].map((k) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td className="mono">{binTest[k] == null ? "—" : Number(binTest[k]).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel panel-interactive">
            <h3 style={{ marginTop: 0 }}>Multiclass model</h3>
            <p className="mono muted">Selected: {String(meta.multiclass_model ?? cmp?.multiclass_best ?? "—")}</p>
            <table className="table">
              <tbody>
                {["f1_macro", "f1_weighted", "accuracy"].map((k) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td className="mono">{multiTest[k] == null ? "—" : Number(multiTest[k]).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              Attack families: {(meta.attack_classes as string[] | undefined)?.join(", ") || "see training report"}
            </p>
          </section>
        </div>
      )}

      {view === "decisions" && (
        <>
          <section className="panel panel-interactive" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginTop: 0 }}>Research decisions</h3>
            <div className="quick-launch" style={{ marginBottom: "1rem" }}>
              {STATIC_CONCLUSIONS.map((c) => (
                <div key={c.id} className="launch-tile" style={{ cursor: "default" }}>
                  <span className="kicker">{c.id}</span>
                  <strong>{c.title}</strong>
                  <span>{c.conclusion}</span>
                </div>
              ))}
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Decision</th>
                  <th>Final choice</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Dataset</td>
                  <td>CICIDS2017 · MachineLearningCVE</td>
                  <td>Labeled flow CSVs (raw files not shipped in Git)</td>
                </tr>
                <tr>
                  <td>Binary model</td>
                  <td>{String(meta.binary_model ?? cmp?.binary_best ?? "decision_tree")}</td>
                  <td>Best multi-objective selection score</td>
                </tr>
                <tr>
                  <td>Multiclass model</td>
                  <td>{String(meta.multiclass_model ?? cmp?.multiclass_best ?? "random_forest")}</td>
                  <td>Best attack-family selection score</td>
                </tr>
                <tr>
                  <td>Stage-2 classes</td>
                  <td>6 attack families</td>
                  <td>BENIGN handled by Stage-1</td>
                </tr>
                <tr>
                  <td>Threshold</td>
                  <td>{String(info?.binary_threshold ?? "0.85")}</td>
                  <td>Validation operating-point optimization</td>
                </tr>
                <tr>
                  <td>Confidence band</td>
                  <td>
                    [{String(meta.uncertainty_lower ?? "0.10")}, {String(meta.uncertainty_upper ?? "0.95")}]
                  </td>
                  <td>Separate review band (not the attack decision itself)</td>
                </tr>
                <tr>
                  <td>Calibration</td>
                  <td>Disabled</td>
                  <td>Isotonic worsened Brier/recall</td>
                </tr>
                <tr>
                  <td>Simulation</td>
                  <td>Deterministic state machine</td>
                  <td>Safe controlled visualization; efficacy values are assumptions</td>
                </tr>
              </tbody>
            </table>
          </section>
        </>
      )}

      {view === "checklist" && (
        <section className="panel panel-interactive">
          <h3 style={{ marginTop: 0 }}>Experiment checklist</h3>
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
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Key conclusion IDs: {STATIC_CONCLUSIONS.map((c) => c.id).join(", ")} · artifacts present for{" "}
            {STATIC_CONCLUSIONS.filter((c) => present.has(c.id)).map((c) => c.id).join(", ") || "—"}
          </p>
        </section>
      )}
    </div>
  );
}
