import { useEffect, useState } from "react";
import { api } from "../services/api";

export function ReportsPage() {
  const [incidents, setIncidents] = useState<Array<Record<string, unknown>>>([]);
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    Promise.all([api.incidents(), api.analytics()]).then(([i, a]) => {
      setIncidents(i.items);
      setAnalytics(a as unknown as Record<string, unknown>);
    });
  }, []);

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Reports & Analytics</h2>
          <p>Persisted incident history and severity distribution.</p>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: "1rem" }}>
        <pre className="mono" style={{ margin: 0, whiteSpace: "pre-wrap" }}>
          {JSON.stringify(analytics, null, 2)}
        </pre>
      </div>

      <div className="panel">
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
