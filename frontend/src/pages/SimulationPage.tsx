import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { NetworkTopology } from "../components/NetworkTopology";
import { CompareTable } from "../components/DecisionTrace";
import { api, SimSession } from "../services/api";

const ATTACKS = ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot"];
const INTENSITY_PRESETS: Record<string, number> = { Low: 0.35, Medium: 0.6, High: 0.9 };

const STEPS = [
  "Start normal traffic",
  "Start attack",
  "Propagate to target",
  "IDS detects",
  "Show recommendation",
  "Apply defense",
  "Recover",
];

const SPEED_MS: Record<string, number> = { "0.5x": 1600, "1x": 900, "2x": 450 };

function pct(v: unknown) {
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return `${Math.round(n * 100)}%`;
}

function SeriesBars({
  title,
  labels,
  withVals,
  withoutVals,
  format = "pct",
}: {
  title: string;
  labels: string[];
  withVals: number[];
  withoutVals: number[];
  format?: "pct" | "risk";
}) {
  if (!labels.length) return null;
  return (
    <div className="panel panel-interactive" style={{ marginBottom: "1rem" }}>
      <h4 style={{ marginTop: 0 }}>{title}</h4>
      <p className="muted" style={{ marginTop: 0, fontSize: "0.85rem" }}>
        With defense vs no-defense counterfactual (simulated).
      </p>
      {labels.map((label, i) => {
        const w = withVals[i] ?? 0;
        const o = withoutVals[i] ?? 0;
        const wPct = format === "risk" ? Math.min(100, w) : Math.min(100, w * 100);
        const oPct = format === "risk" ? Math.min(100, o) : Math.min(100, o * 100);
        return (
          <div key={`${label}-${i}`} style={{ marginBottom: "0.65rem" }}>
            <div className="mono muted" style={{ fontSize: "0.8rem", marginBottom: "0.2rem" }}>
              {label}
            </div>
            <div className="feature-bar">
              <span>defense</span>
              <div className="track">
                <div className="fill" style={{ width: `${wPct}%`, background: "var(--cyan)" }} />
              </div>
              <span className="mono muted">{format === "risk" ? w : pct(w)}</span>
            </div>
            <div className="feature-bar">
              <span>none</span>
              <div className="track">
                <div className="fill" style={{ width: `${oPct}%`, background: "var(--danger)" }} />
              </div>
              <span className="mono muted">{format === "risk" ? o : pct(o)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function SimulationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [attackType, setAttackType] = useState("DDoS");
  const [intensityLabel, setIntensityLabel] = useState("High");
  const [confidence, setConfidence] = useState(0.96);
  const [session, setSession] = useState<SimSession | null>(null);
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState("1x");
  const [error, setError] = useState<string | null>(null);
  const playRef = useRef(false);
  const sessionRef = useRef<SimSession | null>(null);

  function refreshHistory() {
    api.listSims(15).then((r) => setHistory(r.items ?? [])).catch(() => setHistory([]));
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
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
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
            break;
          }
        } catch (e) {
          if (!cancelled) {
            setError(e instanceof Error ? e.message : String(e));
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
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function replay(sessionId: string) {
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
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const m = session?.metrics ?? {};
  const lat = session?.latencies;
  const series = session?.series;

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Attack–Defense Simulation</h2>
          <p>Interactive cyber-range visualization — attack → detect → defend → recover (no real traffic).</p>
        </div>
        {session && (
          <span className={`live-chip ${playing ? "" : "off"}`}>
            <span className={`status-dot ${playing ? "on" : ""}`} />
            {playing ? "Playing" : session.state === "recovered" ? "Recovered" : `State · ${session.state}`}
          </span>
        )}
      </div>

      <div className="panel panel-interactive stack" style={{ marginBottom: "1rem" }}>
        <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
          <label className="muted">
            Attack{" "}
            <select className="select" value={attackType} onChange={(e) => setAttackType(e.target.value)}>
              {ATTACKS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
          <label className="muted">
            Intensity{" "}
            <select className="select" value={intensityLabel} onChange={(e) => setIntensityLabel(e.target.value)}>
              {Object.keys(INTENSITY_PRESETS).map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </label>
          <label className="muted">
            Confidence{" "}
            <input
              className="select"
              type="number"
              min={0.5}
              max={1}
              step={0.01}
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
              style={{ width: "5rem" }}
            />
          </label>
          <button className="btn btn-primary" onClick={createSession} disabled={busy}>
            Run simulation
          </button>
          <button
            className="btn btn-amber"
            onClick={() => setPlaying((p) => !p)}
            disabled={busy || !session || session.state === "recovered"}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <select className="select" value={speed} onChange={(e) => setSpeed(e.target.value)} disabled={!session}>
            {Object.keys(SPEED_MS).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button className="btn btn-secondary" onClick={() => advance()} disabled={busy || !session || playing}>
            Step
          </button>
          <button className="btn btn-secondary" onClick={() => advance("defend")} disabled={busy || !session || playing}>
            Apply defense
          </button>
          <button className="btn btn-danger" onClick={() => advance("reset")} disabled={busy || !session}>
            Reset
          </button>
        </div>
      </div>

      {error && <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>{error}</div>}

      {!session && (
        <div className="empty-state" style={{ marginBottom: "1rem" }}>
          <strong>Ready to simulate</strong>
          <p className="muted" style={{ margin: "0 0 0.85rem" }}>
            Configure attack intensity and confidence, then run — or replay a saved session below.
          </p>
          <ol className="muted" style={{ textAlign: "left", display: "inline-block", margin: 0 }}>
            {STEPS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </div>
      )}

      {history.length > 0 && (
        <div className="panel panel-interactive" style={{ marginBottom: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>Simulation history</h3>
          <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
            {history.map((h) => (
              <button
                key={String(h.session_id)}
                className={`btn ${session?.id === String(h.session_id) ? "btn-primary" : "btn-secondary"}`}
                type="button"
                onClick={() => replay(String(h.session_id))}
              >
                {String(h.attack_type)} · {String(h.state)} · {String(h.session_id).slice(0, 8)}
              </button>
            ))}
          </div>
        </div>
      )}

      {session && (
        <>
          <div className="panel phase-strip" style={{ marginBottom: "1rem" }}>
            {(session.phase_guide ?? []).map((p, idx) => {
              const order = (session.phase_guide ?? []).map((x) => x.state);
              const cur = order.indexOf(session.state);
              const done = cur > idx;
              const active = session.state === p.state;
              return (
                <div key={p.state} className={`phase-chip${active ? " active" : ""}${done ? " done" : ""}`}>
                  <span className="mono muted">{p.t}</span>
                  <strong>{p.label}</strong>
                </div>
              );
            })}
          </div>

          <div className="grid-stats" style={{ marginBottom: "1rem" }}>
            <div className="stat">
              <div className="label">Detection latency</div>
              <div className="value" style={{ fontSize: "1.1rem" }}>
                {lat?.detection_s != null
                  ? `${lat.detection_s}s`
                  : m.detection_delay_s != null
                    ? `${m.detection_delay_s}s`
                    : "—"}
              </div>
            </div>
            <div className="stat">
              <div className="label">Defense latency</div>
              <div className="value" style={{ fontSize: "1.1rem" }}>
                {lat?.defense_s != null
                  ? `${lat.defense_s}s`
                  : m.defense_delay_s != null
                    ? `${m.defense_delay_s}s`
                    : "—"}
              </div>
            </div>
            <div className="stat">
              <div className="label">Recovery time</div>
              <div className="value" style={{ fontSize: "1.1rem" }}>
                {lat?.recovery_s != null
                  ? `${lat.recovery_s}s`
                  : m.recovery_time_s != null
                    ? `${m.recovery_time_s}s`
                    : "—"}
              </div>
            </div>
            <div className="stat">
              <div className="label">Attack→recover</div>
              <div className="value" style={{ fontSize: "1.1rem" }}>
                {lat?.attack_to_recover_s != null ? `${lat.attack_to_recover_s}s` : "—"}
              </div>
            </div>
          </div>

          {series && series.labels.length > 0 && (
            <div className="split" style={{ marginBottom: "1rem" }}>
              <SeriesBars
                title="Traffic before / after"
                labels={series.labels}
                withVals={series.with_defense.traffic}
                withoutVals={series.without_defense.traffic}
              />
              <SeriesBars
                title="Risk before / after"
                labels={series.labels}
                withVals={series.with_defense.risk}
                withoutVals={series.without_defense.risk}
                format="risk"
              />
            </div>
          )}

          <div className="split">
            <section className="stack">
              <NetworkTopology nodes={session.nodes} edges={session.edges} />
              <div className="panel row">
                <span className={`badge ${session.severity.toLowerCase()}`}>{session.severity}</span>
                <span className="mono">State: {session.state}</span>
                <span className="mono muted">Risk {session.risk_score}</span>
                <span className="mono muted">{session.attack_type}</span>
                {session.campaign_id && <span className="mono muted">Campaign {session.campaign_id}</span>}
                {session.incident_id && <span className="mono muted">{session.incident_id}</span>}
              </div>
              {session.comparison ? (
                <CompareTable
                  without={session.comparison.without_defense}
                  withDefense={session.comparison.with_defense}
                  recoveryS={lat?.recovery_s ?? (m.recovery_time_s as number | undefined)}
                />
              ) : null}
            </section>
            <section className="panel stack">
              <h3 style={{ marginTop: 0 }}>Timeline</h3>
              <ul className="timeline">
                {session.timeline.map((t, idx) => (
                  <li key={`${t.event}-${idx}`}>
                    <strong>{t.event}</strong>
                    <div className="mono muted" style={{ fontSize: "0.78rem" }}>
                      {t.t_s != null ? `t=${t.t_s}s` : ""}
                      {t.timestamp ? ` · ${t.timestamp}` : ""}
                    </div>
                    <div className="muted">{t.detail}</div>
                  </li>
                ))}
              </ul>
              {session.narrative && session.narrative.length > 0 && (
                <div>
                  <h4>Attack narrative</h4>
                  <ol>
                    {session.narrative.map((n, i) => (
                      <li key={i}>{n}</li>
                    ))}
                  </ol>
                </div>
              )}
              <div className="mono muted">
                Metrics (simulated): peak={String(m.peak_traffic ?? "—")} stress=
                {String(m.server_stress ?? "—")} remaining=
                {String(m.remaining_malicious ?? "—")} persistence={String(m.persistence ?? "—")}
              </div>
              {session.disclaimer && (
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  {session.disclaimer}
                </p>
              )}
              <p className="muted" style={{ fontSize: "0.85rem" }}>
                Defense effectiveness values are <strong>simulation assumptions</strong> for comparative
                visualization, not empirically measured real-world mitigation rates.
              </p>
              <div>
                <h4>Recommendation</h4>
                <p style={{ marginTop: 0 }}>{session.recommendation.primary}</p>
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  {session.recommendation.rationale}
                </p>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
