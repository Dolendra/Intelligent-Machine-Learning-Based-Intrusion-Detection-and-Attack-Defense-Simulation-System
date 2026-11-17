import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Download, FileBarChart2, FileJson, FileSpreadsheet, FileText, Filter, Layers, ListChecks, ShieldHalf, X } from "lucide-react";
import { api, type Analytics, type ExportKind, type Incident, type SeverityLevel } from "../services/api";
import { useLive } from "../app/live";
import { formatDateTime, formatRelative, formatRisk, humanize, parseTimestamp, truncate } from "../lib/format";
import { mergeSeverityCounts, normalizeSeverity, severityVar } from "../lib/severity";
import { bucketByTime } from "../lib/timeseries";
import { Card } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { SEVERITY_META, SeverityBadge, StatusBadge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { useToast } from "../components/ui/Toast";
import { BarList, DonutChart, TimeSeriesArea, attackColor, useChartTheme } from "../components/charts";

const SEVERITIES: SeverityLevel[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const ALL = "ALL";

/** Within the last 30 days — only then is a relative "x ago" hint useful next to the date. */
function isRecent(ts: unknown): boolean {
  const d = parseTimestamp(ts);
  return d ? Date.now() - d.getTime() < 30 * 86400_000 : false;
}

export function ReportsPage() {
  const toast = useToast();
  const theme = useChartTheme();
  const { incidentSignal } = useLive();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [exporting, setExporting] = useState<ExportKind | null>(null);
  const [sevFilter, setSevFilter] = useState<string>(ALL);
  const [attackFilter, setAttackFilter] = useState(ALL);
  const [statusFilter, setStatusFilter] = useState(ALL);
  const [campaignFilter, setCampaignFilter] = useState(ALL);

  const refresh = useCallback(async () => {
    try {
      const [i, a] = await Promise.all([api.incidents(1000), api.analytics()]);
      setIncidents(i.items ?? []);
      setAnalytics(a);
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, incidentSignal]);

  async function changeStatus(incidentId: string, status: string) {
    setBusyId(incidentId);
    try {
      await api.updateIncident(incidentId, status);
      toast.success("Status updated", `${incidentId} → ${humanize(status)}`);
      await refresh();
    } catch (e) {
      toast.error(e, "Could not update status");
    } finally {
      setBusyId(null);
    }
  }

  async function doExport(kind: ExportKind) {
    setExporting(kind);
    try {
      await api.downloadExport(kind);
      toast.success("Export ready", `aegis_${kind} downloaded`);
    } catch (e) {
      toast.error(e, "Export failed");
    } finally {
      setExporting(null);
    }
  }

  const attackOptions = useMemo(() => Array.from(new Set(incidents.map((r) => r.attack_type))).sort(), [incidents]);
  const statusOptions = useMemo(() => Array.from(new Set(incidents.map((r) => r.status))).sort(), [incidents]);
  const campaignOptions = useMemo(
    () => Array.from(new Set(incidents.map((r) => r.campaign_id || "").filter(Boolean))).sort(),
    [incidents]
  );

  const filtered = useMemo(
    () =>
      incidents.filter((r) => {
        if (sevFilter !== ALL && normalizeSeverity(r.severity) !== sevFilter) return false;
        if (attackFilter !== ALL && r.attack_type !== attackFilter) return false;
        if (statusFilter !== ALL && r.status !== statusFilter) return false;
        if (campaignFilter !== ALL && (r.campaign_id || "") !== campaignFilter) return false;
        return true;
      }),
    [incidents, sevFilter, attackFilter, statusFilter, campaignFilter]
  );

  const sevCounts = mergeSeverityCounts(analytics?.by_severity);
  const total = analytics?.total_incidents ?? 0;
  const anyFilter = sevFilter !== ALL || attackFilter !== ALL || statusFilter !== ALL || campaignFilter !== ALL;
  const resolved = Object.entries(analytics?.by_status ?? {})
    .filter(([k]) => /resolv|falsepositive/i.test(k))
    .reduce((s, [, v]) => s + v, 0);

  const { buckets } = useMemo(
    () => bucketByTime(filtered, (r) => r.created_at, (r) => normalizeSeverity(r.severity), [...SEVERITIES, "INFO"] as const, 36),
    [filtered]
  );
  const trend = buckets.map((b) => ({ label: b.label, count: b.total }));

  const clearFilters = () => {
    setSevFilter(ALL);
    setAttackFilter(ALL);
    setStatusFilter(ALL);
    setCampaignFilter(ALL);
  };

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
    {
      key: "created_at",
      header: "Time",
      sortable: true,
      accessor: (r) => r.created_at ?? "",
      cell: (r) => (
        <span style={{ whiteSpace: "nowrap" }}>
          {formatDateTime(r.created_at)}
          {isRecent(r.created_at) ? (
            <span className="muted small" style={{ display: "block" }}>
              {formatRelative(r.created_at)}
            </span>
          ) : null}
        </span>
      ),
    },
    { key: "attack_type", header: "Attack", sortable: true },
    {
      key: "severity",
      header: "Severity",
      sortable: true,
      accessor: (r) => SEVERITIES.indexOf(normalizeSeverity(r.severity)),
      searchable: false,
      cell: (r) => <SeverityBadge severity={r.severity} size="sm" />,
    },
    { key: "risk_score", header: "Risk", sortable: true, align: "right", cell: (r) => <span className="mono">{formatRisk(r.risk_score)}</span> },
    {
      key: "campaign_id",
      header: "Campaign",
      sortable: true,
      accessor: (r) => r.campaign_id ?? "",
      cell: (r) =>
        r.campaign_id ? (
          <Link className="mono small" to={`/campaigns/${encodeURIComponent(r.campaign_id)}`}>
            {r.campaign_id}
          </Link>
        ) : (
          <span className="muted">—</span>
        ),
    },
    {
      key: "recommendation",
      header: "Recommendation",
      accessor: (r) => r.recommendation ?? "",
      cell: (r) => (
        <span className="cell-truncate" title={r.recommendation ?? undefined}>
          {r.recommendation ? truncate(r.recommendation, 60) : <span className="muted">—</span>}
        </span>
      ),
    },
    { key: "status", header: "Status", sortable: true, cell: (r) => <StatusBadge status={r.status} size="sm" /> },
    {
      key: "advance",
      header: "Advance",
      searchable: false,
      cell: (r) => {
        const next = r.allowed_next_statuses ?? [];
        if (!next.length) return <span className="muted">—</span>;
        return (
          <select
            className="select select-sm"
            style={{ width: 150 }}
            aria-label={`Advance status of ${r.incident_id}`}
            disabled={busyId === r.incident_id}
            defaultValue=""
            onChange={(e) => {
              const v = e.target.value;
              e.target.value = "";
              if (v) void changeStatus(r.incident_id, v);
            }}
          >
            <option value="">Update…</option>
            {next.map((s) => (
              <option key={s} value={s}>
                {humanize(s)}
              </option>
            ))}
          </select>
        );
      },
    },
  ];

  const filterSelect = (id: string, label: string, value: string, set: (v: string) => void, options: string[], fmt = (s: string) => s) => (
    <label className="field" style={{ minWidth: 140, flex: "1 1 140px", maxWidth: 200 }}>
      <span className="field-label sr-only">{label}</span>
      <select id={id} className="select select-sm" value={value} onChange={(e) => set(e.target.value)} aria-label={label}>
        <option value={ALL}>All {label.toLowerCase()}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {fmt(o)}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="page">
      <PageHeader
        eyebrow="Investigate"
        icon={FileBarChart2}
        title="Reports & Analytics"
        subtitle="Filter, triage and export the incident registry produced by the detection pipeline."
        actions={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => void doExport("incidents.csv")} disabled={exporting !== null}>
              <FileSpreadsheet size={16} aria-hidden /> CSV
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => void doExport("incidents.json")} disabled={exporting !== null}>
              <FileJson size={16} aria-hidden /> JSON
            </button>
            <button type="button" className="btn btn-primary" onClick={() => void doExport("report.pdf")} disabled={exporting !== null}>
              {exporting === "report.pdf" ? <Download size={16} className="spin" aria-hidden /> : <FileText size={16} aria-hidden />} PDF report
            </button>
          </>
        }
      />

      {error ? <ErrorState error={error} title="Could not load reports" onRetry={() => void refresh()} /> : null}

      <div className="grid grid-stats">
        <StatTile label="Incidents" icon={Layers} value={total.toLocaleString()} loading={loading} />
        <StatTile label="Critical" icon={SEVERITY_META.CRITICAL.icon} tone={severityVar("CRITICAL")} value={sevCounts.CRITICAL} loading={loading} />
        <StatTile label="High" icon={SEVERITY_META.HIGH.icon} tone={severityVar("HIGH")} value={sevCounts.HIGH} loading={loading} />
        <StatTile label="Attack families" icon={ShieldHalf} value={Object.keys(analytics?.by_attack_type ?? {}).length} loading={loading} />
        <StatTile
          label="Closed"
          icon={ListChecks}
          tone="var(--ok)"
          value={resolved}
          hint={total ? `${Math.round((resolved / total) * 100)}% resolved / false positive` : undefined}
          loading={loading}
        />
      </div>

      <div className="grid grid-3">
        <Card title="Attack distribution" subtitle="Click to filter the table" icon={ShieldHalf}>
          {loading ? (
            <Skeleton height={180} radius={10} />
          ) : (
            <DonutChart
              ariaLabel="Incidents by attack family"
              centerLabel="Incidents"
              data={Object.entries(analytics?.by_attack_type ?? {}).map(([k, v]) => ({ name: k, value: v, color: attackColor(theme, k) }))}
              activeName={attackFilter === ALL ? null : attackFilter}
              onSelect={(n) => setAttackFilter((cur) => (cur === n ? ALL : n))}
            />
          )}
        </Card>
        <Card title="Lifecycle status" subtitle="Click to filter the table" icon={ListChecks}>
          {loading ? (
            <Skeleton height={180} radius={10} />
          ) : (
            <BarList
              ariaLabel="Incidents by lifecycle status"
              items={Object.entries(analytics?.by_status ?? {}).map(([k, v], i) => ({
                label: k,
                display: humanize(k),
                value: v,
                color: theme.series[(i + 2) % theme.series.length],
              }))}
              activeLabel={statusFilter === ALL ? null : statusFilter}
              onSelect={(l) => setStatusFilter((cur) => (cur === l ? ALL : l))}
            />
          )}
        </Card>
        <Card title="Detections over time" subtitle={anyFilter ? "Matching current filters" : "All incidents"} icon={Activity}>
          {loading ? (
            <Skeleton height={180} radius={10} />
          ) : (
            <TimeSeriesArea
              ariaLabel="Incident count over time"
              data={trend}
              xKey="label"
              height={200}
              series={[{ key: "count", label: "Incidents", color: theme.series[0] }]}
              yFormatter={(v) => String(Math.round(v))}
            />
          )}
        </Card>
      </div>

      <Card
        title="Incident registry"
        subtitle={anyFilter ? `${filtered.length} of ${incidents.length} match the filters` : `${incidents.length} incidents${incidents.length >= 1000 ? " (newest 1,000 — use the exports for the full registry)" : ""}`}
        icon={Filter}
        actions={
          anyFilter ? (
            <button type="button" className="btn btn-ghost btn-sm" onClick={clearFilters}>
              <X size={14} aria-hidden /> Clear filters
            </button>
          ) : null
        }
      >
        <DataTable
          data={filtered}
          columns={columns}
          rowKey={(r) => r.incident_id}
          searchable
          searchPlaceholder="Search ID, attack, status, campaign…"
          initialSort={{ key: "created_at", dir: "desc" }}
          pageSize={15}
          pageSizeOptions={[15, 30, 60]}
          maxHeight="70vh"
          loading={loading}
          emptyTitle={incidents.length ? "No matching incidents" : "No incidents yet"}
          emptyDescription={incidents.length ? "Adjust the filters." : <Link to="/detection">Run a detection to create one.</Link>}
          caption="Incident registry"
          toolbar={
            <>
              {filterSelect("f-sev", "Severities", sevFilter, setSevFilter, SEVERITIES, (s) => SEVERITY_META[s as SeverityLevel].label)}
              {filterSelect("f-attack", "Attacks", attackFilter, setAttackFilter, attackOptions)}
              {filterSelect("f-status", "Statuses", statusFilter, setStatusFilter, statusOptions, humanize)}
              {filterSelect("f-campaign", "Campaigns", campaignFilter, setCampaignFilter, campaignOptions)}
            </>
          }
        />
      </Card>
    </div>
  );
}
