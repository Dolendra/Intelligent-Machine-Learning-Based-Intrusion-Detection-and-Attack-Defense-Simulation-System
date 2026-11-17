import { Suspense, useCallback, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronRight, LogIn, Menu, PanelLeftClose, PanelLeftOpen, RefreshCw, Search } from "lucide-react";
import { matchRoute, NAV_ROUTES, NAV_SECTIONS } from "../app/routes";
import { useAuth } from "../app/auth";
import { useLive } from "../app/live";
import { readStorage, writeStorage } from "../lib/storage";
import { Callout } from "./ui/Card";
import { PageSkeleton } from "./ui/Skeleton";
import { useToast } from "./ui/Toast";
import { CommandPalette } from "./layout/CommandPalette";
import { LiveIndicator } from "./layout/LiveIndicator";
import { ThemeToggle } from "./layout/ThemeToggle";
import { UserMenu } from "./layout/UserMenu";

const COLLAPSE_KEY = "aegis_sidebar_collapsed";

function BrandShield() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M12 3l7 3v5c0 4.5-2.8 7.8-7 10-4.2-2.2-7-5.5-7-10V6l7-3z" />
      <path d="M9.2 12.2l1.9 1.9 3.8-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();
  const { needsLogin, sessionExpired, clearSessionExpired } = useAuth();
  const { apiOnline, modelsLoaded, apiVersion, recheckHealth } = useLive();
  const [collapsed, setCollapsed] = useState(() => readStorage(COLLAPSE_KEY) === "1");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const route = matchRoute(location.pathname);
  const parent = route?.parent ? matchRoute(route.parent) : undefined;

  const toggleCollapsed = useCallback(() => {
    setCollapsed((c) => {
      writeStorage(COLLAPSE_KEY, c ? "0" : "1");
      return !c;
    });
  }, []);

  // Ctrl/Cmd+K anywhere opens the palette.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
    window.scrollTo?.({ top: 0 });
  }, [location.pathname]);

  // Global 401 handling: token already cleared by api.ts — prompt for sign-in and come back here after.
  useEffect(() => {
    if (!sessionExpired) return;
    clearSessionExpired();
    toast.warning("Session expired", "Please sign in again to continue.");
    const next = `${location.pathname}${location.search}`;
    navigate(`/login?next=${encodeURIComponent(next)}`);
  }, [sessionExpired, clearSessionExpired, toast, navigate, location.pathname, location.search]);

  return (
    <div className="app-shell" data-collapsed={collapsed} data-mobile-open={mobileOpen}>
      <a href="#main" className="skip-link">
        Skip to content
      </a>

      <aside className="sidebar" aria-label="Sidebar">
        <Link to="/" className="sidebar-brand" aria-label="Aegis IDS home">
          <span className="brand-shield">
            <BrandShield />
          </span>
          <span className="brand-text">
            <span className="brand-name">Aegis</span>
            <span className="brand-sub">Intrusion Detection · SOC</span>
          </span>
        </Link>

        <nav className="sidebar-nav" aria-label="Primary">
          {NAV_SECTIONS.map((section) => {
            const items = NAV_ROUTES.filter((r) => r.section === section);
            if (!items.length) return null;
            return (
              <div key={section} role="group" aria-label={section}>
                <div className="nav-section">{section}</div>
                {items.map((r) => {
                  const Icon = r.icon;
                  const forceActive = route?.parent === r.path;
                  return (
                    <NavLink
                      key={r.path}
                      to={r.path}
                      end={r.end}
                      className={({ isActive }) => `nav-link${isActive || forceActive ? " active" : ""}`}
                      title={collapsed ? r.label : undefined}
                    >
                      <Icon size={18} aria-hidden />
                      <span className="nav-label">{r.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            );
          })}
        </nav>

        <div className="sidebar-foot">
          <div className="row" style={{ gap: 8, padding: "0 4px" }} title={apiVersion ? `API v${apiVersion}` : undefined}>
            <span
              className="status-dot"
              data-state={modelsLoaded ? "live" : modelsLoaded === false ? "off" : undefined}
              aria-hidden
            />
            <span className="sidebar-foot-text small text-2">
              {modelsLoaded === null ? "Checking models…" : modelsLoaded ? "Models online" : "Models offline"}
              {apiVersion ? <span className="muted"> · v{apiVersion}</span> : null}
            </span>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm desktop-only"
            onClick={toggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            style={{ justifyContent: collapsed ? "center" : "flex-start" }}
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
            <span className="sidebar-foot-text">Collapse</span>
          </button>
        </div>
      </aside>

      {mobileOpen && <button type="button" className="scrim mobile-only" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}

      <div className="content">
        <header className="topbar">
          <button
            type="button"
            className="btn btn-ghost btn-icon mobile-only"
            aria-label="Open navigation"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div className="topbar-title">
            <nav className="breadcrumb" aria-label="Breadcrumb">
              <span>{route?.section ?? "Aegis"}</span>
              {parent && (
                <>
                  <ChevronRight size={12} aria-hidden />
                  <Link to={parent.path}>{parent.label}</Link>
                </>
              )}
            </nav>
            <div className="topbar-page" aria-current="page">
              {route?.label ?? "Not found"}
            </div>
          </div>
          <div className="topbar-actions">
            <button type="button" className="search-trigger" onClick={() => setPaletteOpen(true)} aria-label="Open command palette">
              <Search size={16} aria-hidden />
              <span className="search-label">Search…</span>
              <kbd>{isMac ? "⌘" : "Ctrl"} K</kbd>
            </button>
            <LiveIndicator />
            <ThemeToggle />
            <UserMenu onOpenPalette={() => setPaletteOpen(true)} />
          </div>
        </header>

        <main id="main" className="main" tabIndex={-1}>
          <div className="stack" style={{ gap: 12, marginBottom: apiOnline === false || needsLogin || modelsLoaded === false ? 16 : 0 }}>
            {apiOnline === false && (
              <Callout
                tone="warn"
                title="Backend offline"
                action={
                  <button type="button" className="btn btn-secondary btn-sm" onClick={recheckHealth}>
                    <RefreshCw size={14} aria-hidden /> Retry
                  </button>
                }
              >
                Start the API with <code>uvicorn backend.main:app --port 8000</code>. Pages show cached or empty states until it
                responds.
              </Callout>
            )}
            {apiOnline && modelsLoaded === false && (
              <Callout tone="warn" title="Models not loaded">
                Detection and explainability need trained artifacts — run <code>scripts/02_train_models.py</code>.
              </Callout>
            )}
            {needsLogin && location.pathname !== "/login" && (
              <Callout
                tone="info"
                icon={LogIn}
                title="Sign in required"
                action={
                  <Link className="btn btn-primary btn-sm" to={`/login?next=${encodeURIComponent(location.pathname)}`}>
                    Sign in
                  </Link>
                }
              >
                Server-side RBAC is enabled. Hiding UI is not the security boundary — the API enforces permissions.
              </Callout>
            )}
          </div>
          <Suspense fallback={<PageSkeleton />}>
            <Outlet />
          </Suspense>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
