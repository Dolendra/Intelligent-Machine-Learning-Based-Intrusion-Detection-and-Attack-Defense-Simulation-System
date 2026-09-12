import { useCallback, useEffect, useRef, useState } from "react";
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
  // Dev: UI on 5173, API on 8000
  if (host.includes("5173")) {
    return `${proto}://127.0.0.1:8000/api/ws/events`;
  }
  return `${proto}://${host}/api/ws/events`;
}

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
  const pollRef = useRef<number | null>(null);

  const applySnapshot = useCallback(
    (a: { total_incidents: number; by_severity: Record<string, number>; by_attack_type: Record<string, number> }, items: Array<Record<string, unknown>>) => {
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

  return (
    <div className="rise">
      <div className="page-header">
        <div>
          <h2>Security Overview</h2>
          <p>
            Incident analytics from the IDS decision-support pipeline (demo/prototype — not live packet capture).
            {modelVersion && <span className="mono muted"> · model v{modelVersion}</span>}
            {lastUpdate && (
              <span className="mono muted">
                {" "}
                · updated {lastUpdate}
                {liveMode !== "off" ? ` · ${liveMode}` : ""}
              </span>
            )}
          </p>
        </div>
        <div className="row">
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

      {loading && (
        <div className="panel" style={{ marginBottom: "1rem" }}>
          <span className="muted mono">Loading analytics…</span>
        </div>
      )}
      {error && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.4)" }}>
          Could not reach API: {error}
        </div>
      )}

      <div className="grid-stats">
        <div className="stat">
          <div className="label">Incidents</div>
          <div className="value">{analytics?.total_incidents ?? 0}</div>
        </div>
        <div className="stat">
          <div className="label">Critical</div>
          <div className="value" style={{ color: "var(--danger)" }}>
            {critical}
          </div>
        </div>
        <div className="stat">
          <div className="label">High</div>
          <div className="value" style={{ color: "#ff9d5c" }}>
            {high}
          </div>
        </div>
        <div className="stat">
          <div className="label">Medium</div>
          <div className="value" style={{ color: "var(--amber)" }}>
            {medium}
          </div>
        </div>
      </div>

      <div className="split">
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Recent incidents</h3>
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
              {incidents.length === 0 && (
                <tr>
                  <td colSpan={4} className="muted">
                    No incidents yet — run a detection on a demo flow.
                  </td>
                </tr>
              )}
              {incidents.slice(0, 8).map((row) => (
                <tr key={String(row.incident_id)}>
                  <td className="mono">{String(row.incident_id)}</td>
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
        </section>

        <section className="panel stack">
          <h3 style={{ marginTop: 0 }}>Attack mix</h3>
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
