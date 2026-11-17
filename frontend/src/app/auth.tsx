import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, getAccessToken, setAccessToken, UNAUTHORIZED_EVENT, type AuthMe } from "../services/api";

export interface AuthState {
  /** Initial auth probe still running. */
  loading: boolean;
  /** Server-side auth (RBAC) is switched on. */
  authEnabled: boolean;
  me: AuthMe | null;
  /** Set when a request came back 401 — the layout uses it to prompt sign-in. */
  sessionExpired: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  clearSessionExpired: () => void;
  /** UI hint only — the API enforces RBAC. */
  can: (permission: string) => boolean;
  /** Auth is on and nobody is signed in. */
  needsLogin: boolean;
}

const DEMO_PERMISSIONS = ["write_response", "approve_response", "admin"];

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [me, setMe] = useState<AuthMe | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const status = await api.securityStatus().catch(() => null);
      const enabled = Boolean(status?.auth?.enabled);
      setAuthEnabled(enabled);
      if (!enabled) {
        const profile = await api.authMe().catch(() => null);
        setMe({
          authenticated: false,
          auth_enabled: false,
          role: profile?.role ?? "anonymous",
          note: profile?.note ?? "Authentication is disabled — open demo access.",
          permissions: profile?.permissions?.length ? profile.permissions : DEMO_PERMISSIONS,
        });
        return;
      }
      if (!getAccessToken()) {
        setMe({ authenticated: false, auth_enabled: true, permissions: [] });
        return;
      }
      try {
        setMe(await api.authMe());
      } catch {
        setAccessToken(null);
        setMe({ authenticated: false, auth_enabled: true, permissions: [] });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const onUnauthorized = () => {
      setSessionExpired(true);
      setMe((cur) => ({ ...(cur ?? {}), authenticated: false, auth_enabled: true, permissions: [] }));
      setAuthEnabled(true);
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      await api.authLogin(username, password);
      setSessionExpired(false);
      await refresh();
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    try {
      await api.authLogout();
    } finally {
      await refresh();
    }
  }, [refresh]);

  const value = useMemo<AuthState>(() => {
    const perms = new Set(me?.permissions ?? []);
    return {
      loading,
      authEnabled,
      me,
      sessionExpired,
      login,
      logout,
      refresh,
      clearSessionExpired: () => setSessionExpired(false),
      can: (p: string) => !authEnabled || perms.has(p) || perms.has("admin"),
      needsLogin: authEnabled && !me?.authenticated,
    };
  }, [loading, authEnabled, me, sessionExpired, login, logout, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

const OPEN_ACCESS: AuthState = {
  loading: false,
  authEnabled: false,
  me: { authenticated: false, auth_enabled: false, role: "anonymous", permissions: DEMO_PERMISSIONS },
  sessionExpired: false,
  login: async () => undefined,
  logout: async () => undefined,
  refresh: async () => undefined,
  clearSessionExpired: () => undefined,
  can: () => true,
  needsLogin: false,
};

/** Auth state; outside the provider (isolated page tests) it reports open demo access. */
export function useAuth(): AuthState {
  return useContext(AuthContext) ?? OPEN_ACCESS;
}
