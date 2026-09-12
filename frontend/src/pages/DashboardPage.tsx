import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

function severityClass(sev: string) {
  return (sev || "low").toLowerCase();
}

export function DashboardPage() {
  const [analytics, setAnalytics] = useState<{
    total_incidents: number;
    by_severity: Record<string, number>;
    by_attack_type: Record<string, number>;
  } | null>(null);
  const [incidents, setIncidents] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.analytics(), api.incidents()])
      .then(([a, i]) => {
        setAnalytics(a);
        setIncidents(i.items);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const critical = analytics?.by_severity?.CRITICAL ?? 0;
  const high = analytics?.by_severity?.HIGH ?? 0;
  const medium = analytics?.by_severity?.MEDIUM ?? 0;

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Security Overview</h2>
          <p>Live incident analytics from the IDS decision pipeline.</p>
        </div>
        <Link className="btn btn-primary" to="/detection">
          Run detection
        </Link>
      </div>

      {loading && (
        <div className="panel" style={{ marginBottom: "1rem" }}>
          <span className="muted mono">Loading analytics…</span>
        </div>
      )}
      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          Could not reach API: {error}
        </div>
      )}

      <div className="grid-stats">
        <div className="stat">
          <div className="label">Incidents</div>
          <div className="value">{analytics?.total_incidents ?? 0}</div>
        </div>
        <div className="stat">
          <div className="label">Critical</div>
          <div className="value" style={{ color: "var(--danger)" }}>
            {critical}
          </div>
        </div>
        <div className="stat">
          <div className="label">High</div>
          <div className="value" style={{ color: "#ff9d5c" }}>
            {high}
          </div>
        </div>
        <div className="stat">
          <div className="label">Medium</div>
          <div className="value" style={{ color: "var(--amber)" }}>
            {medium}
          </div>
        </div>
      </div>

      <div className="split">
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Recent incidents</h3>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Attack</th>
                <th>Severity</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {incidents.length === 0 && (
                <tr>
                  <td colSpan={4} className="muted">
                    No incidents yet — run a detection on a demo flow.
                  </td>
                </tr>
              )}
              {incidents.slice(0, 8).map((row) => (
                <tr key={String(row.incident_id)}>
                  <td className="mono">{String(row.incident_id)}</td>
                  <td>{String(row.attack_type)}</td>
                  <td>
                    <span className={`badge ${severityClass(String(row.severity))}`}>
                      {String(row.severity)}
                    </span>
                  </td>
                  <td className="mono">{(Number(row.confidence) * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel stack">
          <h3 style={{ marginTop: 0 }}>Attack mix</h3>
          {Object.entries(analytics?.by_attack_type ?? {}).length === 0 && (
            <p className="muted">Waiting for classified attacks.</p>
          )}
          {Object.entries(analytics?.by_attack_type ?? {}).map(([k, v]) => (
            <div key={k} className="feature-bar">
              <span>{k}</span>
              <div className="track">
                <div
                  className="fill"
                  style={{
                    width: `${Math.min(100, (v / Math.max(1, analytics?.total_incidents || 1)) * 100)}%`,
                  }}
                />
              </div>
              <span className="mono muted">{v}</span>
            </div>
          ))}
          <Link className="btn btn-secondary" to="/simulation">
            Open attack–defense simulation
          </Link>
        </section>
      </div>
    </div>
  );
}
