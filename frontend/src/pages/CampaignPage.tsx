import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Activity, ArrowRight, GitBranch, Layers, Loader2, Network, Radar, Search, ShieldAlert } from "lucide-react";
import { api, type Campaign, type CampaignDetail, type Incident } from "../services/api";
import { formatRelative, formatRisk } from "../lib/format";
import { normalizeRisk } from "../lib/severity";
import { Badge, SeverityBadge, StatusBadge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton, SkeletonText } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { useToast } from "../components/ui/Toast";
import { TimeSeriesArea, attackColor, useChartTheme } from "../components/charts";

export function CampaignPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const theme = useChartTheme();
  const [list, setList] = useState<Campaign[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [detail, setDetail] = useState<CampaignDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api
      .campaigns()
      .then((r) => setList(r.items ?? []))
      .catch((e) => setError(e))
      .finally(() => setListLoading(false));
  }, []);

  useEffect(() => {
    if (!campaignId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    api
      .getCampaign(campaignId)
      .then((d) => {
        setDetail(d);
        setError(null);
      })
      .catch((e) => setError(e))
      .finally(() => setDetailLoading(false));
  }, [campaignId]);

  async function simulateCampaign() {
    if (!campaignId) return;
    setBusy(true);
    try {
      const session = await api.simulateCampaign(campaignId);
      navigate(`/simulation?session=${encodeURIComponent(session.id)}`);
    } catch (e) {
      toast.error(e, "Could not simulate campaign");
    } finally {
      setBusy(false);
    }
  }

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((c) => c.campaign_id.toLowerCase().includes(q) || (c.attack_types ?? []).some((a) => a.toLowerCase().includes(q)));
  }, [list, query]);

  const progression = detail?.progression ?? [];
  const incidents = detail?.incidents ?? [];
  const riskTrend = useMemo(
    () =>
      [...incidents]
        .sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)))
        .map((inc, i) => ({ step: `#${i + 1}`, risk: normalizeRisk(inc.risk_score) })),
    [incidents]
  );

  const columns: Column<Incident>[] = [
    {
      key: "incident_id",
      header: "Incident",
      sortable: true,
      cell: (r) => (
        <Link className="mono" to={`/incidents/${encodeURIComponent(r.incident_id)}`}>
          {r.incident_id}
        </Link>
      ),
    },
    { key: "attack_type", header: "Attack", sortable: true },
    { key: "risk_score", header: "Risk", sortable: true, align: "right", cell: (r) => <span className="mono">{formatRisk(r.risk_score)}</span> },
    { key: "severity", header: "Severity", sortable: true, cell: (r) => <SeverityBadge severity={r.severity} size="sm" /> },
    { key: "status", header: "Status", sortable: true, cell: (r) => <StatusBadge status={r.status} size="sm" /> },
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow="Investigate"
        icon={Activity}
        title="Attack Campaigns"
        subtitle="Correlated investigations that share a source fingerprint — select a campaign to drill in."
        actions={
          <Link className="btn btn-secondary" to="/detection">
            <Radar size={16} aria-hidden /> New detection
          </Link>
        }
      />

      {error ? <ErrorState error={error} onRetry={() => window.location.reload()} /> : null}

      <div className="grid grid-split-rev">
        <Card title="Campaigns" subtitle={`${list.length} correlated threads`} icon={Layers}>
          <div className="stack-sm">
            <label className="input-with-icon">
              <Search size={15} aria-hidden />
              <span className="sr-only">Search campaigns</span>
              <input className="input input-sm" type="search" placeholder="Search by ID or attack…" value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
            {listLoading ? (
              <SkeletonText lines={5} />
            ) : shown.length === 0 ? (
              <EmptyState
                compact
                title={list.length ? "No campaigns match" : "No campaigns yet"}
                description={list.length ? undefined : <>Detections need an explicit <code>source_ref</code> to correlate.</>}
              />
            ) : (
              <ul className="list-plain stack-sm" style={{ maxHeight: 560, overflowY: "auto", paddingRight: 4 }}>
                {shown.map((c) => {
                  const active = campaignId === c.campaign_id;
                  return (
                    <li key={c.campaign_id}>
                      <Link
                        to={`/campaigns/${encodeURIComponent(c.campaign_id)}`}
                        className="launch-tile"
                        aria-current={active ? "page" : undefined}
                        style={active ? { borderColor: "var(--accent)", background: "var(--accent-soft)" } : undefined}
                      >
                        <span className="launch-tile-icon" aria-hidden style={{ color: attackColor(theme, c.attack_types?.[0] ?? "") }}>
                          <GitBranch size={16} />
                        </span>
                        <span className="grow">
                          <strong className="mono" style={{ fontSize: "0.85rem" }}>
                            {c.campaign_id}
                          </strong>
                          <span>
                            {(c.attack_types ?? []).join(", ") || "—"} · {c.incident_count} incident{c.incident_count === 1 ? "" : "s"} · max risk{" "}
                            {formatRisk(c.max_risk)}
                          </span>
                          {c.latest_at ? <span style={{ display: "block" }}>Last seen {formatRelative(c.latest_at)}</span> : null}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Card>

        <div className="stack">
          {!campaignId && (
            <EmptyState
              icon={GitBranch}
              title="Select a campaign"
              description="View its attack progression, linked incidents and run a campaign-level simulation."
            />
          )}
          {campaignId && detailLoading && !detail && (
            <Card>
              <Skeleton width="40%" height={22} />
              <div style={{ height: 12 }} />
              <SkeletonText lines={4} />
            </Card>
          )}
          {detail && (
            <>
              <Card
                title={<span className="mono">{detail.campaign_id}</span>}
                subtitle="Correlated campaign"
                icon={GitBranch}
                actions={
                  <button type="button" className="btn btn-warn" disabled={busy} onClick={() => void simulateCampaign()}>
                    {busy ? <Loader2 size={16} className="spin" aria-hidden /> : <Network size={16} aria-hidden />} Simulate progression
                  </button>
                }
              >
                <div className="stack">
                  <div className="grid grid-stats">
                    <StatTile label="Incidents" icon={Layers} value={detail.incident_count} />
                    <StatTile label="Max risk" icon={ShieldAlert} value={formatRisk(detail.max_risk)} />
                    <StatTile label="Max severity" compact value={<SeverityBadge severity={detail.max_severity} />} />
                  </div>
                  <div>
                    <h4 style={{ marginBottom: 8 }}>Attack progression</h4>
                    <ol className="row list-plain" style={{ gap: 6 }} aria-label="Attack progression">
                      {progression.map((p, i) => (
                        <li key={`${p}-${i}`} className="row" style={{ gap: 6 }}>
                          <Badge tone="accent">
                            <span className="mono">#{i + 1}</span> {p}
                          </Badge>
                          {i < progression.length - 1 && <ArrowRight size={14} className="muted" aria-hidden />}
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              </Card>

              {riskTrend.length > 1 && (
                <Card title="Risk across the campaign" subtitle="Normalised 0–100 risk per incident in order of detection" icon={Activity}>
                  <TimeSeriesArea
                    ariaLabel="Risk per incident across the campaign"
                    data={riskTrend}
                    xKey="step"
                    height={200}
                    yDomain={[0, 100]}
                    series={[{ key: "risk", label: "Risk", color: theme.severity.HIGH }]}
                    yFormatter={(v) => String(Math.round(v))}
                  />
                </Card>
              )}

              <Card title="Linked incidents" icon={Layers}>
                <DataTable data={incidents} columns={columns} rowKey={(r) => r.incident_id} pageSize={10} pageSizeOptions={[10]} emptyTitle="No incidents" caption="Campaign incidents" />
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
