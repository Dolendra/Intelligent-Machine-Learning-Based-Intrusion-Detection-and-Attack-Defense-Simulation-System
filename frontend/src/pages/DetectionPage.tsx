import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BrainCircuit,
  Crosshair,
  FileSpreadsheet,
  FlaskConical,
  Layers,
  ListChecks,
  Loader2,
  Network,
  Percent,
  Radar,
  RotateCcw,
  ScanSearch,
  Search,
  Shield,
  Sigma,
  SlidersHorizontal,
  Split,
  Upload,
  Wand2,
  Sparkles,
  Fingerprint,
} from "lucide-react";
import { GateLabelBadge, GateVerdictPanel } from "../components/zeroday/GateVisuals";
import {
  api,
  type BatchPredictResult,
  type CounterfactualResult,
  type ExplainResult,
  type FeatureVector,
  type IngestCapabilities,
  type PredictResult,
  type QueueJob,
} from "../services/api";
import { DecisionTraceTimeline } from "../components/DecisionTrace";
import { Badge, SeverityBadge, StatusBadge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { FileDropzone } from "../components/ui/FileDropzone";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton, SkeletonText } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { useToast } from "../components/ui/Toast";
import { BarList, DonutChart, Gauge, HorizontalBars, StackBar, attackColor, useChartTheme } from "../components/charts";
import { formatNumber, formatPct, formatRisk, humanize } from "../lib/format";
import { normalizeSeverity } from "../lib/severity";

const ATTACK_OPTIONS = ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot", "BENIGN"];
const PREVIEW_COUNT = 12;

type Busy = null | "load" | "detect" | "batch" | "upload";
type FileKind = "csv" | "pcap";
type CsvMode = "direct" | "validated" | "queue";
type PcapMode = "extract" | "queue";

const CSV_MODES: Array<{ id: CsvMode; label: string; help: string }> = [
  { id: "direct", label: "Quick score", help: "Score every row with the frozen models (not persisted)." },
  { id: "validated", label: "Schema-validated", help: "Validate columns against the training schema, then score." },
  { id: "queue", label: "Background job", help: "Submit to the in-process ingestion queue and track the job." },
];
const PCAP_MODES: Array<{ id: PcapMode; label: string; help: string }> = [
  { id: "extract", label: "Extract & score", help: "Offline PCAP → flow extraction → detection (requires the extractor)." },
  { id: "queue", label: "Background job", help: "PCAP → extract → same detection queue as CSV." },
];

function FeatureField({
  name,
  original,
  draft,
  onChange,
}: {
  name: string;
  original: number;
  draft: string | undefined;
  onChange: (v: string | undefined) => void;
}) {
  const id = `feat-${name.replace(/[^a-z0-9]+/gi, "-")}`;
  const edited = draft !== undefined && Number(draft) !== original;
  return (
    <div className="field feature-input" data-edited={edited || undefined}>
      <label className="field-label" htmlFor={id} title={name}>
        {name}
      </label>
      <input
        id={id}
        className="input input-sm mono"
        inputMode="decimal"
        value={draft ?? String(original)}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => {
          if (e.target.value.trim() === "" || Number(e.target.value) === original) onChange(undefined);
        }}
        aria-invalid={draft !== undefined && Number.isNaN(Number(draft))}
      />
    </div>
  );
}

export function DetectionPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const theme = useChartTheme();

  const [attackHint, setAttackHint] = useState("DDoS");
  const [label, setLabel] = useState<string | null>(null);
  /** true when `label` is a ground-truth family (single sample); false for batch / upload descriptions. */
  const [labelIsTruth, setLabelIsTruth] = useState(true);
  const [sourceRef, setSourceRef] = useState("");
  const [baseFeatures, setBaseFeatures] = useState<FeatureVector | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [featureQuery, setFeatureQuery] = useState("");
  const [showAll, setShowAll] = useState(false);

  const [result, setResult] = useState<PredictResult | null>(null);
  const [batch, setBatch] = useState<BatchPredictResult | null>(null);
  const [explain, setExplain] = useState<ExplainResult | null>(null);
  const [lime, setLime] = useState<ExplainResult | null>(null);
  const [xaiTab, setXaiTab] = useState<"shap" | "lime">("shap");
  const [xaiLoading, setXaiLoading] = useState(false);
  const [counterfactual, setCounterfactual] = useState<CounterfactualResult | null>(null);

  const [busy, setBusy] = useState<Busy>(null);
  const [error, setError] = useState<unknown>(null);
  const [ingestInfo, setIngestInfo] = useState<IngestCapabilities | null>(null);
  const [queueJob, setQueueJob] = useState<QueueJob | null>(null);
  const [fileKind, setFileKind] = useState<FileKind>("csv");
  const [csvMode, setCsvMode] = useState<CsvMode>("direct");
  const [pcapMode, setPcapMode] = useState<PcapMode>("extract");

  useEffect(() => {
    api.ingestCapabilities().then(setIngestInfo).catch(() => setIngestInfo(null));
  }, []);

  /** Sample features with valid analyst edits applied. */
  const features = useMemo<FeatureVector | null>(() => {
    if (!baseFeatures) return null;
    const out: FeatureVector = { ...baseFeatures };
    for (const [k, v] of Object.entries(drafts)) {
      const n = Number(v);
      if (v.trim() !== "" && Number.isFinite(n)) out[k] = n;
    }
    return out;
  }, [baseFeatures, drafts]);

  const editedCount = useMemo(
    () => Object.entries(drafts).filter(([k, v]) => baseFeatures && v.trim() !== "" && Number(v) !== baseFeatures[k]).length,
    [drafts, baseFeatures]
  );
  const invalidDraft = Object.values(drafts).some((v) => v.trim() !== "" && Number.isNaN(Number(v)));

  const featureNames = useMemo(() => Object.keys(baseFeatures ?? {}), [baseFeatures]);
  const visibleFeatures = useMemo(() => {
    const q = featureQuery.trim().toLowerCase();
    const list = q ? featureNames.filter((f) => f.toLowerCase().includes(q)) : featureNames;
    return showAll || q ? list : list.slice(0, PREVIEW_COUNT);
  }, [featureNames, featureQuery, showAll]);

  function clearResults() {
    setResult(null);
    setExplain(null);
    setLime(null);
    setCounterfactual(null);
  }

  async function loadDemo() {
    setBusy("load");
    setError(null);
    clearResults();
    setBatch(null);
    try {
      const demo = await api.demoFlow(attackHint);
      setBaseFeatures(demo.features);
      setDrafts({});
      setLabel(demo.label);
      setLabelIsTruth(true);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  }

  async function runDetect() {
    if (!features) return;
    setBusy("detect");
    setError(null);
    setBatch(null);
    clearResults();
    try {
      const pred = await api.predict(features, sourceRef.trim() || undefined);
      setResult(pred);
      if (pred.incident_id) toast.success("Incident logged", pred.incident_id);
      if (pred.is_attack) {
        setXaiLoading(true);
        const [ex, lx, cf] = await Promise.all([
          api.explain(features, "shap").catch(() => null),
          api.explain(features, "lime").catch(() => null),
          api.counterfactual(features).catch(() => null),
        ]);
        setExplain(ex);
        setLime(lx);
        setCounterfactual(cf);
        setXaiTab(ex ? "shap" : "lime");
      }
    } catch (e) {
      setError(e);
    } finally {
      setXaiLoading(false);
      setBusy(null);
    }
  }

  async function runBatch() {
    setBusy("batch");
    setError(null);
    clearResults();
    try {
      const demo = await api.demoFlows(attackHint === "BENIGN" ? "BENIGN" : attackHint, 12);
      if (!demo.items.length) throw new Error("No demo flows available — prepare processed data first.");
      const out = await api.predictBatch(
        demo.items.map((i) => i.features),
        false
      );
      setBatch(out);
      setLabel(`${demo.count} sample flows (${attackHint})`);
      setLabelIsTruth(false);
      setBaseFeatures(null);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  }

  async function pollJob(job: QueueJob, prefix: string) {
    setQueueJob(job);
    // poll for up to ~60 s; the job keeps running server-side even if we stop watching
    let finished = false;
    for (let i = 0; i < 400; i++) {
      await new Promise((r) => setTimeout(r, 150));
      const cur = await api.ingestQueueJob(String(job.job_id));
      setQueueJob(cur);
      if (cur.status === "done" || cur.status === "error") {
        const summary = cur.result_summary;
        if (cur.status === "done" && summary) {
          setLabel(`${prefix} ${String(summary.total_flows ?? "?")} flows · ${String(cur.latency_ms ?? "?")} ms`);
          setLabelIsTruth(false);
          toast.success("Queue job finished", `${String(summary.total_flows ?? "?")} flows processed`);
        } else if (cur.status === "error") {
          toast.error("Queue job failed", String(cur.error ?? "See job details"));
        }
        finished = true;
        break;
      }
    }
    if (!finished) {
      toast.error("Still processing", "The job is taking longer than 60 s — it keeps running on the server; check the ingest queue later.");
    }
  }

  async function handleFile(file: File) {
    setBusy("upload");
    setError(null);
    clearResults();
    try {
      if (fileKind === "csv" && csvMode === "direct") {
        const out = await api.predictBatchCsv(file, false);
        setBatch(out);
        setLabel(`CSV upload (${out.total_flows} flows)`);
        setLabelIsTruth(false);
        setBaseFeatures(null);
      } else if (fileKind === "csv" && csvMode === "validated") {
        const out = await api.ingestFlowsCsv(file, true, false);
        if (out.prediction) {
          setBatch(out.prediction);
          setLabel(`Validated ingest (${out.prediction.total_flows} flows)`);
          setLabelIsTruth(false);
          setBaseFeatures(null);
        } else {
          toast.info("File validated", "No prediction was returned for this file.");
        }
      } else if (fileKind === "csv" && csvMode === "queue") {
        setQueueJob(null);
        const submitted = await api.ingestQueueSubmit(file);
        await pollJob(submitted.job, "Queue job");
      } else if (fileKind === "pcap" && pcapMode === "extract") {
        const out = await api.ingestPcap(file, true, false);
        if (out.prediction) {
          setBatch(out.prediction);
          setLabel(`PCAP ingest (${out.prediction.total_flows} flows)`);
          setLabelIsTruth(false);
          setBaseFeatures(null);
        } else {
          setLabel(`PCAP validated (${String(out.flow_count ?? 0)} flows)`);
          setLabelIsTruth(false);
        }
      } else {
        setQueueJob(null);
        const submitted = await api.ingestQueueSubmitPcap(file);
        await pollJob(submitted.job, "PCAP queue");
      }
    } catch (e) {
      setError(e);
      toast.error(e, "Upload failed");
    } finally {
      setBusy(null);
    }
  }

  async function simulate() {
    if (!result) return;
    try {
      const session = result.incident_id
        ? await api.simulateIncident(result.incident_id)
        : await api.startSim(result.attack_type, result.confidence, result.incident_id ?? undefined);
      navigate(`/simulation?session=${encodeURIComponent(session.id)}`);
    } catch (e) {
      toast.error(e, "Could not start simulation");
    }
  }

  const activeExplain = xaiTab === "shap" ? explain : lime;
  const schema = ingestInfo?.schema;
  const pcapStatus = String(ingestInfo?.pcap?.status ?? "unknown");

  const riskSegments = result?.risk_contributions
    ? Object.entries(result.risk_contributions)
        .filter(([, v]) => typeof v === "number")
        .map(([k, v], i) => ({ label: humanize(k), value: Number(v), color: theme.series[i % theme.series.length] }))
    : [];
  const riskFactors = Object.entries(result?.risk_factors ?? {});
  const classProbs = Object.entries(result?.class_probabilities ?? {});

  const batchColumns: Column<BatchPredictResult["results"][number]>[] = [
    { key: "flow_index", header: "#", sortable: true, align: "right", cell: (r) => <span className="mono">{r.flow_index}</span> },
    {
      key: "verdict",
      header: "Verdict",
      sortable: true,
      accessor: (r) => (r.is_attack ? r.attack_type : "BENIGN"),
      cell: (r) => (r.is_attack ? <strong>{r.attack_type}</strong> : <span className="muted">Benign</span>),
    },
    { key: "confidence", header: "Confidence", sortable: true, align: "right", cell: (r) => <span className="mono">{formatPct(r.confidence)}</span> },
    { key: "risk_score", header: "Risk", sortable: true, align: "right", cell: (r) => <span className="mono">{formatRisk(r.risk_score)}</span> },
    {
      key: "severity",
      header: "Severity",
      sortable: true,
      accessor: (r) => ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].indexOf(normalizeSeverity(r.severity)),
      cell: (r) => <SeverityBadge severity={r.severity} size="sm" />,
    },
    {
      key: "band",
      header: "Confidence band",
      accessor: (r) => r.confidence_band_label ?? r.certainty ?? "",
      cell: (r) => <span className="muted small">{r.confidence_band_label ?? humanize(r.certainty)}</span>,
    },
    {
      key: "gate",
      header: "Zero-Day Gate",
      sortable: true,
      accessor: (r) => r.zero_day?.label ?? "",
      cell: (r) => (
        <span className="row" style={{ gap: 4, flexWrap: "nowrap" }}>
          <GateLabelBadge label={r.zero_day?.label} size="sm" />
          {r.zero_day?.novel && !r.is_attack ? (
            <Badge tone="danger" size="sm" title="The gate flagged this flow as novel and the frozen model called it benign">
              frozen missed
            </Badge>
          ) : null}
        </span>
      ),
    },
  ];

  const cfColumns: Column<NonNullable<CounterfactualResult["edits"]>[number]>[] = [
    { key: "feature", header: "Feature", sortable: true },
    {
      key: "edit",
      header: "Edit",
      accessor: (e) => e.original_value,
      cell: (e) => (
        <span className="mono small">
          {formatNumber(e.original_value, 3)} → {formatNumber(e.counterfactual_value, 3)}
        </span>
      ),
    },
    { key: "new_attack_type", header: "New label", sortable: true },
    {
      key: "new_binary_proba_attack",
      header: "P(attack)",
      sortable: true,
      align: "right",
      cell: (e) => <span className="mono">{formatPct(e.new_binary_proba_attack, 1)}</span>,
    },
    {
      key: "flip",
      header: "Outcome",
      accessor: (e) => (e.flipped_to_benign ? 2 : e.family_changed ? 1 : 0),
      sortable: true,
      cell: (e) =>
        e.flipped_to_benign ? (
          <Badge tone="ok" size="sm">
            Flips to benign
          </Badge>
        ) : e.family_changed ? (
          <Badge tone="warn" size="sm">
            Family changes
          </Badge>
        ) : (
          <Badge tone="neutral" size="sm">
            No change
          </Badge>
        ),
    },
  ];

  const csvHelp = CSV_MODES.find((m) => m.id === csvMode)?.help;
  const pcapHelp = PCAP_MODES.find((m) => m.id === pcapMode)?.help;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Operations"
        icon={Radar}
        title="Detection Lab"
        subtitle="Two-stage pipeline: binary detection → attack-family classification → risk scoring → advisory recommendation."
        actions={
          <Link className="btn btn-secondary" to="/models">
            <BrainCircuit size={16} aria-hidden /> Model performance
          </Link>
        }
      />

      {error ? <ErrorState error={error} onRetry={() => setError(null)} /> : null}

      <div className="grid grid-split">
        {/* ---------------------------------------------------------- sample picker + features */}
        <Card
          title="Sample flow"
          subtitle="Pick a CICIDS2017 flow, optionally edit features, then classify."
          icon={FlaskConical}
          actions={label ? <Badge tone="accent" icon={Crosshair}>{labelIsTruth ? `Ground truth: ${label}` : label}</Badge> : null}
        >
          <div className="stack">
            <div className="row" style={{ alignItems: "flex-end" }}>
              <div className="field" style={{ flex: "1 1 180px", maxWidth: 240 }}>
                <label className="field-label" htmlFor="demo-family">
                  Flow family
                </label>
                <select id="demo-family" className="select" value={attackHint} onChange={(e) => setAttackHint(e.target.value)}>
                  {ATTACK_OPTIONS.map((a) => (
                    <option key={a} value={a}>
                      {a === "BENIGN" ? "Benign" : a}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field" style={{ flex: "1 1 160px", maxWidth: 200 }}>
                <label className="field-label" htmlFor="source-ref" title="Detections that share a source are de-duplicated and correlated into a campaign">
                  Source host (optional)
                </label>
                <input
                  id="source-ref"
                  className="input mono"
                  placeholder="e.g. 203.0.113.24"
                  maxLength={128}
                  value={sourceRef}
                  onChange={(e) => setSourceRef(e.target.value)}
                />
              </div>
              <button type="button" className="btn btn-secondary" onClick={() => void loadDemo()} disabled={busy !== null}>
                {busy === "load" ? <Loader2 size={16} className="spin" aria-hidden /> : <Wand2 size={16} aria-hidden />}
                Load sample
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void runDetect()}
                disabled={busy !== null || !features || invalidDraft}
              >
                {busy === "detect" ? <Loader2 size={16} className="spin" aria-hidden /> : <ScanSearch size={16} aria-hidden />}
                {busy === "detect" ? "Detecting…" : "Detect & classify"}
              </button>
            </div>

            {!baseFeatures ? (
              <EmptyState
                icon={SlidersHorizontal}
                title="No flow loaded"
                description="Load a sample to preview and edit its 78 flow features before detection. Each single detection is logged as an incident; give a source host to correlate repeated detections into a campaign. Batch and file scoring is not logged."
              />
            ) : (
              <>
                <div className="row-between">
                  <label className="input-with-icon" style={{ flex: "1 1 220px", maxWidth: 320 }}>
                    <Search size={15} aria-hidden />
                    <span className="sr-only">Filter features</span>
                    <input
                      className="input input-sm"
                      type="search"
                      placeholder={`Filter ${featureNames.length} features…`}
                      value={featureQuery}
                      onChange={(e) => setFeatureQuery(e.target.value)}
                    />
                  </label>
                  <div className="row" style={{ gap: 6 }}>
                    {editedCount > 0 && (
                      <>
                        <Badge tone="warn">{editedCount} edited</Badge>
                        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDrafts({})}>
                          <RotateCcw size={14} aria-hidden /> Reset
                        </button>
                      </>
                    )}
                    {!featureQuery && (
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowAll((s) => !s)} aria-expanded={showAll}>
                        {showAll ? "Show fewer" : `Show all ${featureNames.length}`}
                      </button>
                    )}
                  </div>
                </div>
                <div className="feature-grid" style={showAll || featureQuery ? { maxHeight: 420, overflowY: "auto", paddingRight: 4 } : undefined}>
                  {visibleFeatures.map((f) => (
                    <FeatureField
                      key={f}
                      name={f}
                      original={baseFeatures[f]}
                      draft={drafts[f]}
                      onChange={(v) =>
                        setDrafts((cur) => {
                          const next = { ...cur };
                          if (v === undefined) delete next[f];
                          else next[f] = v;
                          return next;
                        })
                      }
                    />
                  ))}
                  {visibleFeatures.length === 0 && <p className="muted small">No feature matches “{featureQuery}”.</p>}
                </div>
                {invalidDraft && <p className="small" style={{ color: "var(--danger)" }}>Fix non-numeric feature values before detecting.</p>}
              </>
            )}
          </div>
        </Card>

        {/* ---------------------------------------------------------- bulk & file analysis */}
        <Card title="Bulk & file analysis" subtitle="Score many flows at once from demo data, CSV or PCAP." icon={Layers}>
          <div className="stack">
            <button type="button" className="btn btn-secondary" onClick={() => void runBatch()} disabled={busy !== null}>
              {busy === "batch" ? <Loader2 size={16} className="spin" aria-hidden /> : <Sigma size={16} aria-hidden />}
              Score 12 demo flows ({attackHint === "BENIGN" ? "Benign" : attackHint})
            </button>

            <Tabs
              id="file-kind"
              label="File type"
              variant="pill"
              value={fileKind}
              onChange={setFileKind}
              items={[
                { id: "csv", label: "CSV flows", icon: FileSpreadsheet },
                { id: "pcap", label: "PCAP capture", icon: Network },
              ]}
            />
            <TabPanel tabsId="file-kind" value="csv" active={fileKind}>
              <div className="stack-sm">
                <div className="segmented" role="radiogroup" aria-label="CSV processing mode">
                  {CSV_MODES.map((m) => (
                    <button key={m.id} type="button" role="radio" aria-checked={csvMode === m.id} onClick={() => setCsvMode(m.id)}>
                      {m.label}
                    </button>
                  ))}
                </div>
                <p className="muted small">{csvHelp}</p>
                <FileDropzone
                  accept=".csv,text/csv"
                  label="Drop a flow CSV"
                  description={`CICIDS2017 column schema${schema?.feature_count ? ` · ${schema.feature_count} features` : ""}`}
                  icon={FileSpreadsheet}
                  onFile={(f) => void handleFile(f)}
                  busy={busy === "upload"}
                  disabled={busy !== null && busy !== "upload"}
                  buttonLabel="Choose CSV"
                />
              </div>
            </TabPanel>
            <TabPanel tabsId="file-kind" value="pcap" active={fileKind}>
              <div className="stack-sm">
                <div className="segmented" role="radiogroup" aria-label="PCAP processing mode">
                  {PCAP_MODES.map((m) => (
                    <button key={m.id} type="button" role="radio" aria-checked={pcapMode === m.id} onClick={() => setPcapMode(m.id)}>
                      {m.label}
                    </button>
                  ))}
                </div>
                <p className="muted small">{pcapHelp}</p>
                <FileDropzone
                  accept=".pcap,.pcapng,.cap,application/vnd.tcpdump.pcap"
                  label="Drop a packet capture"
                  description=".pcap / .pcapng — offline analysis only, not live capture"
                  icon={Upload}
                  onFile={(f) => void handleFile(f)}
                  busy={busy === "upload"}
                  disabled={busy !== null && busy !== "upload"}
                  buttonLabel="Choose PCAP"
                />
              </div>
            </TabPanel>

            {ingestInfo && (
              <div className="row" style={{ gap: 6 }}>
                <Badge tone="neutral" size="sm">
                  Schema {schema?.schema_version ?? "—"}
                </Badge>
                <Badge tone={ingestInfo.flows_csv?.available ? "ok" : "warn"} size="sm">
                  CSV {ingestInfo.flows_csv?.available ? "ready" : "off"}
                </Badge>
                <Badge tone={pcapStatus === "ready" || pcapStatus === "ok" ? "ok" : "warn"} size="sm">
                  PCAP {humanize(pcapStatus).toLowerCase()}
                </Badge>
                {ingestInfo.pcap?.live_capture === false && (
                  <Badge tone="neutral" size="sm">
                    Offline only
                  </Badge>
                )}
              </div>
            )}

            {queueJob && (
              <div className="callout" aria-live="polite">
                <ListChecks size={18} aria-hidden />
                <div className="grow stack-sm">
                  <div className="row-between">
                    <strong>Ingestion job</strong>
                    <StatusBadge status={queueJob.status} size="sm" />
                  </div>
                  <div className="mono small muted">{queueJob.job_id}</div>
                  {queueJob.status !== "done" && queueJob.status !== "error" ? (
                    <div className="progress" aria-hidden>
                      <span className="progress-indeterminate" />
                    </div>
                  ) : (
                    <div className="small text-2">
                      {queueJob.result_summary?.total_flows != null ? `${queueJob.result_summary.total_flows} flows` : ""}
                      {queueJob.latency_ms != null ? ` · ${queueJob.latency_ms} ms` : ""}
                      {queueJob.error ? ` · ${String(queueJob.error)}` : ""}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* ---------------------------------------------------------- single-flow result */}
      {busy === "detect" && !result && (
        <Card title="Classifying…" icon={ScanSearch}>
          <div className="hero">
            <Skeleton height={180} radius={90} />
            <SkeletonText lines={4} />
          </div>
        </Card>
      )}

      {result && (
        <>
          <div className="grid grid-split">
          <Card
            title="Detection result"
            icon={Shield}
            tone={result.is_attack ? "danger" : "default"}
            actions={
              <>
                {result.incident_id && (
                  <Link className="btn btn-ghost btn-sm" to={`/incidents/${encodeURIComponent(result.incident_id)}`}>
                    Open {result.incident_id}
                  </Link>
                )}
                {result.is_attack && (
                  <button type="button" className="btn btn-warn btn-sm" onClick={() => void simulate()}>
                    <Network size={14} aria-hidden /> Simulate this incident
                  </button>
                )}
              </>
            }
          >
            <div className="hero">
              <Gauge value={result.risk_score} label="Risk score" ariaLabel={`Risk score ${Math.round(result.risk_score)} of 100`} />
              <div className="stack">
                <div>
                  <div className="muted small">Verdict</div>
                  <div className="verdict" data-attack={result.is_attack}>
                    {result.is_attack ? result.attack_type : "Benign traffic"}
                  </div>
                </div>
                <div className="row" style={{ gap: 6 }}>
                  <SeverityBadge severity={result.severity} />
                  {(result.confidence_band_label || result.certainty) && (
                    <Badge tone={(result.confidence_band ?? result.certainty) === "uncertain" ? "warn" : "neutral"}>
                      {result.confidence_band_label ?? humanize(result.certainty)}
                    </Badge>
                  )}
                  {result.deduplicated ? <Badge tone="info">Deduplicated</Badge> : null}
                  {result.campaign_id ? (
                    <Link to={`/campaigns/${encodeURIComponent(result.campaign_id)}`}>
                      <Badge tone="accent">Campaign {result.campaign_id}</Badge>
                    </Link>
                  ) : null}
                </div>
                <div className="grid grid-stats">
                  <StatTile label="Confidence" icon={Percent} value={formatPct(result.confidence)} compact />
                  <StatTile label="P(attack)" icon={Split} value={formatPct(result.binary_proba_attack, 1)} compact />
                  <StatTile
                    label="Threshold"
                    icon={SlidersHorizontal}
                    value={result.threshold ?? "—"}
                    hint={
                      result.uncertainty_lower != null
                        ? `Review band ${result.uncertainty_lower}–${result.uncertainty_upper}`
                        : undefined
                    }
                    compact
                  />
                </div>
                {(result.confidence_band ?? result.certainty) === "uncertain" && (
                  <Callout tone="warn">Prediction falls inside the review band — analyst review recommended.</Callout>
                )}
                {result.threshold_note ? <p className="muted small">{result.threshold_note}</p> : null}
              </div>
            </div>
          </Card>
          <Card
            title="Zero-Day Gate (advisory)"
            subtitle="Open-set check beside the frozen verdict — never changes it"
            icon={Sparkles}
            tone={result.zero_day?.alert && !result.is_attack ? "danger" : "default"}
            actions={
              <Link className="btn btn-ghost btn-sm" to="/zero-day">
                How it works
              </Link>
            }
          >
            <GateVerdictPanel result={result.zero_day} frozenIsAttack={result.is_attack} compact={!result.zero_day?.alert} />
          </Card>
          </div>

          <div className="grid grid-2">
            <Card title="Attack-family probabilities" subtitle="Attack-family classifier output across known families" icon={Crosshair}>
              {classProbs.length ? (
                <BarList
                  ariaLabel="Class probabilities"
                  max={1}
                  valueFormatter={(v) => formatPct(v, 1)}
                  items={classProbs.map(([k, v]) => ({ label: k, value: Number(v), color: attackColor(theme, k) }))}
                />
              ) : (
                <EmptyState compact title="No class probabilities returned" />
              )}
            </Card>

            <Card title="Why this risk?" subtitle={result.risk_why ?? "Additive risk components"} icon={Sigma}>
              <div className="stack">
                {riskSegments.length ? (
                  <StackBar segments={riskSegments} total={100} ariaLabel="Risk score composition out of 100" />
                ) : (
                  <p className="muted small">No component breakdown available.</p>
                )}
                {riskFactors.length > 0 && (
                  <>
                    <h4 className="muted small" style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      Inputs
                    </h4>
                    <dl className="kv">
                      {riskFactors.map(([k, v]) => (
                        <div key={k} style={{ display: "contents" }}>
                          <dt>{humanize(k)}</dt>
                          <dd>{typeof v === "number" ? formatNumber(v, 3) : humanize(v)}</dd>
                        </div>
                      ))}
                    </dl>
                  </>
                )}
              </div>
            </Card>
          </div>

          <div className="grid grid-2">
            <Card
              title="Explainability"
              subtitle="Local feature attributions for this prediction"
              icon={BrainCircuit}
              actions={
                <Tabs
                  id="xai"
                  label="Explanation method"
                  variant="pill"
                  value={xaiTab}
                  onChange={setXaiTab}
                  items={[
                    { id: "shap", label: "SHAP", disabled: !explain },
                    { id: "lime", label: "LIME", disabled: !lime },
                  ]}
                />
              }
            >
              <TabPanel tabsId="xai" value={xaiTab} active={xaiTab}>
                {!result.is_attack ? (
                  <EmptyState compact title="Explanations are generated for attack predictions" />
                ) : xaiLoading ? (
                  <SkeletonText lines={6} />
                ) : activeExplain ? (
                  <div className="stack">
                    <div className="row" style={{ gap: 6 }}>
                      <Badge tone="neutral" size="sm">
                        {(activeExplain.actual_method ?? activeExplain.method ?? xaiTab).toString()}
                      </Badge>
                      {activeExplain.fallback_used ? (
                        <Badge tone="warn" size="sm">
                          Fallback method
                        </Badge>
                      ) : null}
                    </div>
                    <HorizontalBars
                      ariaLabel={`${xaiTab.toUpperCase()} feature contributions`}
                      items={activeExplain.top_features.map((f) => ({ label: f.feature, value: f.contribution }))}
                      positiveLabel={`Toward ${activeExplain.prediction}`}
                      negativeLabel="Against"
                    />
                    <p className="muted small">{activeExplain.explanation}</p>
                  </div>
                ) : (
                  <EmptyState compact title="Explanation unavailable" />
                )}
              </TabPanel>
            </Card>

            <Card title="Recommended defense" subtitle="Advisory only — no network changes are executed" icon={Shield}>
              <div className="stack">
                <div>
                  <div style={{ fontWeight: 600, fontSize: "1.05rem" }}>{result.recommendation.primary}</div>
                  {result.recommendation.rationale ? <p className="muted small">{result.recommendation.rationale}</p> : null}
                </div>
                <ul className="check-list">
                  {result.recommendation.actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                {result.recommendation.rule_actions && result.recommendation.rule_actions.length > 0 && (
                  <div className="row" style={{ gap: 6 }}>
                    <span className="muted small">Rules fired:</span>
                    {result.recommendation.rule_actions.map((r) => (
                      <Badge key={r} tone="info" size="sm">
                        {humanize(r)}
                      </Badge>
                    ))}
                  </div>
                )}
                <Callout tone="neutral">
                  {result.recommendation.disclaimer ?? "Advisory only — the platform does not execute network changes."}
                </Callout>
                {result.decision_trace ? (
                  <DecisionTraceTimeline title={result.decision_trace.title} steps={result.decision_trace.steps} />
                ) : null}
              </div>
            </Card>
          </div>

          {counterfactual && (
            <Card
              title="What-if counterfactual"
              subtitle={counterfactual.note ?? "Illustrative feature edits only."}
              icon={Wand2}
              actions={
                counterfactual.baseline ? (
                  <Badge tone="neutral">
                    Baseline {counterfactual.baseline.attack_type} · P(attack) {formatPct(counterfactual.baseline.binary_proba_attack, 1)}
                  </Badge>
                ) : null
              }
            >
              <div className="stack">
                <DataTable
                  data={counterfactual.edits ?? []}
                  columns={cfColumns}
                  rowKey={(e) => e.feature}
                  pageSize={0}
                  dense
                  emptyTitle="No counterfactual edits"
                  caption="Counterfactual feature edits"
                />
                {counterfactual.combined ? (
                  <Callout tone={counterfactual.combined.flipped_to_benign ? "ok" : "info"} title="Combined edit">
                    Changing {counterfactual.combined.features_changed.join(", ")} → {counterfactual.combined.new_attack_type} · P(attack){" "}
                    {formatPct(counterfactual.combined.new_binary_proba_attack, 1)}
                    {counterfactual.combined.flipped_to_benign ? " · flips to benign" : ""}
                  </Callout>
                ) : null}
              </div>
            </Card>
          )}
        </>
      )}

      {/* ---------------------------------------------------------- batch result */}
      {batch && (
        <Card title="Batch results" subtitle={label ?? undefined} icon={Layers}>
          <div className="stack">
            <div className="grid grid-stats">
              <StatTile label="Flows" icon={Layers} value={batch.total_flows.toLocaleString()} />
              <StatTile label="Attacks" icon={Crosshair} tone="var(--sev-high)" value={batch.attack_flows.toLocaleString()} />
              <StatTile label="Benign" icon={Shield} tone="var(--ok)" value={batch.benign_flows.toLocaleString()} />
              <StatTile
                label="Highest risk"
                icon={Radar}
                tone="var(--sev-critical)"
                compact
                value={batch.highest_risk ? `${batch.highest_risk.attack_type} · ${formatRisk(batch.highest_risk.risk_score)}` : "—"}
                hint={batch.highest_risk ? `Flow #${batch.highest_risk.flow_index}` : undefined}
              />
              {batch.zero_day_alerts != null && (
                <StatTile
                  label="Gate alerts"
                  icon={Sparkles}
                  tone="var(--chart-7)"
                  value={batch.zero_day_alerts.toLocaleString()}
                  hint={`${batch.zero_day_novel ?? 0} novel (unknown / zero-day)`}
                />
              )}
              {batch.zero_day_missed_by_frozen != null && (
                <StatTile
                  label="Missed by frozen"
                  icon={Fingerprint}
                  tone={batch.zero_day_missed_by_frozen > 0 ? "var(--danger)" : undefined}
                  value={batch.zero_day_missed_by_frozen.toLocaleString()}
                  hint="Novel flows the frozen model called benign"
                />
              )}
            </div>
            {(batch.zero_day_missed_by_frozen ?? 0) > 0 && (
              <Callout tone="danger" title="Possible zero-day traffic in this batch">
                The advisory gate flagged {batch.zero_day_missed_by_frozen} novel flow(s) that the frozen v1.1 model classified as benign. Sort the
                table by “Zero-Day Gate” to inspect them.
              </Callout>
            )}
            <div className="grid grid-split-rev">
              <DonutChart
                ariaLabel="Batch verdicts by attack family"
                centerValue={`${Math.round(batch.attack_percentage)}%`}
                centerLabel="Attack share"
                data={[
                  ...Object.entries(batch.by_attack_type).map(([k, v]) => ({ name: k, value: v, color: attackColor(theme, k) })),
                  ...(batch.benign_flows > 0 && !("BENIGN" in batch.by_attack_type)
                    ? [{ name: "BENIGN", value: batch.benign_flows, color: theme.surface3 }]
                    : []),
                ]}
              />
              <DataTable
                data={batch.results}
                columns={batchColumns}
                rowKey={(r) => String(r.flow_index)}
                searchable
                searchPlaceholder="Search verdicts…"
                pageSize={10}
                maxHeight={460}
                caption="Per-flow batch results"
              />
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
