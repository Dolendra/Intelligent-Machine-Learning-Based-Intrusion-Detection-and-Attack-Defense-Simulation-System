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
  const [responseActions, setResponseActions] = useState<Array<Record<string, unknown>>>([]);
  const [activeResponse, setActiveResponse] = useState<Record<string, unknown> | null>(null);

  async function loadResponses() {
    if (!incidentId) return;
    const list = await api.listIncidentResponses(incidentId);
    setResponseActions(list.items);
    const pending = list.items.find((a) => a.pending_approval) || list.items[0] || null;
    setActiveResponse(pending);
  }

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
    await loadResponses().catch(() => {
      setResponseActions([]);
      setActiveResponse(null);
    });
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

  async function proposeResponse() {
    if (!incidentId) return;
    setBusy(true);
    setError(null);
    try {
      const action = await api.proposeIncidentResponse(incidentId);
      setActiveResponse(action);
      await loadResponses();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function dryRunActive() {
    if (!activeResponse?.action_id) return;
    setBusy(true);
    setError(null);
    try {
      const out = await api.dryRunResponse(String(activeResponse.action_id));
      setActiveResponse(out.action as Record<string, unknown>);
      await loadResponses();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function approveActive() {
    if (!activeResponse?.action_id) return;
    setBusy(true);
    setError(null);
    try {
      const out = await api.approveResponse(String(activeResponse.action_id));
      setActiveResponse(out.action as Record<string, unknown>);
      await loadResponses();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function rejectActive() {
    if (!activeResponse?.action_id) return;
    setBusy(true);
    setError(null);
    try {
      const out = await api.rejectResponse(String(activeResponse.action_id), "Rejected from incident UI");
      setActiveResponse(out.action as Record<string, unknown>);
      await loadResponses();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const next = (item?.allowed_next_statuses as string[] | undefined) ?? [];
  const events = (item?.events as Array<Record<string, unknown>> | undefined) ?? [];
  const pending = Boolean(activeResponse?.pending_approval);

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Incident {incidentId}</h2>
          <p>Analyst workspace — review evidence, dry-run response, approve or reject (no live mitigation).</p>
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

          <section className="panel panel-interactive" style={{ marginBottom: "1rem" }}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ marginTop: 0, marginBottom: "0.35rem" }}>Controlled response (P2)</h3>
                <p className="muted" style={{ margin: 0 }}>
                  Default mode: <strong>DRY_RUN</strong> — approval never changes a real network.
                </p>
              </div>
              <button className="btn btn-primary" disabled={busy} onClick={() => void proposeResponse()}>
                Propose response
              </button>
            </div>

            {activeResponse ? (
              <div style={{ marginTop: "1rem" }}>
                <div style={{ fontSize: "1.1rem", fontWeight: 650 }}>
                  {String(item.severity)} — {String(item.attack_type)}
                </div>
                <div className="muted">Risk: {String(item.risk_score)}</div>
                <p style={{ marginBottom: "0.35rem" }}>
                  <strong>Recommended action</strong>
                  <br />
                  <span className="mono">{String(activeResponse.action_type)}</span> →{" "}
                  <span className="mono">{String(activeResponse.target)}</span>
                </p>
                <p className="muted" style={{ marginTop: 0 }}>
                  {String(activeResponse.dry_run_preview || activeResponse.result || activeResponse.reason)}
                </p>
                <div className="row" style={{ marginBottom: "0.75rem" }}>
                  <span className="live-chip off">DRY RUN</span>
                  <span className="badge">{String(activeResponse.approval_status || activeResponse.status)}</span>
                  <span className="muted mono" style={{ fontSize: "0.8rem" }}>
                    {String(activeResponse.action_id)}
                  </span>
                </div>
                <div className="row">
                  <button className="btn btn-secondary" disabled={busy} onClick={() => void dryRunActive()}>
                    Dry run
                  </button>
                  <button className="btn btn-primary" disabled={busy || !pending} onClick={() => void approveActive()}>
                    Approve
                  </button>
                  <button className="btn btn-secondary" disabled={busy || !pending} onClick={() => void rejectActive()}>
                    Reject
                  </button>
                </div>
                {Array.isArray(activeResponse.audit) && (activeResponse.audit as unknown[]).length > 0 && (
                  <ul className="timeline" style={{ marginTop: "1rem" }}>
                    {(activeResponse.audit as Array<Record<string, unknown>>).slice(-6).map((ev, idx) => (
                      <li key={idx}>
                        <strong>{String(ev.event)}</strong>
                        <div className="muted mono">
                          {String(ev.timestamp ?? "")} · {String(ev.actor ?? "system")}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <p className="muted" style={{ marginBottom: 0, marginTop: "0.75rem" }}>
                No response action yet. Propose one to open the dry-run / approval gate.
              </p>
            )}

            {responseActions.length > 1 && (
              <div style={{ marginTop: "1rem" }}>
                <div className="muted" style={{ marginBottom: "0.35rem" }}>
                  Prior actions for this incident
                </div>
                <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
                  {responseActions.map((a) => (
                    <li key={String(a.action_id)}>
                      <button
                        type="button"
                        className="mono"
                        style={{
                          background: "none",
                          border: "none",
                          padding: 0,
                          cursor: "pointer",
                          color: "inherit",
                          textDecoration: "underline",
                        }}
                        onClick={() => setActiveResponse(a)}
                      >
                        {String(a.action_type)} · {String(a.status)} · {String(a.action_id)}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

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
                  <p className="muted" style={{ margin: 0 }}>
                    Advance the status to build the audit trail.
                  </p>
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
