import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BrainCircuit,
  Combine,
  Crosshair,
  FlaskConical,
  Gauge as GaugeIcon,
  Loader2,
  Network,
  Radar,
  Radio,
  Scale,
  ScanSearch,
  ShieldCheck,
  ShieldQuestion,
  Sigma,
  Sparkles,
  Timer,
  Wand2,
} from "lucide-react";
import {
  api,
  GATE_UNKNOWN_ATTACK,
  GATE_ZERO_DAY,
  type FeatureVector,
  type NaturalUnknownRow,
  type PredictResult,
  type ZeroDayResult,
  type ZeroDayStatus,
} from "../services/api";
import { Badge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { SkeletonCard, SkeletonText } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { CurveChart, GroupedBars, TimeSeriesArea, attackColor, useChartTheme } from "../components/charts";
import { GateLabelBadge, GateVerdictPanel } from "../components/zeroday/GateVisuals";
import { formatCompact, formatDateTime, formatNumber, formatPct } from "../lib/format";

/** Families the demo-flow endpoint actually serves (it silently falls back for others). */
const DEMO_FAMILIES = ["BENIGN", "DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot"];

const ALPHA_MIN = 0.0005;
const ALPHA_MAX = 0.05;
const sliderToAlpha = (t: number) => {
  const a = 10 ** (Math.log10(ALPHA_MIN) + (t / 100) * (Math.log10(ALPHA_MAX) - Math.log10(ALPHA_MIN)));
  return Number(a.toPrecision(2));
};
const alphaToSlider = (a: number) =>
  ((Math.log10(a) - Math.log10(ALPHA_MIN)) / (Math.log10(ALPHA_MAX) - Math.log10(ALPHA_MIN))) * 100;

const LABELS = [
  { label: "BENIGN", text: "p > α: the flow is consistent with benign traffic. No alert." },
  { label: "DDoS", text: "Alert, attack-like and conforms to a known family (Mondrian conformity p > α_family)." },
  { label: GATE_UNKNOWN_ATTACK, text: "Alert, the classifier says attack, but the flow does not conform to any known family." },
  { label: GATE_ZERO_DAY, text: "Alert driven by novelty: unlike benign traffic and not recognized as a known attack." },
];

function MethodCard({ icon: Icon, title, text }: { icon: typeof Sigma; title: string; text?: string }) {
  return (
    <div className="info-tile">
      <span className="row" style={{ gap: 8 }}>
        <Icon size={16} aria-hidden style={{ color: "var(--accent)" }} />
        <strong>{title}</strong>
      </span>
      <p>{text ?? "—"}</p>
    </div>
  );
}

function Pipeline() {
  const Arrow = () => (
    <span className="pipeline-arrow" aria-hidden>
      <ArrowRight size={18} />
    </span>
  );
  return (
    <div className="pipeline" role="img" aria-label="Gate pipeline: flow features feed classifier and novelty evidence, which are fused with Fisher's method, converted to a conformal p-value, compared with alpha, and labelled.">
      <div className="pipeline-node">
        <strong>Flow features</strong>
        <span>77 CICIDS2017 flow statistics, signed-log scaled</span>
      </div>
      <Arrow />
      <div className="pipeline-col">
        <div className="pipeline-node">
          <strong>Classifier evidence</strong>
          <span>XGBoost (benign + 6 families) → benign surprisal of P(attack)</span>
        </div>
        <div className="pipeline-node">
          <strong>Novelty evidence</strong>
          <span>Mean distance to k=5 benign neighbours → benign surprisal</span>
        </div>
      </div>
      <Arrow />
      <div className="pipeline-node" data-accent="true">
        <strong>Fisher fusion</strong>
        <span>Sum of surprisals — evidence accumulates across sources</span>
      </div>
      <Arrow />
      <div className="pipeline-node" data-accent="true">
        <strong>Conformal p-value</strong>
        <span>Calibrated on held-out benign flows → P(false alarm) ≤ α</span>
      </div>
      <Arrow />
      <div className="pipeline-node">
        <strong>Label</strong>
        <span>Benign · known family · unknown attack · zero-day anomaly</span>
      </div>
    </div>
  );
}

export function ZeroDayLabPage() {
  const theme = useChartTheme();
  const [status, setStatus] = useState<ZeroDayStatus | null>(null);
  const [statusError, setStatusError] = useState<unknown>(null);
  const [family, setFamily] = useState("DDoS");
  const [flow, setFlow] = useState<{ features: FeatureVector; label: string | null } | null>(null);
  const [frozen, setFrozen] = useState<PredictResult | null>(null);
  const [assessment, setAssessment] = useState<ZeroDayResult | null>(null);
  const [alpha, setAlpha] = useState(0.01);
  const [busy, setBusy] = useState<null | "load" | "assess">(null);
  const [tryError, setTryError] = useState<unknown>(null);
  const debounce = useRef<number | undefined>(undefined);

  const loadStatus = useCallback(() => {
    setStatusError(null);
    api
      .zeroDayStatus()
      .then((s) => {
        setStatus(s);
        if (s.alpha) setAlpha(s.alpha);
      })
      .catch(setStatusError);
  }, []);
  useEffect(loadStatus, [loadStatus]);
  useEffect(() => () => window.clearTimeout(debounce.current), []);

  const assess = useCallback(async (features: FeatureVector, a: number) => {
    setBusy("assess");
    try {
      const out = await api.zeroDayAssess([features], { alpha: a, explain_top: 8 });
      setAssessment(out.results[0] ?? null);
      setTryError(null);
    } catch (e) {
      setTryError(e);
    } finally {
      setBusy(null);
    }
  }, []);

  async function loadFlow() {
    setBusy("load");
    setTryError(null);
    setAssessment(null);
    setFrozen(null);
    try {
      const demo = await api.demoFlow(family);
      setFlow(demo);
      // Frozen verdict via the non-persisting batch endpoint (no incident is written).
      const batch = await api.predictBatch([demo.features], false).catch(() => null);
      setFrozen(batch?.results[0] ?? null);
      await assess(demo.features, alpha);
    } catch (e) {
      setTryError(e);
      setBusy(null);
    }
  }

  function changeAlpha(a: number) {
    setAlpha(a);
    if (!flow) return;
    window.clearTimeout(debounce.current);
    debounce.current = window.setTimeout(() => void assess(flow.features, a), 250);
  }

  const ev = status?.evaluation;
  const ops = ev?.operating_points ?? [];
  const frozenFpr = ev?.frozen_v11_operating_point?.benign_fpr ?? ev?.frozen_v11?.benign_fpr;
  const perFamily = Object.entries(ev?.per_family_recall ?? {}).map(([fam, v]) => ({ family: fam, gate: v.gate * 100, frozen: v.frozen_v11 * 100 }));
  const opRates = ops.map((o) => ({
    alpha: String(o.alpha),
    known: o.known_attack_recall * 100,
    unseen: o.natural_unknown_alert_rate * 100,
  }));

  const nuColumns: Column<NaturalUnknownRow>[] = [
    { key: "family", header: "Unseen family", sortable: true, cell: (r) => <strong>{r.family}</strong> },
    { key: "n", header: "n", sortable: true, align: "right", cell: (r) => <span className="mono">{r.n}</span> },
    {
      key: "frozen_v11_attack_rate",
      header: "Frozen v1.1 alerts",
      sortable: true,
      align: "right",
      cell: (r) => <span className="mono">{formatPct(r.frozen_v11_attack_rate, 0)}</span>,
    },
    {
      key: "frozen_labels",
      header: "Frozen labels",
      accessor: (r) => Object.keys(r.frozen_v11_labels).join(" "),
      cell: (r) => (
        <span className="row" style={{ gap: 4 }}>
          {Object.entries(r.frozen_v11_labels).map(([l, n]) => (
            <Badge key={l} tone="neutral" size="sm">
              {l} × {n}
            </Badge>
          ))}
        </span>
      ),
    },
    {
      key: "gate_alert_rate",
      header: "Gate alerts",
      sortable: true,
      align: "right",
      cell: (r) => (
        <strong className="mono" style={{ color: "var(--chart-7)" }}>
          {formatPct(r.gate_alert_rate, 0)}
        </strong>
      ),
    },
    {
      key: "gate_labels",
      header: "Gate labels",
      accessor: (r) => Object.keys(r.gate_labels).join(" "),
      cell: (r) => (
        <span className="row" style={{ gap: 4 }}>
          {Object.entries(r.gate_labels).map(([l, n]) => (
            <span key={l} className="row" style={{ gap: 2 }}>
              <GateLabelBadge label={l} size="sm" />
              <span className="mono small">× {n}</span>
            </span>
          ))}
        </span>
      ),
    },
  ];

  const unavailable = status && !status.available;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Zero-Day Research"
        icon={Radar}
        title="Zero-Day Lab"
        subtitle="Aegis-OSR is an open-set detector that flags traffic the frozen closed-set model cannot recognize, with a calibrated false-alarm guarantee."
        actions={
          <Link className="btn btn-primary" to="/live">
            <Radio size={16} aria-hidden /> Watch it live
          </Link>
        }
      />

      {statusError ? <ErrorState error={statusError} title="Could not load gate status" onRetry={loadStatus} /> : null}
      {unavailable && (
        <Callout tone="warn" title="Zero-Day Gate unavailable">
          {status.reason ?? "Gate artifacts are missing."}
        </Callout>
      )}

      <Card title="How the gate decides" subtitle="Conformal evidence fusion — one p-value per flow, compared with a false-alarm budget α" icon={Combine}>
        <div className="stack">
          <Pipeline />
          <div className="grid grid-2">
            {LABELS.map((l) => (
              <div key={l.label} className="row" style={{ alignItems: "flex-start", gap: 10, flexWrap: "nowrap" }}>
                <span style={{ flexShrink: 0 }}>
                  <GateLabelBadge label={l.label} size="sm" />
                </span>
                <span className="small text-2">{l.text}</span>
              </div>
            ))}
          </div>
          <Callout tone="info" icon={ShieldCheck} title="Advisory by design">
            The gate runs beside the frozen v1.1 model (Decision Tree @ 0.85 + attack-only Random Forest) and never changes its verdict.
            Guarantee: on benign traffic like the calibration set, P(alert) ≤ α.
          </Callout>
        </div>
      </Card>

      {!status && !statusError ? (
        <div className="grid grid-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : null}

      {status?.available && (
        <>
          <div className="grid grid-stats">
            <StatTile label="Budget α" icon={Scale} value={status.alpha ?? "—"} hint={`family α ${status.alpha_family ?? "—"}`} />
            <StatTile
              label="Benign FPR"
              icon={ShieldCheck}
              value={formatPct(ev?.gate?.benign_fpr, 2)}
              hint={`frozen v1.1 ${formatPct(ev?.frozen_v11?.benign_fpr, 3)}`}
            />
            <StatTile
              label="Known recall"
              icon={Crosshair}
              value={formatPct(ev?.gate?.known_attack_recall, 2)}
              hint={`frozen v1.1 ${formatPct(ev?.frozen_v11?.known_attack_recall, 2)}`}
            />
            <StatTile
              label="Unseen alerts"
              icon={Sparkles}
              tone="var(--chart-7)"
              value={formatPct(ev?.gate?.natural_unknown_alert_rate, 0)}
              hint={`frozen v1.1 ${formatPct(ev?.frozen_v11?.natural_unknown_attack_rate, 0)}`}
            />
            <StatTile label="Family accuracy" icon={ShieldQuestion} value={formatPct(ev?.gate?.known_family_accuracy, 1)} hint="on known attacks" />
            <StatTile
              label="Latency"
              icon={Timer}
              value={`${formatNumber(ev?.gate?.latency_ms_per_flow_batch, 3)} ms`}
              hint={`per flow (batched) · parity ${formatPct(ev?.gate?.served_vs_research_parity, 2)}`}
            />
          </div>

          <Card title="Method" subtitle={`Trained ${formatDateTime(status.trained_at)} · commit ${status.git_commit ?? "—"}`} icon={BrainCircuit}>
            <div className="grid grid-3">
              <MethodCard icon={BrainCircuit} title="Classifier" text={status.method?.classifier} />
              <MethodCard icon={Network} title="Novelty" text={status.method?.novelty} />
              <MethodCard icon={Sigma} title="Fusion" text={status.method?.fusion} />
              <MethodCard icon={Scale} title="Calibration" text={status.method?.calibration} />
              <MethodCard icon={Crosshair} title="Family attribution" text={status.method?.attribution} />
              <div className="info-tile">
                <strong>Footprint</strong>
                <p>
                  {status.n_features ?? "—"} features · {formatCompact(status.knn_reference_size)} benign kNN references ·{" "}
                  {formatCompact(status.calibration_size)} calibration flows · trained on {formatCompact(status.training?.n_train)} flows
                </p>
              </div>
            </div>
          </Card>
        </>
      )}

      <Card
        title="Try a flow"
        subtitle="Load a held-out demo flow, then move α to see how the decision and guarantee trade off."
        icon={FlaskConical}
        actions={flow?.label ? <Badge tone="accent">Ground truth: {flow.label}</Badge> : null}
      >
        <div className="stack">
          <div className="row" style={{ alignItems: "flex-end", gap: 14 }}>
            <div className="field" style={{ width: 200 }}>
              <label className="field-label" htmlFor="zd-family">
                Demo flow family
              </label>
              <select id="zd-family" className="select" value={family} onChange={(e) => setFamily(e.target.value)}>
                {DEMO_FAMILIES.map((f) => (
                  <option key={f} value={f}>
                    {f === "BENIGN" ? "Benign" : f}
                  </option>
                ))}
              </select>
            </div>
            <button type="button" className="btn btn-primary" onClick={() => void loadFlow()} disabled={busy !== null || unavailable === true}>
              {busy === "load" ? <Loader2 size={16} className="spin" aria-hidden /> : <Wand2 size={16} aria-hidden />}
              Load & assess
            </button>
            <label className="field" style={{ flex: "1 1 240px", maxWidth: 380 }}>
              <span className="field-label row-between">
                <span>False-alarm budget α (log scale)</span>
                <span className="mono">{alpha}</span>
              </span>
              <input
                className="range-slider"
                type="range"
                min={0}
                max={100}
                step={1}
                value={Math.round(alphaToSlider(alpha))}
                onChange={(e) => changeAlpha(sliderToAlpha(Number(e.target.value)))}
                aria-valuetext={`alpha ${alpha}`}
              />
              <span className="pmeter-scale" aria-hidden>
                <span>{ALPHA_MIN}</span>
                <span>0.005</span>
                <span>{ALPHA_MAX}</span>
              </span>
            </label>
          </div>
          <p className="muted small">
            Unseen families (Infiltration, Heartbleed) are not offered here: the demo-flow endpoint does not serve them. Watch them in the{" "}
            <Link to="/live">Live Traffic Monitor</Link>.
          </p>
          {tryError ? <ErrorState error={tryError} onRetry={() => flow && void assess(flow.features, alpha)} /> : null}

          {!flow && !busy ? (
            <EmptyState icon={ScanSearch} title="No flow loaded" description="Pick a family and press “Load & assess”." />
          ) : busy === "load" && !assessment ? (
            <SkeletonText lines={5} />
          ) : (
            <div className="grid grid-split-rev">
              <Card title="Frozen v1.1 verdict" subtitle="Closed-set — unchanged by the gate" icon={ShieldCheck} as="div">
                {frozen ? (
                  <dl className="kv">
                    <dt>Verdict</dt>
                    <dd>{frozen.is_attack ? frozen.attack_type : "Benign"}</dd>
                    <dt>Confidence</dt>
                    <dd>{formatPct(frozen.confidence, 1)}</dd>
                    <dt>P(attack)</dt>
                    <dd>{formatPct(frozen.binary_proba_attack, 1)}</dd>
                    <dt>Severity</dt>
                    <dd>{frozen.severity}</dd>
                  </dl>
                ) : (
                  <p className="muted small">Not available.</p>
                )}
              </Card>
              <Card
                title="Zero-Day Gate"
                subtitle={busy === "assess" ? "Re-assessing…" : `Decision at α = ${assessment?.alpha ?? alpha}`}
                icon={Sparkles}
                as="div"
              >
                <GateVerdictPanel result={assessment} frozenIsAttack={frozen?.is_attack} alphaFamily={status?.alpha_family} />
              </Card>
            </div>
          )}
        </div>
      </Card>

      {status?.available && ops.length > 0 && (
        <div className="grid grid-3">
          <Card title="False-alarm guarantee" subtitle="Measured benign FPR vs the budget α — points under the diagonal keep the promise" icon={Scale}>
            <CurveChart
              ariaLabel="Benign false-positive rate versus alpha with the y equals x guarantee line and the frozen model's FPR"
              height={260}
              diagonal
              domain={{ x: [0, Math.max(...ops.map((o) => o.alpha))], y: [0, Math.max(...ops.map((o) => o.alpha))] }}
              baselineY={frozenFpr ?? undefined}
              xLabel="α (budget)"
              yLabel="Benign FPR"
              digits={4}
              series={[{ label: "Gate benign FPR", summary: "dashed diagonal = FPR = α", points: ops.map((o) => ({ x: o.alpha, y: o.benign_fpr, meta: `α=${o.alpha}` })), color: theme.series[6] }]}
            />
            <p className="muted small" style={{ marginTop: 6 }}>
              Horizontal dashed line: frozen v1.1 benign FPR ({formatPct(frozenFpr, 3)}) at its 0.85 threshold.
            </p>
          </Card>
          <Card title="What α buys" subtitle="Detection rates across operating points" icon={GaugeIcon}>
            <TimeSeriesArea
              ariaLabel="Known-attack recall and unseen-attack alert rate across alpha"
              data={opRates}
              xKey="alpha"
              variant="line"
              height={260}
              yDomain={[0, 100]}
              yFormatter={(v) => `${Math.round(v)}%`}
              xFormatter={(v) => `α ${v}`}
              series={[
                { key: "known", label: "Known-attack recall", color: theme.series[0] },
                { key: "unseen", label: "Unseen-attack alert rate", color: theme.series[6] },
              ]}
            />
          </Card>
          <Card title="Per-family recall" subtitle={`Gate at α = ${status.alpha} vs frozen v1.1`} icon={Crosshair}>
            {perFamily.length ? (
              <GroupedBars
                ariaLabel="Per-family recall, gate versus frozen model"
                data={perFamily}
                categoryKey="family"
                yDomain={[0, 100]}
                yFormatter={(v) => `${Math.round(v)}%`}
                series={[
                  { key: "frozen", label: "Frozen v1.1", color: theme.series[0] },
                  { key: "gate", label: "Zero-Day Gate", color: theme.series[6] },
                ]}
              />
            ) : (
              <EmptyState compact title="No per-family evaluation" />
            )}
          </Card>
        </div>
      )}

      {status?.available && (
        <Card title="Never-seen families (natural unknowns)" subtitle="Held-out flows of families neither model was trained on" icon={Sparkles}>
          <div className="stack">
            <DataTable data={ev?.natural_unknowns ?? []} columns={nuColumns} rowKey={(r) => r.family} pageSize={0} dense emptyTitle="No natural unknowns evaluated" caption="Natural unknown families" />
            <Callout tone="warn" title="Small samples">
              {ev?.note ??
                "Natural unknowns are tiny; treat rates as illustrative — the research protocols are the statistical evidence."}{" "}
              <Link to="/research-lab">See the Research Lab →</Link>
            </Callout>
          </div>
        </Card>
      )}

      {status?.available && (
        <div className="row small muted" style={{ gap: 6 }}>
          {(status.known_classes ?? []).map((c) => (
            <Badge key={c} tone="neutral" size="sm">
              <span className="legend-swatch" style={{ background: attackColor(theme, c), width: 8, height: 8 }} aria-hidden /> {c}
            </Badge>
          ))}
          <span>known to the gate's classifier</span>
        </div>
      )}
    </div>
  );
}
