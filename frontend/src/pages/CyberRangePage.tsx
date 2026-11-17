import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  BellRing,
  Clock3,
  FastForward,
  FlaskConical,
  Gauge as GaugeIcon,
  Loader2,
  Network,
  Pause,
  Play,
  Plus,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  SkipForward,
  Sparkles,
  Swords,
  Target,
  Timer,
  Users,
} from "lucide-react";
import {
  api,
  type RangeDefense,
  type RangeExperiments,
  type RangeScenario,
  type RangeSweep,
  type RangeView,
} from "../services/api";
import { NetworkTopology } from "../components/NetworkTopology";
import { Badge, StatusBadge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { Tabs } from "../components/ui/Tabs";
import { useToast } from "../components/ui/Toast";
import { HorizontalBars, TimeSeriesArea, useChartTheme } from "../components/charts";
import { formatPct, humanize } from "../lib/format";

/** Detection-side states, in the order the locked design defines them. */
const SOC_STATES = [
  "NORMAL",
  "SUSPICIOUS",
  "DETECTED",
  "EXPLAINED",
  "RESPONSE_OPTIONS",
  "MITIGATING",
  "CONTAINED",
  "RECOVERY",
  "COMPLETED",
] as const;
const STATE_HELP: Record<string, string> = {
  NORMAL: "Only normal traffic has been flagged so far",
  SUSPICIOUS: "A first alert hit an attacking source",
  DETECTED: "Enough alerts from one source: an incident is raised",
  EXPLAINED: "SHAP explains the flow that triggered the incident",
  RESPONSE_OPTIONS: "Waiting for a response decision",
  MITIGATING: "A defense is changing the traffic",
  MONITORING: "Watching only — the attack continues",
  NO_ACTION: "Alert ignored — the attack continues",
  CONTAINED: "Attack traffic reaching the target fell by ≥75%",
  RECOVERY: "The service is back to normal",
  COMPLETED: "Run finished; metrics are final and saved",
};
const INTENSITY: Record<string, number> = { Low: 0.5, Medium: 1, High: 2 };
const SPEED_MS: Record<string, number> = { "1×": 700, "2×": 350, "4×": 175 };
const DETECTOR_LABEL: Record<string, string> = {
  union: "Both (v1.1 + Zero-Day Gate)",
  frozen: "Frozen v1.1 only",
  gate: "Zero-Day Gate only",
};

const sec = (v: number | null | undefined) => (v == null ? "—" : `${v} s`);
const pct = (v: number | null | undefined, d = 1) => (v == null ? "—" : formatPct(v, d));

export function CyberRangePage() {
  const toast = useToast();
  const theme = useChartTheme();
  const [tab, setTab] = useState<"run" | "experiments">("run");
  const [scenarios, setScenarios] = useState<RangeScenario[]>([]);
  const [defenses, setDefenses] = useState<Record<string, RangeDefense>>({});
  const [scenarioId, setScenarioId] = useState("dos");
  const [intensity, setIntensity] = useState("Medium");
  const [detector, setDetector] = useState<"union" | "frozen" | "gate">("union");
  const [mode, setMode] = useState<"manual" | "auto">("manual");
  const [defense, setDefense] = useState("recommended");
  const [delay, setDelay] = useState(3);
  const [threshold, setThreshold] = useState(3);
  const [seed, setSeed] = useState(1);
  const [run, setRun] = useState<RangeView | null>(null);
  const [events, setEvents] = useState<RangeView["events"]>([]);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState("1×");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const runRef = useRef<RangeView | null>(null);
  const inFlight = useRef(false);

  useEffect(() => {
    api
      .rangeScenarios()
      .then((r) => {
        setScenarios(r.items);
        setDefenses(r.defenses);
      })
      .catch((e) => setError(e));
  }, []);

  const scenario = useMemo(() => scenarios.find((s) => s.id === scenarioId), [scenarios, scenarioId]);

  const absorb = useCallback((v: RangeView, reset = false) => {
    runRef.current = v;
    setRun(v);
    setEvents((prev) => {
      // the server may resend recent events (e.g. after a response); keep each sequence number once
      const base = reset ? [] : prev;
      const seen = new Set(base.map((e) => e.sequence));
      return [...base, ...v.events.filter((e) => !seen.has(e.sequence))].slice(-200);
    });
    if (v.awaiting_decision || v.done) setPlaying(false);
  }, []);

  async function start() {
    setBusy(true);
    setError(null);
    setPlaying(false);
    try {
      const v = await api.rangeCreate({
        scenario: scenarioId,
        seed,
        intensity: INTENSITY[intensity],
        detector,
        response_mode: mode,
        defense,
        approval_delay_s: delay,
        alert_threshold: threshold,
      });
      absorb(v, true);
      setPlaying(true);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const step = useCallback(
    async (seconds = 1) => {
      const cur = runRef.current;
      if (!cur || cur.done || inFlight.current) return;
      inFlight.current = true;
      try {
        absorb(await api.rangeStep(cur.run_id, seconds));
      } catch (e) {
        setPlaying(false);
        setError(e);
      } finally {
        inFlight.current = false;
      }
    },
    [absorb]
  );

  async function respond(action: string) {
    if (!run) return;
    setBusy(true);
    try {
      absorb(await api.rangeRespond(run.run_id, action));
      toast.success(`Applied: ${defenses[action]?.title ?? humanize(action)}`, "The defense now changes which flows reach the server.");
      setPlaying(true);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!run) return;
    setBusy(true);
    setPlaying(false);
    try {
      absorb(await api.rangeComplete(run.run_id));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => void step(1), SPEED_MS[speed]);
    return () => window.clearInterval(id);
  }, [playing, speed, step]);

  const chart = useMemo(
    () =>
      (run?.telemetry ?? []).map((r) => ({
        t: r.t,
        availability: Math.round(r.availability * 1000) / 10,
        attack_sent: r.attack_sent,
        attack_passed: r.attack_passed,
        benign_blocked: r.benign_blocked,
        alerts_true: r.alerts_true,
        alerts_false: r.alerts_false,
      })),
    [run?.telemetry]
  );
  const marks = run?.marks ?? {};
  const refLines = [
    marks.attack_start != null ? { x: marks.attack_start, label: "attack", color: theme.severity.HIGH } : null,
    marks.detected != null ? { x: marks.detected, label: "detected", color: theme.severity.CRITICAL } : null,
    marks.defense != null ? { x: marks.defense, label: "defense", color: theme.accent } : null,
  ]
    .filter(Boolean)
    // drop the label of a marker that sits within 4 s of the previous one, so labels never overprint
    .map((r, i, arr) => {
      const prev = i > 0 ? (arr[i - 1] as { x: number }) : null;
      const cur = r as { x: number; label: string; color: string };
      return prev && Math.abs(cur.x - prev.x) < 4 ? { ...cur, label: "" } : cur;
    }) as Array<{ x: number; label: string; color: string }>;

  const stateIdx = run ? SOC_STATES.indexOf(run.state as (typeof SOC_STATES)[number]) : -1;
  const last = run?.telemetry[run.telemetry.length - 1];
  const m = run?.metrics;

  return (
    <div className="stack">
      <PageHeader
        title="Cyber Range"
        eyebrow="Operations"
        icon={Swords}
        subtitle="Run a controlled attack in a virtual network and watch the real detectors catch it, explain it, and the defense you choose stop it — every number is measured from the run."
      />

      <Callout tone="info" title="How this range works">
        Recorded CICIDS2017 network flows (normal users plus the chosen attack) are replayed on a simulated clock, one
        second per step. Every flow that gets past the firewall is scored by the real frozen v1.1 model and the
        Zero-Day Gate; a source becomes an incident after {threshold} alerts in 5 s. Defenses really change which
        later flows reach the server. Modelled, not measured: traffic rates, how much each flow loads the server, and
        the 20% pass-through of a rate limit. The same seed always replays the same run.
      </Callout>

      <Tabs
        id="range-tabs"
        label="Cyber range views"
        value={tab}
        onChange={setTab}
        items={[
          { id: "run", label: "Run a scenario", icon: Play },
          { id: "experiments", label: "Experiments", icon: FlaskConical },
        ]}
      />

      {error ? <ErrorState error={error} onRetry={() => setError(null)} /> : null}

      {tab === "run" && (
        <>
          <Card title="1 · Set up the scenario" icon={Target} subtitle={scenario ? `${scenario.description} Research focus: ${scenario.research_focus}.` : undefined}>
            <div className="row" style={{ gap: 14, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div className="field" style={{ width: 250 }}>
                <label className="field-label" htmlFor="rg-scenario">Scenario</label>
                <select id="rg-scenario" className="select" value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
                  {scenarios.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <span className="field-label" id="rg-int">Attack intensity</span>
                <div className="segmented" role="radiogroup" aria-labelledby="rg-int">
                  {Object.keys(INTENSITY).map((k) => (
                    <button key={k} type="button" aria-pressed={intensity === k} onClick={() => setIntensity(k)}>
                      {k}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field" style={{ width: 230 }}>
                <label className="field-label" htmlFor="rg-det">Detector raising incidents</label>
                <select id="rg-det" className="select" value={detector} onChange={(e) => setDetector(e.target.value as typeof detector)}>
                  {Object.entries(DETECTOR_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <span className="field-label" id="rg-mode">Who responds</span>
                <div className="segmented" role="radiogroup" aria-labelledby="rg-mode">
                  <button type="button" aria-pressed={mode === "manual"} onClick={() => setMode("manual")}>I decide</button>
                  <button type="button" aria-pressed={mode === "auto"} onClick={() => setMode("auto")}>Automatic playbook</button>
                </div>
              </div>
              {mode === "auto" && (
                <>
                  <div className="field" style={{ width: 190 }}>
                    <label className="field-label" htmlFor="rg-def">Defense</label>
                    <select id="rg-def" className="select" value={defense} onChange={(e) => setDefense(e.target.value)}>
                      {Object.entries(defenses).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v.title}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field" style={{ width: 130 }}>
                    <label className="field-label" htmlFor="rg-delay">Approval delay (s)</label>
                    <input id="rg-delay" className="input mono" type="number" min={0} max={60} value={delay} onChange={(e) => setDelay(Number(e.target.value))} />
                  </div>
                </>
              )}
              <div className="field" style={{ width: 120 }}>
                <label className="field-label" htmlFor="rg-k">Alerts to raise incident</label>
                <input id="rg-k" className="input mono" type="number" min={1} max={20} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
              </div>
              <div className="field" style={{ width: 100 }}>
                <label className="field-label" htmlFor="rg-seed">Seed</label>
                <input id="rg-seed" className="input mono" type="number" min={0} value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
              </div>
              <button type="button" className="btn btn-primary" onClick={() => void start()} disabled={busy || !scenarios.length}>
                {busy && !run ? <Loader2 size={16} className="spin" aria-hidden /> : <Plus size={16} aria-hidden />}
                Start run
              </button>
            </div>
          </Card>

          {!run && (
            <EmptyState
              icon={Network}
              title="No run yet"
              description="Pick a scenario and press Start run. The clock starts with normal traffic; the attack begins after about 15 simulated seconds."
            />
          )}

          {run && (
            <>
              <Card
                title="2 · Watch it unfold"
                icon={Clock3}
                subtitle={`${run.scenario.name} · seed ${run.config.seed} · ${DETECTOR_LABEL[run.config.detector]} · ${run.config.response_mode === "manual" ? "you decide the response" : `automatic: ${defenses[run.config.defense]?.title}`}`}
                actions={
                  <div className="row" role="toolbar" aria-label="Playback" style={{ gap: 8 }}>
                    <button type="button" className="btn btn-warn" onClick={() => setPlaying((p) => !p)} disabled={run.done || run.awaiting_decision}>
                      {playing ? <Pause size={16} aria-hidden /> : <Play size={16} aria-hidden />}
                      {playing ? "Pause" : "Play"}
                    </button>
                    <label className="row" style={{ gap: 6 }}>
                      <FastForward size={15} aria-hidden className="muted" />
                      <span className="sr-only">Speed</span>
                      <select className="select select-sm" style={{ width: 70 }} value={speed} onChange={(e) => setSpeed(e.target.value)}>
                        {Object.keys(SPEED_MS).map((s) => (
                          <option key={s}>{s}</option>
                        ))}
                      </select>
                    </label>
                    <button type="button" className="btn btn-secondary" onClick={() => void step(1)} disabled={run.done || playing}>
                      <SkipForward size={16} aria-hidden /> +1 s
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={() => void step(10)} disabled={run.done || playing}>
                      +10 s
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={() => void finish()} disabled={run.done || busy}>
                      Run to end
                    </button>
                  </div>
                }
              >
                <div className="row-between" style={{ flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
                  <div className="row" style={{ gap: 8 }}>
                    <Badge tone="info">Clock {run.t} / {run.duration_s} s</Badge>
                    <Badge tone={run.stage.startsWith("ATTACK") || run.stage === "RECONNAISSANCE" ? "critical" : "neutral"}>
                      Attacker: {humanize(run.stage.toLowerCase())}
                    </Badge>
                    <StatusBadge status={humanize(run.state.toLowerCase())} />
                  </div>
                  <span className="small muted">{STATE_HELP[run.state] ?? ""}</span>
                </div>
                <ol className="stepper list-plain" aria-label="Detection and response states">
                  {SOC_STATES.map((s, i) => {
                    const st = i < stateIdx ? "done" : i === stateIdx ? "active" : undefined;
                    return (
                      <li key={s} className="step" data-state={st} aria-current={st === "active" ? "step" : undefined} title={STATE_HELP[s]}>
                        <span className="step-bar" aria-hidden />
                        <span className="step-label">{humanize(s.toLowerCase())}</span>
                      </li>
                    );
                  })}
                </ol>
              </Card>

              {run.awaiting_decision && (
                <Card tone="danger" title="3 · Your decision" icon={ShieldAlert} subtitle={`Incident on ${run.detected_family ?? "attack"} traffic. The attack keeps running while you decide — the clock is paused until you choose.`}>
                  {run.mitre_attack && (
                    <p className="small" style={{ marginTop: 0 }}>
                      Threat intelligence: MITRE ATT&CK <strong>{run.mitre_attack.tactic}</strong> ({run.mitre_attack.tactic_id}) ·{" "}
                      <a href={run.mitre_attack.url} target="_blank" rel="noreferrer">
                        {run.mitre_attack.technique_id} {run.mitre_attack.technique}
                      </a>
                      {run.mitre_attack.note ? <span className="muted"> — {run.mitre_attack.note}</span> : null}
                    </p>
                  )}
                  <div className="grid grid-3">
                    {Object.entries(defenses)
                      .filter(([k]) => k !== "recommended")
                      .map(([k, d]) => (
                        <button
                          key={k}
                          type="button"
                          className={`btn ${k === run.recommended ? "btn-primary" : "btn-secondary"}`}
                          style={{ height: "auto", padding: 12, textAlign: "left", flexDirection: "column", alignItems: "flex-start", gap: 4 }}
                          onClick={() => void respond(k)}
                          disabled={busy}
                        >
                          <strong>
                            {d.title}
                            {k === run.recommended ? " · recommended" : ""}
                          </strong>
                          <span className="small">{d.effect}</span>
                        </button>
                      ))}
                  </div>
                </Card>
              )}

              <div className="grid grid-stats">
                <StatTile label="Detection latency" icon={Timer} value={sec(m?.detection_latency_s)} hint="Attack start → incident" tone="var(--sev-critical)" />
                <StatTile label="Time to mitigate" icon={ShieldCheck} value={sec(m?.time_to_mitigate_s)} hint={m?.defense_applied ? `Defense: ${defenses[m.defense_applied]?.title ?? m.defense_applied}` : "No defense yet"} tone="var(--accent)" />
                <StatTile label="Service availability" icon={GaugeIcon} value={pct(last?.availability ?? 1, 0)} hint={`Worst during attack ${pct(m?.availability_min_during_attack, 0)}`} tone="var(--ok)" />
                <StatTile label="Attack getting through" icon={Activity} value={pct(m?.attack_success_after_defense ?? m?.attack_success_rate, 0)} hint={m?.attack_success_after_defense != null ? "after the defense" : "so far"} tone="var(--sev-high)" />
                <StatTile label="False alarms" icon={BellRing} value={String(m?.false_positive_alerts ?? 0)} hint={`${m?.false_incidents ?? 0} false incidents · flow FPR ${pct(m?.fpr_flows, 2)}`} />
                <StatTile label="Users blocked" icon={Users} value={pct(m?.collateral_rate, 1)} hint={`${m?.collateral_benign_blocked ?? 0} legitimate flows dropped`} />
              </div>

              <div className="grid grid-split">
                <Card title="Network" icon={Network} subtitle={`Attackers: ${run.attackers.map((a) => `${a.ip}${a.detected_at != null ? ` (caught at ${a.detected_at}s)` : ""}`).join(", ")}`}>
                  <NetworkTopology nodes={run.topology.nodes} edges={run.topology.edges} />
                </Card>
                <Card title="Why the incident was raised" icon={Sparkles} subtitle={run.explanation ? `SHAP (${run.explanation.actual_method}) on the flow that triggered the incident — truth: ${run.explanation.flow_family_truth}` : "Appears when the first incident is raised"}>
                  {run.explanation?.top_features?.length ? (
                    <div className="stack-sm">
                      <HorizontalBars
                        ariaLabel="Feature contributions"
                        items={run.explanation.top_features.map((f) => ({
                          label: f.feature,
                          value: f.contribution,
                          hint: `${f.feature} = ${run.explanation?.feature_values?.[f.feature] ?? "?"} → ${f.contribution.toFixed(3)}`,
                        }))}
                        positiveLabel="pushes toward attack"
                        negativeLabel="pushes toward normal"
                      />
                      <p className="small muted">{run.explanation.explanation} Attributions describe what the model relied on — they are not proof of how the attack works.</p>
                    </div>
                  ) : (
                    <p className="small muted">
                      {run.config.detector === "gate" || run.detected_family?.includes("ZERO")
                        ? "The Zero-Day Gate raised this incident; SHAP explains the frozen model, which did not flag it."
                        : "No incident yet."}
                    </p>
                  )}
                </Card>
              </div>

              <div className="grid grid-2">
                <Card title="Service availability" icon={GaugeIcon} subtitle="Share of legitimate requests the target served each second (%)">
                  <TimeSeriesArea data={chart} xKey="t" variant="line" series={[{ key: "availability", label: "availability %", color: theme.accent }]} yDomain={[0, 100]} referenceLines={refLines} ariaLabel="Availability over time" animate={false} dots={false} />
                </Card>
                <Card title="Traffic at the firewall" icon={Activity} subtitle="Attack flows sent vs. getting through, legitimate flows blocked, and alerts per second">
                  <TimeSeriesArea
                    data={chart}
                    xKey="t"
                    variant="line"
                    series={[
                      { key: "attack_sent", label: "attack sent", color: theme.severity.HIGH, dashed: true },
                      { key: "attack_passed", label: "attack through", color: theme.severity.CRITICAL },
                      { key: "benign_blocked", label: "users blocked", color: theme.series[6] },
                      { key: "alerts_false", label: "false alerts", color: theme.muted },
                    ]}
                    referenceLines={refLines}
                    ariaLabel="Traffic over time"
                    animate={false}
                    dots={false}
                  />
                </Card>
              </div>

              <div className="grid grid-2">
                <Card title="Event log" icon={ScrollText} subtitle="Every state change is an event with run ID, sequence number and simulated time" actions={<Badge tone="neutral">{run.event_count}</Badge>}>
                  <ul className="list-plain stack-sm" style={{ maxHeight: 320, overflow: "auto" }}>
                    {[...events].reverse().slice(0, 60).map((e) => (
                      <li key={e.event_id} style={{ display: "grid", gridTemplateColumns: "40px auto 1fr", gap: 8, alignItems: "baseline" }}>
                        <span className="mono small muted">{e.sim_time_s}s</span>
                        <Badge size="sm" tone={e.event_type.startsWith("detection") ? "critical" : e.event_type.startsWith("response") ? "info" : "neutral"}>
                          {e.event_type}
                        </Badge>
                        <span className="small">{describeEvent(e.event_type, e.payload)}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
                <Card title="Latest flows" icon={Activity} subtitle="What each detector said about the most recent flows">
                  <div style={{ maxHeight: 320, overflow: "auto" }}>
                    <table className="table table-dense">
                      <thead>
                        <tr>
                          <th>t</th>
                          <th>Source</th>
                          <th>Truth</th>
                          <th>Firewall</th>
                          <th>v1.1</th>
                          <th>Gate</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...run.recent_flows].reverse().map((f, i) => (
                          <tr key={`${f.t}-${i}`}>
                            <td className="mono">{f.t}</td>
                            <td className="mono small">{f.src}</td>
                            <td>{f.is_attack ? <Badge size="sm" tone="critical">{f.truth}</Badge> : <span className="small muted">normal</span>}</td>
                            <td className="small">{f.status === "blocked" ? "blocked" : "passed"}</td>
                            <td className="small">{f.frozen ? (f.frozen.alert ? f.frozen.type : "—") : ""}</td>
                            <td className="small">{f.gate ? (f.gate.alert ? f.gate.label : "—") : ""}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>

              {run.done && m && (
                <Card title="Result" icon={ShieldCheck} subtitle={m.outcome}>
                  <div className="grid grid-3 small">
                    <div>Detected attackers: <strong>{m.attackers_detected} / {m.attackers_total}</strong></div>
                    <div>Attack flows sent: <strong>{m.attack_flows_sent}</strong></div>
                    <div>Attack-flow recall: <strong>{pct(m.attack_flow_recall)}</strong> (v1.1 {pct(m.attack_flow_recall_frozen)}, gate {pct(m.attack_flow_recall_gate)})</div>
                    <div>Availability during attack: <strong>{pct(m.availability_mean_during_attack)}</strong></div>
                    <div>Recovery after defense: <strong>{sec(m.recovery_time_s)}</strong></div>
                    <div>Mitigation effectiveness: <strong>{pct(m.mitigation_effectiveness)}</strong></div>
                  </div>
                  <p className="small muted" style={{ marginTop: 10 }}>The full record (configuration, seed, every event and per-second telemetry) was saved to results/cyber_range/runs/{run.run_id}.json.</p>
                </Card>
              )}
            </>
          )}
        </>
      )}

      {tab === "experiments" && <RangeExperimentsPanel scenarios={scenarios} defenses={defenses} />}
    </div>
  );
}

function describeEvent(type: string, p: Record<string, unknown>): string {
  switch (type) {
    case "attack.stage_changed":
      return `Attacker stage: ${humanize(String(p.stage ?? "").toLowerCase())}`;
    case "run.state_changed":
      return `${humanize(String(p.from ?? "").toLowerCase())} → ${humanize(String(p.to ?? "").toLowerCase())}${p.detail ? ` — ${p.detail}` : ""}`;
    case "detection.created":
      return `Incident for ${p.source} (${p.true_attacker ? "real attacker" : "FALSE ALARM: normal user"})`;
    case "response.recommended":
      return `Playbook recommends ${humanize(String(p.recommended))}`;
    case "response.applied":
      return `Defense applied: ${humanize(String(p.action))}`;
    case "attack.mitigated":
      return `Attack contained ${p.seconds_after_defense}s after the defense`;
    case "service.recovered":
      return `Service recovered ${p.seconds_after_defense}s after the defense`;
    case "explanation.ready":
      return `Explanation ready (${p.method})`;
    case "simulation.started":
      return "Run created";
    case "topology.ready":
      return `Virtual network ready (${p.nodes} nodes)`;
    case "simulation.completed":
      return "Run complete — metrics saved";
    default:
      return humanize(type.replace(/\./g, " "));
  }
}

function RangeExperimentsPanel({ scenarios, defenses }: { scenarios: RangeScenario[]; defenses: Record<string, RangeDefense> }) {
  const [data, setData] = useState<RangeExperiments | null>(null);
  const [missing, setMissing] = useState(false);
  const [sweepScenario, setSweepScenario] = useState("ddos");
  const [sweep, setSweep] = useState<RangeSweep | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api
      .rangeExperiments()
      .then(setData)
      .catch(() => setMissing(true));
  }, []);

  async function runSweep() {
    setBusy(true);
    setError(null);
    try {
      setSweep(await api.rangeSweep({ scenarios: [sweepScenario], defenses: ["block_source", "rate_limit", "isolate_host", "monitor_only"], seeds: [1, 2, 3, 4, 5] }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const name = (id: string) => scenarios.find((s) => s.id === id)?.name ?? data?.scenarios?.[id]?.name ?? id;
  const ci = (c: { mean: number | null } | undefined, f: (v: number) => string) => (c?.mean == null ? "—" : f(c.mean));
  const p1 = (v: number) => formatPct(v, 1);
  const s1 = (v: number) => `${v.toFixed(1)} s`;

  return (
    <div className="stack">
      <Card title="Try it: compare defenses on one scenario" icon={FlaskConical} subtitle="Runs each defense on 5 seeds in the range (takes a few seconds)">
        <div className="row" style={{ gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div className="field" style={{ width: 260 }}>
            <label className="field-label" htmlFor="sw-scn">Scenario</label>
            <select id="sw-scn" className="select" value={sweepScenario} onChange={(e) => setSweepScenario(e.target.value)}>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <button type="button" className="btn btn-primary" onClick={() => void runSweep()} disabled={busy}>
            {busy ? <Loader2 size={16} className="spin" aria-hidden /> : <Play size={16} aria-hidden />} Compare defenses
          </button>
        </div>
        {error ? <ErrorState error={error} /> : null}
        {sweep && (
          <table className="table" style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>Defense</th>
                <th>Attack getting through after defense</th>
                <th>Availability during attack</th>
                <th>Users blocked</th>
                <th>Recovery time</th>
              </tr>
            </thead>
            <tbody>
              {sweep.cells.map((c) => (
                <tr key={String(c.cell.defense)}>
                  <td>{defenses[String(c.cell.defense)]?.title ?? c.cell.defense}</td>
                  <td>{ci(c.summary.attack_success_after_defense, p1)}</td>
                  <td>{ci(c.summary.availability_mean_during_attack, p1)}</td>
                  <td>{ci(c.summary.collateral_rate, p1)}</td>
                  <td>{ci(c.summary.recovery_time_s, s1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {missing && (
        <Callout tone="warn" title="Full experiment program not run yet">
          Run <code>python scripts/56_cyber_range_experiments.py</code> to generate the full suites (about 1,200 runs, two minutes).
        </Callout>
      )}

      {data && (
        <>
          <p className="small muted">
            Full experiment program · {data.seeds.length} seeds per cell · generated {new Date(data.generated_at).toLocaleString()}. Values are means over seeds.
          </p>
          {data.suites.detector && (
            <Card title="Which detector catches what" icon={Sparkles} subtitle="Share of runs where an incident was raised, and how fast, by the detector used">
              <table className="table">
                <thead>
                  <tr>
                    <th>Scenario</th>
                    {["frozen", "gate", "union"].map((d) => (
                      <th key={d}>{d === "frozen" ? "Frozen v1.1" : d === "gate" ? "Zero-Day Gate" : "Both"}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...new Set(data.suites.detector.cells.map((c) => String(c.cell.scenario)))].map((sid) => (
                    <tr key={sid}>
                      <td>{name(sid)}</td>
                      {["frozen", "gate", "union"].map((d) => {
                        const c = data.suites.detector.cells.find((x) => x.cell.scenario === sid && x.cell.detector === d);
                        const det = c?.summary.detected?.mean ?? 0;
                        return (
                          <td key={d}>
                            {det === 0 ? <Badge size="sm" tone="critical">never</Badge> : `${p1(det)} · ${ci(c?.summary.detection_latency_s, s1)}`}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
          {data.suites.defense && (
            <Card title="Defense comparison (E8)" icon={ShieldCheck} subtitle="Every scenario × every defense, automatic response after 3 s">
              <div style={{ maxHeight: 420, overflow: "auto" }}>
                <table className="table table-dense">
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      <th>Defense</th>
                      <th>Attack through after</th>
                      <th>Availability (attack)</th>
                      <th>Users blocked</th>
                      <th>Recovery</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.suites.defense.cells.map((c) => (
                      <tr key={`${c.cell.scenario}-${c.cell.defense}`}>
                        <td>{name(String(c.cell.scenario))}</td>
                        <td>{data.defenses[String(c.cell.defense)]?.title}</td>
                        <td>{ci(c.summary.attack_success_after_defense, p1)}</td>
                        <td>{ci(c.summary.availability_mean_during_attack, p1)}</td>
                        <td>{ci(c.summary.collateral_rate, p1)}</td>
                        <td>{ci(c.summary.recovery_time_s, s1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
          {data.suites.threshold && (
            <Card title="False-alarm control: alerts needed to raise an incident" icon={BellRing} subtitle="Fewer alerts = faster detection but more false incidents on normal users">
              <table className="table">
                <thead>
                  <tr>
                    <th>Scenario</th>
                    <th>Alerts needed</th>
                    <th>Detection latency</th>
                    <th>False incidents per run</th>
                  </tr>
                </thead>
                <tbody>
                  {data.suites.threshold.cells.map((c) => (
                    <tr key={`${c.cell.scenario}-${c.cell.alert_threshold}`}>
                      <td>{name(String(c.cell.scenario))}</td>
                      <td>{c.cell.alert_threshold}</td>
                      <td>{ci(c.summary.detection_latency_s, s1)}</td>
                      <td>{ci(c.summary.false_incidents, (v) => v.toFixed(1))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
          {data.suites.delay && (
            <Card title="Cost of a slow decision" icon={Timer} subtitle="How long the analyst takes to approve vs. how well the service holds up">
              <table className="table">
                <thead>
                  <tr>
                    <th>Scenario</th>
                    <th>Approval delay</th>
                    <th>Availability during attack</th>
                  </tr>
                </thead>
                <tbody>
                  {data.suites.delay.cells.map((c) => (
                    <tr key={`${c.cell.scenario}-${c.cell.approval_delay_s}`}>
                      <td>{name(String(c.cell.scenario))}</td>
                      <td>{c.cell.approval_delay_s} s</td>
                      <td>{ci(c.summary.availability_mean_during_attack, p1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
