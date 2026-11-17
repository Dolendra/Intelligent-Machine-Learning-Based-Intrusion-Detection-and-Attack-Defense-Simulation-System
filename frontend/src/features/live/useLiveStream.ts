import { useCallback, useEffect, useReducer, useRef } from "react";
import {
  GATE_ZERO_DAY,
  liveWsUrl,
  type LiveCommand,
  type LiveFlow,
  type LiveMessage,
  type LiveStats,
  type LiveTick,
} from "../../services/api";

/** Memory caps — the stream runs indefinitely during a demo. */
export const FEED_CAP = 200;
export const HISTORY_CAP = 120; // 120 ticks × 0.5 s = 60 s window
export const ALERT_CAP = 60;
export const TICK_SECONDS = 0.5;

export type LiveConnection = "connecting" | "open" | "reconnecting" | "error" | "closed";

export interface ThroughputPoint {
  seq: number;
  /** Seconds since the stream (re)started. */
  t: number;
  /** Rates in flows/s for this tick, split by ground truth. */
  benign: number;
  attack: number;
  frozenAlerts: number;
  gateAlerts: number;
}

export interface LiveState {
  connection: LiveConnection;
  error: { code: string; message: string } | null;
  /** Latest tick without its flows (flows live in `feed`). */
  tick: Omit<LiveTick, "flows"> | null;
  stats: LiveStats | null;
  /** Newest first, capped at FEED_CAP. */
  feed: LiveFlow[];
  history: ThroughputPoint[];
  /** Gate-only catches and zero-day anomalies, newest first. */
  alerts: LiveFlow[];
  /** Retry attempt counter while reconnecting. */
  attempt: number;
}

type Action =
  | { type: "connecting"; reconnect: boolean; attempt: number }
  | { type: "open" }
  | { type: "message"; msg: LiveMessage }
  | { type: "closed"; error?: LiveState["error"] }
  | { type: "clear" };

export const initialLiveState: LiveState = {
  connection: "connecting",
  error: null,
  tick: null,
  stats: null,
  feed: [],
  history: [],
  alerts: [],
  attempt: 0,
};

/** Flows worth surfacing in the alerts panel. */
export function isNotableFlow(f: LiveFlow): boolean {
  return f.outcome === "caught_gate_only" || f.gate?.label === GATE_ZERO_DAY;
}

export function liveReducer(state: LiveState, action: Action): LiveState {
  switch (action.type) {
    case "connecting":
      return { ...state, connection: action.reconnect ? "reconnecting" : "connecting", attempt: action.attempt };
    case "open":
      return { ...state, connection: "open", error: null, attempt: 0 };
    case "closed":
      return { ...state, connection: action.error ? "error" : "closed", error: action.error ?? state.error };
    case "clear":
      return { ...state, feed: [], history: [], alerts: [] };
    case "message": {
      const msg = action.msg;
      if (msg.type === "error") return { ...state, error: { code: msg.code, message: msg.message } };
      if (msg.type !== "tick") return state;
      const { flows, ...rest } = msg;
      if (msg.paused || !flows.length) return { ...state, tick: rest, stats: msg.stats };
      const perSecond = 1 / TICK_SECONDS;
      let benign = 0;
      let attack = 0;
      let frozenAlerts = 0;
      let gateAlerts = 0;
      for (const f of flows) {
        if (f.truth === "BENIGN") benign++;
        else attack++;
        if (f.frozen.is_attack) frozenAlerts++;
        if (f.gate?.alert) gateAlerts++;
      }
      const prev = state.history[state.history.length - 1];
      const point: ThroughputPoint = {
        seq: msg.seq,
        t: prev ? prev.t + TICK_SECONDS : 0,
        benign: benign * perSecond,
        attack: attack * perSecond,
        frozenAlerts: frozenAlerts * perSecond,
        gateAlerts: gateAlerts * perSecond,
      };
      const newestFirst = [...flows].reverse();
      const notable = newestFirst.filter(isNotableFlow);
      return {
        ...state,
        tick: rest,
        stats: msg.stats,
        feed: [...newestFirst, ...state.feed].slice(0, FEED_CAP),
        history: [...state.history, point].slice(-HISTORY_CAP),
        alerts: notable.length ? [...notable, ...state.alerts].slice(0, ALERT_CAP) : state.alerts,
      };
    }
    default:
      return state;
  }
}

/** Close codes / server errors that retrying cannot fix. */
const FATAL_CLOSE: Record<number, { code: string; message: string }> = {
  4401: { code: "UNAUTHORIZED", message: "Sign in to view the live stream." },
  4403: { code: "FORBIDDEN", message: "Your role lacks read_models permission for the live stream." },
};
const FATAL_ERRORS = new Set(["POOL_MISSING"]);

export interface UseLiveStream extends LiveState {
  send: (cmd: LiveCommand) => boolean;
  pause: () => void;
  resume: () => void;
  /** Reset server counters and clear local buffers. */
  reset: () => void;
  setScenario: (scenario: string) => void;
  setRate: (rate: number) => void;
  reconnect: () => void;
}

/**
 * Connects to /api/ws/live with automatic exponential-backoff reconnects. Scenario/rate changes
 * are sent as `set` commands on the open socket (no reconnect). Cleans up fully on unmount.
 */
export function useLiveStream(opts: { scenario: string; rate: number; enabled?: boolean }): UseLiveStream {
  const { enabled = true } = opts;
  const [state, dispatch] = useReducer(liveReducer, initialLiveState);
  const wsRef = useRef<WebSocket | null>(null);
  const params = useRef({ scenario: opts.scenario, rate: opts.rate });
  params.current = { scenario: opts.scenario, rate: opts.rate };
  const [connectKey, bump] = useReducer((n: number) => n + 1, 0);

  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    let attempt = 0;
    let timer: number | undefined;
    let fatal: LiveState["error"] = null;

    const connect = () => {
      dispatch({ type: "connecting", reconnect: attempt > 0, attempt });
      let ws: WebSocket;
      try {
        ws = new WebSocket(liveWsUrl(params.current.scenario, params.current.rate));
      } catch {
        schedule();
        return;
      }
      wsRef.current = ws;
      ws.onopen = () => {
        if (disposed) return;
        attempt = 0;
        dispatch({ type: "open" });
      };
      ws.onmessage = (ev) => {
        if (disposed) return;
        let msg: LiveMessage;
        try {
          msg = JSON.parse(String(ev.data));
        } catch {
          return;
        }
        if (msg.type === "error" && FATAL_ERRORS.has(msg.code)) fatal = { code: msg.code, message: msg.message };
        dispatch({ type: "message", msg });
      };
      ws.onclose = (ev) => {
        if (disposed) return;
        wsRef.current = null;
        const err = fatal ?? FATAL_CLOSE[ev.code] ?? null;
        if (err) {
          dispatch({ type: "closed", error: err });
          return;
        }
        schedule();
      };
    };

    const schedule = () => {
      attempt += 1;
      dispatch({ type: "connecting", reconnect: true, attempt });
      timer = window.setTimeout(connect, Math.min(15_000, 1000 * 2 ** (attempt - 1)));
    };

    connect();
    return () => {
      disposed = true;
      if (timer) window.clearTimeout(timer);
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) {
        ws.onopen = ws.onmessage = ws.onclose = null;
        ws.close();
      }
    };
  }, [enabled, connectKey]);

  const send = useCallback((cmd: LiveCommand) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== 1) return false;
    ws.send(JSON.stringify(cmd));
    return true;
  }, []);

  return {
    ...state,
    send,
    pause: useCallback(() => void send({ action: "pause" }), [send]),
    resume: useCallback(() => void send({ action: "resume" }), [send]),
    reset: useCallback(() => {
      send({ action: "reset" });
      dispatch({ type: "clear" });
    }, [send]),
    setScenario: useCallback(
      (scenario: string) => {
        params.current.scenario = scenario;
        send({ action: "set", scenario });
      },
      [send]
    ),
    setRate: useCallback(
      (rate: number) => {
        params.current.rate = rate;
        send({ action: "set", rate });
      },
      [send]
    ),
    reconnect: bump as () => void,
  };
}
