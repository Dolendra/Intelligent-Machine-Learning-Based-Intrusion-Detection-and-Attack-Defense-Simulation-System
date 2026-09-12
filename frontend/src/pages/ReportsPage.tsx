import { useEffect, useState } from "react";
import { api } from "../services/api";

export function ReportsPage() {
  const [incidents, setIncidents] = useState<Array<Record<string, unknown>>>([]);
  const [analytics, setAnalytics] = useState<{
    total_incidents: number;
    by_severity: Record<string, number>;
    by_attack_type: Record<string, number>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.incidents(), api.analytics()])
      .then(([i, a]) => {
        setIncidents(i.items);
        setAnalytics(a);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const total = analytics?.total_incidents ?? 0;

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Reports & Analytics</h2>
          <p>Persisted incident history from the IDS decision-support pipeline (not live packet capture).</p>
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
          <h3 style={{ marginTop: 0 }}>Severity distribution</h3>
          {Object.entries(analytics?.by_severity ?? {}).map(([k, v]) => (
            <div className="feature-bar" key={k}>
              <span>{k}</span>
              <div className="track">
                <div className="fill" style={{ width: `${Math.min(100, (v / Math.max(1, total)) * 100)}%` }} />
              </div>
              <span className="mono muted">{v}</span>
            </div>
          ))}
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
            </tr>
          </thead>
          <tbody>
            {incidents.map((r) => (
              <tr key={String(r.incident_id)}>
                <td className="mono">{String(r.incident_id)}</td>
                <td className="mono muted">{String(r.created_at ?? "")}</td>
                <td>{String(r.attack_type)}</td>
                <td>
                  <span className={`badge ${String(r.severity).toLowerCase()}`}>{String(r.severity)}</span>
                </td>
                <td className="mono">{String(r.risk_score)}</td>
                <td>{String(r.recommendation)}</td>
                <td>{String(r.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
