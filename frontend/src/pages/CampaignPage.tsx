import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../services/api";

export function CampaignPage() {
  const { campaignId } = useParams();
  const [list, setList] = useState<Array<Record<string, unknown>>>([]);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const progression = (detail?.progression as string[] | undefined) ?? [];
  const incidents = (detail?.incidents as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Attack Campaigns</h2>
          <p>Correlated incidents sharing an explicit source fingerprint (controlled SOC view).</p>
        </div>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          {error}
        </div>
      )}

      <div className="split">
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Campaign list</h3>
          {list.length === 0 && <p className="muted">No campaigns yet — need detections with source_ref.</p>}
          <ul className="timeline">
            {list.map((c) => (
              <li key={String(c.campaign_id)}>
                <Link className="mono" to={`/campaigns/${encodeURIComponent(String(c.campaign_id))}`}>
                  {String(c.campaign_id)}
                </Link>
                <div className="muted">
                  {String((c.progression as string[] | undefined)?.join(" → ") || "—")} · n=
                  {String(c.incident_count)} · max risk {String(c.max_risk)}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel stack">
          {!campaignId && <p className="muted">Select a campaign to view progression.</p>}
          {detail && (
            <>
              <h3 style={{ marginTop: 0 }}>{String(detail.campaign_id)}</h3>
              <p className="mono muted">
                Incidents: {String(detail.incident_count)} · Max risk: {String(detail.max_risk)} · Severity:{" "}
                {String(detail.max_severity)}
              </p>
              <h4>Attack progression</h4>
              <ol>
                {progression.map((p, i) => (
                  <li key={`${p}-${i}`}>{p}</li>
                ))}
              </ol>
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
