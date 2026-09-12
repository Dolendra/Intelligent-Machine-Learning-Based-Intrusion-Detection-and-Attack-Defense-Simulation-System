import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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
  const [sevFilter, setSevFilter] = useState("ALL");
  const [attackFilter, setAttackFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [campaignFilter, setCampaignFilter] = useState("ALL");

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

  const attackOptions = useMemo(
    () => Array.from(new Set(incidents.map((r) => String(r.attack_type)))).sort(),
    [incidents]
  );
  const statusOptions = useMemo(
    () => Array.from(new Set(incidents.map((r) => String(r.status)))).sort(),
    [incidents]
  );
  const campaignOptions = useMemo(
    () =>
      Array.from(
        new Set(incidents.map((r) => String(r.campaign_id || "")).filter(Boolean))
      ).sort(),
    [incidents]
  );

  const filtered = useMemo(
    () =>
      incidents.filter((r) => {
        if (sevFilter !== "ALL" && String(r.severity) !== sevFilter) return false;
        if (attackFilter !== "ALL" && String(r.attack_type) !== attackFilter) return false;
        if (statusFilter !== "ALL" && String(r.status) !== statusFilter) return false;
        if (campaignFilter !== "ALL" && String(r.campaign_id || "") !== campaignFilter) return false;
        return true;
      }),
    [incidents, sevFilter, attackFilter, statusFilter, campaignFilter]
  );

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
          <button
            className="btn btn-amber"
            onClick={() => api.downloadExport("report.pdf").catch((e) => setError(String(e)))}
          >
            Export PDF
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
        <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
          <h3 style={{ margin: 0 }}>Incident table</h3>
          <div className="row" style={{ flexWrap: "wrap" }}>
            <select className="select" value={sevFilter} onChange={(e) => setSevFilter(e.target.value)}>
              <option value="ALL">All severities</option>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select className="select" value={attackFilter} onChange={(e) => setAttackFilter(e.target.value)}>
              <option value="ALL">All attacks</option>
              {attackOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select className="select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="ALL">All statuses</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select className="select" value={campaignFilter} onChange={(e) => setCampaignFilter(e.target.value)}>
              <option value="ALL">All campaigns</option>
              {campaignOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="muted mono">
          Showing {filtered.length} / {incidents.length}
        </p>
        <table className="table">
          <thead>
            <tr>
              <th>Incident</th>
              <th>Time</th>
              <th>Attack</th>
              <th>Severity</th>
              <th>Risk</th>
              <th>Campaign</th>
              <th>Recommendation</th>
              <th>Status</th>
              <th>Advance</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const id = String(r.incident_id);
              const next = (r.allowed_next_statuses as string[] | undefined) ?? [];
              const camp = r.campaign_id ? String(r.campaign_id) : "";
              return (
                <tr key={id}>
                  <td className="mono">
                    <Link to={`/incidents/${id}`}>{id}</Link>
                  </td>
                  <td className="mono muted">{String(r.created_at ?? "")}</td>
                  <td>{String(r.attack_type)}</td>
                  <td>
                    <span className={`badge ${String(r.severity).toLowerCase()}`}>{String(r.severity)}</span>
                  </td>
                  <td className="mono">{String(r.risk_score)}</td>
                  <td className="mono">
                    {camp ? <Link to={`/campaigns/${encodeURIComponent(camp)}`}>{camp}</Link> : "—"}
                  </td>
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
