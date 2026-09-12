import { useEffect, useState } from "react";
import { api } from "../services/api";

export function ReportsPage() {
  const [incidents, setIncidents] = useState<Array<Record<string, unknown>>>([]);
  const [analytics, setAnalytics] = useState<{
    total_incidents: number;
    by_severity: Record<string, number>;
    by_attack_type: Record<string, number>;
    by_status?: Record<string, number>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    const [i, a] = await Promise.all([api.incidents(), api.analytics()]);
    setIncidents(i.items);
    setAnalytics(a);
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  async function changeStatus(incidentId: string, status: string) {
    setBusyId(incidentId);
    setError(null);
    try {
      await api.updateIncident(incidentId, status);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyId(null);
    }
  }

  const total = analytics?.total_incidents ?? 0;

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Reports & Analytics</h2>
          <p>Persisted incident history from the IDS decision-support pipeline (not live packet capture).</p>
        </div>
        <div className="row">
          <button
            className="btn btn-secondary"
            onClick={() => api.downloadExport("incidents.csv").catch((e) => setError(String(e)))}
          >
            Export CSV
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => api.downloadExport("incidents.json").catch((e) => setError(String(e)))}
          >
            Export JSON
          </button>
        </div>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      <div className="grid-stats">
        <div className="stat">
          <div className="label">Incidents</div>
          <div className="value">{total}</div>
        </div>
        <div className="stat">
          <div className="label">Critical</div>
          <div className="value" style={{ color: "var(--danger)" }}>
            {analytics?.by_severity?.CRITICAL ?? 0}
          </div>
        </div>
        <div className="stat">
          <div className="label">High</div>
          <div className="value" style={{ color: "#ff9d5c" }}>
            {analytics?.by_severity?.HIGH ?? 0}
          </div>
        </div>
        <div className="stat">
          <div className="label">Attack families</div>
          <div className="value">{Object.keys(analytics?.by_attack_type ?? {}).length}</div>
        </div>
      </div>

      <div className="split" style={{ marginBottom: "1rem" }}>
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Attack distribution</h3>
          {Object.entries(analytics?.by_attack_type ?? {}).length === 0 && (
            <p className="muted">No classified attacks logged yet.</p>
          )}
          {Object.entries(analytics?.by_attack_type ?? {}).map(([k, v]) => (
            <div className="feature-bar" key={k}>
              <span>{k}</span>
              <div className="track">
                <div className="fill" style={{ width: `${Math.min(100, (v / Math.max(1, total)) * 100)}%` }} />
              </div>
              <span className="mono muted">{v}</span>
            </div>
          ))}
        </section>
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Lifecycle status</h3>
          {Object.entries(analytics?.by_status ?? {}).map(([k, v]) => (
            <div className="feature-bar" key={k}>
              <span>{k}</span>
              <div className="track">
                <div className="fill" style={{ width: `${Math.min(100, (v / Math.max(1, total)) * 100)}%` }} />
              </div>
              <span className="mono muted">{v}</span>
            </div>
          ))}
          {Object.keys(analytics?.by_status ?? {}).length === 0 && (
            <p className="muted">No status data yet.</p>
          )}
        </section>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Incident table</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Incident</th>
              <th>Time</th>
              <th>Attack</th>
              <th>Severity</th>
              <th>Risk</th>
              <th>Recommendation</th>
              <th>Status</th>
              <th>Advance</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((r) => {
              const id = String(r.incident_id);
              const next = (r.allowed_next_statuses as string[] | undefined) ?? [];
              return (
                <tr key={id}>
                  <td className="mono">{id}</td>
                  <td className="mono muted">{String(r.created_at ?? "")}</td>
                  <td>{String(r.attack_type)}</td>
                  <td>
                    <span className={`badge ${String(r.severity).toLowerCase()}`}>{String(r.severity)}</span>
                  </td>
                  <td className="mono">{String(r.risk_score)}</td>
                  <td>{String(r.recommendation)}</td>
                  <td>{String(r.status)}</td>
                  <td>
                    {next.length === 0 ? (
                      <span className="muted mono">—</span>
                    ) : (
                      <select
                        className="select"
                        disabled={busyId === id}
                        defaultValue=""
                        onChange={(e) => {
                          const v = e.target.value;
                          if (v) void changeStatus(id, v);
                          e.target.value = "";
                        }}
                      >
                        <option value="">Update…</option>
                        {next.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
