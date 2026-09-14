import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

function severityClass(sev: string) {
  return (sev || "low").toLowerCase();
}

function wsUrl(): string {
  const base = import.meta.env.VITE_API_BASE ?? "";
  if (base.startsWith("http")) {
    return base.replace(/^http/, "ws") + "/api/ws/events";
  }
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  if (host.includes("5173")) {
    return `${proto}://127.0.0.1:8000/api/ws/events`;
  }
  return `${proto}://${host}/api/ws/events`;
}

type SevFilter = "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export function DashboardPage() {
  const [analytics, setAnalytics] = useState<{
    total_incidents: number;
    by_severity: Record<string, number>;
    by_attack_type: Record<string, number>;
  } | null>(null);
  const [incidents, setIncidents] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [liveMode, setLiveMode] = useState<"websocket" | "polling" | "off">("off");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [modelVersion, setModelVersion] = useState<string | null>(null);
  const [sevFilter, setSevFilter] = useState<SevFilter>("ALL");
  const pollRef = useRef<number | null>(null);

  const applySnapshot = useCallback(
    (
      a: { total_incidents: number; by_severity: Record<string, number>; by_attack_type: Record<string, number> },
      items: Array<Record<string, unknown>>
    ) => {
      setAnalytics(a);
      setIncidents(items);
      setLastUpdate(new Date().toLocaleTimeString());
      setError(null);
      setLoading(false);
    },
    []
  );

  const refreshOnce = useCallback(async () => {
    const [a, i] = await Promise.all([api.analytics(), api.incidents()]);
    applySnapshot(a, i.items);
  }, [applySnapshot]);

  useEffect(() => {
    void refreshOnce().catch((e) => {
      setError(e instanceof Error ? e.message : String(e));
      setLoading(false);
    });
    api
      .models()
      .then((m) => setModelVersion(String(m.model_version ?? m.application_version ?? "")))
      .catch(() => undefined);
  }, [refreshOnce]);

  useEffect(() => {
    if (!autoRefresh) {
      setLiveMode("off");
      if (pollRef.current) window.clearInterval(pollRef.current);
      return;
    }

    let ws: WebSocket | null = null;
    let closed = false;

    try {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => {
        if (!closed) setLiveMode("websocket");
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "analytics" && msg.analytics) {
            applySnapshot(msg.analytics, msg.incidents ?? []);
          } else if (msg.type === "incident_created") {
            void refreshOnce();
          }
        } catch {
          /* ignore malformed */
        }
      };
      ws.onerror = () => {
        /* fall through to polling via onclose */
      };
      ws.onclose = () => {
        if (closed) return;
        setLiveMode("polling");
        if (pollRef.current) window.clearInterval(pollRef.current);
        pollRef.current = window.setInterval(() => {
          void refreshOnce().catch(() => undefined);
        }, 5000);
      };
    } catch {
      setLiveMode("polling");
      pollRef.current = window.setInterval(() => {
        void refreshOnce().catch(() => undefined);
      }, 5000);
    }

    return () => {
      closed = true;
      ws?.close();
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [autoRefresh, applySnapshot, refreshOnce]);

  const critical = analytics?.by_severity?.CRITICAL ?? 0;
  const high = analytics?.by_severity?.HIGH ?? 0;
  const medium = analytics?.by_severity?.MEDIUM ?? 0;
  const low = analytics?.by_severity?.LOW ?? 0;

  const filteredIncidents = useMemo(() => {
    if (sevFilter === "ALL") return incidents;
    return incidents.filter((row) => String(row.severity).toUpperCase() === sevFilter);
  }, [incidents, sevFilter]);

  function toggleSev(sev: SevFilter) {
    setSevFilter((cur) => (cur === sev ? "ALL" : sev));
  }

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Security Overview</h2>
          <p>
            Live decision-support console for the Aegis IDS prototype — detect, triage, and simulate defenses.
            {modelVersion && <span className="mono muted"> · model v{modelVersion}</span>}
            {lastUpdate && <span className="mono muted"> · updated {lastUpdate}</span>}
          </p>
        </div>
        <div className="row">
          <span className={`live-chip ${liveMode === "off" ? "off" : ""}`}>
            <span className={`status-dot ${liveMode !== "off" ? "on" : ""}`} />
            {liveMode === "websocket" ? "Live · websocket" : liveMode === "polling" ? "Live · polling" : "Paused"}
          </span>
          <button
            className={`btn ${autoRefresh ? "btn-amber" : "btn-secondary"}`}
            onClick={() => setAutoRefresh((v) => !v)}
          >
            {autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}
          </button>
          <button className="btn btn-secondary" onClick={() => void refreshOnce()}>
            Refresh
          </button>
          <Link className="btn btn-primary" to="/detection">
            Run detection
          </Link>
        </div>
      </div>

      <div className="quick-launch rise rise-delay-1">
        <Link className="launch-tile" to="/detection">
          <span className="kicker">Action</span>
          <strong>Detection Lab</strong>
          <span>Load a demo flow, classify, and open SHAP evidence.</span>
        </Link>
        <Link className="launch-tile" to="/simulation">
          <span className="kicker">Replay</span>
          <strong>Attack simulation</strong>
          <span>Walk attack → defense → recovery on the topology.</span>
        </Link>
        <Link className="launch-tile" to="/reports">
          <span className="kicker">Registry</span>
          <strong>Incident reports</strong>
          <span>Filter, export, and advance lifecycle statuses.</span>
        </Link>
        <Link className="launch-tile" to="/campaigns">
          <span className="kicker">Correlate</span>
          <strong>Campaigns</strong>
          <span>Group related detections into investigation threads.</span>
        </Link>
      </div>

      {loading && (
        <div className="grid-stats rise-delay-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="stat">
              <div className="skeleton" style={{ width: "40%" }} />
              <div className="skeleton lg" style={{ width: "55%", marginTop: "0.7rem" }} />
            </div>
          ))}
        </div>
      )}
      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          Could not reach API: {error}
        </div>
      )}

      {!loading && (
        <div className="grid-stats rise rise-delay-2">
          <button
            type="button"
            className={`stat is-clickable ${sevFilter === "ALL" ? "is-active" : ""}`}
            onClick={() => setSevFilter("ALL")}
          >
            <div className="label">Incidents</div>
            <div className="value">{analytics?.total_incidents ?? 0}</div>
          </button>
          <button
            type="button"
            className={`stat is-clickable ${sevFilter === "CRITICAL" ? "is-active" : ""}`}
            onClick={() => toggleSev("CRITICAL")}
          >
            <div className="label">Critical</div>
            <div className="value" style={{ color: "var(--danger)" }}>
              {critical}
            </div>
          </button>
          <button
            type="button"
            className={`stat is-clickable ${sevFilter === "HIGH" ? "is-active" : ""}`}
            onClick={() => toggleSev("HIGH")}
          >
            <div className="label">High</div>
            <div className="value" style={{ color: "#ff9d5c" }}>
              {high}
            </div>
          </button>
          <button
            type="button"
            className={`stat is-clickable ${sevFilter === "MEDIUM" ? "is-active" : ""}`}
            onClick={() => toggleSev("MEDIUM")}
          >
            <div className="label">Medium</div>
            <div className="value" style={{ color: "var(--amber)" }}>
              {medium}
            </div>
          </button>
        </div>
      )}

      <div className="split rise rise-delay-3">
        <section className="panel panel-interactive">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.35rem" }}>
            <h3 style={{ margin: 0 }}>Recent incidents</h3>
            {sevFilter !== "ALL" && (
              <button className="btn btn-secondary" type="button" onClick={() => setSevFilter("ALL")}>
                Clear {sevFilter} filter
              </button>
            )}
          </div>
          {filteredIncidents.length === 0 ? (
            <div className="empty-state">
              <strong>{incidents.length === 0 ? "No incidents yet" : `No ${sevFilter} incidents`}</strong>
              <p className="muted" style={{ margin: "0 0 0.85rem" }}>
                {incidents.length === 0
                  ? "Run a demo detection to populate the console."
                  : "Try another severity tile or clear the filter."}
              </p>
              <Link className="btn btn-primary" to="/detection">
                Open Detection Lab
              </Link>
            </div>
          ) : (
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
                {filteredIncidents.slice(0, 8).map((row) => (
                  <tr key={String(row.incident_id)}>
                    <td className="mono">
                      <Link to={`/incidents/${encodeURIComponent(String(row.incident_id))}`}>
                        {String(row.incident_id)}
                      </Link>
                    </td>
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
          )}
          <Link className="btn btn-secondary" to="/reports" style={{ marginTop: "0.85rem" }}>
            View all incidents →
          </Link>
        </section>

        <section className="panel panel-interactive stack">
          <h3 style={{ marginTop: 0 }}>Risk distribution</h3>
          {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) => {
            const v =
              sev === "CRITICAL" ? critical : sev === "HIGH" ? high : sev === "MEDIUM" ? medium : low;
            const pct = Math.min(100, (v / Math.max(1, analytics?.total_incidents || 1)) * 100);
            return (
              <button
                key={sev}
                type="button"
                className="feature-bar"
                style={{
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  color: "inherit",
                  cursor: "pointer",
                  padding: 0,
                  textAlign: "left",
                  opacity: sevFilter === "ALL" || sevFilter === sev ? 1 : 0.35,
                }}
                onClick={() => toggleSev(sev)}
                title={`Filter ${sev}`}
              >
                <span>{sev}</span>
                <div className="track">
                  <div className="fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="mono muted">{v}</span>
              </button>
            );
          })}
          <h3>Attack mix</h3>
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
