import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Activity,
  BookOpen,
  Clock3,
  Cpu,
  FastForward,
  GitCompareArrows,
  History,
  Loader2,
  Network,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  SkipForward,
  Timer,
  Zap,
} from "lucide-react";
import { api, type SimHistoryItem, type SimSession } from "../services/api";
import { NetworkTopology } from "../components/NetworkTopology";
import { CompareTable } from "../components/DecisionTrace";
import { Badge, SeverityBadge, StatusBadge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { useToast } from "../components/ui/Toast";
import { TimeSeriesArea, useChartTheme } from "../components/charts";
import { formatDuration, formatPct, formatRelative, formatRisk, humanize } from "../lib/format";

const ATTACKS = ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot"];
const INTENSITY_PRESETS: Record<string, number> = { Low: 0.35, Medium: 0.6, High: 0.9 };
const SPEED_MS: Record<string, number> = { "0.5x": 1600, "1x": 900, "2x": 450 };

const STEPS = [
  "Start normal traffic",
  "Start attack",
  "Propagate to target",
  "IDS detects",
  "Show recommendation",
  "Apply defense",
  "Recover",
];

function latency(primary: number | null | undefined, fallback: unknown): string {
  if (primary != null) return formatDuration(primary);
  if (fallback != null && fallback !== "") return formatDuration(fallback);
  return "—";
}

export function SimulationPage() {
  const toast = useToast();
  const theme = useChartTheme();
  const [searchParams, setSearchParams] = useSearchParams();
  const [attackType, setAttackType] = useState("DDoS");
  const [intensityLabel, setIntensityLabel] = useState("High");
  const [confidence, setConfidence] = useState(0.96);
  const [session, setSession] = useState<SimSession | null>(null);
  const [history, setHistory] = useState<SimHistoryItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState("1x");
  const [error, setError] = useState<unknown>(null);
  const playRef = useRef(false);
  const sessionRef = useRef<SimSession | null>(null);

  function refreshHistory() {
    api
      .listSims(15)
      .then((r) => setHistory(r.items ?? []))
      .catch(() => setHistory([]));
  }

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    refreshHistory();
  }, []);

  useEffect(() => {
    const sid = searchParams.get("session");
    if (!sid) return;
    let cancelled = false;
    setBusy(true);
    api
      .getSim(sid)
      .then((s) => {
        if (!cancelled) {
          setSession(s);
          setAttackType(s.attack_type);
          setError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  useEffect(() => {
    playRef.current = playing;
    if (!playing || !session) return;
    let cancelled = false;

    async function tick() {
      while (playRef.current && !cancelled) {
        const cur = sessionRef.current;
        if (!cur || cur.state === "recovered") {
          setPlaying(false);
          break;
        }
        try {
          const s = await api.advanceSim(cur.id);
          if (cancelled) break;
          setSession(s);
          if (s.state === "recovered") {
            setPlaying(false);
            refreshHistory();
            toast.success("Simulation complete", "The network recovered.");
            break;
          }
        } catch (e) {
          if (!cancelled) {
            setError(e);
            setPlaying(false);
          }
          break;
        }
        await new Promise((r) => setTimeout(r, SPEED_MS[speed] ?? 900));
      }
    }

    void tick();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed, session?.id]);

  async function createSession() {
    setBusy(true);
    setPlaying(false);
    setError(null);
    try {
      const s = await api.startSim(attackType, confidence, undefined, {
        traffic_intensity: INTENSITY_PRESETS[intensityLabel] ?? 0.6,
      });
      setSession(s);
      setSearchParams({ session: s.id });
      refreshHistory();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  function replay(sessionId: string) {
    setPlaying(false);
    setSearchParams({ session: sessionId });
  }

  async function advance(action?: string) {
    if (!session) return;
    setPlaying(false);
    setBusy(true);
    setError(null);
    try {
      const s = await api.advanceSim(session.id, action);
      setSession(s);
      if (action === "reset") setSearchParams({ session: s.id });
      refreshHistory();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const m = session?.metrics ?? {};
  const lat = session?.latencies;
  const series = session?.series;
  const chartRows =
    series?.labels.map((label, i) => ({
      phase: humanize(label),
      trafficWith: (series.with_defense.traffic[i] ?? 0) * 100,
      trafficWithout: (series.without_defense.traffic[i] ?? 0) * 100,
      stressWith: (series.with_defense.stress[i] ?? 0) * 100,
      stressWithout: (series.without_defense.stress[i] ?? 0) * 100,
      riskWith: series.with_defense.risk[i] ?? 0,
      riskWithout: series.without_defense.risk[i] ?? 0,
    })) ?? [];
  const phaseOrder = (session?.phase_guide ?? []).map((x) => x.state);
  const phaseIdx = session ? phaseOrder.indexOf(session.state) : -1;
  const pctFmt = (v: number) => `${Math.round(v)}%`;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Operations"
        icon={Network}
        title="Attack Storyboard"
        subtitle="An illustrative walkthrough of attack → detect → defend → recover for teaching and demos. No traffic is generated and the defense effectiveness shown is an assumed value."
        actions={
          session ? (
            <span className="live-pill">
              <span className="status-dot" data-state={playing ? "live" : session.state === "recovered" ? undefined : "warn"} aria-hidden />
              {playing ? "Playing" : session.state === "recovered" ? "Recovered" : humanize(session.state)}
            </span>
          ) : null
        }
      />

      <Callout tone="info" title="Looking for measured results?">
        This page animates a scripted story. The <Link to="/range">Cyber Range</Link> replays real traffic through the real
        detectors and measures detection time, service impact and the effect of each defense.
      </Callout>

      <Card title="Scenario" subtitle="Configure the attack, then run or step through it." icon={Zap}>
        <div className="stack">
          <div className="row" style={{ alignItems: "flex-end", gap: 14 }}>
            <div className="field" style={{ width: 170 }}>
              <label className="field-label" htmlFor="sim-attack">
                Attack
              </label>
              <select id="sim-attack" className="select" value={attackType} onChange={(e) => setAttackType(e.target.value)}>
                {ATTACKS.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <span className="field-label" id="sim-intensity-label">
                Intensity
              </span>
              <div className="segmented" role="radiogroup" aria-labelledby="sim-intensity-label">
                {Object.keys(INTENSITY_PRESETS).map((k) => (
                  <button key={k} type="button" role="radio" aria-checked={intensityLabel === k} onClick={() => setIntensityLabel(k)}>
                    {k}
                  </button>
                ))}
              </div>
            </div>
            <div className="field" style={{ width: 120 }}>
              <label className="field-label" htmlFor="sim-confidence">
                Confidence
              </label>
              <input
                id="sim-confidence"
                className="input mono"
                type="number"
                min={0.5}
                max={1}
                step={0.01}
                value={confidence}
                onChange={(e) => setConfidence(Number(e.target.value))}
              />
            </div>
            <button type="button" className="btn btn-primary" onClick={() => void createSession()} disabled={busy}>
              {busy && !session ? <Loader2 size={16} className="spin" aria-hidden /> : <Play size={16} aria-hidden />}
              Run simulation
            </button>
          </div>

          <div className="row" role="toolbar" aria-label="Playback controls" style={{ gap: 8 }}>
            <button
              type="button"
              className="btn btn-warn"
              onClick={() => setPlaying((p) => !p)}
              disabled={busy || !session || session.state === "recovered"}
            >
              {playing ? <Pause size={16} aria-hidden /> : <Play size={16} aria-hidden />}
              {playing ? "Pause" : "Play"}
            </button>
            <label className="row" style={{ gap: 6 }}>
              <FastForward size={15} aria-hidden className="muted" />
              <span className="sr-only">Playback speed</span>
              <select className="select select-sm" style={{ width: 84 }} value={speed} onChange={(e) => setSpeed(e.target.value)} disabled={!session}>
                {Object.keys(SPEED_MS).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="btn btn-secondary" onClick={() => void advance()} disabled={busy || !session || playing}>
              <SkipForward size={16} aria-hidden /> Step
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => void advance("defend")} disabled={busy || !session || playing}>
              <ShieldCheck size={16} aria-hidden /> Apply defense
            </button>
            <button type="button" className="btn btn-danger" onClick={() => void advance("reset")} disabled={busy || !session}>
              <RotateCcw size={16} aria-hidden /> Reset
            </button>
          </div>
        </div>
      </Card>

      {error ? <ErrorState error={error} onRetry={() => setError(null)} /> : null}

      {!session && (
        <EmptyState
          icon={Network}
          title="Ready to simulate"
          description={
            <>
              Configure intensity and confidence, then run — or replay a saved session below. Phases: {STEPS.join(" → ")}.
            </>
          }
        />
      )}

      {session && (
        <>
          {session.phase_guide && session.phase_guide.length > 0 && (
            <ol className="stepper list-plain" aria-label="Simulation phases">
              {session.phase_guide.map((p, idx) => {
                const state = idx < phaseIdx ? "done" : idx === phaseIdx ? "active" : undefined;
                return (
                  <li key={p.state} className="step" data-state={state} aria-current={state === "active" ? "step" : undefined}>
                    <span className="step-bar" aria-hidden />
                    <span className="step-label">{p.label}</span>
                    <span className="step-meta">{p.t}</span>
                  </li>
                );
              })}
            </ol>
          )}

          <div className="grid grid-stats">
            <StatTile label="Detection latency" icon={Timer} value={latency(lat?.detection_s, m.detection_delay_s)} compact />
            <StatTile label="Defense latency" icon={ShieldCheck} value={latency(lat?.defense_s, m.defense_delay_s)} compact />
            <StatTile label="Recovery time" icon={Clock3} value={latency(lat?.recovery_s, m.recovery_time_s)} compact />
            <StatTile label="Attack → recover" icon={Activity} value={latency(lat?.attack_to_recover_s, null)} compact />
          </div>

          {chartRows.length > 0 && (
            <div className="grid grid-3">
              <Card title="Traffic load" subtitle="Share of link capacity per phase" icon={Activity}>
                <TimeSeriesArea
                  ariaLabel="Traffic load with and without defense across phases"
                  data={chartRows}
                  xKey="phase"
                  variant="line"
                  height={220}
                  yDomain={[0, 100]}
                  yFormatter={pctFmt}
                  series={[
                    { key: "trafficWithout", label: "No defense", color: theme.negative, dashed: true },
                    { key: "trafficWith", label: "With defense", color: theme.positive },
                  ]}
                />
              </Card>
              <Card title="Server stress" subtitle="Target utilisation per phase" icon={Cpu}>
                <TimeSeriesArea
                  ariaLabel="Server stress with and without defense across phases"
                  data={chartRows}
                  xKey="phase"
                  variant="line"
                  height={220}
                  yDomain={[0, 100]}
                  yFormatter={pctFmt}
                  series={[
                    { key: "stressWithout", label: "No defense", color: theme.negative, dashed: true },
                    { key: "stressWith", label: "With defense", color: theme.positive },
                  ]}
                />
              </Card>
              <Card title="Risk" subtitle="Risk score 0–100 per phase" icon={Zap}>
                <TimeSeriesArea
                  ariaLabel="Risk score with and without defense across phases"
                  data={chartRows}
                  xKey="phase"
                  variant="line"
                  height={220}
                  yDomain={[0, 100]}
                  yFormatter={(v) => String(Math.round(v))}
                  series={[
                    { key: "riskWithout", label: "No defense", color: theme.negative, dashed: true },
                    { key: "riskWith", label: "With defense", color: theme.positive },
                  ]}
                />
              </Card>
            </div>
          )}

          <div className="grid grid-split">
            <Card
              title="Network topology"
              subtitle="Node health and traffic flows for the current phase"
              icon={Network}
              actions={
                <div className="row" style={{ gap: 6 }}>
                  <SeverityBadge severity={session.severity} size="sm" />
                  <Badge tone="neutral" size="sm">
                    Risk {formatRisk(session.risk_score)}
                  </Badge>
                  <Badge tone="neutral" size="sm">
                    {session.attack_type}
                  </Badge>
                </div>
              }
            >
              <div className="stack">
                <NetworkTopology nodes={session.nodes} edges={session.edges} />
                <div className="row small muted" style={{ gap: 12 }}>
                  <span>
                    State <StatusBadge status={session.state} size="sm" />
                  </span>
                  {session.campaign_id && (
                    <Link to={`/campaigns/${encodeURIComponent(session.campaign_id)}`}>Campaign {session.campaign_id}</Link>
                  )}
                  {session.incident_id && <Link to={`/incidents/${encodeURIComponent(session.incident_id)}`}>{session.incident_id}</Link>}
                </div>
              </div>
            </Card>

            <Card title="Timeline" subtitle="Events emitted by the simulation state machine" icon={Clock3}>
              <div className="stack">
                <ol className="timeline" style={{ maxHeight: 360, overflowY: "auto", paddingRight: 4 }}>
                  {session.timeline.map((t, idx) => (
                    <li key={`${t.event}-${idx}`}>
                      <div className="timeline-title">{humanize(t.event)}</div>
                      <div className="timeline-meta">
                        {t.t_s != null ? `t = ${t.t_s}s` : ""}
                        {t.state ? ` · ${humanize(t.state)}` : ""}
                      </div>
                      <div className="timeline-detail">{t.detail}</div>
                    </li>
                  ))}
                </ol>
                <dl className="kv">
                  <dt>Peak traffic</dt>
                  <dd>{formatPct(m.peak_traffic)}</dd>
                  <dt>Server stress</dt>
                  <dd>{formatPct(m.server_stress)}</dd>
                  <dt>Traffic blocked</dt>
                  <dd>{formatPct(m.traffic_blocked)}</dd>
                  {m.remaining_malicious != null && (
                    <>
                      <dt>Remaining malicious</dt>
                      <dd>{String(m.remaining_malicious)}</dd>
                    </>
                  )}
                  {m.persistence != null && (
                    <>
                      <dt>Persistence</dt>
                      <dd>{String(m.persistence)}</dd>
                    </>
                  )}
                </dl>
              </div>
            </Card>
          </div>

          <div className="grid grid-2">
            {session.comparison ? (
              <Card title="Before vs after defense" subtitle="Simulated counterfactual comparison" icon={GitCompareArrows}>
                <CompareTable
                  without={session.comparison.without_defense}
                  withDefense={session.comparison.with_defense}
                  recoveryS={lat?.recovery_s ?? (m.recovery_time_s as number | undefined)}
                />
              </Card>
            ) : null}
            <Card title="Narrative & recommendation" icon={BookOpen}>
              <div className="stack">
                {session.narrative && session.narrative.length > 0 && (
                  <ol className="check-list">
                    {session.narrative.map((n, i) => (
                      <li key={i}>{n}</li>
                    ))}
                  </ol>
                )}
                <div>
                  <div style={{ fontWeight: 600 }}>{session.recommendation.primary}</div>
                  <p className="muted small">{session.recommendation.rationale}</p>
                </div>
                <Callout tone="neutral">
                  {session.disclaimer ??
                    "Defense effectiveness values are simulation assumptions for comparative visualization, not measured real-world mitigation rates."}
                </Callout>
              </div>
            </Card>
          </div>
        </>
      )}

      {history.length > 0 && (
        <Card title="Simulation history" subtitle="Replay a previous session" icon={History}>
          <div className="row" style={{ gap: 8 }}>
            {history.map((h) => {
              const activeSession = session?.id === h.session_id;
              return (
                <button
                  key={h.session_id}
                  type="button"
                  className={`btn btn-sm ${activeSession ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => replay(h.session_id)}
                  aria-pressed={activeSession}
                  title={h.session_id}
                >
                  {h.attack_type} · {humanize(h.state)}
                  <span style={{ opacity: 0.7, fontWeight: 400 }}>· {h.created_at ? formatRelative(h.created_at) : h.session_id.slice(0, 8)}</span>
                </button>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
