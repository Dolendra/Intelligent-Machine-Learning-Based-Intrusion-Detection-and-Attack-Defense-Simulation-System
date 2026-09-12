import { useEffect, useState } from "react";
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

export function SimulationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [attackType, setAttackType] = useState("DDoS");
  const [session, setSession] = useState<SimSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  async function createSession() {
    setBusy(true);
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
    setBusy(true);
    setError(null);
    try {
      const s = await api.advanceSim(session.id, action);
      setSession(s);
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
        <button className="btn btn-secondary" onClick={() => advance()} disabled={busy || !session}>
          Next state
        </button>
        <button className="btn btn-amber" onClick={() => advance("defend")} disabled={busy || !session}>
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
      )}
    </div>
  );
}
