import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { DecisionTraceTimeline } from "../components/DecisionTrace";
import { api } from "../services/api";

export function IncidentDetailPage() {
  const { incidentId } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState<Record<string, unknown> | null>(null);
  const [trace, setTrace] = useState<{
    title: string;
    steps: Array<{ stage: string; title: string; detail: string; timestamp?: string }>;
  } | null>(null);
  const [notes, setNotes] = useState("");
  const [defense, setDefense] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!incidentId) return;
    const [data, tr] = await Promise.all([
      api.getIncident(incidentId),
      api.incidentTrace(incidentId).catch(() => null),
    ]);
    setItem(data);
    setTrace(tr);
    setNotes(String(data.analyst_notes ?? ""));
    setDefense(String(data.defense_action ?? ""));
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [incidentId]);

  async function advance(status: string) {
    if (!incidentId) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateIncident(incidentId, status, {
        analyst_notes: notes || undefined,
        defense_action: defense || undefined,
      });
      setItem(updated);
      const tr = await api.incidentTrace(incidentId).catch(() => null);
      setTrace(tr);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function saveInvestigation() {
    if (!incidentId || !item) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateIncident(incidentId, String(item.status), {
        analyst_notes: notes,
        defense_action: defense,
      });
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
          <p>Analyst workspace — review evidence, advance lifecycle, simulate defense (advisory only).</p>
        </div>
        <div className="row">
          <Link className="btn btn-secondary" to="/reports">
            Back to reports
          </Link>
          {item && (
            <button className="btn btn-amber" onClick={() => void simulate()} disabled={busy}>
              Simulate this incident
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      {!item && !error && (
        <div className="panel">
          <div className="skeleton lg" style={{ width: "40%", marginBottom: "0.75rem" }} />
          <div className="skeleton" style={{ width: "70%" }} />
        </div>
      )}

      {item && (
        <>
          <div className="hero-action">
            <div>
              <div style={{ fontSize: "1.35rem", fontWeight: 650 }}>{String(item.attack_type)}</div>
              <div className="muted">
                <span className={`badge ${String(item.severity).toLowerCase()}`}>{String(item.severity)}</span>
                {" · "}Risk {String(item.risk_score)}
                {item.campaign_id ? (
                  <>
                    {" · "}
                    <Link to={`/campaigns/${encodeURIComponent(String(item.campaign_id))}`}>
                      {String(item.campaign_id)}
                    </Link>
                  </>
                ) : null}
              </div>
            </div>
            <div className="row">
              {next.slice(0, 3).map((s) => (
                <button key={s} className="btn btn-secondary" disabled={busy} onClick={() => void advance(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="split">
            <section className="panel panel-interactive stack">
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
                <strong>Recommendation:</strong> {String(item.recommendation)}
              </p>

              <label className="muted">
                Analyst notes
                <textarea
                  className="select"
                  style={{ width: "100%", minHeight: "4.5rem", display: "block", marginTop: "0.35rem" }}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </label>
              <label className="muted">
                Defense action
                <input
                  className="select"
                  style={{ width: "100%", display: "block", marginTop: "0.35rem" }}
                  value={defense}
                  onChange={(e) => setDefense(e.target.value)}
                  placeholder="e.g. rate-limit applied (advisory)"
                />
              </label>
              <div className="row">
                <button className="btn btn-primary" disabled={busy} onClick={() => void saveInvestigation()}>
                  Save investigation
                </button>
                {next.map((s) => (
                  <button key={s} className="btn btn-secondary" disabled={busy} onClick={() => void advance(s)}>
                    {s}
                  </button>
                ))}
              </div>
              {trace ? <DecisionTraceTimeline title={trace.title} steps={trace.steps} /> : null}
            </section>
            <section className="panel panel-interactive">
              <h3 style={{ marginTop: 0 }}>Lifecycle events</h3>
              {events.length === 0 && (
                <div className="empty-state">
                  <strong>No events yet</strong>
                  <p className="muted" style={{ margin: 0 }}>Advance the status to build the audit trail.</p>
                </div>
              )}
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
        </>
      )}
    </div>
  );
}
