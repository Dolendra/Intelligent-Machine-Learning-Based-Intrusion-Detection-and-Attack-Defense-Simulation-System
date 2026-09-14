import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";

type Dep = { status?: string; detail?: string; depth?: number | null };
type Alert = { id: string; severity: string; message: string; component?: string; value?: unknown };

function depTone(status?: string): string {
  if (status === "ok" || status === "ready") return "var(--ok)";
  if (status === "degraded") return "var(--amber)";
  return "var(--danger)";
}

export function SystemPage() {
  const [ops, setOps] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setOps(await api.opsStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const deps = (ops?.dependencies as Record<string, Dep> | undefined) ?? {};
  const perf = (ops?.performance as Record<string, number | null> | undefined) ?? {};
  const security = (ops?.security as Record<string, number> | undefined) ?? {};
  const response = (ops?.response as Record<string, number> | undefined) ?? {};
  const detection = (ops?.detection as Record<string, unknown> | undefined) ?? {};
  const queue = (ops?.queue as Record<string, unknown> | undefined) ?? {};
  const alerts = (ops?.alerts as Alert[] | undefined) ?? [];
  const ready = ops?.readiness as { ready?: boolean; status?: string } | undefined;

  return (
    <>
      <header className="page-header" style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
        <div>
          <p className="muted" style={{ fontSize: "0.85rem", letterSpacing: "0.04em", textTransform: "uppercase" }}>
            Operations · P7
          </p>
          <h2>System status</h2>
          <p>Operational health and signals — separate from the SOC incident dashboard.</p>
        </div>
        <button className="btn btn-secondary" disabled={busy} onClick={() => void refresh()}>
          {busy ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {error && (
        <div className="panel rise" style={{ borderColor: "rgba(227,93,106,.45)", background: "var(--danger-dim)" }}>
          <strong>Ops snapshot unavailable.</strong> <span className="muted">{error}</span>
        </div>
      )}

      <section className="panel rise">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3>Dependencies</h3>
          <span className="mono muted">{ready?.ready ? "READY" : "NOT_READY"}</span>
        </div>
        <div className="grid-stats" style={{ marginTop: "0.85rem" }}>
          {Object.entries(deps).map(([name, info]) => (
            <div className="stat" key={name}>
              <div className="label" style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span className="status-dot" style={{ background: depTone(info.status) }} />
                {name.replace(/_/g, " ")}
              </div>
              <div className="value" style={{ fontSize: "1rem" }}>
                {info.status ?? "—"}
              </div>
              <div className="muted" style={{ fontSize: "0.78rem", marginTop: "0.25rem" }}>
                {info.detail}
                {typeof info.depth === "number" ? ` · depth ${info.depth}` : ""}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel rise">
        <h3>Performance</h3>
        <div className="grid-stats" style={{ marginTop: "0.85rem" }}>
          <div className="stat">
            <div className="label">Requests</div>
            <div className="value">{perf.requests_total ?? "—"}</div>
          </div>
          <div className="stat">
            <div className="label">P95 latency</div>
            <div className="value">{perf.p95_latency_ms != null ? `${perf.p95_latency_ms}ms` : "—"}</div>
          </div>
          <div className="stat">
            <div className="label">Queue depth</div>
            <div className="value">{(queue.queue_depth as number | undefined) ?? "—"}</div>
          </div>
          <div className="stat">
            <div className="label">Flows</div>
            <div className="value">{(detection.flows_processed_total as number | undefined) ?? "—"}</div>
          </div>
        </div>
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "0.9rem" }}>
        <section className="panel rise">
          <h3>Security</h3>
          <div className="grid-stats" style={{ marginTop: "0.85rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
            <div className="stat">
              <div className="label">Auth failures</div>
              <div className="value">{security.authentication_failures ?? 0}</div>
            </div>
            <div className="stat">
              <div className="label">403 denials</div>
              <div className="value">{security.authorization_denials ?? 0}</div>
            </div>
            <div className="stat">
              <div className="label">Rate limits</div>
              <div className="value">{security.rate_limit_hits ?? 0}</div>
            </div>
            <div className="stat">
              <div className="label">Validation</div>
              <div className="value">{security.validation_failures ?? 0}</div>
            </div>
          </div>
        </section>

        <section className="panel rise">
          <h3>Response</h3>
          <div className="grid-stats" style={{ marginTop: "0.85rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
            <div className="stat">
              <div className="label">Pending</div>
              <div className="value">{response.pending_approvals ?? 0}</div>
            </div>
            <div className="stat">
              <div className="label">Verified</div>
              <div className="value">{response.verified_actions ?? 0}</div>
            </div>
            <div className="stat">
              <div className="label">Failed</div>
              <div className="value">{response.failed_actions_open ?? response.actions_failed ?? 0}</div>
            </div>
            <div className="stat">
              <div className="label">Rolled back</div>
              <div className="value">{response.rolled_back_or_expired ?? 0}</div>
            </div>
          </div>
        </section>
      </div>

      <section className="panel rise">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3>Active alerts</h3>
          <span className="muted">{alerts.length ? `${alerts.length} open` : "none"}</span>
        </div>
        {alerts.length === 0 ? (
          <p className="muted" style={{ marginTop: "0.75rem" }}>
            No threshold conditions require attention.
          </p>
        ) : (
          <div style={{ display: "grid", gap: "0.55rem", marginTop: "0.75rem" }}>
            {alerts.map((a) => (
              <div
                key={a.id}
                className="panel"
                style={{
                  margin: 0,
                  padding: "0.75rem 1rem",
                  background: a.severity === "critical" ? "var(--danger-dim)" : "var(--amber-dim)",
                }}
              >
                <strong>{a.message}</strong>
                <div className="muted mono" style={{ fontSize: "0.8rem" }}>
                  {a.id}
                  {a.component ? ` · ${a.component}` : ""}
                  {a.value != null ? ` · ${String(a.value)}` : ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
