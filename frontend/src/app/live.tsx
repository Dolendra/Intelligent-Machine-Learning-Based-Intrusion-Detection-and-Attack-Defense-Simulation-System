import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, eventsWsUrl, type Analytics, type Incident } from "../services/api";
import { useAuth } from "./auth";

/**
 * connecting → live (WebSocket open) | reconnecting (socket dropped, retrying with backoff)
 * | offline (API health check failed) | paused (user paused the stream).
 */
export type LiveStatus = "connecting" | "live" | "reconnecting" | "offline" | "paused";

export interface LiveSnapshot {
  analytics: Analytics;
  incidents: Incident[];
  receivedAt: number;
}

export interface LiveState {
  status: LiveStatus;
  /** API reachable (from /api/health). null while probing. */
  apiOnline: boolean | null;
  modelsLoaded: boolean | null;
  apiVersion: string | null;
  /** Latest analytics push from the WebSocket. */
  snapshot: LiveSnapshot | null;
  /** Increments on every `incident_created` push — depend on it to refetch. */
  incidentSignal: number;
  paused: boolean;
  setPaused: (p: boolean) => void;
  recheckHealth: () => void;
}

const LiveContext = createContext<LiveState | null>(null);

const HEALTH_INTERVAL_MS = 30_000;

export function LiveProvider({ children }: { children: ReactNode }) {
  const { needsLogin, me } = useAuth();
  const [status, setStatus] = useState<LiveStatus>("connecting");
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [modelsLoaded, setModelsLoaded] = useState<boolean | null>(null);
  const [apiVersion, setApiVersion] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<LiveSnapshot | null>(null);
  const [incidentSignal, setIncidentSignal] = useState(0);
  const [paused, setPaused] = useState(false);
  const [healthTick, setHealthTick] = useState(0);
  const retryRef = useRef(0);

  const recheckHealth = useCallback(() => setHealthTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      api
        .health()
        .then((h) => {
          if (cancelled) return;
          setApiOnline(true);
          setModelsLoaded(Boolean(h.models_loaded));
          setApiVersion(h.version ?? null);
        })
        .catch(() => {
          if (cancelled) return;
          setApiOnline(false);
          setModelsLoaded(false);
        });
    void check();
    const id = window.setInterval(check, HEALTH_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [healthTick]);

  useEffect(() => {
    if (paused) {
      setStatus("paused");
      return;
    }
    if (apiOnline === false) {
      setStatus("offline");
      return;
    }
    if (needsLogin || typeof WebSocket === "undefined") {
      setStatus("reconnecting");
      return;
    }

    let ws: WebSocket | null = null;
    let closed = false;
    let retryTimer: number | undefined;

    const connect = () => {
      setStatus(retryRef.current === 0 ? "connecting" : "reconnecting");
      try {
        ws = new WebSocket(eventsWsUrl());
      } catch {
        scheduleRetry();
        return;
      }
      ws.onopen = () => {
        if (closed) return;
        retryRef.current = 0;
        setStatus("live");
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data));
          if (msg.type === "analytics" && msg.analytics) {
            setSnapshot({ analytics: msg.analytics, incidents: msg.incidents ?? [], receivedAt: Date.now() });
          } else if (msg.type === "incident_created") {
            setIncidentSignal((n) => n + 1);
          }
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        if (closed) return;
        scheduleRetry();
      };
    };

    const scheduleRetry = () => {
      setStatus("reconnecting");
      const delay = Math.min(30_000, 1500 * 2 ** retryRef.current);
      retryRef.current += 1;
      retryTimer = window.setTimeout(connect, delay);
    };

    connect();
    return () => {
      closed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      ws?.close();
    };
    // `me` identity changes → reconnect with the new token.
  }, [paused, apiOnline, needsLogin, me?.username]);

  const value = useMemo<LiveState>(
    () => ({ status, apiOnline, modelsLoaded, apiVersion, snapshot, incidentSignal, paused, setPaused, recheckHealth }),
    [status, apiOnline, modelsLoaded, apiVersion, snapshot, incidentSignal, paused, recheckHealth]
  );
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

const STATIC_LIVE: LiveState = {
  status: "offline",
  apiOnline: null,
  modelsLoaded: null,
  apiVersion: null,
  snapshot: null,
  incidentSignal: 0,
  paused: false,
  setPaused: () => undefined,
  recheckHealth: () => undefined,
};

export function useLive(): LiveState {
  return useContext(LiveContext) ?? STATIC_LIVE;
}

export const LIVE_LABEL: Record<LiveStatus, string> = {
  connecting: "Connecting…",
  live: "Live",
  reconnecting: "Reconnecting",
  offline: "API offline",
  paused: "Paused",
};
