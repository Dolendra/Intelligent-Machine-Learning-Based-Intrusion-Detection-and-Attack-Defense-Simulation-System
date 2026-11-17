import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  BellRing,
  Fingerprint,
  Gauge as GaugeIcon,
  Layers,
  ListTree,
  Pause,
  PieChart,
  Play,
  Radio,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Target,
  TriangleAlert,
  Waves,
} from "lucide-react";
import { api, type LiveFlow, type LiveScenario, type LiveScenariosResponse } from "../services/api";
import { useLiveStream, TICK_SECONDS } from "../features/live/useLiveStream";
import { Badge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { Drawer } from "../components/ui/Modal";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { BarList, GroupedBars, TimeSeriesArea, useChartTheme } from "../components/charts";
import {
  DeviationBars,
  GateLabelBadge,
  OUTCOME_META,
  OutcomeBadge,
  PValueMeter,
} from "../components/zeroday/GateVisuals";
import { formatCompact, formatNumber, formatPct, formatTime } from "../lib/format";

const UNSEEN_FAMILIES = new Set(["Infiltration", "Heartbleed"]);
type FeedFilter = "all" | "alerts" | "gate" | "unseen";

const FILTERS: Array<{ id: FeedFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "alerts", label: "Any alert" },
  { id: "gate", label: "Gate-only" },
  { id: "unseen", label: "Unseen families" },
];

function matchesFilter(f: LiveFlow, filter: FeedFilter) {
  if (filter === "alerts") return f.frozen.is_attack || Boolean(f.gate?.alert);
  if (filter === "gate") return f.outcome === "caught_gate_only";
  if (filter === "unseen") return f.unseen_family;
  return true;
}

function rowHighlight(f: LiveFlow): string | undefined {
  if (f.outcome === "caught_gate_only") return "gate";
  if (f.unseen_family) return "unseen";
  if (f.outcome === "missed") return "missed";
  return undefined;
}

/** Attack share of a phase mixture (0..1). */
function attackShare(mix: Record<string, number>) {
  const total = Object.values(mix).reduce((s, v) => s + v, 0) || 1;
  return 1 - (mix.BENIGN ?? 0) / total;
}

function ScenarioCard({
  s,
  active,
  phaseIndex,
  progress,
  onSelect,
}: {
  s: LiveScenario;
  active: boolean;
  phaseIndex?: number;
  progress?: number;
  onSelect: () => void;
}) {
  const hasUnseen = s.phases.some((p) => Object.keys(p.mix).some((f) => UNSEEN_FAMILIES.has(f)));
  return (
    <button type="button" className="scenario-card" aria-pressed={active} onClick={onSelect}>
      <div className="row-between" style={{ width: "100%" }}>
        <strong>{s.title}</strong>
        {hasUnseen && (
          <Badge tone="novel" icon={Sparkles} size="sm">
            Unseen families
          </Badge>
        )}
      </div>
      <p>{s.description}</p>
      <div className="phase-bar" aria-hidden>
        {s.phases.map((p, i) => {
          const unseen = Object.keys(p.mix).some((f) => UNSEEN_FAMILIES.has(f));
          const isActive = active && phaseIndex === i;
          return (
            <span
              key={p.name}
              className="phase-seg"
              data-active={isActive || undefined}
              data-unseen={unseen || undefined}
              title={`${p.name} · ${p.seconds}s · ${Math.round(attackShare(p.mix) * 100)}% attack`}
              style={{ flex: `${p.seconds} 1 0`, ["--attack-pct" as string]: `${Math.round(attackShare(p.mix) * 100)}%` }}
            >
              {isActive && <span className="phase-seg-progress" style={{ width: `${Math.round((progress ?? 0) * 100)}%` }} />}
            </span>
          );
        })}
      </div>
      <span className="small muted">
        {s.phases.length} phases · {s.cycle_seconds}s loop
        {active && phaseIndex != null && s.phases[phaseIndex] ? (
          <>
            {" "}
            · now: <strong style={{ color: "var(--text)" }}>{s.phases[phaseIndex].name}</strong>
          </>
        ) : null}
      </span>
    </button>
  );
}

function FlowDrawer({ flow, alpha, onClose }: { flow: LiveFlow | null; alpha: number; onClose: () => void }) {
  return (
    <Drawer
      open={flow !== null}
      onClose={onClose}
      title={flow ? `Flow #${flow.id}` : ""}
      subtitle={flow ? `${formatTime(flow.ts * 1000)} · ${flow.src} → ${flow.dst}:${flow.dst_port}` : undefined}
    >
      {flow && (
        <div className="stack">
          <div className="row" style={{ gap: 6 }}>
            <OutcomeBadge outcome={flow.outcome} size="md" />
            {flow.unseen_family && (
              <Badge tone="novel" icon={Fingerprint}>
                Unseen family
              </Badge>
            )}
          </div>
          <dl className="kv">
            <dt>Ground truth (replay label)</dt>
            <dd>{flow.truth}</dd>
            <dt>Source → destination</dt>
            <dd>
              {flow.src} → {flow.dst}:{flow.dst_port}
            </dd>
            <dt>Bytes (fwd + bwd)</dt>
            <dd>{formatCompact(flow.bytes)}</dd>
            <dt>Duration</dt>
            <dd>{formatNumber(flow.duration_ms, 2)} ms</dd>
          </dl>

          <Card title="Frozen v1.1 detector" subtitle="Decision Tree @0.85 → attack-only Random Forest" icon={ShieldCheck}>
            <dl className="kv">
              <dt>Verdict</dt>
              <dd>{flow.frozen.is_attack ? flow.frozen.attack_type ?? "Attack" : "Benign"}</dd>
              <dt>Confidence</dt>
              <dd>{formatPct(flow.frozen.confidence, 1)}</dd>
              <dt>Risk / severity</dt>
              <dd>
                {formatNumber(flow.frozen.risk_score, 1)} · {flow.frozen.severity ?? "—"}
              </dd>
            </dl>
          </Card>

          <Card title="Zero-Day Gate (advisory)" subtitle="Aegis-OSR conformal benign test" icon={Sparkles}>
            {flow.gate ? (
              <div className="stack">
                <div className="row" style={{ gap: 6 }}>
                  <GateLabelBadge label={flow.gate.label} />
                </div>
                <p className="text-2 small">{flow.gate.summary}</p>
                <PValueMeter p={flow.gate.p_value} alpha={alpha} />
                {flow.gate.alert && (
                  <div className="stack-sm">
                    <h4 className="small muted" style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      {flow.gate.novel ? "Why it looks novel" : "Largest deviations from benign neighbours"}
                    </h4>
                    <DeviationBars deviations={flow.gate.top_deviations} />
                  </div>
                )}
              </div>
            ) : (
              <p className="muted small">Gate not loaded on the server.</p>
            )}
          </Card>
        </div>
      )}
    </Drawer>
  );
}

export function LiveMonitorPage() {
  const theme = useChartTheme();
  const [catalog, setCatalog] = useState<LiveScenariosResponse | null>(null);
  const [catalogError, setCatalogError] = useState<unknown>(null);
  const [scenario, setScenarioState] = useState("enterprise_day");
  const [rate, setRateState] = useState(20);
  const [filter, setFilter] = useState<FeedFilter>("all");
  const [hold, setHold] = useState(false);
  const [held, setHeld] = useState<LiveFlow[]>([]);
  const [selected, setSelected] = useState<LiveFlow | null>(null);
  const [alpha, setAlpha] = useState(0.01);
  const rateTimer = useRef<number | undefined>(undefined);

  const loadCatalog = () => {
    setCatalogError(null);
    api
      .liveScenarios()
      .then(setCatalog)
      .catch(setCatalogError);
  };
  useEffect(loadCatalog, []);
  useEffect(() => {
    api
      .zeroDayStatus()
      .then((s) => s.alpha && setAlpha(s.alpha))
      .catch(() => undefined);
  }, []);

  const stream = useLiveStream({ scenario, rate, enabled: Boolean(catalog?.pool_available) });
  const { stats, tick, connection } = stream;
  const paused = Boolean(tick?.paused);
  const maxRate = catalog?.max_rate ?? 200;

  useEffect(() => () => window.clearTimeout(rateTimer.current), []);

  function chooseScenario(id: string) {
    setScenarioState(id);
    stream.setScenario(id);
  }

  function changeRate(v: number) {
    setRateState(v);
    window.clearTimeout(rateTimer.current);
    rateTimer.current = window.setTimeout(() => stream.setRate(v), 250);
  }

  function toggleHold() {
    setHold((h) => {
      if (!h) setHeld(stream.feed);
      return !h;
    });
  }

  const feedSource = hold ? held : stream.feed;
  const feed = useMemo(() => feedSource.filter((f) => matchesFilter(f, filter)), [feedSource, filter]);

  const measuredRate = useMemo(() => {
    const recent = stream.history.slice(-6);
    if (!recent.length) return 0;
    return recent.reduce((s, p) => s + p.benign + p.attack, 0) / recent.length;
  }, [stream.history]);

  const lastT = stream.history[stream.history.length - 1]?.t ?? 0;
  const throughput = stream.history.map((p) => ({ ...p, label: p.t - lastT }));

  const families = useMemo(
    () =>
      Object.entries(stats?.by_family ?? {})
        .filter(([fam]) => fam !== "BENIGN")
        .sort((a, b) => b[1].n - a[1].n)
        .map(([fam, v]) => ({
          family: UNSEEN_FAMILIES.has(fam) ? `${fam} (unseen)` : fam,
          frozen: v.n ? (v.frozen / v.n) * 100 : 0,
          gate: v.n ? (v.gate / v.n) * 100 : 0,
          n: v.n,
        })),
    [stats]
  );

  const r = stats?.rates;
  const activeScenario = catalog?.scenarios.find((s) => s.id === (tick?.scenario ?? scenario));
  const unseenTotal = stats?.unseen_total ?? 0;

  const connLabel =
    connection === "open"
      ? paused
        ? "Paused"
        : "Streaming"
      : connection === "reconnecting"
        ? `Reconnecting${stream.attempt > 1 ? ` (try ${stream.attempt})` : ""}…`
        : connection === "connecting"
          ? catalog && !catalog.pool_available
            ? "Unavailable"
            : "Connecting…"
          : connection === "error"
            ? "Stopped"
            : "Disconnected";

  function onRowKey(e: KeyboardEvent<HTMLTableRowElement>, f: LiveFlow) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setSelected(f);
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Zero-Day Research"
        icon={Radio}
        title="Live Traffic Monitor"
        subtitle="Replayed network flows scored in real time by the frozen v1.1 detector and the advisory Aegis-OSR Zero-Day Gate, side by side."
        actions={
          <>
            <span className="live-pill" role="status" aria-live="polite">
              <span
                className="status-dot"
                data-state={connection === "open" && !paused ? "live" : connection === "error" ? "off" : "warn"}
                aria-hidden
              />
              {connLabel}
            </span>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={connection !== "open"}
              onClick={() => (paused ? stream.resume() : stream.pause())}
              aria-pressed={paused}
            >
              {paused ? <Play size={16} aria-hidden /> : <Pause size={16} aria-hidden />}
              {paused ? "Resume" : "Pause"}
            </button>
            <button type="button" className="btn btn-secondary" disabled={connection !== "open"} onClick={stream.reset}>
              <RotateCcw size={16} aria-hidden /> Reset
            </button>
          </>
        }
      />

      <Callout tone="info" title="Replay, not live capture">
        {catalog?.disclaimer ?? "Replay of held-out CICIDS2017 flows."} The Zero-Day Gate is advisory — it never changes the frozen
        model's verdict. Ground-truth labels are known for replayed flows, which is what makes the outcome counts below possible.
      </Callout>

      {catalogError ? <ErrorState error={catalogError} title="Could not load live scenarios" onRetry={loadCatalog} /> : null}
      {catalog && !catalog.pool_available && (
        <Callout tone="warn" title="Replay pool missing">
          Build it with <code>scripts/52_build_replay_pool.py</code>, then reload this page.
        </Callout>
      )}
      {stream.error && (
        <ErrorState
          error={{ detail: { message: stream.error.message } }}
          title={stream.error.code === "POOL_MISSING" ? "Replay pool missing" : "Live stream stopped"}
          onRetry={stream.reconnect}
        />
      )}
      {tick?.models && !tick.models.gate && (
        <Callout tone="warn" title="Zero-Day Gate not loaded">
          Only the frozen detector is scoring flows. Train the gate with <code>scripts/51_train_zero_day_gate.py</code>.
        </Callout>
      )}

      <Card
        title="Scenario"
        subtitle="Pick a traffic story. Phases loop; the highlighted segment is playing now."
        icon={Waves}
        actions={
          <label className="field" style={{ width: "min(260px, 100%)" }}>
            <span className="field-label row-between">
              <span>Replay rate</span>
              <span className="mono">{rate} flows/s</span>
            </span>
            <input
              className="range-slider"
              type="range"
              min={1}
              max={maxRate}
              step={1}
              value={rate}
              onChange={(e) => changeRate(Number(e.target.value))}
              aria-valuetext={`${rate} flows per second`}
            />
          </label>
        }
      >
        {!catalog && !catalogError ? (
          <div className="grid grid-2">
            <Skeleton height={130} radius={12} />
            <Skeleton height={130} radius={12} />
          </div>
        ) : (
          <div className="grid grid-2">
            {(catalog?.scenarios ?? []).map((s) => (
              <ScenarioCard
                key={s.id}
                s={s}
                active={s.id === (tick?.scenario ?? scenario)}
                phaseIndex={tick?.phase.index}
                progress={tick?.phase.progress}
                onSelect={() => chooseScenario(s.id)}
              />
            ))}
          </div>
        )}
        {activeScenario && tick?.phase.mix && (
          <div className="row small" style={{ marginTop: 12, gap: 6 }}>
            <span className="muted">Current mix:</span>
            {Object.entries(tick.phase.mix).map(([fam, w]) => (
              <Badge key={fam} tone={fam === "BENIGN" ? "neutral" : UNSEEN_FAMILIES.has(fam) ? "novel" : "high"} size="sm">
                {fam} {Math.round(w * 100)}%
              </Badge>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-stats">
        <StatTile
          label="Throughput"
          icon={Activity}
          value={`${measuredRate.toFixed(0)}/s`}
          sparkline={stream.history.slice(-40).map((p) => p.benign + p.attack)}
          hint={`target ${rate}/s`}
        />
        <StatTile label="Flows scored" icon={Layers} value={formatCompact(stats?.total ?? 0)} hint={`${formatCompact(stats?.attacks_truth ?? 0)} attacks (truth)`} />
        <StatTile label="Frozen recall" icon={ShieldCheck} tone="var(--chart-1)" value={formatPct(r?.frozen_recall ?? 0, 1)} hint={`FPR ${formatPct(r?.frozen_fpr ?? 0, 2)}`} />
        <StatTile label="Gate recall" icon={Sparkles} tone="var(--chart-7)" value={formatPct(r?.gate_recall ?? 0, 1)} hint={`FPR ${formatPct(r?.gate_fpr ?? 0, 2)}`} />
        <StatTile label="Combined recall" icon={Target} tone="var(--ok)" value={formatPct(r?.combined_recall ?? 0, 1)} hint="Either detector alerts" />
        <StatTile
          label="Zero-day hits"
          icon={Fingerprint}
          tone="var(--chart-7)"
          value={formatCompact(stats?.caught_gate_only ?? 0)}
          hint={`${formatCompact(stats?.novel_flags ?? 0)} flagged novel`}
        />
      </div>

      <Card
        title="Never-seen attack families"
        subtitle="Infiltration and Heartbleed were in neither model's training data — this is the open-set problem."
        icon={Fingerprint}
        actions={
          unseenTotal === 0 && scenario !== "zero_day" ? (
            <button type="button" className="btn btn-primary btn-sm" onClick={() => chooseScenario("zero_day")}>
              <Sparkles size={14} aria-hidden /> Play “Zero-day intrusion”
            </button>
          ) : (
            <Badge tone="neutral">{unseenTotal} unseen flows so far</Badge>
          )
        }
      >
        <div className="vs-card">
          <div className="vs-side">
            <div className="stat-label">Frozen v1.1 detector</div>
            <div className="vs-value">{r?.unseen_frozen_recall == null ? "—" : formatPct(r.unseen_frozen_recall, 0)}</div>
            <div className="muted small">
              {stats?.unseen_caught_frozen ?? 0} of {unseenTotal} caught · closed-set: can only name families it was trained on
            </div>
          </div>
          <div className="vs-side" data-win={(r?.unseen_gate_recall ?? 0) > (r?.unseen_frozen_recall ?? 0) || undefined}>
            <div className="stat-label">Aegis-OSR Zero-Day Gate</div>
            <div className="vs-value" style={{ color: "var(--chart-7)" }}>
              {r?.unseen_gate_recall == null ? "—" : formatPct(r.unseen_gate_recall, 0)}
            </div>
            <div className="muted small">
              {stats?.unseen_caught_gate ?? 0} of {unseenTotal} caught · open-set: flags traffic unlike benign at α = {alpha}
            </div>
          </div>
        </div>
      </Card>

      <div className="grid grid-split">
        <Card title="Throughput" subtitle="Last 60 s · flows/s by ground truth, with alert rates" icon={Waves}>
          {throughput.length > 1 ? (
            <TimeSeriesArea
              ariaLabel="Rolling throughput of benign and attack flows with frozen and gate alert rates"
              data={throughput}
              xKey="label"
              stacked
              animate={false}
              curve="linear"
              height={240}
              xFormatter={(v) => `${Math.round(Number(v))}s`}
              yFormatter={(v) => String(Math.round(v))}
              series={[
                { key: "benign", label: "Benign", color: theme.muted },
                { key: "attack", label: "Attack (truth)", color: theme.series[1] },
                { key: "frozenAlerts", label: "Frozen alerts", color: theme.series[0], kind: "line" },
                { key: "gateAlerts", label: "Gate alerts", color: theme.series[6], kind: "line", dashed: true },
              ]}
            />
          ) : (
            <EmptyState compact icon={Waves} title={connection === "open" ? "Collecting…" : "Waiting for the stream"} />
          )}
        </Card>
        <Card title="Outcomes" subtitle="Every attack flow is caught by both, one, or neither model" icon={PieChart}>
          <BarList
            ariaLabel="Detection outcomes"
            sort={false}
            items={[
              { label: "both", display: OUTCOME_META.caught_both.text, value: stats?.caught_both ?? 0, color: OUTCOME_META.caught_both.color },
              { label: "frozen", display: OUTCOME_META.caught_frozen_only.text, value: stats?.caught_frozen_only ?? 0, color: OUTCOME_META.caught_frozen_only.color },
              { label: "gate", display: OUTCOME_META.caught_gate_only.text, value: stats?.caught_gate_only ?? 0, color: OUTCOME_META.caught_gate_only.color },
              { label: "missed", display: OUTCOME_META.missed.text, value: stats?.missed ?? 0, color: OUTCOME_META.missed.color },
              { label: "fa-frozen", display: "False alarms · frozen", value: stats?.false_alarm_frozen ?? 0, color: OUTCOME_META.false_alarm.color },
              { label: "fa-gate", display: "False alarms · gate", value: stats?.false_alarm_gate ?? 0, color: OUTCOME_META.false_alarm.color },
            ]}
          />
        </Card>
      </div>

      <div className="grid grid-split">
        <Card title="Detection rate per family" subtitle="Share of each replayed attack family flagged by each detector" icon={GaugeIcon}>
          {families.length ? (
            <GroupedBars
              ariaLabel="Per-family detection rate, frozen versus gate"
              data={families}
              categoryKey="family"
              height={250}
              yDomain={[0, 100]}
              yFormatter={(v) => `${Math.round(v)}%`}
              series={[
                { key: "frozen", label: "Frozen v1.1", color: theme.series[0] },
                { key: "gate", label: "Zero-Day Gate", color: theme.series[6] },
              ]}
            />
          ) : (
            <EmptyState compact title="No attack flows replayed yet" />
          )}
        </Card>

        <Card title="Zero-day alerts" subtitle="Gate-only catches and zero-day anomalies" icon={BellRing} actions={<Badge tone="novel">{stream.alerts.length}</Badge>}>
          {stream.alerts.length === 0 ? (
            <EmptyState
              compact
              icon={Sparkles}
              title="No zero-day catches yet"
              description={scenario === "zero_day" ? "Keep watching — unseen families appear during the foothold phase." : "Try the “Zero-day intrusion” scenario."}
            />
          ) : (
            <ul className="alert-list" aria-live="polite">
              {stream.alerts.map((f) => (
                <li key={f.id}>
                  <button type="button" className="alert-item" onClick={() => setSelected(f)}>
                    <Sparkles size={16} aria-hidden style={{ color: "var(--chart-7)", flexShrink: 0, marginTop: 2 }} />
                    <span className="grow" style={{ minWidth: 0 }}>
                      <span className="row-between" style={{ gap: 6 }}>
                        <strong>
                          Flow #{f.id} · {f.truth}
                        </strong>
                        <span className="muted small mono">{formatTime(f.ts * 1000)}</span>
                      </span>
                      <span className="row" style={{ gap: 6, marginTop: 4 }}>
                        <GateLabelBadge label={f.gate?.label} size="sm" />
                        <OutcomeBadge outcome={f.outcome} short />
                      </span>
                      {f.outcome === "caught_gate_only" && (
                        <span className="small muted" style={{ display: "block", marginTop: 4 }}>
                          Frozen model said benign.
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="row small" style={{ marginTop: 12, gap: 8 }}>
            <TriangleAlert size={14} aria-hidden className="muted" />
            <span className="muted">
              Gate false alarms are bounded by α on benign traffic. <Link to="/zero-day">How the gate works →</Link>
            </span>
          </div>
        </Card>
      </div>

      <Card
        title="Flow feed"
        subtitle={`Newest first · last ${feedSource.length} flows${hold ? " (held)" : ""} · click a row for evidence`}
        icon={ListTree}
        actions={
          <>
            <div className="segmented" role="radiogroup" aria-label="Feed filter">
              {FILTERS.map((f) => (
                <button key={f.id} type="button" role="radio" aria-checked={filter === f.id} onClick={() => setFilter(f.id)}>
                  {f.label}
                </button>
              ))}
            </div>
            <button type="button" className="btn btn-secondary btn-sm" aria-pressed={hold} onClick={toggleHold}>
              {hold ? <Play size={14} aria-hidden /> : <Pause size={14} aria-hidden />} {hold ? "Follow" : "Hold"}
            </button>
          </>
        }
      >
        {feed.length === 0 ? (
          <EmptyState compact title={stream.feed.length ? "No flows match this filter" : "No flows yet"} />
        ) : (
          <div className="table-wrap" style={{ maxHeight: 520 }}>
            <table className="table dense feed-table">
              <caption className="sr-only">Live flow feed</caption>
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Flow</th>
                  <th scope="col">Truth</th>
                  <th scope="col">Frozen v1.1</th>
                  <th scope="col">Zero-Day Gate</th>
                  <th scope="col">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {feed.map((f) => (
                  <tr
                    key={f.id}
                    tabIndex={0}
                    data-highlight={rowHighlight(f)}
                    onClick={() => setSelected(f)}
                    onKeyDown={(e) => onRowKey(e, f)}
                    aria-label={`Flow ${f.id}, truth ${f.truth}, outcome ${OUTCOME_META[f.outcome].text}`}
                  >
                    <td className="mono small">{formatTime(f.ts * 1000)}</td>
                    <td className="mono small">
                      {f.src} → :{f.dst_port}
                    </td>
                    <td>
                      <span className="row" style={{ gap: 4, flexWrap: "nowrap" }}>
                        {f.truth === "BENIGN" ? <span className="muted">Benign</span> : <strong>{f.truth}</strong>}
                        {f.unseen_family && <Fingerprint size={13} aria-label="unseen family" style={{ color: "var(--chart-7)" }} />}
                      </span>
                    </td>
                    <td>{f.frozen.is_attack ? <Badge tone="info" size="sm">{f.frozen.attack_type ?? "Attack"}</Badge> : <span className="muted small">Benign</span>}</td>
                    <td>
                      <GateLabelBadge label={f.gate?.label} size="sm" />
                    </td>
                    <td>
                      <OutcomeBadge outcome={f.outcome} short />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {connection !== "open" && connection !== "error" && catalog?.pool_available && (
        <p className="muted small row" style={{ gap: 6 }}>
          <RefreshCw size={14} className="spin" aria-hidden /> Live updates every {TICK_SECONDS}s once connected.
        </p>
      )}

      <FlowDrawer flow={selected} alpha={alpha} onClose={() => setSelected(null)} />
    </div>
  );
}
