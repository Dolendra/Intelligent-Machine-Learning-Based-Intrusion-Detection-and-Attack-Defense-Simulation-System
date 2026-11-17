import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  CalendarClock,
  FlaskConical,
  GitCompareArrows,
  Globe2,
  Grid3x3,
  Layers,
  Lightbulb,
  ListChecks,
  Radar,
  Scale,
  Shuffle,
  Sigma,
  Sparkles,
  Target,
} from "lucide-react";
import {
  api,
  type AdaptationRow,
  type ProtocolBlock,
  type ProtocolHeadline,
  type ProtocolKey,
  type ResearchMethodRow,
  type ResearchOverview,
  type SignificanceRow,
} from "../services/api";
import { Badge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { SkeletonCard } from "../components/ui/Skeleton";
import { StackBar, Heatmap, RangeChart, TimeSeriesArea, useChartTheme, type ChartTheme } from "../components/charts";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { formatCI, formatDateTime, formatPct, humanize } from "../lib/format";

type TabId = "overview" | ProtocolKey | "gate";

const PROTOCOLS: Record<ProtocolKey, { title: string; short: string; icon: typeof Shuffle; question: string; script: string }> = {
  loafo: {
    title: "Leave-one-family-out",
    short: "LOAFO",
    icon: Shuffle,
    question: "Hold one attack family out of training entirely, then ask: is it caught as an unknown at test time?",
    script: "loafo",
  },
  temporal: {
    title: "Temporal",
    short: "Temporal",
    icon: CalendarClock,
    question: "Train on earlier days, test on later days: does the false-alarm guarantee survive benign drift?",
    script: "temporal",
  },
  cross: {
    title: "Cross-dataset (2017 → 2018)",
    short: "Cross-dataset",
    icon: Globe2,
    question: "Train on CICIDS2017, test on CSE-CIC-IDS2018: does the method transfer to a different network?",
    script: "cross",
  },
};

const EVIDENCE_TEXT: Record<string, string> = {
  sup: "Classifier",
  knn: "kNN novelty",
  ae: "Autoencoder",
  if: "Isolation Forest",
  energy: "Energy score",
  dt: "Decision tree",
};

const GROUP_LABEL: Record<string, string> = { proposed: "Proposed", ablation: "Ablations", baseline: "Baselines" };

function groupColor(theme: ChartTheme, group: string) {
  if (group === "proposed") return theme.series[6];
  if (group === "ablation") return theme.series[0];
  return theme.axis;
}

function NotGenerated({ protocol }: { protocol: ProtocolKey }) {
  return (
    <EmptyState
      icon={FlaskConical}
      title={`${PROTOCOLS[protocol].title} results not generated yet`}
      description={
        <>
          Run <code>python scripts/50_openset_experiments.py --protocol {PROTOCOLS[protocol].script}</code> to produce them. This page
          shows them once the summary artifact exists (reload the page after the run finishes).
        </>
      }
    />
  );
}

/* ------------------------------------------------------------------ headline */

function HeadlineCard({ protocol, h, proposed, baseline }: { protocol: ProtocolKey; h: ProtocolHeadline; proposed: string; baseline: string }) {
  const P = PROTOCOLS[protocol];
  const delta = (h.proposed_zero_day_recall - h.baseline_zero_day_recall) * 100;
  return (
    <Card title={P.title} subtitle="Zero-day recall at matched false-alarm budget" icon={P.icon}>
      <div className="stack">
        <div className="vs-card">
          <div className="vs-side" data-win={delta > 0 || undefined}>
            <div className="stat-label">{proposed}</div>
            <div className="vs-value" style={{ color: "var(--chart-7)" }}>
              {formatPct(h.proposed_zero_day_recall, 1)}
            </div>
            <div className="muted small">FPR {formatPct(h.proposed_fpr, 2)} · AUROC {h.proposed_auroc?.toFixed(3) ?? "—"}</div>
          </div>
          <div className="vs-side">
            <div className="stat-label">{baseline}</div>
            <div className="vs-value">{formatPct(h.baseline_zero_day_recall, 1)}</div>
            <div className="muted small">FPR {formatPct(h.baseline_fpr, 2)} · AUROC {h.baseline_auroc?.toFixed(3) ?? "—"}</div>
          </div>
        </div>
        <p className="text-2">
          {proposed} catches <strong>{formatPct(h.proposed_zero_day_recall, 1)}</strong> of never-seen attack flows versus{" "}
          {formatPct(h.baseline_zero_day_recall, 1)} for the {baseline} baseline ({delta >= 0 ? "+" : ""}
          {delta.toFixed(1)} pp), at benign false-alarm rates of {formatPct(h.proposed_fpr, 1)} and {formatPct(h.baseline_fpr, 1)} respectively.
        </p>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ protocol view */

function SignificanceTable({ rows }: { rows: SignificanceRow[] }) {
  const columns: Column<SignificanceRow>[] = [
    { key: "metric", header: "Metric", sortable: true, cell: (r) => humanize(r.metric) },
    { key: "versus", header: "Proposed vs", sortable: true },
    {
      key: "mean_diff",
      header: "Mean diff [95% CI]",
      sortable: true,
      align: "right",
      cell: (r) => {
        const pp = /fpr|recall|auroc|auprc/i.test(r.metric);
        const fmt = (v: number) => (pp ? `${v > 0 ? "+" : ""}${(v * 100).toFixed(1)}` : `${v > 0 ? "+" : ""}${v.toFixed(3)}`);
        return (
          <span className="mono" style={{ color: r.mean_diff > 0 ? "var(--ok)" : r.mean_diff < 0 ? "var(--danger)" : undefined }}>
            {fmt(r.mean_diff)}
            {pp ? " pp" : ""}
            {r.diff_ci_low != null && r.diff_ci_high != null ? (
              <span className="muted"> [{fmt(r.diff_ci_low)}, {fmt(r.diff_ci_high)}]</span>
            ) : null}
          </span>
        );
      },
    },
    {
      key: "seeds",
      header: "Seeds better",
      align: "right",
      accessor: (r) => r.positive_seeds ?? -1,
      sortable: true,
      cell: (r) => <span className="mono">{r.positive_seeds != null && r.n_seeds != null ? `${r.positive_seeds} / ${r.n_seeds}` : "—"}</span>,
    },
    {
      key: "wlt",
      header: "Fold W / L / T (descriptive)",
      accessor: (r) => r.wins - r.losses,
      sortable: true,
      cell: (r) => (
        <span className="mono muted">
          {r.wins} / {r.losses} / {r.ties}
        </span>
      ),
    },
    {
      key: "p_value",
      header: "p (paired t, seeds)",
      sortable: true,
      align: "right",
      cell: (r) =>
        r.p_value == null ? (
          "—"
        ) : (
          <span className="row" style={{ gap: 6, justifyContent: "flex-end", flexWrap: "nowrap" }}>
            <span className="mono">{r.p_value < 0.001 ? r.p_value.toExponential(1) : r.p_value.toFixed(4)}</span>
            {r.p_value < 0.05 ? (
              <Badge tone="ok" size="sm">
                p &lt; 0.05
              </Badge>
            ) : (
              <Badge tone="neutral" size="sm">
                n.s.
              </Badge>
            )}
          </span>
        ),
    },
  ];
  return <DataTable data={rows} columns={columns} rowKey={(r) => `${r.metric}-${r.versus}`} searchable pageSize={10} dense caption="Paired significance tests" />;
}

function AdaptationCharts({ rows, block, proposed, alpha }: { rows: AdaptationRow[]; block: ProtocolBlock; proposed: string; alpha: number }) {
  const theme = useChartTheme();
  const own = rows.filter((r) => r.method === proposed);
  const variants = Array.from(new Set(own.map((r) => r.variant)));
  const windows = Array.from(new Set(own.map((r) => String(r.window)))).sort((a, b) => Number(a) - Number(b) || a.localeCompare(b));
  const base = block.methods.find((m) => m.method === proposed);
  const mean = (xs: number[]) => (xs.length ? xs.reduce((s, v) => s + v, 0) / xs.length : NaN);

  const build = (metric: "fpr" | "zero_day_recall") =>
    windows.map((w) => {
      const row: Record<string, number | string> = { window: w };
      row.none = ((base?.[metric]?.mean ?? NaN) as number) * 100;
      for (const v of variants) {
        const vals = own.filter((r) => String(r.window) === w && r.variant === v).map((r) => r[metric]?.mean ?? NaN).filter(Number.isFinite);
        row[v] = mean(vals) * 100;
      }
      return row;
    });

  const VARIANT_LABEL: Record<string, string> = { recal: "Re-calibrate", "recal+ref": "Re-calibrate + kNN refs", oracle: "Oracle (full retrain)" };
  const series = [
    { key: "none", label: "No adaptation", color: theme.axis, dashed: true },
    ...variants.map((v, i) => ({ key: v, label: VARIANT_LABEL[v] ?? humanize(v), color: [theme.series[6], theme.series[2], theme.series[0]][i % 3] })),
  ];
  return (
    <div className="stack">
      <Callout tone="info" icon={Lightbulb} title="Why adaptation matters">
        Benign traffic drifts, which breaks the conformal false-alarm guarantee. Re-calibrating on a small window of recent benign
        flows restores FPR ≈ α without retraining the classifier.
      </Callout>
      <div className="grid grid-2">
        <Card title="Benign FPR vs warm-up window" subtitle={`Mean over folds · dashed reference at α = ${formatPct(alpha, 1)}`} icon={Scale} as="div">
          <TimeSeriesArea
            ariaLabel="Benign false-positive rate versus warm-up window size per adaptation variant"
            data={build("fpr")}
            xKey="window"
            variant="line"
            height={240}
            xFormatter={(v) => `${v}`}
            yFormatter={(v) => `${v.toFixed(1)}%`}
            referenceLines={[{ y: alpha * 100, label: `α = ${formatPct(alpha, 1)}`, color: theme.danger }]}
            series={series}
          />
        </Card>
        <Card title="Zero-day recall vs warm-up window" subtitle="Mean over folds" icon={Target} as="div">
          <TimeSeriesArea
            ariaLabel="Zero-day recall versus warm-up window size per adaptation variant"
            data={build("zero_day_recall")}
            xKey="window"
            variant="line"
            height={240}
            yDomain={[0, 100]}
            yFormatter={(v) => `${Math.round(v)}%`}
            series={series}
          />
        </Card>
      </div>
    </div>
  );
}

function AttributionView({ attribution }: { attribution: ProtocolBlock["attribution"] }) {
  const theme = useChartTheme();
  const folds = Object.entries(attribution);
  if (!folds.length) return null;
  return (
    <Card title="Where do unknowns go?" subtitle={`Held-out flows: flagged unknown vs misattributed to a known family vs missed as benign`} icon={Layers}>
      <div className="stack">
        {folds.map(([fold, d]) => (
          <div key={fold} className="stack-sm">
            <div className="row-between small">
              <strong>{fold}</strong>
              <span className="muted">
                family acc. {formatPct(d.known_family_accuracy?.mean, 1)} · open-set macro-F1 {d.openset_macro_f1?.mean?.toFixed(3) ?? "—"}
              </span>
            </div>
            <StackBar
              ariaLabel={`Fate of held-out ${fold} flows`}
              total={1}
              valueFormatter={(v) => formatPct(v, 1)}
              segments={[
                { label: "Flagged unknown", value: d.unknown_flagged_as_unknown?.mean ?? 0, color: theme.series[6] },
                { label: "Misattributed", value: d.unknown_misattributed_to_known?.mean ?? 0, color: theme.series[3] },
                { label: "Missed as benign", value: d.unknown_missed_as_benign?.mean ?? 0, color: theme.axis },
              ]}
            />
          </div>
        ))}
      </div>
    </Card>
  );
}

function ProtocolView({ protocol, block, overview }: { protocol: ProtocolKey; block: ProtocolBlock | null; overview: ResearchOverview }) {
  const theme = useChartTheme();
  const P = PROTOCOLS[protocol];
  if (!block) return <NotGenerated protocol={protocol} />;
  const proposed = overview.proposed;
  const baselineRow = block.methods.find((m) => m.method === overview.baseline);
  const proposedRow = block.methods.find((m) => m.method === proposed);
  const nDone = proposedRow?.zero_day_recall?.n ?? 0;
  const seeds = block.meta.seeds ?? [];
  const alpha = block.meta.alpha ?? 0.01;
  const methodsOrder = block.methods.map((m) => m.method);
  const folds = block.folds.map((f) => f.fold);

  const columns: Column<ResearchMethodRow>[] = [
    {
      key: "method",
      header: "Method",
      sortable: true,
      cell: (r) => (
        <span className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
          <span className="legend-swatch" style={{ background: groupColor(theme, r.group) }} aria-hidden />
          <span style={{ fontWeight: r.group === "proposed" ? 650 : undefined }}>{r.method}</span>
        </span>
      ),
    },
    { key: "group", header: "Group", sortable: true, cell: (r) => <Badge tone={r.group === "proposed" ? "novel" : r.group === "ablation" ? "info" : "neutral"} size="sm">{GROUP_LABEL[r.group] ?? r.group}</Badge> },
    {
      key: "evidence",
      header: "Evidence · fusion",
      accessor: (r) => r.evidence.join(" "),
      cell: (r) => (
        <span className="small text-2">
          {r.evidence.map((e) => EVIDENCE_TEXT[e] ?? e).join(" + ")}
          {r.evidence.length > 1 && r.fusion ? ` · ${r.fusion}` : ""}
        </span>
      ),
    },
    { key: "zdr", header: "Zero-day recall @α", sortable: true, align: "right", accessor: (r) => r.zero_day_recall?.mean ?? -1, cell: (r) => <span className="mono">{formatCI(r.zero_day_recall)}</span> },
    { key: "zdr001", header: "@0.1%", sortable: true, align: "right", accessor: (r) => r.zero_day_recall_at_0_001?.mean ?? -1, cell: (r) => <span className="mono">{formatPct(r.zero_day_recall_at_0_001?.mean, 1)}</span> },
    { key: "zdr05", header: "@5%", sortable: true, align: "right", accessor: (r) => r.zero_day_recall_at_0_05?.mean ?? -1, cell: (r) => <span className="mono">{formatPct(r.zero_day_recall_at_0_05?.mean, 1)}</span> },
    { key: "auroc", header: "AUROC", sortable: true, align: "right", accessor: (r) => r.auroc_unknown?.mean ?? -1, cell: (r) => <span className="mono">{r.auroc_unknown?.mean?.toFixed(3) ?? "—"}</span> },
    { key: "auprc", header: "AUPRC", sortable: true, align: "right", accessor: (r) => r.auprc_unknown?.mean ?? -1, cell: (r) => <span className="mono">{r.auprc_unknown?.mean?.toFixed(3) ?? "—"}</span> },
    { key: "known", header: "Known recall", sortable: true, align: "right", accessor: (r) => r.known_recall?.mean ?? -1, cell: (r) => <span className="mono">{formatPct(r.known_recall?.mean, 2)}</span> },
    { key: "fpr", header: "Benign FPR", sortable: true, align: "right", accessor: (r) => r.fpr?.mean ?? -1, cell: (r) => <span className="mono">{formatPct(r.fpr?.mean, 2)}</span> },
  ];

  const heatRows = methodsOrder;
  const heatValues = heatRows.map((m) => block.folds.map((f) => f.methods[m]?.zero_day_recall?.mean ?? 0));
  const perFamilyFams = Object.keys(block.per_family);
  const showPerFamily = protocol !== "loafo" && perFamilyFams.length > 0;

  return (
    <div className="stack">
      <Callout tone="neutral" icon={P.icon} title={P.question}>
        {seeds.length ? `Seeds ${seeds.join(", ")}` : "Seeds —"} · α = {formatPct(alpha, 1)} · {folds.length} folds · completed runs per cell: n = {nDone}
        {seeds.length ? ` of ${seeds.length}` : ""} · generated {formatDateTime(block.meta.generated_at)}
        {block.meta.git_commit ? ` · commit ${block.meta.git_commit}` : ""}
      </Callout>

      <Card title="Zero-day recall by method" subtitle={`Mean across folds and seeds at α = ${formatPct(alpha, 1)}`} icon={BarChart3}>
        <RangeChart
          ariaLabel="Zero-day recall with confidence intervals per method"
          items={block.methods.map((m) => ({
            label: m.method,
            mean: m.zero_day_recall?.mean ?? 0,
            low: m.zero_day_recall?.low,
            high: m.zero_day_recall?.high,
            group: m.group,
            color: groupColor(theme, m.group),
            emphasize: m.group === "proposed",
          }))}
          groupLabels={GROUP_LABEL}
          reference={baselineRow?.zero_day_recall ? { value: baselineRow.zero_day_recall.mean, label: `${overview.baseline} mean` } : undefined}
        />
      </Card>

      <Card title="All metrics" subtitle="Mean [95% CI across seeds]; single-seed cells show (n=1)" icon={ListChecks}>
        <DataTable data={block.methods} columns={columns} rowKey={(r) => r.method} pageSize={0} dense caption={`${P.title} method comparison`} />
      </Card>

      {folds.length > 0 && (
        <Card title={protocol === "loafo" ? "Held-out family × method" : "Fold × method"} subtitle="Zero-day recall per fold (linear colour scale 0–100%)" icon={Grid3x3}>
          <Heatmap
            ariaLabel="Zero-day recall per fold and method"
            rows={heatRows}
            cols={folds}
            values={heatValues}
            scale="linear"
            domain={[0, 1]}
            minCellWidth={64}
            rowAxisLabel="Method"
            colAxisLabel={protocol === "loafo" ? "Held-out family" : "Fold"}
            valueFormatter={(v) => `${Math.round(v * 100)}%`}
          />
        </Card>
      )}

      {showPerFamily && (
        <Card title="Per-family zero-day recall" subtitle="Unknown-family recall by method" icon={Grid3x3}>
          <Heatmap
            ariaLabel="Per-family zero-day recall per method"
            rows={methodsOrder.filter((m) => perFamilyFams.some((f) => block.per_family[f]?.[m]))}
            cols={perFamilyFams}
            values={methodsOrder
              .filter((m) => perFamilyFams.some((f) => block.per_family[f]?.[m]))
              .map((m) => perFamilyFams.map((f) => block.per_family[f]?.[m]?.mean ?? 0))}
            scale="linear"
            domain={[0, 1]}
            minCellWidth={64}
            valueFormatter={(v) => `${Math.round(v * 100)}%`}
          />
        </Card>
      )}

      {block.adaptation.length > 0 && <AdaptationCharts rows={block.adaptation} block={block} proposed={proposed} alpha={alpha} />}

      {block.significance.length > 0 && (
        <Card
          title="Paired significance"
          subtitle={`${proposed} vs each method. Folds are averaged within each seed and compared with a paired t-test over independent seeds; fold-level win counts are shown for context only, because folds of one seed share a data split.`}
          icon={Sigma}
        >
          <SignificanceTable rows={block.significance} />
        </Card>
      )}

      <AttributionView attribution={block.attribution} />
    </div>
  );
}

/* ------------------------------------------------------------------ generic JSON (frozen v1.1 on 2018) */

function GenericValue({ value, depth = 0 }: { value: unknown; depth?: number }): ReactNode {
  if (value == null) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
  if (typeof value !== "object") return String(value);
  if (Array.isArray(value)) return value.every((v) => typeof v !== "object") ? value.join(", ") : `${value.length} items`;
  if (depth >= 2) return `${Object.keys(value).length} fields`;
  return (
    <dl className="kv" style={{ textAlign: "left" }}>
      {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
        <div key={k} style={{ display: "contents" }}>
          <dt>{humanize(k)}</dt>
          <dd>
            <GenericValue value={v} depth={depth + 1} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

/* ------------------------------------------------------------------ page */

export function ResearchLabPage() {
  const [data, setData] = useState<ResearchOverview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [tab, setTab] = useState<TabId>("overview");

  const load = useCallback(() => {
    setError(null);
    api
      .researchOverview()
      .then(setData)
      .catch(setError);
  }, []);
  useEffect(load, [load]);

  const tabs = useMemo(
    () => [
      { id: "overview" as TabId, label: "Overview", icon: Lightbulb },
      ...(Object.keys(PROTOCOLS) as ProtocolKey[]).map((p) => ({
        id: p as TabId,
        label: PROTOCOLS[p].short,
        icon: PROTOCOLS[p].icon,
        count: data && !data.status[p] ? undefined : data?.[p]?.methods.length,
      })),
      { id: "gate" as TabId, label: "Zero-Day Gate", icon: Radar },
    ],
    [data]
  );

  const seedsInfo = (() => {
    if (!data) return null;
    const block = data.loafo ?? data.temporal ?? data.cross;
    if (!block) return null;
    const n = block.methods.find((m) => m.method === data.proposed)?.zero_day_recall?.n ?? 0;
    return { seeds: block.meta.seeds ?? [], n };
  })();

  return (
    <div className="page">
      <PageHeader
        eyebrow="Zero-Day Research"
        icon={FlaskConical}
        title="Research Lab"
        subtitle="Open-set evaluation of Aegis-OSR against closed-set and anomaly-detection baselines across three protocols."
        actions={
          <>
            <Link className="btn btn-secondary" to="/research">
              <BookOpenCheck size={16} aria-hidden /> Baseline study (v1.1)
            </Link>
            <Link className="btn btn-primary" to="/zero-day">
              <Radar size={16} aria-hidden /> Zero-Day Lab
            </Link>
          </>
        }
      />

      {error ? <ErrorState error={error} title="Could not load research results" onRetry={load} /> : null}

      <Callout tone="warn" icon={Scale} title="Honest reporting">
        The design (fusion rule, novelty source) was selected on pilot seed 0 only; reported results use held-out seeds{" "}
        {seedsInfo?.seeds.length ? seedsInfo.seeds.join(", ") : "1–5"}
        {seedsInfo ? ` — ${seedsInfo.n} of ${seedsInfo.seeds.length || 5} completed so far` : ""}. Intervals are 95% CIs across seeds and
        collapse to a point while n = 1.
      </Callout>

      <Tabs id="research-lab" label="Research protocols" items={tabs} value={tab} onChange={setTab} />

      {!data && !error ? (
        <div className="grid grid-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : null}

      {data && (
        <>
          <TabPanel tabsId="research-lab" value="overview" active={tab} className="stack">
            <div className="row" style={{ gap: 6 }}>
              {(Object.keys(PROTOCOLS) as ProtocolKey[]).map((p) => (
                <Badge key={p} tone={data.status[p] ? "ok" : "neutral"} dot>
                  {PROTOCOLS[p].title}: {data.status[p] ? "generated" : "pending"}
                </Badge>
              ))}
              <Badge tone={data.status.gate ? "ok" : "neutral"} dot>
                Gate report: {data.status.gate ? "ready" : "pending"}
              </Badge>
            </div>
            {Object.keys(data.headline).length === 0 ? (
              <EmptyState icon={FlaskConical} title="No protocol results yet" description={<>Run <code>scripts/50_openset_experiments.py</code>.</>} />
            ) : (
              <div className="grid grid-2">
                {(Object.keys(PROTOCOLS) as ProtocolKey[]).map((p) =>
                  data.headline[p] ? <HeadlineCard key={p} protocol={p} h={data.headline[p]!} proposed={data.proposed} baseline={data.baseline} /> : null
                )}
              </div>
            )}
            <div className="grid grid-3">
              {(Object.keys(PROTOCOLS) as ProtocolKey[])
                .filter((p) => !data.headline[p])
                .map((p) => (
                  <div key={p} className="info-tile">
                    <span className="row" style={{ gap: 8 }}>
                      {(() => {
                        const Icon = PROTOCOLS[p].icon;
                        return <Icon size={16} aria-hidden style={{ color: "var(--muted)" }} />;
                      })()}
                      <strong>{PROTOCOLS[p].title}</strong>
                      <Badge tone="neutral" size="sm">
                        pending
                      </Badge>
                    </span>
                    <p>{PROTOCOLS[p].question}</p>
                    <code className="small">--protocol {PROTOCOLS[p].script}</code>
                  </div>
                ))}
            </div>
            <Card title="Methods compared" subtitle="Every method shares the same conformal calibration, so differences come from evidence and fusion" icon={GitCompareArrows}>
              <DataTable
                data={data.methods_catalog}
                rowKey={(r) => r.method}
                pageSize={0}
                dense
                caption="Methods catalog"
                columns={[
                  { key: "method", header: "Method", sortable: true, cell: (r) => <strong style={{ fontWeight: r.group === "proposed" ? 650 : 500 }}>{r.method}</strong> },
                  { key: "group", header: "Group", sortable: true, cell: (r) => <Badge tone={r.group === "proposed" ? "novel" : r.group === "ablation" ? "info" : "neutral"} size="sm">{GROUP_LABEL[r.group] ?? r.group}</Badge> },
                  { key: "evidence", header: "Evidence", accessor: (r) => r.evidence.join(" "), cell: (r) => r.evidence.map((e) => EVIDENCE_TEXT[e] ?? e).join(" + ") },
                  { key: "fusion", header: "Fusion", cell: (r) => (r.evidence.length > 1 ? humanize(r.fusion) : "—") },
                ]}
              />
            </Card>
            {data.frozen_v11_on_cic2018 && (
              <Card title="Frozen v1.1 on CSE-CIC-IDS2018" subtitle="How the deployed closed-set model transfers to a different network" icon={Globe2}>
                <GenericValue value={data.frozen_v11_on_cic2018} />
              </Card>
            )}
          </TabPanel>

          {(Object.keys(PROTOCOLS) as ProtocolKey[]).map((p) => (
            <TabPanel key={p} tabsId="research-lab" value={p} active={tab}>
              <ProtocolView protocol={p} block={data[p]} overview={data} />
            </TabPanel>
          ))}

          <TabPanel tabsId="research-lab" value="gate" active={tab} className="stack">
            {data.gate ? (
              <Card
                title={String(data.gate.name ?? "Aegis-OSR Zero-Day Gate")}
                subtitle={`Trained ${formatDateTime(data.gate.trained_at)} · commit ${data.gate.git_commit ?? "—"}`}
                icon={Sparkles}
                actions={
                  <Link className="btn btn-primary btn-sm" to="/zero-day">
                    Open Zero-Day Lab <ArrowRight size={14} aria-hidden />
                  </Link>
                }
              >
                <div className="grid grid-2">
                  <dl className="kv">
                    <dt>Benign FPR (α = 1%)</dt>
                    <dd>{formatPct(data.gate.evaluation?.gate?.benign_fpr, 2)}</dd>
                    <dt>Known-attack recall</dt>
                    <dd>{formatPct(data.gate.evaluation?.gate?.known_attack_recall, 2)}</dd>
                    <dt>Unseen-attack alert rate</dt>
                    <dd>{formatPct(data.gate.evaluation?.gate?.natural_unknown_alert_rate, 1)}</dd>
                    <dt>Served vs research parity</dt>
                    <dd>{formatPct(data.gate.evaluation?.gate?.served_vs_research_parity, 3)}</dd>
                  </dl>
                  <dl className="kv">
                    <dt>Frozen v1.1 benign FPR</dt>
                    <dd>{formatPct(data.gate.evaluation?.frozen_v11?.benign_fpr, 3)}</dd>
                    <dt>Frozen v1.1 known recall</dt>
                    <dd>{formatPct(data.gate.evaluation?.frozen_v11?.known_attack_recall, 2)}</dd>
                    <dt>Frozen v1.1 unseen-attack rate</dt>
                    <dd>{formatPct(data.gate.evaluation?.frozen_v11?.natural_unknown_attack_rate, 1)}</dd>
                    <dt>Advisory only</dt>
                    <dd>{data.gate.advisory_only === false ? "no" : "yes"}</dd>
                  </dl>
                </div>
                {data.gate.evaluation?.note && (
                  <p className="muted small" style={{ marginTop: 12 }}>
                    {data.gate.evaluation.note}
                  </p>
                )}
              </Card>
            ) : (
              <EmptyState
                icon={Radar}
                title="Gate report not generated yet"
                description={<>Run <code>python scripts/51_train_zero_day_gate.py</code>.</>}
                action={
                  <Link className="btn btn-secondary" to="/zero-day">
                    Open Zero-Day Lab
                  </Link>
                }
              />
            )}
          </TabPanel>
        </>
      )}
    </div>
  );
}
