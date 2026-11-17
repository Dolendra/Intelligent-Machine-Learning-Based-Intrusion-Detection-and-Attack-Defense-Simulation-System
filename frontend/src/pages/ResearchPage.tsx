import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FileText,
  FlaskConical,
  Gauge as GaugeIcon,
  Grid3x3,
  Lightbulb,
  ListChecks,
  Scale,
  SlidersHorizontal,
  XCircle,
} from "lucide-react";
import { api, type Experiment, type ModelsComparison, type ModelsInfo } from "../services/api";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { BarList, DonutChart, Heatmap, useChartTheme } from "../components/charts";
import { formatCompact, formatMetric, humanize } from "../lib/format";

type Conclusion = { id: string; title: string; conclusion: string };

const STATIC_CONCLUSIONS: Conclusion[] = [
  {
    id: "EXP-001",
    title: "Model selection",
    conclusion:
      "Binary Decision Tree selected over XGBoost for higher recall under multi-objective weights; multiclass Random Forest edged XGBoost on the macro/weighted blend.",
  },
  {
    id: "EXP-004",
    title: "Threshold",
    conclusion: "0.85 selected because it maximised F1 under recall ≥ 0.95 after the freeze retrain (decision-tree binary).",
  },
  { id: "EXP-003", title: "Calibration", conclusion: "Disabled — isotonic improved ECE slightly but worsened Brier score and reduced recall." },
  { id: "EXP-005", title: "Risk sensitivity", conclusion: "Severity labels remained stable across A/B/C weight configurations." },
  {
    id: "EXP-008",
    title: "Drift (IID)",
    conclusion:
      "No feature exceeded PSI ≥ 0.2 between train and IID test — expected under stratified same-corpus splits; not a live-drift claim.",
  },
  {
    id: "EXP-011",
    title: "Error analysis",
    conclusion: "IID residuals: FP 1,377 / FN 255; multiclass 18 confusions / 85k attacks, mainly PortScan / DoS / WebAttack.",
  },
  {
    id: "EXP-013",
    title: "Temporal holdout",
    conclusion:
      "Frozen models on Friday samples stay strong on binary F1; Friday multiclass covered only Bot/DDoS/PortScan — not a full six-class temporal claim.",
  },
  {
    id: "EXP-009",
    title: "External dataset",
    conclusion: "Not performed in the current experimental scope — identified as future work for cross-dataset generalisation.",
  },
];

type DecisionRow = { decision: string; choice: string; reason: string };

export function ResearchPage() {
  const theme = useChartTheme();
  const [info, setInfo] = useState<ModelsInfo | null>(null);
  const [cmp, setCmp] = useState<ModelsComparison | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [view, setView] = useState<"decisions" | "metrics" | "checklist">("decisions");

  function load() {
    setLoading(true);
    Promise.all([api.models(), api.modelsComparison().catch(() => null), api.experiments().catch(() => null)])
      .then(([m, c, e]) => {
        setInfo(m);
        setCmp(c);
        setExperiments(e?.experiments ?? []);
        setError(null);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  const meta = info?.metadata ?? {};
  const binTest = cmp?.binary_test ?? {};
  const multiTest = cmp?.multiclass_test ?? {};
  const present = new Set(experiments.filter((x) => x.present).map((x) => x.experiment_id));
  const presentCount = experiments.filter((x) => x.present).length;
  const lower = meta.uncertainty_lower ?? 0.1;
  const upper = meta.uncertainty_upper ?? 0.95;

  const decisions: DecisionRow[] = useMemo(
    () => [
      { decision: "Dataset", choice: "CICIDS2017 · MachineLearningCVE", reason: "Labelled flow CSVs (raw files not shipped in Git)" },
      { decision: "Binary model", choice: humanize(meta.binary_model ?? cmp?.binary_best ?? "decision_tree"), reason: "IDS multi-objective score (recall-first; not raw F1 alone)" },
      { decision: "Attack-family model", choice: humanize(meta.multiclass_model ?? cmp?.multiclass_best ?? "random_forest"), reason: "Best attack-family selection score (attack rows only)" },
      { decision: "Attack-family classes", choice: "6 attack families", reason: "Benign traffic is handled by the binary detector" },
      { decision: "Threshold", choice: String(info?.binary_threshold ?? "0.85"), reason: "Validation operating-point optimisation" },
      { decision: "Confidence band", choice: `[${lower}, ${upper}]`, reason: "Separate review band (not the attack decision itself)" },
      { decision: "Calibration", choice: "Disabled", reason: "Isotonic worsened Brier score / recall" },
      { decision: "Features", choice: "SelectKBest(f_classif, k=40)", reason: "Dual selectors fit on the training split only" },
      { decision: "Simulation", choice: "Deterministic state machine", reason: "Safe controlled visualisation; efficacy values are assumptions" },
      { decision: "External dataset", choice: "Future work", reason: "Not fabricated within current scope" },
    ],
    [meta.binary_model, meta.multiclass_model, cmp, info, lower, upper]
  );

  const decisionCols: Column<DecisionRow>[] = [
    { key: "decision", header: "Decision", sortable: true, cell: (r) => <strong>{r.decision}</strong> },
    { key: "choice", header: "Final choice", cell: (r) => <span className="mono small">{r.choice}</span> },
    { key: "reason", header: "Reason", cell: (r) => <span className="text-2">{r.reason}</span> },
  ];
  const expCols: Column<Experiment>[] = [
    { key: "experiment_id", header: "ID", sortable: true, cell: (r) => <span className="mono">{r.experiment_id}</span> },
    { key: "name", header: "Name", sortable: true, cell: (r) => humanize(r.name) },
    { key: "artifact", header: "Artifact", cell: (r) => <span className="mono small muted">{r.artifact}</span> },
    {
      key: "present",
      header: "Present",
      sortable: true,
      cell: (r) =>
        r.present ? (
          <Badge tone="ok" icon={CheckCircle2} size="sm">
            Yes
          </Badge>
        ) : (
          <Badge tone="warn" icon={XCircle} size="sm">
            No
          </Badge>
        ),
    },
  ];

  const binMetrics: Array<[string, number | undefined]> = [
    ["Precision", binTest.precision],
    ["Recall", binTest.recall],
    ["F1", binTest.f1],
    ["PR-AUC", binTest.pr_auc],
    ["MCC", binTest.mcc],
  ];
  const multiMetrics: Array<[string, number | undefined]> = [
    ["Macro-F1", multiTest.f1_macro],
    ["Weighted-F1", multiTest.f1_weighted],
    ["Accuracy", multiTest.accuracy],
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow="Lab"
        icon={BookOpenCheck}
        title="Baseline Study (v1.1)"
        subtitle={`Frozen experiment conclusions for the Aegis IDS v${info?.application_version ?? "1.1"} closed-set baseline. The v3 open-set results live in the Research Lab.`}
        actions={
          <>
            <Link className="btn btn-secondary" to="/models">
              <BrainCircuit size={16} aria-hidden /> Open Model Lab
            </Link>
            <Link className="btn btn-primary" to="/research-lab">
              <FlaskConical size={16} aria-hidden /> Research Lab (v3)
            </Link>
          </>
        }
      />

      {error ? <ErrorState error={error} onRetry={load} /> : null}

      <div className="grid grid-stats">
        <StatTile label="Dataset" icon={Database} value={meta.dataset ?? "CICIDS2017"} compact loading={loading} hint={formatCompact(meta.split_sizes?.training_rows) + " training rows"} />
        <StatTile label="Threshold" icon={SlidersHorizontal} value={String(info?.binary_threshold ?? meta.binary_threshold ?? "0.85")} compact loading={loading} />
        <StatTile label="Review band" icon={Scale} value={`[${lower}, ${upper}]`} compact loading={loading} />
        <StatTile
          label="Calibration"
          icon={GaugeIcon}
          value={info?.calibrated_binary_active || meta.use_calibrated_binary ? "On" : "Off"}
          compact
          loading={loading}
        />
        <StatTile
          label="Artifacts present"
          icon={ClipboardCheck}
          value={`${presentCount}/${experiments.length || "—"}`}
          compact
          loading={loading}
          tone={presentCount === experiments.length && experiments.length ? "var(--ok)" : "var(--warn)"}
        />
      </div>

      <Tabs
        id="research"
        label="Research sections"
        value={view}
        onChange={setView}
        items={[
          { id: "decisions", label: "Decisions", icon: Lightbulb },
          { id: "metrics", label: "Test metrics", icon: GaugeIcon },
          { id: "checklist", label: "Experiment checklist", icon: ListChecks, count: experiments.length || undefined },
        ]}
      />

      <TabPanel tabsId="research" value="decisions" active={view} className="stack">
        <div className="grid grid-3">
          {STATIC_CONCLUSIONS.map((c) => (
            <div key={c.id} className="info-tile">
              <div className="row-between">
                <span className="info-tile-kicker">{c.id}</span>
                {experiments.length > 0 &&
                  (present.has(c.id) ? (
                    <Badge tone="ok" size="sm" icon={CheckCircle2}>
                      Artifact
                    </Badge>
                  ) : (
                    <Badge tone="neutral" size="sm">
                      Documented
                    </Badge>
                  ))}
              </div>
              <strong>{c.title}</strong>
              <p>{c.conclusion}</p>
            </div>
          ))}
        </div>
        <Card title="Design decisions" subtitle="Final choices and their justification" icon={Lightbulb} footer={<>Submission pack: docs/DEMO.md · docs/VIVA_QA.md · docs/Aegis_IDS_Viva_Presentation.pptx · docs/PROJECT_REPORT.md</>}>
          <DataTable data={decisions} columns={decisionCols} rowKey={(r) => r.decision} pageSize={0} caption="Research design decisions" />
        </Card>
      </TabPanel>

      <TabPanel tabsId="research" value="metrics" active={view} className="stack">
        <div className="grid grid-3">
          <Card title="Binary detector" subtitle={`Selected: ${humanize(meta.binary_model ?? cmp?.binary_best ?? "—")}`} icon={GaugeIcon}>
            <BarList
              ariaLabel="Binary test metrics"
              max={1}
              sort={false}
              valueFormatter={(v) => v.toFixed(4)}
              items={binMetrics.filter(([, v]) => v != null).map(([k, v]) => ({ label: k, value: Number(v), color: theme.series[0] }))}
            />
            <dl className="kv" style={{ marginTop: 12 }}>
              <dt>False positive rate</dt>
              <dd>{formatMetric(binTest.fpr, 4)}</dd>
              <dt>False negative rate</dt>
              <dd>{formatMetric(binTest.fnr, 4)}</dd>
            </dl>
          </Card>
          <Card title="Attack-family classifier" subtitle={`Selected: ${humanize(meta.multiclass_model ?? cmp?.multiclass_best ?? "—")}`} icon={GaugeIcon}>
            <BarList
              ariaLabel="Attack-family test metrics"
              max={1}
              sort={false}
              valueFormatter={(v) => v.toFixed(4)}
              items={multiMetrics.filter(([, v]) => v != null).map(([k, v]) => ({ label: k, value: Number(v), color: theme.series[2] }))}
            />
            <p className="muted small" style={{ marginTop: 12 }}>
              Attack families: {(meta.attack_classes ?? []).join(", ") || "see training report"}
            </p>
          </Card>
          <Card title="Confusion matrix (test)" subtitle="Row-normalised — recall per actual class" icon={Grid3x3}>
            {binTest.confusion_matrix ? (
              <Heatmap
                ariaLabel="Binary test confusion matrix"
                rows={["Benign", "Attack"]}
                cols={["Benign", "Attack"]}
                values={binTest.confusion_matrix}
                normalize="row"
                rowAxisLabel="Actual"
                colAxisLabel="Predicted"
                highlightDiagonal
              />
            ) : (
              <p className="muted small">Not available.</p>
            )}
          </Card>
        </div>
        {meta.split_sizes && (
          <Card title="Data splits" subtitle="Stratified train / validation / test rows" icon={Database}>
            <DonutChart
              ariaLabel="Rows per data split"
              centerLabel="Rows"
              valueFormatter={(v) => formatCompact(v)}
              data={[
                { name: "Training", value: meta.split_sizes.training_rows ?? 0, color: theme.series[0] },
                { name: "Validation", value: meta.split_sizes.validation_rows ?? 0, color: theme.series[1] },
                { name: "Test", value: meta.split_sizes.test_rows ?? 0, color: theme.series[2] },
              ]}
            />
          </Card>
        )}
      </TabPanel>

      <TabPanel tabsId="research" value="checklist" active={view}>
        <Card
          title="Experiment checklist"
          subtitle={`Key conclusion IDs with artifacts: ${STATIC_CONCLUSIONS.filter((c) => present.has(c.id)).map((c) => c.id).join(", ") || "—"}`}
          icon={FlaskConical}
          actions={
            experiments.length ? (
              <div style={{ width: 160 }} title={`${presentCount} of ${experiments.length} present`}>
                <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={experiments.length} aria-valuenow={presentCount} aria-label="Artifacts present">
                  <span style={{ width: `${(presentCount / experiments.length) * 100}%` }} />
                </div>
              </div>
            ) : null
          }
        >
          <DataTable data={experiments} columns={expCols} rowKey={(r) => r.experiment_id} searchable pageSize={15} loading={loading} emptyTitle="No experiments indexed" caption="Experiment checklist" />
          <p className="muted small" style={{ marginTop: 12 }}>
            <FileText size={12} aria-hidden /> Missing artifacts are documented conclusions without a regenerated JSON report in this checkout.
          </p>
        </Card>
      </TabPanel>
    </div>
  );
}
