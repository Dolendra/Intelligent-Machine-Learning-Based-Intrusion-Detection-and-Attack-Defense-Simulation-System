import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { NetworkTopology } from "../components/NetworkTopology";
import { api, SimSession } from "../services/api";

const ATTACKS = ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot"];

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

export function SimulationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [attackType, setAttackType] = useState("DDoS");
  const [session, setSession] = useState<SimSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState("1x");
  const [error, setError] = useState<string | null>(null);
  const playRef = useRef(false);
  const sessionRef = useRef<SimSession | null>(null);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

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
      const s = await api.startSim(attackType);
      setSession(s);
      setSearchParams({ session: s.id });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
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
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Attack–Defense Simulation</h2>
          <p>Controlled visualization only — no real attacks are launched.</p>
        </div>
      </div>

      <div className="panel row" style={{ marginBottom: "1rem" }}>
        <select className="select" value={attackType} onChange={(e) => setAttackType(e.target.value)}>
          {ATTACKS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={createSession} disabled={busy}>
          New scenario
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

      {error && <div className="panel" style={{ marginBottom: "1rem" }}>{error}</div>}

      {!session && (
        <div className="panel">
          <p className="muted">
            Create a scenario, or open one from Detection via{" "}
            <span className="mono">Simulate this incident</span>.
          </p>
          <ol className="muted">
            {STEPS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
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

          <div className="split">
            <section className="stack">
              <NetworkTopology nodes={session.nodes} edges={session.edges} />
              <div className="panel row">
                <span className={`badge ${session.severity.toLowerCase()}`}>{session.severity}</span>
                <span className="mono">State: {session.state}</span>
                <span className="mono muted">Risk {session.risk_score}</span>
                <span className="mono muted">{session.attack_type}</span>
                {session.incident_id && <span className="mono muted">{session.incident_id}</span>}
              </div>
              {session.comparison && (
                <div className="panel compare-grid">
                  <div>
                    <h4 style={{ marginTop: 0 }}>Without defense (peak)</h4>
                    <p className="mono muted">
                      traffic {session.comparison.without_defense.peak_traffic} · stress{" "}
                      {session.comparison.without_defense.server_stress} · risk{" "}
                      {session.comparison.without_defense.risk}
                    </p>
                  </div>
                  <div>
                    <h4 style={{ marginTop: 0 }}>With defense (simulated)</h4>
                    <p className="mono muted">
                      traffic {session.comparison.with_defense.peak_traffic} · stress{" "}
                      {session.comparison.with_defense.server_stress} · risk {session.comparison.with_defense.risk} ·
                      blocked {session.comparison.with_defense.traffic_blocked}
                    </p>
                  </div>
                </div>
              )}
            </section>
            <section className="panel stack">
              <h3 style={{ marginTop: 0 }}>Timeline</h3>
              <ul className="timeline">
                {session.timeline.map((t, idx) => (
                  <li key={`${t.event}-${idx}`}>
                    <strong>{t.event}</strong>
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
              {session.metrics && (
                <div className="mono muted">
                  Metrics (simulated): peak={session.metrics.peak_traffic ?? "—"} stress=
                  {session.metrics.server_stress ?? "—"} blocked={session.metrics.traffic_blocked ?? "—"}
                </div>
              )}
              {session.disclaimer && (
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  {session.disclaimer}
                </p>
              )}
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
