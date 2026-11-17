import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  FileWarning,
  Gauge as GaugeIcon,
  HardDrive,
  KeyRound,
  Layers,
  ListOrdered,
  Network,
  RefreshCw,
  ServerCog,
  ShieldAlert,
  ShieldCheck,
  Timer,
  Undo2,
  Workflow,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, type OpsStatus } from "../services/api";
import { Badge, StatusBadge } from "../components/ui/Badge";
import { Callout, Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { SkeletonCard } from "../components/ui/Skeleton";
import { StatTile } from "../components/ui/StatTile";
import { formatDuration, formatNumber, formatRelative, humanize } from "../lib/format";

const POLL_MS = 8000;
const HISTORY = 20;

const DEP_ICON: Record<string, LucideIcon> = {
  database: Database,
  models: Cpu,
  queue: ListOrdered,
  filesystem: HardDrive,
  pcap_extractor: Network,
};

function depTone(status?: string) {
  if (status === "ok" || status === "ready") return "var(--ok)";
  if (status === "degraded") return "var(--warn)";
  return "var(--danger)";
}

export function SystemPage() {
  const [ops, setOps] = useState<OpsStatus | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [p95History, setP95History] = useState<number[]>([]);
  const [reqHistory, setReqHistory] = useState<number[]>([]);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      const o = await api.opsStatus();
      if (!mounted.current) return;
      setOps(o);
      setError(null);
      setUpdatedAt(Date.now());
      const p95 = o.performance?.p95_latency_ms;
      if (p95 != null) setP95History((h) => [...h, p95].slice(-HISTORY));
      if (o.performance?.requests_total != null) setReqHistory((h) => [...h, o.performance!.requests_total!].slice(-HISTORY));
    } catch (err) {
      if (mounted.current) setError(err);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(id);
    };
  }, [refresh]);

  const deps = ops?.dependencies ?? {};
  const perf = ops?.performance ?? {};
  const security = ops?.security ?? {};
  const response = ops?.response ?? {};
  const detection = ops?.detection ?? {};
  const queue = ops?.queue ?? {};
  const alerts = ops?.alerts ?? [];
  const ready = ops?.readiness;
  const depEntries = Object.entries(deps);
  const healthy = depEntries.filter(([, d]) => d.status === "ok" || d.status === "ready").length;
  const errRate = perf.requests_total ? ((perf.errors_5xx ?? 0) / perf.requests_total) * 100 : 0;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Lab"
        icon={ServerCog}
        title="System status"
        subtitle="Operational health and service signals — separate from the SOC incident dashboard."
        actions={
          <>
            {updatedAt ? <span className="muted small">Updated {formatRelative(updatedAt)} · auto every 8 s</span> : null}
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void refresh()}>
              <RefreshCw size={16} className={busy ? "spin" : undefined} aria-hidden /> Refresh
            </button>
          </>
        }
      />

      {error ? <ErrorState error={error} title="Operations snapshot unavailable" onRetry={() => void refresh()} retrying={busy} /> : null}

      {!ops && !error ? (
        <div className="grid grid-2">
          <SkeletonCard height={140} />
          <SkeletonCard height={140} />
        </div>
      ) : null}

      {ops && (
        <>
          <Callout
            tone={ready?.ready ? "ok" : "warn"}
            icon={ready?.ready ? ShieldCheck : AlertTriangle}
            title={ready?.ready ? "Service ready" : "Service not ready"}
          >
            {healthy}/{depEntries.length} dependencies healthy
            {ops.environment ? ` · ${humanize(ops.environment)} environment` : ""}
            {ready?.missing?.length ? ` · missing: ${ready.missing.join(", ")}` : ""}
          </Callout>

          <Card title="Dependencies" subtitle="Readiness probes" icon={Workflow}>
            <div className="grid grid-stats">
              {depEntries.map(([name, info]) => {
                const Icon = DEP_ICON[name] ?? ServerCog;
                return (
                  <StatTile
                    key={name}
                    label={humanize(name)}
                    icon={Icon}
                    tone={depTone(info.status)}
                    value={<StatusBadge status={info.status ?? "unknown"} />}
                    hint={`${humanize(info.detail ?? "")}${typeof info.depth === "number" ? ` · depth ${info.depth}` : ""}`}
                    compact
                  />
                );
              })}
            </div>
          </Card>

          <Card title="Performance" subtitle="In-process metrics (reset on restart)" icon={GaugeIcon}>
            <div className="grid grid-stats">
              <StatTile label="Requests" icon={Layers} value={formatNumber(perf.requests_total)} sparkline={reqHistory} />
              <StatTile
                label="P95 latency"
                icon={Timer}
                value={perf.p95_latency_ms != null ? `${formatNumber(perf.p95_latency_ms, 1)} ms` : "—"}
                hint={perf.p50_latency_ms != null ? `P50 ${formatNumber(perf.p50_latency_ms, 1)} ms` : undefined}
                sparkline={p95History}
                tone="var(--chart-1)"
              />
              <StatTile
                label="Server errors"
                icon={XCircle}
                tone={(perf.errors_5xx ?? 0) > 0 ? "var(--danger)" : undefined}
                value={formatNumber(perf.errors_5xx ?? 0)}
                hint={`${errRate.toFixed(2)}% · 4xx ${perf.errors_4xx ?? 0}`}
              />
              <StatTile label="Uptime" icon={Clock} value={formatDuration(perf.uptime_seconds)} compact />
              <StatTile label="Queue depth" icon={ListOrdered} value={formatNumber(queue.queue_depth)} hint={`${queue.jobs_completed ?? 0} jobs done`} />
              <StatTile
                label="Flows processed"
                icon={Network}
                value={formatNumber(detection.flows_processed_total)}
                hint={`${detection.attacks_detected_total ?? 0} attacks detected`}
              />
            </div>
          </Card>

          <div className="grid grid-2">
            <Card title="Security" subtitle="Authentication and request hygiene" icon={ShieldAlert}>
              <div className="grid grid-stats">
                <StatTile label="Auth failures" icon={KeyRound} value={security.authentication_failures ?? 0} />
                <StatTile label="Access denied" icon={Ban} value={security.authorization_denials ?? 0} />
                <StatTile label="Rate limited" icon={Timer} value={security.rate_limit_hits ?? 0} />
                <StatTile label="Validation" icon={FileWarning} value={security.validation_failures ?? 0} />
              </div>
            </Card>
            <Card title="Response actions" subtitle="Controlled-response workflow counters" icon={ShieldCheck}>
              <div className="grid grid-stats">
                <StatTile label="Pending approval" icon={Clock} tone={(response.pending_approvals ?? 0) > 0 ? "var(--warn)" : undefined} value={response.pending_approvals ?? 0} />
                <StatTile label="Verified" icon={CheckCircle2} value={response.verified_actions ?? 0} />
                <StatTile label="Failed" icon={XCircle} value={response.failed_actions_open ?? response.actions_failed ?? 0} />
                <StatTile label="Rolled back" icon={Undo2} value={response.rolled_back_or_expired ?? 0} />
              </div>
            </Card>
          </div>

          <Card
            title="Active alerts"
            subtitle="Threshold conditions raised by the ops monitor"
            icon={AlertTriangle}
            actions={<Badge tone={alerts.length ? "warn" : "ok"}>{alerts.length ? `${alerts.length} open` : "None"}</Badge>}
          >
            {alerts.length === 0 ? (
              <EmptyState compact icon={CheckCircle2} title="All clear" description="No threshold conditions require attention." />
            ) : (
              <div className="stack-sm">
                {alerts.map((a) => (
                  <Callout key={a.id} tone={a.severity === "critical" ? "danger" : "warn"} title={a.message}>
                    <span className="mono">
                      {a.id}
                      {a.component ? ` · ${a.component}` : ""}
                      {a.value != null ? ` · ${String(a.value)}` : ""}
                    </span>
                  </Callout>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
