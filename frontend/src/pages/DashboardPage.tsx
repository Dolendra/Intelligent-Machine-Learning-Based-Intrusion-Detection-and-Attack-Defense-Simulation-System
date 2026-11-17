import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  BellRing,
  Crosshair,
  FileBarChart2,
  Gauge as GaugeIcon,
  Layers,
  Network,
  Pause,
  Play,
  Radar,
  Radio,
  RefreshCw,
  ShieldHalf,
  Sparkles,
} from "lucide-react";
import { api, type Analytics, type Incident, type SeverityLevel, type ZeroDayStatus } from "../services/api";
import { Badge } from "../components/ui/Badge";
import { useLive } from "../app/live";
import { formatDateTime, formatPct, formatRelative, formatRisk } from "../lib/format";
import { mergeSeverityCounts, normalizeRisk, normalizeSeverity, severityVar } from "../lib/severity";
import { bucketByTime } from "../lib/timeseries";
import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { SEVERITY_META, SeverityBadge, StatusBadge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Skeleton } from "../components/ui/Skeleton";
import { BarList, DonutChart, Gauge, TimeSeriesArea, attackColor, useChartTheme } from "../components/charts";

const SEVERITIES: SeverityLevel[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const POLL_MS = 5000;

export function DashboardPage() {
  const live = useLive();
  const theme = useChartTheme();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [lastUpdate, setLastUpdate] = useState<number | null>(null);
  const [modelVersion, setModelVersion] = useState<string | null>(null);
  const [gate, setGate] = useState<ZeroDayStatus | null>(null);
  const [sevFilter, setSevFilter] = useState<SeverityLevel | null>(null);
  const [attackFilter, setAttackFilter] = useState<string | null>(null);
  const knownTotal = useRef<number | null>(null);

  const refreshOnce = useCallback(async () => {
    setRefreshing(true);
    try {
      const [a, i] = await Promise.all([api.analytics(), api.incidents()]);
      setAnalytics(a);
      setIncidents(i.items ?? []);
      knownTotal.current = a.total_incidents;
      setLastUpdate(Date.now());
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refreshOnce();
    api
      .models()
      .then((m) => setModelVersion(String(m.model_version ?? m.application_version ?? "") || null))
      .catch(() => undefined);
    api
      .zeroDayStatus()
      .then(setGate)
      .catch(() => setGate({ available: false, reason: "Status endpoint unreachable" }));
  }, [refreshOnce]);

  // WebSocket pushes: analytics snapshot every few seconds; refetch the full list when the total moves.
  useEffect(() => {
    const snap = live.snapshot;
    if (!snap) return;
    setAnalytics(snap.analytics);
    setLastUpdate(snap.receivedAt);
    if (knownTotal.current !== null && snap.analytics.total_incidents !== knownTotal.current) void refreshOnce();
  }, [live.snapshot, refreshOnce]);

  useEffect(() => {
    if (live.incidentSignal > 0) void refreshOnce();
  }, [live.incidentSignal, refreshOnce]);

  // Polling fallback whenever the socket is not live (and the user has not paused).
  const shouldPoll = !live.paused && live.status !== "live" && live.apiOnline !== false;
  useEffect(() => {
    if (!shouldPoll) return;
    const id = window.setInterval(() => void refreshOnce(), POLL_MS);
    return () => window.clearInterval(id);
  }, [shouldPoll, refreshOnce]);

  const sevCounts = useMemo(() => mergeSeverityCounts(analytics?.by_severity), [analytics]);
  const total = analytics?.total_incidents ?? 0;

  const { unit, buckets } = useMemo(
    () => bucketByTime(incidents, (r) => r.created_at, (r) => normalizeSeverity(r.severity), [...SEVERITIES, "INFO"] as const, 36),
    [incidents]
  );
  const timeData = useMemo(
    () => buckets.map((b) => ({ label: b.label, CRITICAL: b.counts.CRITICAL, HIGH: b.counts.HIGH, MEDIUM: b.counts.MEDIUM, LOW: b.counts.LOW + b.counts.INFO })),
    [buckets]
  );
  const sparkTotal = buckets.slice(-12).map((b) => b.total);
  const sparkBySev = (s: SeverityLevel) => buckets.slice(-12).map((b) => b.counts[s]);

  const recentRisk = useMemo(() => {
    const recent = incidents.slice(0, 10);
    if (!recent.length) return null;
    const vals = recent.map((r) => normalizeRisk(r.risk_score));
    return {
      avg: vals.reduce((s, v) => s + v, 0) / vals.length,
      peak: Math.max(...vals),
      avgConf: recent.reduce((s, r) => s + (Number(r.confidence) || 0), 0) / recent.length,
      n: recent.length,
    };
  }, [incidents]);

  const filtered = useMemo(
    () =>
      incidents.filter(
        (r) => (!sevFilter || normalizeSeverity(r.severity) === sevFilter) && (!attackFilter || r.attack_type === attackFilter)
      ),
    [incidents, sevFilter, attackFilter]
  );

  const feed = (live.snapshot?.incidents?.length ? live.snapshot.incidents : incidents).slice(0, 6);
  const attackEntries = Object.entries(analytics?.by_attack_type ?? {});

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
    {
      key: "severity",
      header: "Severity",
      sortable: true,
      accessor: (r) => SEVERITIES.indexOf(normalizeSeverity(r.severity)),
      cell: (r) => <SeverityBadge severity={r.severity} size="sm" />,
    },
    { key: "risk_score", header: "Risk", sortable: true, align: "right", cell: (r) => <span className="mono">{formatRisk(r.risk_score)}</span> },
    { key: "confidence", header: "Conf.", sortable: true, align: "right", cell: (r) => <span className="mono">{formatPct(r.confidence)}</span> },
    { key: "status", header: "Status", sortable: true, cell: (r) => <StatusBadge status={r.status} size="sm" /> },
    {
      key: "created_at",
      header: "Seen",
      sortable: true,
      accessor: (r) => r.created_at ?? "",
      cell: (r) => (
        <span className="muted small" title={formatDateTime(r.created_at)}>
          {formatRelative(r.created_at)}
        </span>
      ),
    },
  ];

  const anyFilter = sevFilter || attackFilter;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Security operations"
        icon={ShieldHalf}
        title="Security Overview"
        subtitle={
          <>
            Live decision-support console — detect, triage and simulate defenses.
            {modelVersion ? <span className="mono"> · model v{modelVersion}</span> : null}
            {lastUpdate ? <span className="mono"> · updated {formatRelative(lastUpdate)}</span> : null}
          </>
        }
        actions={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => live.setPaused(!live.paused)} aria-pressed={live.paused}>
              {live.paused ? <Play size={16} aria-hidden /> : <Pause size={16} aria-hidden />}
              {live.paused ? "Resume live" : "Pause live"}
            </button>
            <button type="button" className="btn btn-secondary btn-icon" onClick={() => void refreshOnce()} aria-label="Refresh now" disabled={refreshing}>
              <RefreshCw size={16} className={refreshing ? "spin" : undefined} />
            </button>
            <Link className="btn btn-primary" to="/detection">
              <Radar size={16} aria-hidden /> Run detection
            </Link>
          </>
        }
      />

      {error && !analytics ? <ErrorState error={error} title="Could not load the overview" onRetry={() => void refreshOnce()} retrying={refreshing} /> : null}

      <div className="grid grid-stats rise">
        <StatTile
          label="Incidents"
          icon={Layers}
          value={total.toLocaleString()}
          loading={loading}
          sparkline={sparkTotal}
          hint={live.status === "live" ? "Streaming" : live.paused ? "Paused" : "Polling every 5 s"}
          onClick={() => setSevFilter(null)}
          active={!sevFilter}
        />
        {SEVERITIES.map((s) => (
          <StatTile
            key={s}
            label={SEVERITY_META[s].label}
            icon={SEVERITY_META[s].icon}
            tone={severityVar(s)}
            value={sevCounts[s].toLocaleString()}
            loading={loading}
            sparkline={sparkBySev(s)}
            hint={total ? `${Math.round((sevCounts[s] / total) * 100)}% of total` : "—"}
            onClick={() => setSevFilter((cur) => (cur === s ? null : s))}
            active={sevFilter === s}
          />
        ))}
      </div>

      <div className="launch-grid">
        <Link className="launch-tile" to="/live" style={gate?.available ? { borderColor: "color-mix(in srgb, var(--chart-7) 45%, transparent)" } : undefined}>
          <span className="launch-tile-icon" aria-hidden style={{ color: "var(--chart-7)", background: "color-mix(in srgb, var(--chart-7) 14%, transparent)" }}>
            <Sparkles size={18} />
          </span>
          <span className="grow">
            <span className="row" style={{ gap: 8 }}>
              <strong>Zero-Day Gate</strong>
              {gate === null ? (
                <Badge size="sm" tone="neutral">
                  checking…
                </Badge>
              ) : gate.available ? (
                <Badge size="sm" tone="ok" dot>
                  online · α {gate.alpha}
                </Badge>
              ) : (
                <Badge size="sm" tone="warn" dot>
                  unavailable
                </Badge>
              )}
            </span>
            <span>
              {gate?.available
                ? `Advisory open-set detector · flags ${formatPct(gate.evaluation?.gate?.natural_unknown_alert_rate, 0)} of never-seen attacks (Infiltration, Heartbleed) — the frozen model flags none of them. Open the live monitor →`
                : gate?.reason ?? "Open-set detector status"}
            </span>
          </span>
        </Link>
        <Link className="launch-tile" to="/zero-day">
          <span className="launch-tile-icon" aria-hidden>
            <Radio size={18} />
          </span>
          <span>
            <strong>Zero-Day Lab</strong>
            <span>See how the gate decides and tune its false-alarm budget α.</span>
          </span>
        </Link>
      </div>

      <div className="grid grid-split">
        <Card
          title="Incident activity"
          subtitle={`${unit === "hour" ? "Hourly" : unit === "day" ? "Daily" : "Weekly"} detections by severity, from incident timestamps`}
          icon={Activity}
        >
          {loading ? (
            <Skeleton height={260} radius={10} />
          ) : timeData.length ? (
            <TimeSeriesArea
              data={timeData}
              xKey="label"
              stacked
              ariaLabel="Stacked area chart of incidents over time by severity"
              series={SEVERITIES.map((s) => ({ key: s, label: SEVERITY_META[s].label, color: theme.severity[s] }))}
              yFormatter={(v) => String(Math.round(v))}
            />
          ) : (
            <EmptyState icon={Activity} title="No activity yet" description="Run a demo detection to populate the timeline." />
          )}
        </Card>

        <Card title="Threat level" subtitle={recentRisk ? `Mean risk of the latest ${recentRisk.n} incidents` : "Waiting for incidents"} icon={GaugeIcon}>
          {loading ? (
            <Skeleton height={220} radius={10} />
          ) : (
            <div className="stack" style={{ alignItems: "center" }}>
              <Gauge value={recentRisk?.avg ?? 0} label="Risk index" ariaLabel="Current mean risk index" />
              <dl className="kv" style={{ width: "100%" }}>
                <dt>Peak risk (recent)</dt>
                <dd>{recentRisk ? Math.round(recentRisk.peak) : "—"}</dd>
                <dt>Mean confidence</dt>
                <dd>{recentRisk ? formatPct(recentRisk.avgConf) : "—"}</dd>
                <dt>Critical + high share</dt>
                <dd>{total ? formatPct((sevCounts.CRITICAL + sevCounts.HIGH) / total) : "—"}</dd>
              </dl>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-3">
        <Card title="Severity mix" subtitle="Click a slice to filter" icon={ShieldHalf}>
          {loading ? (
            <Skeleton height={180} radius={10} />
          ) : (
            <DonutChart
              ariaLabel="Incidents by severity"
              centerLabel="Incidents"
              data={SEVERITIES.map((s) => ({ name: SEVERITY_META[s].label, value: sevCounts[s], color: theme.severity[s] }))}
              activeName={sevFilter ? SEVERITY_META[sevFilter].label : null}
              onSelect={(name) => {
                const s = SEVERITIES.find((x) => SEVERITY_META[x].label === name) ?? null;
                setSevFilter((cur) => (cur === s ? null : s));
              }}
            />
          )}
        </Card>

        <Card title="Attack mix" subtitle="Classified attack families" icon={Crosshair}>
          {loading ? (
            <Skeleton height={180} radius={10} />
          ) : attackEntries.length ? (
            <BarList
              ariaLabel="Incidents by attack family"
              items={attackEntries.map(([k, v]) => ({ label: k, value: v, color: attackColor(theme, k) }))}
              activeLabel={attackFilter}
              onSelect={(l) => setAttackFilter((cur) => (cur === l ? null : l))}
            />
          ) : (
            <EmptyState compact title="Waiting for classified attacks" />
          )}
        </Card>

        <Card
          title="Live feed"
          subtitle={live.status === "live" ? "Pushed over WebSocket" : "Latest detections"}
          icon={BellRing}
          actions={<span className="status-dot" data-state={live.status === "live" ? "live" : "warn"} aria-hidden />}
        >
          {loading ? (
            <Skeleton height={180} radius={10} />
          ) : feed.length ? (
            <ul className="feed" aria-live="polite">
              {feed.map((r) => {
                const sev = normalizeSeverity(r.severity);
                const Icon = SEVERITY_META[sev].icon;
                return (
                  <li key={r.incident_id}>
                    <span className="feed-icon" style={{ ["--tone" as string]: severityVar(sev) }} aria-hidden>
                      <Icon size={16} />
                    </span>
                    <div className="grow">
                      <Link to={`/incidents/${encodeURIComponent(r.incident_id)}`} style={{ fontWeight: 600, color: "var(--text)" }}>
                        {r.attack_type}
                      </Link>
                      <div className="muted small mono" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {r.incident_id}
                      </div>
                    </div>
                    <div className="feed-meta">
                      <SeverityBadge severity={sev} size="sm" />
                      <div className="muted small">{formatRelative(r.created_at)}</div>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState compact title="No detections yet" />
          )}
        </Card>
      </div>

      <Card
        title="Recent incidents"
        subtitle={anyFilter ? `Filtered — ${filtered.length} of ${incidents.length}` : `${incidents.length} most recent of ${total.toLocaleString()}`}
        icon={FileBarChart2}
        actions={
          <>
            {sevFilter && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setSevFilter(null)}>
                Severity: {SEVERITY_META[sevFilter].label} ✕
              </button>
            )}
            {attackFilter && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAttackFilter(null)}>
                Attack: {attackFilter} ✕
              </button>
            )}
            <Link className="btn btn-ghost btn-sm" to="/reports">
              View all →
            </Link>
          </>
        }
      >
        <DataTable
          data={filtered}
          columns={columns}
          rowKey={(r) => r.incident_id}
          pageSize={8}
          pageSizeOptions={[8]}
          loading={loading}
          emptyTitle={incidents.length ? "No incidents match the filter" : "No incidents yet"}
          emptyDescription={
            incidents.length ? (
              "Pick another tile or clear the filters."
            ) : (
              <Link to="/detection">Run a demo detection to populate the console.</Link>
            )
          }
          caption="Recent incidents"
        />
      </Card>

      <div className="launch-grid">
        {[
          { to: "/detection", icon: Radar, title: "Detection Lab", text: "Classify a flow and open SHAP / LIME evidence." },
          { to: "/simulation", icon: Network, title: "Attack simulation", text: "Walk attack → defense → recovery on the topology." },
          { to: "/reports", icon: FileBarChart2, title: "Incident reports", text: "Filter, export and advance lifecycle status." },
          { to: "/campaigns", icon: Activity, title: "Campaigns", text: "Group related detections into investigations." },
        ].map((t) => (
          <Link key={t.to} className="launch-tile" to={t.to}>
            <span className="launch-tile-icon" aria-hidden>
              <t.icon size={18} />
            </span>
            <span>
              <strong>{t.title}</strong>
              <span>{t.text}</span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
