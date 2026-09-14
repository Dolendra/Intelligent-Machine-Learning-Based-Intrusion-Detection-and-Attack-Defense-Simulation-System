import { NavLink, Outlet } from "react-router-dom";
import { FormEvent, useEffect, useState } from "react";
import { api, getAccessToken, setAccessToken } from "../services/api";

const NAV = [
  { to: "/", end: true, label: "Dashboard", ico: "01", section: "Operations" },
  { to: "/detection", label: "Detection", ico: "02", section: "Operations" },
  { to: "/simulation", label: "Simulation", ico: "03", section: "Operations" },
  { to: "/reports", label: "Reports", ico: "04", section: "Investigate" },
  { to: "/campaigns", label: "Campaigns", ico: "05", section: "Investigate" },
  { to: "/models", label: "Models", ico: "06", section: "Lab" },
  { to: "/research", label: "Research", ico: "07", section: "Lab" },
  { to: "/system", label: "System", ico: "08", section: "Lab" },
] as const;

type MeState = {
  authenticated: boolean;
  auth_enabled?: boolean;
  username?: string;
  role?: string;
  permissions?: string[];
  note?: string;
};

export function AppLayout() {
  const [modelsLoaded, setModelsLoaded] = useState<boolean | null>(null);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [me, setMe] = useState<MeState | null>(null);
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authBusy, setAuthBusy] = useState(false);

  async function refreshAuth() {
    const status = await api.securityStatus().catch(() => null);
    const enabled = Boolean((status?.auth as Record<string, unknown> | undefined)?.enabled);
    setAuthEnabled(enabled);
    if (!enabled) {
      setMe({
        authenticated: false,
        auth_enabled: false,
        role: "anonymous",
        note: "Auth disabled — demo open access",
        permissions: ["write_response", "approve_response", "admin"],
      });
      return;
    }
    if (!getAccessToken()) {
      setMe({ authenticated: false, auth_enabled: true, permissions: [] });
      return;
    }
    try {
      const profile = await api.authMe();
      setMe(profile);
    } catch {
      setAccessToken(null);
      setMe({ authenticated: false, auth_enabled: true, permissions: [] });
    }
  }

  useEffect(() => {
    api
      .health()
      .then((h) => setModelsLoaded(h.models_loaded))
      .catch(() => setModelsLoaded(false));
    refreshAuth().catch(() => setAuthEnabled(false));
  }, []);

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError(null);
    try {
      await api.authLogin(username, password);
      await refreshAuth();
      setPassword("");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : String(err));
    } finally {
      setAuthBusy(false);
    }
  }

  async function onLogout() {
    setAuthBusy(true);
    try {
      await api.authLogout();
      await refreshAuth();
    } finally {
      setAuthBusy(false);
    }
  }

  let lastSection = "";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-shield" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M12 3l7 3v5c0 4.5-2.8 7.8-7 10-4.2-2.2-7-5.5-7-10V6l7-3z" />
              <path d="M9.2 12.2l1.9 1.9 3.8-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="brand-mark">Aegis</div>
          <h1>IDS Platform</h1>
          <p>Detect · Explain · Recommend · Simulate</p>
        </div>

        <nav className="nav" aria-label="Primary">
          {NAV.map((item) => {
            const showSection = item.section !== lastSection;
            lastSection = item.section;
            return (
              <div key={item.to}>
                {showSection && <div className="nav-section">{item.section}</div>}
                <NavLink to={item.to} end={"end" in item ? item.end : undefined}>
                  <span className="nav-ico">{item.ico}</span>
                  {item.label}
                </NavLink>
              </div>
            );
          })}
        </nav>

        <div className="sidebar-foot">
          <div className="status-pill">
            <span className={`status-dot ${modelsLoaded ? "on" : ""}`} />
            {modelsLoaded === null
              ? "Checking models…"
              : modelsLoaded
                ? "Models online"
                : "Models offline"}
          </div>

          <div style={{ marginTop: "0.75rem", padding: "0.55rem 0.35rem" }}>
            <div className="nav-section">Session (P4)</div>
            {!authEnabled && (
              <p className="muted" style={{ fontSize: "0.75rem", margin: "0.25rem 0 0", lineHeight: 1.35 }}>
                Auth off (demo). Server-side RBAC inactive.
              </p>
            )}
            {authEnabled && me?.authenticated && (
              <div style={{ fontSize: "0.8rem", lineHeight: 1.4 }}>
                <div className="mono">{me.username}</div>
                <div className="muted">role · {me.role}</div>
                <button className="btn btn-secondary" style={{ marginTop: "0.45rem" }} disabled={authBusy} onClick={() => void onLogout()}>
                  Log out
                </button>
              </div>
            )}
            {authEnabled && !me?.authenticated && (
              <form onSubmit={(e) => void onLogin(e)} style={{ display: "grid", gap: "0.35rem" }}>
                <input
                  className="select"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="username"
                  autoComplete="username"
                />
                <input
                  className="select"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="password"
                  autoComplete="current-password"
                />
                <button className="btn btn-primary" disabled={authBusy} type="submit">
                  Log in
                </button>
                {authError && (
                  <p className="muted" style={{ fontSize: "0.72rem", margin: 0, color: "var(--danger, #c44)" }}>
                    {authError}
                  </p>
                )}
              </form>
            )}
          </div>

          {modelsLoaded === false && (
            <p className="muted" style={{ fontSize: "0.78rem", margin: "0 0.35rem", lineHeight: 1.35 }}>
              Start API: <span className="mono">uvicorn backend.main:app --port 8000</span>
              <br />
              Train if needed: <span className="mono">scripts/02_train_models.py</span>
            </p>
          )}
        </div>
      </aside>

      <main className="main">
        {modelsLoaded === false && (
          <div
            className="panel rise"
            style={{ marginBottom: "1rem", borderColor: "rgba(228,165,74,.45)", background: "var(--amber-dim)" }}
          >
            <strong>Backend offline or models missing.</strong>
            <span className="muted"> Detection and explainability need the FastAPI server with trained artifacts.</span>
          </div>
        )}
        {authEnabled && !me?.authenticated && (
          <div
            className="panel rise"
            style={{ marginBottom: "1rem", borderColor: "rgba(227,93,106,.35)" }}
          >
            <strong>Authentication required.</strong>
            <span className="muted"> Log in from the sidebar. UI hiding is not the security boundary — the API enforces RBAC.</span>
          </div>
        )}
        <Outlet context={{ me, authEnabled, refreshAuth }} />
      </main>
    </div>
  );
}
