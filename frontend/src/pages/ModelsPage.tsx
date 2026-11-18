import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  BarChart3,
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  Database,
  FlaskConical,
  Gauge as GaugeIcon,
  Grid3x3,
  HeartPulse,
  Layers,
  ListChecks,
  ScatterChart,
  SlidersHorizontal,
  Sparkles,
  TrendingUp,
  XCircle,
} from "lucide-react";
import {
  api,
  type BinaryValidationRow,
  type DriftReport,
  type Experiment,
  type FeatureImportance,
  type GlobalShap,
  type ModelsComparison,
  type ModelsHealth,
  type ModelsInfo,
  type MulticlassValidationRow,
  type RetrainRecommendation,
} from "../services/api";
import { Badge, StatusBadge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { SkeletonCard } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { BarList, CurveChart, GroupedBars, Heatmap, HorizontalBars, attackColor, useChartTheme } from "../components/charts";
import { formatCompact, formatDateTime, formatMetric, formatNumber, humanize } from "../lib/format";

type LabTab = "overview" | "performance" | "xai" | "drift";

function importanceItems(items: FeatureImportance[] | undefined, color: string) {
  return (items ?? []).map((i) => ({ label: i.feature, value: Number(i.importance ?? i.mean_abs_contribution ?? 0), color }));
}

function retrainAction(r: DriftReport["retrain_recommendation"]): RetrainRecommendation | null {
  if (!r || typeof r === "boolean") return r ? { action: "review" } : null;
  return r;
}

export function ModelsPage() {
  const theme = useChartTheme();
  const [info, setInfo] = useState<ModelsInfo | null>(null);
  const [health, setHealth] = useState<ModelsHealth | null>(null);
  const [cmp, setCmp] = useState<ModelsComparison | null>(null);
  const [shap, setShap] = useState<GlobalShap | null>(null);
  const [drift, setDrift] = useState<DriftReport | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [attackKey, setAttackKey] = useState<string>("");
  const [tab, setTab] = useState<LabTab>("overview");
  const [cmNorm, setCmNorm] = useState<"none" | "row">("row");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  function load() {
    setLoading(true);
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
        setExperiments(e?.experiments ?? []);
        const attacks = Object.keys(s?.attack_specific?.by_attack ?? {});
        if (attacks.length) setAttackKey((cur) => (cur && attacks.includes(cur) ? cur : attacks[0]));
        setError(null);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  const meta = info?.metadata ?? health?.metadata ?? {};
  const online = Boolean(info?.models_loaded || /ok|online|healthy/i.test(String(health?.status ?? "")));
  const binaryRows = cmp?.binary_validation ?? [];
  const multiRows = cmp?.multiclass_validation ?? [];
  const binTest = cmp?.binary_test ?? meta.test_metrics_binary;
  const byAttack = shap?.attack_specific?.by_attack ?? {};
  const attackOptions = Object.keys(byAttack);
  const flagged = health?.drift_summary?.flagged ?? drift?.feature_drift?.["flagged_psi_ge_0.2"] ?? [];
  const retrain = retrainAction(drift?.retrain_recommendation);
  const topPsi = drift?.feature_drift?.top_psi ?? [];

  const cm = binTest?.confusion_matrix;
  const rocPoint = binTest?.fpr != null && binTest?.recall != null ? { x: binTest.fpr, y: binTest.recall } : null;

  const binaryChart = useMemo(
    () => binaryRows.map((r) => ({ model: humanize(r.model), recall: r.recall ?? 0, f1: r.f1 ?? 0, pr_auc: r.pr_auc ?? 0, precision: r.precision ?? 0 })),
    [binaryRows]
  );
  const multiChart = useMemo(
    () => multiRows.map((r) => ({ model: humanize(r.model), macro: r.f1_macro ?? 0, weighted: r.f1_weighted ?? 0 })),
    [multiRows]
  );
  const yLow = (vals: number[]) => Math.max(0, Math.floor((Math.min(1, ...vals) - 0.02) * 20) / 20);

  const binCols: Column<BinaryValidationRow>[] = [
    {
      key: "model",
      header: "Model",
      sortable: true,
      cell: (r) => (
        <span className="row" style={{ gap: 6 }}>
          {humanize(r.model)}
          {r.model === cmp?.binary_best && (
            <Badge tone="ok" size="sm" icon={CheckCircle2}>
              Selected
            </Badge>
          )}
        </span>
      ),
    },
    { key: "recall", header: "Recall", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.recall)}</span> },
    { key: "f1", header: "F1", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.f1)}</span> },
    { key: "pr_auc", header: "PR-AUC", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.pr_auc)}</span> },
    { key: "fpr", header: "FPR", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.fpr, 4)}</span> },
    { key: "selection_score", header: "Score", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.selection_score)}</span> },
  ];
  const multiCols: Column<MulticlassValidationRow>[] = [
    {
      key: "model",
      header: "Model",
      sortable: true,
      cell: (r) => (
        <span className="row" style={{ gap: 6 }}>
          {humanize(r.model)}
          {r.model === cmp?.multiclass_best && (
            <Badge tone="ok" size="sm" icon={CheckCircle2}>
              Selected
            </Badge>
          )}
        </span>
      ),
    },
    { key: "f1_macro", header: "Macro-F1", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.f1_macro, 4)}</span> },
    { key: "f1_weighted", header: "Weighted-F1", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.f1_weighted, 4)}</span> },
    { key: "selection_score", header: "Score", sortable: true, align: "right", cell: (r) => <span className="mono">{formatMetric(r.selection_score, 4)}</span> },
  ];
  const expCols: Column<Experiment>[] = [
    { key: "experiment_id", header: "ID", sortable: true, cell: (r) => <span className="mono">{r.experiment_id}</span> },
    { key: "name", header: "Name", sortable: true, cell: (r) => humanize(r.name) },
    { key: "intended_conclusion", header: "Purpose", cell: (r) => <span className="muted small">{r.intended_conclusion ?? "—"}</span> },
    {
      key: "present",
      header: "Artifact",
      sortable: true,
      cell: (r) =>
        r.present ? (
          <Badge tone="ok" icon={CheckCircle2} size="sm">
            Present
          </Badge>
        ) : (
          <Badge tone="warn" icon={XCircle} size="sm">
            Missing
          </Badge>
        ),
    },
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow="Lab"
        icon={BrainCircuit}
        title="Model Lab"
        subtitle="Inspect the frozen model artifacts — health, validation performance, explainability and data drift."
        actions={
          <>
            <span className="live-pill">
              <span className="status-dot" data-state={online ? "live" : "off"} aria-hidden />
              {online ? "Artifacts online" : "Artifacts offline"}
            </span>
            <Link className="btn btn-secondary" to="/research">
              <BookOpenCheck size={16} aria-hidden /> Research results
            </Link>
          </>
        }
      />

      {error ? <ErrorState error={error} title="Could not load model information" onRetry={load} /> : null}

      <div className="grid grid-stats">
        <StatTile
          label="Health"
          icon={HeartPulse}
          tone={online ? "var(--ok)" : "var(--warn)"}
          value={humanize(health?.status ?? (info?.models_loaded ? "online" : "offline"))}
          compact
          loading={loading}
        />
        <StatTile label="Model version" icon={Layers} value={info?.model_version ?? "—"} compact loading={loading} hint={`App ${info?.application_version ?? "—"}`} />
        <StatTile
          label="Decision threshold"
          icon={SlidersHorizontal}
          value={info?.binary_threshold ?? "—"}
          compact
          loading={loading}
          hint={meta.uncertainty_lower != null ? `Review band ${meta.uncertainty_lower}–${meta.uncertainty_upper}` : undefined}
        />
        <StatTile label="Test F1 (binary)" icon={GaugeIcon} value={formatMetric(binTest?.f1, 4)} compact loading={loading} hint={`Recall ${formatMetric(binTest?.recall, 4)}`} />
      </div>

      <Tabs
        id="model-lab"
        label="Model lab sections"
        value={tab}
        onChange={setTab}
        items={[
          { id: "overview", label: "Overview", icon: Layers },
          { id: "performance", label: "Performance", icon: BarChart3 },
          { id: "xai", label: "Explainability", icon: Sparkles },
          { id: "drift", label: "Drift & experiments", icon: TrendingUp, count: flagged.length || undefined },
        ]}
      />

      {loading && !info ? (
        <div className="grid grid-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : (
        <>
          <TabPanel tabsId="model-lab" value="overview" active={tab} className="stack">
            <Card title="Deployed pipeline" subtitle="Selected artifacts and configuration" icon={Cpu}>
              <div className="stack">
                <div className="row" style={{ gap: 6 }}>
                  <Badge tone="accent">Binary · {humanize(meta.binary_model ?? cmp?.binary_best ?? "—")}</Badge>
                  <Badge tone="accent">Attack family · {humanize(meta.multiclass_model ?? cmp?.multiclass_best ?? "—")}</Badge>
                  <Badge tone={info?.calibrated_binary_active ? "info" : "neutral"}>Calibration {info?.calibrated_binary_active ? "on" : "off"}</Badge>
                  <Badge tone="neutral">Dataset · {meta.dataset ?? "CICIDS2017"}</Badge>
                  {flagged.length === 0 ? (
                    <Badge tone="ok" icon={CheckCircle2}>
                      No drift flags
                    </Badge>
                  ) : (
                    <Badge tone="warn">{flagged.length} drift flags</Badge>
                  )}
                </div>
                <div className="grid grid-2">
                  <dl className="kv">
                    <dt>Features (binary / family)</dt>
                    <dd>
                      {meta.feature_count_binary ?? "—"} / {meta.feature_count_multiclass ?? "—"}
                    </dd>
                    <dt>Attack families</dt>
                    <dd>{(meta.attack_classes ?? cmp?.classes ?? []).join(", ") || "—"}</dd>
                    <dt>Trained</dt>
                    <dd>{formatDateTime(meta.generated_at)}</dd>
                    <dt>Training commit</dt>
                    <dd>{meta.training_git_commit ?? "—"}</dd>
                  </dl>
                  <dl className="kv">
                    <dt>Training rows</dt>
                    <dd>{formatCompact(meta.split_sizes?.training_rows)}</dd>
                    <dt>Validation rows</dt>
                    <dd>{formatCompact(meta.split_sizes?.validation_rows)}</dd>
                    <dt>Test rows</dt>
                    <dd>{formatCompact(meta.split_sizes?.test_rows)}</dd>
                    <dt>Threshold method</dt>
                    <dd>{health?.operating_point?.selection_method ? humanize(health.operating_point.selection_method) : "—"}</dd>
                  </dl>
                </div>
                {health?.missing_artifacts && health.missing_artifacts.length > 0 && (
                  <Callout tone="warn" title="Missing artifacts">
                    {health.missing_artifacts.join(", ")}
                  </Callout>
                )}
              </div>
            </Card>

            <Card title="Experiment conclusions" subtitle="Key decisions from the frozen experiment suite" icon={FlaskConical}>
              <div className="grid grid-3">
                {[
                  { id: "EXP-004", title: "Threshold 0.85", text: "Max F1 under recall ≥ 0.95 after the freeze retrain." },
                  { id: "EXP-003", title: "Calibration off", text: "Isotonic worsened Brier score and reduced recall." },
                  { id: "EXP-005", title: "Risk stable", text: "Severity labels held across weight configurations." },
                  { id: "EXP-008", title: "Drift clear", text: "No feature exceeded PSI ≥ 0.2 on the IID test split." },
                ].map((c) => (
                  <div key={c.id} className="info-tile">
                    <span className="info-tile-kicker">{c.id}</span>
                    <strong>{c.title}</strong>
                    <p>{c.text}</p>
                  </div>
                ))}
              </div>
            </Card>
          </TabPanel>

          <TabPanel tabsId="model-lab" value="performance" active={tab} className="stack">
            <div className="grid grid-2">
              <Card title="Binary detector — validation" subtitle="Recall-first multi-objective selection" icon={BarChart3}>
                {binaryChart.length ? (
                  <div className="stack">
                    <GroupedBars
                      ariaLabel="Binary validation metrics per model"
                      data={binaryChart}
                      categoryKey="model"
                      yDomain={[yLow(binaryChart.flatMap((r) => [r.recall, r.f1, r.pr_auc])), 1]}
                      yFormatter={(v) => v.toFixed(2)}
                      series={[
                        { key: "recall", label: "Recall" },
                        { key: "f1", label: "F1" },
                        { key: "pr_auc", label: "PR-AUC" },
                      ]}
                    />
                    <DataTable data={binaryRows} columns={binCols} rowKey={(r) => r.model} pageSize={0} dense caption="Binary validation metrics" />
                  </div>
                ) : (
                  <EmptyState compact title="No comparison report" />
                )}
              </Card>
              <Card title="Attack-family classifier — validation" subtitle="0.7 × macro-F1 + 0.3 × weighted-F1 on attack rows" icon={BarChart3}>
                {multiChart.length ? (
                  <div className="stack">
                    <GroupedBars
                      ariaLabel="Attack-family validation F1 per model"
                      data={multiChart}
                      categoryKey="model"
                      yDomain={[yLow(multiChart.flatMap((r) => [r.macro, r.weighted])), 1]}
                      yFormatter={(v) => v.toFixed(3)}
                      series={[
                        { key: "macro", label: "Macro-F1" },
                        { key: "weighted", label: "Weighted-F1" },
                      ]}
                    />
                    <DataTable data={multiRows} columns={multiCols} rowKey={(r) => r.model} pageSize={0} dense caption="Attack-family validation metrics" />
                  </div>
                ) : (
                  <EmptyState compact title="No comparison report" />
                )}
              </Card>
            </div>

            <div className="grid grid-3">
              <Card
                title="Confusion matrix (test)"
                subtitle="Binary detector at argmax 0.5 (historical test figure; deployed threshold is 0.85)"
                icon={Grid3x3}
                actions={
                  <div className="segmented" role="radiogroup" aria-label="Confusion matrix scale">
                    <button type="button" role="radio" aria-checked={cmNorm === "row"} onClick={() => setCmNorm("row")}>
                      Row %
                    </button>
                    <button type="button" role="radio" aria-checked={cmNorm === "none"} onClick={() => setCmNorm("none")}>
                      Counts
                    </button>
                  </div>
                }
              >
                {cm ? (
                  <Heatmap
                    ariaLabel="Binary confusion matrix on the test split"
                    rows={["Benign", "Attack"]}
                    cols={["Benign", "Attack"]}
                    values={cm}
                    normalize={cmNorm}
                    rowAxisLabel="Actual"
                    colAxisLabel="Predicted"
                    highlightDiagonal
                    valueFormatter={cmNorm === "none" ? (_v, raw) => formatCompact(raw) : undefined}
                  />
                ) : (
                  <EmptyState compact title="No confusion matrix in the report" />
                )}
              </Card>
              <Card title="Test metrics" subtitle="Held-out IID test split (binary)" icon={GaugeIcon}>
                {binTest ? (
                  <BarList
                    ariaLabel="Binary test metrics"
                    max={1}
                    sort={false}
                    valueFormatter={(v) => v.toFixed(4)}
                    items={(
                      [
                        ["Precision", binTest.precision],
                        ["Recall", binTest.recall],
                        ["F1", binTest.f1],
                        ["Specificity", binTest.specificity],
                        ["ROC-AUC", binTest.roc_auc],
                        ["PR-AUC", binTest.pr_auc],
                        ["MCC", binTest.mcc],
                      ] as Array<[string, number | undefined]>
                    )
                      .filter(([, v]) => v != null)
                      .map(([k, v], i) => ({ label: k, value: Number(v), color: theme.series[i % 3] }))}
                  />
                ) : (
                  <EmptyState compact title="No test metrics" />
                )}
              </Card>
              <Card title="Operating point (ROC space)" subtitle={`ROC-AUC from scores: ${formatMetric(binTest?.roc_auc, 4)}`} icon={ScatterChart}>
                {rocPoint ? (
                  <div className="stack-sm">
                    <CurveChart
                      ariaLabel="Operating point of the binary detector in ROC space versus chance"
                      height={220}
                      diagonal
                      xLabel="False positive rate"
                      yLabel="True positive rate"
                      series={[
                        {
                          label: `Threshold ${info?.binary_threshold ?? ""}`,
                          points: [{ x: 0, y: 0 }, { x: rocPoint.x, y: rocPoint.y, meta: "operating" }, { x: 1, y: 1 }],
                          color: theme.accent,
                        },
                      ]}
                    />
                    <p className="muted small">
                      Piecewise curve through the selected threshold (FPR {formatMetric(rocPoint.x, 4)}, TPR {formatMetric(rocPoint.y, 4)}); dashed line = chance.
                    </p>
                  </div>
                ) : (
                  <EmptyState compact title="No operating point available" />
                )}
              </Card>
            </div>
            <p className="muted small">Selection criteria are project-justified (see the training report). The attack-family classifier is trained on attack rows only.</p>
          </TabPanel>

          <TabPanel tabsId="model-lab" value="xai" active={tab} className="stack">
            <div className="grid grid-2">
              <Card title="Global importance — binary detector" subtitle={shap?.global?.method ? humanize(shap.global.method) : undefined} icon={Sparkles}>
                {shap?.global?.binary_top?.length ? (
                  <BarList ariaLabel="Global binary feature importance" valueFormatter={(v) => v.toFixed(3)} items={importanceItems(shap.global.binary_top, theme.series[0])} />
                ) : (
                  <EmptyState compact title="No global ranking yet" />
                )}
              </Card>
              <Card title="Global importance — attack-family classifier" subtitle={shap?.global?.note} icon={Sparkles}>
                {shap?.global?.multiclass_top?.length ? (
                  <BarList ariaLabel="Global attack-family feature importance" valueFormatter={(v) => v.toFixed(3)} items={importanceItems(shap.global.multiclass_top, theme.series[2])} />
                ) : (
                  <EmptyState compact title="No global ranking yet" />
                )}
              </Card>
            </div>
            <Card
              title="Attack-specific drivers"
              subtitle={shap?.attack_specific?.note ?? "Mean |local contribution| per attack family"}
              icon={Activity}
              actions={
                attackOptions.length > 0 ? (
                  <Tabs
                    id="attack-drivers"
                    label="Attack family"
                    variant="pill"
                    value={attackKey}
                    onChange={setAttackKey}
                    items={attackOptions.map((a) => ({ id: a, label: a, count: byAttack[a]?.samples }))}
                  />
                ) : null
              }
            >
              {attackKey && byAttack[attackKey] ? (
                <TabPanel tabsId="attack-drivers" value={attackKey} active={attackKey}>
                  <BarList
                    ariaLabel={`Top drivers for ${attackKey}`}
                    valueFormatter={(v) => v.toFixed(3)}
                    items={importanceItems(byAttack[attackKey].top_features, attackColor(theme, attackKey))}
                  />
                </TabPanel>
              ) : (
                <EmptyState
                  icon={Sparkles}
                  title="No attack-specific SHAP cache"
                  description="Generate the global SHAP artifacts (experiment script) to populate this view."
                />
              )}
            </Card>
          </TabPanel>

          <TabPanel tabsId="model-lab" value="drift" active={tab} className="stack">
            {!drift?.available ? (
              <EmptyState icon={TrendingUp} title="No drift report" description={drift?.message ?? "The drift artifact is missing."} />
            ) : (
              <>
                <div className="grid grid-stats">
                  <StatTile label="Features compared" icon={Database} value={drift.feature_drift?.features_compared ?? drift.summary?.features_compared ?? "—"} compact />
                  <StatTile
                    label="Flagged (PSI ≥ 0.2)"
                    icon={ListChecks}
                    tone={flagged.length ? "var(--warn)" : "var(--ok)"}
                    value={flagged.length}
                    compact
                  />
                  <StatTile label="Max PSI" icon={TrendingUp} value={formatNumber(drift.summary?.max_psi ?? Math.max(0, ...topPsi.map((p) => p.psi)), 4)} compact />
                  <StatTile label="Recommendation" icon={HeartPulse} value={<StatusBadge status={retrain?.action ?? "monitor"} />} hint={retrain?.reason} compact />
                </div>
                {flagged.length > 0 && (
                  <Callout tone="warn" title="Flagged features">
                    <span className="row" style={{ gap: 6 }}>
                      {flagged.map((f) => (
                        <Badge key={f} tone="warn" size="sm">
                          {f}
                        </Badge>
                      ))}
                    </span>
                  </Callout>
                )}
                <div className="grid grid-2">
                  <Card title="Population stability (PSI)" subtitle={`${drift.ref ?? "reference"} → ${drift.current ?? "current"} · alert at 0.2`} icon={BarChart3}>
                    <BarList
                      ariaLabel="Top features by PSI"
                      max={Math.max(0.25, ...topPsi.map((p) => p.psi))}
                      valueFormatter={(v) => v.toFixed(3)}
                      limit={10}
                      items={topPsi.map((p) => ({
                        label: p.feature,
                        value: p.psi,
                        color: p.psi >= 0.2 ? theme.severity.HIGH : theme.series[0],
                      }))}
                    />
                  </Card>
                  <Card title="Mean shift (z-score)" subtitle="Signed shift of the feature mean, reference → current" icon={TrendingUp}>
                    <HorizontalBars
                      ariaLabel="Signed mean shift per feature"
                      items={topPsi.slice(0, 10).map((p) => ({ label: p.feature, value: Number(p.mean_shift_z ?? 0) }))}
                      positiveLabel="Mean increased"
                      negativeLabel="Mean decreased"
                      valueFormatter={(v) => v.toFixed(4)}
                    />
                  </Card>
                </div>
                {drift.label_drift?.by_label?.length ? (
                  <Card title="Label distribution" subtitle="Share of rows per class (%)" icon={BarChart3}>
                    <GroupedBars
                      ariaLabel="Label share in reference versus current split"
                      data={drift.label_drift.by_label.map((l) => ({ label: l.label, ref: l.ref_pct, cur: l.cur_pct }))}
                      categoryKey="label"
                      yFormatter={(v) => `${v}%`}
                      series={[
                        { key: "ref", label: `Reference (${drift.ref ?? "train"})` },
                        { key: "cur", label: `Current (${drift.current ?? "test"})` },
                      ]}
                    />
                  </Card>
                ) : null}
                {(drift.summary?.academic_caveats?.length || drift.note) && (
                  <Callout tone="info" title="Interpretation">
                    <ul className="check-list" style={{ marginTop: 6 }}>
                      {(drift.summary?.academic_caveats ?? []).map((c) => (
                        <li key={c}>{c}</li>
                      ))}
                      {drift.note ? <li>{drift.note}</li> : null}
                    </ul>
                  </Callout>
                )}
              </>
            )}
            <Card title="Experiment index" subtitle={`${experiments.filter((e) => e.present).length} of ${experiments.length} artifacts present`} icon={FlaskConical}>
              <DataTable data={experiments} columns={expCols} rowKey={(r) => r.experiment_id} searchable pageSize={10} emptyTitle="No experiments indexed" caption="Experiment index" />
            </Card>
          </TabPanel>
        </>
      )}
    </div>
  );
}
