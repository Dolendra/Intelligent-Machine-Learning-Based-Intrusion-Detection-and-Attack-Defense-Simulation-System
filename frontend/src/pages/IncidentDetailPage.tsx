import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../services/api";

export function IncidentDetailPage() {
  const { incidentId } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!incidentId) return;
    const data = await api.getIncident(incidentId);
    setItem(data);
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [incidentId]);

  async function advance(status: string) {
    if (!incidentId) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateIncident(incidentId, status);
      setItem(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function simulate() {
    if (!incidentId) return;
    setBusy(true);
    try {
      const session = await api.simulateIncident(incidentId);
      navigate(`/simulation?session=${encodeURIComponent(session.id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const next = (item?.allowed_next_statuses as string[] | undefined) ?? [];
  const events = (item?.events as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Incident {incidentId}</h2>
          <p>Analyst lifecycle workspace — advisory decision support only.</p>
        </div>
        <Link className="btn btn-secondary" to="/reports">
          Back to reports
        </Link>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      {!item && !error && <div className="panel">Loading…</div>}

      {item && (
        <div className="split">
          <section className="panel stack">
            <div className="grid-stats">
              <div className="stat">
                <div className="label">Attack</div>
                <div className="value" style={{ fontSize: "1.2rem" }}>
                  {String(item.attack_type)}
                </div>
              </div>
              <div className="stat">
                <div className="label">Risk</div>
                <div className="value">{String(item.risk_score)}</div>
              </div>
              <div className="stat">
                <div className="label">Confidence</div>
                <div className="value">{(Number(item.confidence) * 100).toFixed(0)}%</div>
              </div>
              <div className="stat">
                <div className="label">Status</div>
                <div className="value" style={{ fontSize: "1rem" }}>
                  {String(item.status)}
                </div>
              </div>
            </div>
            <p>
              <span className={`badge ${String(item.severity).toLowerCase()}`}>{String(item.severity)}</span>
            </p>
            <p>
              <strong>Recommendation:</strong> {String(item.recommendation)}
            </p>
            <div className="row">
              <button className="btn btn-amber" onClick={() => void simulate()} disabled={busy}>
                Simulate
              </button>
              {next.map((s) => (
                <button key={s} className="btn btn-secondary" disabled={busy} onClick={() => void advance(s)}>
                  {s}
                </button>
              ))}
            </div>
          </section>
          <section className="panel">
            <h3 style={{ marginTop: 0 }}>Timeline</h3>
            {events.length === 0 && <p className="muted">No events recorded yet.</p>}
            <ul className="timeline">
              {events.map((e, idx) => (
                <li key={idx}>
                  <strong>
                    {String(e.old_status ?? "—")} → {String(e.new_status)}
                  </strong>
                  <div className="muted mono">
                    {String(e.timestamp ?? "")} · {String(e.actor ?? "system")}
                  </div>
                  {e.notes ? <div className="muted">{String(e.notes)}</div> : null}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
