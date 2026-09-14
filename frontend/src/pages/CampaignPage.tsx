import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../services/api";

export function CampaignPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [list, setList] = useState<Array<Record<string, unknown>>>([]);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .campaigns()
      .then((r) => setList(r.items ?? []))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    if (!campaignId) {
      setDetail(null);
      return;
    }
    api
      .getCampaign(campaignId)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [campaignId]);

  async function simulateCampaign() {
    if (!campaignId) return;
    setBusy(true);
    setError(null);
    try {
      const session = await api.simulateCampaign(campaignId);
      navigate(`/simulation?session=${encodeURIComponent(session.id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const progression = (detail?.progression as string[] | undefined) ?? [];
  const incidents = (detail?.incidents as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Attack Campaigns</h2>
          <p>Correlated investigations sharing a source fingerprint — select a campaign to drill in.</p>
        </div>
        <Link className="btn btn-secondary" to="/detection">
          New detection
        </Link>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      <div className="split">
        <section className="panel panel-interactive">
          <h3 style={{ marginTop: 0 }}>Campaign list</h3>
          {list.length === 0 && (
            <div className="empty-state">
              <strong>No campaigns yet</strong>
              <p className="muted" style={{ margin: 0 }}>
                Detections need an explicit <span className="mono">source_ref</span> to correlate.
              </p>
            </div>
          )}
          <ul className="timeline">
            {list.map((c) => {
              const id = String(c.campaign_id);
              const active = campaignId === id;
              return (
                <li key={id} style={{ opacity: campaignId && !active ? 0.45 : 1 }}>
                  <Link
                    className="mono"
                    to={`/campaigns/${encodeURIComponent(id)}`}
                    style={{ color: active ? "var(--cyan-bright)" : undefined }}
                  >
                    {id}
                  </Link>
                  <div className="muted">
                    {String((c.progression as string[] | undefined)?.join(" → ") || "—")} · n=
                    {String(c.incident_count)} · max risk {String(c.max_risk)}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="panel panel-interactive stack">
          {!campaignId && (
            <div className="empty-state">
              <strong>Select a campaign</strong>
              <p className="muted" style={{ margin: 0 }}>View progression, linked incidents, and run a campaign simulation.</p>
            </div>
          )}
          {detail && (
            <>
              <h3 style={{ marginTop: 0 }}>{String(detail.campaign_id)}</h3>
              <p className="mono muted">
                Incidents: {String(detail.incident_count)} · Max risk: {String(detail.max_risk)} · Severity:{" "}
                {String(detail.max_severity)}
              </p>
              <button className="btn btn-amber" disabled={busy} onClick={() => void simulateCampaign()}>
                Simulate campaign progression
              </button>
              <h4>Attack progression</h4>
              <div className="phase-strip">
                {progression.map((p, i) => (
                  <div key={`${p}-${i}`} className="phase-chip done" style={{ opacity: 1 }}>
                    <span className="mono muted">#{i + 1}</span>
                    <strong>{p}</strong>
                  </div>
                ))}
              </div>
              <h4>Incidents</h4>
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Attack</th>
                    <th>Risk</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((inc) => (
                    <tr key={String(inc.incident_id)}>
                      <td>
                        <Link className="mono" to={`/incidents/${encodeURIComponent(String(inc.incident_id))}`}>
                          {String(inc.incident_id)}
                        </Link>
                      </td>
                      <td>{String(inc.attack_type)}</td>
                      <td className="mono">{String(inc.risk_score)}</td>
                      <td>{String(inc.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
