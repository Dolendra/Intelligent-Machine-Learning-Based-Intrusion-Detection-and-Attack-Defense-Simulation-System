import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  FileWarning,
  FlaskConical,
  History,
  Loader2,
  Network,
  NotebookPen,
  Percent,
  ShieldAlert,
  ShieldCheck,
  Undo2,
  XCircle,
} from "lucide-react";
import { api, type DecisionTrace, type IncidentDetail, type ResponseAction } from "../services/api";
import { useAuth } from "../app/auth";
import { DecisionTraceTimeline } from "../components/DecisionTrace";
import { Badge, SeverityBadge, StatusBadge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton, SkeletonText } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { useToast } from "../components/ui/Toast";
import { Gauge } from "../components/charts";
import { formatDateTime, formatPct, formatRelative, humanize } from "../lib/format";
import { normalizeRisk } from "../lib/severity";

const WORKFLOW = ["Proposed", "Dry run", "Decision", "Rollback"] as const;

function workflowIndex(a: ResponseAction | null): number {
  if (!a) return -1;
  const s = String(a.status).toUpperCase();
  if (/ROLLED|EXPIRED/.test(s)) return 3;
  if (/APPROVED|REJECTED|EXECUTING|SUCCEEDED|VERIFIED|ACTIVE|FAILED/.test(s)) return 2;
  // "Dry run" is reached only once a dry run actually ran (every proposal already carries a preview)
  const dryRan = /DRY/.test(s) || (a.audit ?? []).some((e) => /dry[-_ ]?run/i.test(JSON.stringify(e)));
  if (dryRan) return 1;
  return 0;
}

export function IncidentDetailPage() {
  const { incidentId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { can } = useAuth();
  const [item, setItem] = useState<IncidentDetail | null>(null);
  const [trace, setTrace] = useState<DecisionTrace | null>(null);
  const [notes, setNotes] = useState("");
  const [defense, setDefense] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [responseActions, setResponseActions] = useState<ResponseAction[]>([]);
  const [activeResponse, setActiveResponse] = useState<ResponseAction | null>(null);

  const canPropose = can("write_response");
  const canApprove = can("approve_response");

  const loadResponses = useCallback(async () => {
    if (!incidentId) return;
    const list = await api.listIncidentResponses(incidentId);
    setResponseActions(list.items);
    setActiveResponse(list.items.find((a) => a.pending_approval) || list.items[0] || null);
  }, [incidentId]);

  const load = useCallback(async () => {
    if (!incidentId) return;
    try {
      const [data, tr] = await Promise.all([api.getIncident(incidentId), api.incidentTrace(incidentId).catch(() => null)]);
      setItem(data);
      setTrace(tr);
      setNotes(data.analyst_notes ?? "");
      setDefense(data.defense_action ?? "");
      setError(null);
      await loadResponses().catch(() => {
        setResponseActions([]);
        setActiveResponse(null);
      });
    } catch (e) {
      setError(e);
    }
  }, [incidentId, loadResponses]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run<T>(key: string, fn: () => Promise<T>, success?: string): Promise<T | undefined> {
    setBusy(key);
    try {
      const out = await fn();
      if (success) toast.success(success);
      return out;
    } catch (e) {
      toast.error(e, `${humanize(key)} failed`);
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function advance(status: string) {
    if (!incidentId) return;
    const updated = await run(
      "status",
      () => api.updateIncident(incidentId, status, { analyst_notes: notes || undefined, defense_action: defense || undefined }),
      `Status → ${humanize(status)}`
    );
    if (updated) {
      setItem(updated);
      setTrace(await api.incidentTrace(incidentId).catch(() => null));
    }
  }

  async function saveInvestigation() {
    if (!incidentId || !item) return;
    const updated = await run(
      "save",
      () => api.updateIncident(incidentId, item.status, { analyst_notes: notes, defense_action: defense }),
      "Investigation saved"
    );
    if (updated) setItem(updated);
  }

  async function simulate() {
    if (!incidentId) return;
    const session = await run("simulate", () => api.simulateIncident(incidentId));
    if (session) navigate(`/simulation?session=${encodeURIComponent(session.id)}`);
  }

  async function responseStep(key: string, fn: (id: string) => Promise<{ action: ResponseAction }>, msg: string) {
    if (!activeResponse?.action_id) return;
    const out = await run(key, () => fn(activeResponse.action_id), msg);
    if (out) {
      setActiveResponse(out.action);
      await loadResponses().catch(() => undefined);
    }
  }

  async function proposeResponse() {
    if (!incidentId) return;
    const action = await run("propose", () => api.proposeIncidentResponse(incidentId), "Response proposed");
    if (action) {
      setActiveResponse(action);
      await loadResponses().catch(() => undefined);
    }
  }

  const next = item?.allowed_next_statuses ?? [];
  const events = item?.events ?? [];
  const pending = Boolean(activeResponse?.pending_approval);
  const canRollback =
    Boolean(activeResponse) &&
    activeResponse?.reversible !== false &&
    ["ACTIVE", "VERIFIED", "SUCCEEDED"].includes(String(activeResponse?.status)) &&
    canApprove;
  const wfIdx = workflowIndex(activeResponse);
  const isBusy = busy !== null;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Incident"
        icon={FileWarning}
        title={incidentId ? `Incident ${incidentId}` : "Incident"}
        subtitle="Analyst workspace — review evidence, dry-run a response, approve or reject. No live mitigation is executed."
        actions={
          <>
            <Link className="btn btn-secondary" to="/reports">
              <ArrowLeft size={16} aria-hidden /> Reports
            </Link>
            {item && (
              <button type="button" className="btn btn-warn" onClick={() => void simulate()} disabled={isBusy}>
                {busy === "simulate" ? <Loader2 size={16} className="spin" aria-hidden /> : <Network size={16} aria-hidden />} Simulate
              </button>
            )}
          </>
        }
      />

      {error ? <ErrorState error={error} title="Could not load incident" onRetry={() => void load()} /> : null}

      {!item && !error && (
        <div className="grid grid-split">
          <Card>
            <Skeleton width="40%" height={24} />
            <div style={{ height: 14 }} />
            <SkeletonText lines={4} />
          </Card>
          <Card>
            <Skeleton height={180} radius={90} />
          </Card>
        </div>
      )}

      {item && (
        <>
          <Card tone={/CRITICAL|HIGH/i.test(item.severity) ? "danger" : "default"}>
            <div className="hero">
              <Gauge value={normalizeRisk(item.risk_score)} display={String(item.risk_score)} label="Risk" ariaLabel={`Risk ${item.risk_score}`} size={220} />
              <div className="stack">
                <div>
                  <div className="muted small">Detected attack</div>
                  <div className="verdict" data-attack="true">
                    {item.attack_type}
                  </div>
                </div>
                <div className="row" style={{ gap: 6 }}>
                  <SeverityBadge severity={item.severity} />
                  <StatusBadge status={item.status} />
                  {item.campaign_id && (
                    <Link to={`/campaigns/${encodeURIComponent(item.campaign_id)}`}>
                      <Badge tone="accent">Campaign {item.campaign_id}</Badge>
                    </Link>
                  )}
                  {item.hit_count && item.hit_count > 1 ? <Badge tone="info">{item.hit_count} hits</Badge> : null}
                </div>
                <div className="grid grid-stats">
                  <StatTile label="Confidence" icon={Percent} value={formatPct(item.confidence)} compact />
                  <StatTile
                    label="Detected"
                    icon={History}
                    value={formatRelative(item.created_at)}
                    hint={/ago|now/.test(formatRelative(item.created_at)) ? formatDateTime(item.created_at) : undefined}
                    compact
                  />
                  <StatTile label="Source" icon={ShieldAlert} value={item.source_ref ?? "—"} compact />
                </div>
                {item.recommendation ? (
                  <Callout tone="info" title="Recommendation">
                    {item.recommendation}
                  </Callout>
                ) : null}
                {next.length > 0 && (
                  <div className="row" style={{ gap: 6 }}>
                    <span className="muted small">Move to:</span>
                    {next.map((s) => (
                      <button key={s} type="button" className="btn btn-secondary btn-sm" disabled={isBusy} onClick={() => void advance(s)}>
                        {humanize(s)}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Card>

          <Card
            title="Controlled response"
            subtitle="Dry-run and controlled test adapters only — no live firewall or EDR changes."
            icon={ShieldCheck}
            actions={
              <button type="button" className="btn btn-primary" disabled={isBusy || !canPropose} onClick={() => void proposeResponse()}>
                {busy === "propose" ? <Loader2 size={16} className="spin" aria-hidden /> : <ClipboardList size={16} aria-hidden />} Propose response
              </button>
            }
          >
            <div className="stack">
              <ol className="stepper list-plain" aria-label="Response workflow">
                {WORKFLOW.map((w, i) => (
                  <li key={w} className="step" data-state={i < wfIdx ? "done" : i === wfIdx ? "active" : undefined}>
                    <span className="step-bar" aria-hidden />
                    <span className="step-label">{w}</span>
                    <span className="step-meta">Step {i + 1}</span>
                  </li>
                ))}
              </ol>

              {!canPropose && <Callout tone="warn">Your role cannot propose responses (write_response permission required).</Callout>}

              {activeResponse ? (
                <div className="grid grid-split">
                  <div className="stack">
                    <div>
                      <div className="muted small">Recommended action</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                        <span className="mono">{humanize(activeResponse.action_type)}</span>
                        {activeResponse.target ? (
                          <>
                            {" "}
                            → <span className="mono">{activeResponse.target}</span>
                          </>
                        ) : null}
                      </div>
                    </div>
                    <p className="text-2">{activeResponse.dry_run_preview || activeResponse.result || activeResponse.reason || "No preview yet — run a dry run."}</p>
                    <div className="row" style={{ gap: 6 }}>
                      <Badge tone="neutral">{activeResponse.mode || "DRY_RUN"}</Badge>
                      <StatusBadge status={activeResponse.approval_status || activeResponse.status} />
                      <span className="muted small mono">
                        {activeResponse.adapter || "dry_run"} · {activeResponse.action_id}
                      </span>
                    </div>
                    <div className="row" style={{ gap: 8 }}>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        disabled={isBusy || !canPropose}
                        onClick={() => void responseStep("dry-run", api.dryRunResponse, "Dry run complete")}
                      >
                        <FlaskConical size={16} aria-hidden /> Dry run
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary"
                        disabled={isBusy || !pending || !canApprove}
                        onClick={() => void responseStep("approve", api.approveResponse, "Action approved")}
                      >
                        <CheckCircle2 size={16} aria-hidden /> Approve &amp; execute
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger"
                        disabled={isBusy || !pending || !canApprove}
                        onClick={() => void responseStep("reject", (id) => api.rejectResponse(id, "Rejected from incident UI"), "Action rejected")}
                      >
                        <XCircle size={16} aria-hidden /> Reject
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        disabled={isBusy || !canRollback}
                        onClick={() => void responseStep("rollback", api.rollbackResponse, "Action rolled back")}
                      >
                        <Undo2 size={16} aria-hidden /> Rollback
                      </button>
                    </div>
                    {responseActions.length > 1 && (
                      <div className="field">
                        <label className="field-label" htmlFor="prior-actions">
                          Prior actions for this incident
                        </label>
                        <select
                          id="prior-actions"
                          className="select select-sm"
                          value={activeResponse.action_id}
                          onChange={(e) => setActiveResponse(responseActions.find((a) => a.action_id === e.target.value) ?? null)}
                        >
                          {responseActions.map((a) => (
                            <option key={a.action_id} value={a.action_id}>
                              {humanize(a.action_type)} · {humanize(a.status)} · {a.action_id}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                  <div>
                    <h4 style={{ marginBottom: 8 }}>Audit trail</h4>
                    {Array.isArray(activeResponse.audit) && activeResponse.audit.length > 0 ? (
                      <ol className="timeline">
                        {activeResponse.audit.slice(-6).map((ev, idx) => (
                          <li key={idx}>
                            <div className="timeline-title">{humanize(ev.event)}</div>
                            <div className="timeline-meta">
                              {formatDateTime(ev.timestamp)} · {ev.actor ?? "system"}
                            </div>
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <p className="muted small">No audit events yet.</p>
                    )}
                  </div>
                </div>
              ) : (
                <EmptyState compact title="No response action yet" description="Propose one to open the dry-run / approval gate." />
              )}
            </div>
          </Card>

          <div className="grid grid-split">
            <Card title="Investigation" subtitle="Notes and defense actions are saved with the incident" icon={NotebookPen}>
              <div className="stack">
                <div className="field">
                  <label className="field-label" htmlFor="analyst-notes">
                    Analyst notes
                  </label>
                  <textarea id="analyst-notes" className="textarea" value={notes} onChange={(e) => setNotes(e.target.value)} />
                </div>
                <div className="field">
                  <label className="field-label" htmlFor="defense-action">
                    Defense action
                  </label>
                  <input
                    id="defense-action"
                    className="input"
                    value={defense}
                    onChange={(e) => setDefense(e.target.value)}
                    placeholder="e.g. rate-limit applied (advisory)"
                  />
                </div>
                <div className="row">
                  <button type="button" className="btn btn-primary" disabled={isBusy} onClick={() => void saveInvestigation()}>
                    {busy === "save" ? <Loader2 size={16} className="spin" aria-hidden /> : null} Save investigation
                  </button>
                </div>
                {trace ? <DecisionTraceTimeline title={trace.title} steps={trace.steps} /> : null}
              </div>
            </Card>
            <Card title="Lifecycle events" subtitle="Status changes and who made them" icon={History}>
              {events.length === 0 ? (
                <EmptyState compact title="No events yet" description="Advance the status to build the audit trail." />
              ) : (
                <ol className="timeline">
                  {events.map((e, idx) => (
                    <li key={idx}>
                      <div className="timeline-title">
                        {e.old_status ? `${humanize(e.old_status)} → ${humanize(e.new_status)}` : `Opened as ${humanize(e.new_status)}`}
                      </div>
                      <div className="timeline-meta">
                        {formatDateTime(e.timestamp)} · {e.actor ?? "system"}
                      </div>
                      {e.notes ? <div className="timeline-detail">{e.notes}</div> : null}
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
