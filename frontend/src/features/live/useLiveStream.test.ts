import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import type { LiveFlow, LiveStats, LiveTick } from "../../services/api";
import { ALERT_CAP, FEED_CAP, HISTORY_CAP, initialLiveState, liveReducer, useLiveStream } from "./useLiveStream";

const STATS = { total: 0, by_family: {}, rates: {} } as unknown as LiveStats;

function flow(id: number, over: Partial<LiveFlow> = {}): LiveFlow {
  return {
    id,
    ts: 1_700_000_000 + id,
    src: "10.0.0.1",
    dst: "10.0.0.2",
    dst_port: 80,
    bytes: 100,
    duration_ms: 1,
    truth: "BENIGN",
    unseen_family: false,
    frozen: { is_attack: false, attack_type: "BENIGN", confidence: 1, risk_score: 0, severity: "LOW" },
    gate: { label: "BENIGN", alert: false, novel: false, p_value: 0.5, summary: "", top_deviations: [] },
    outcome: "clean",
    ...over,
  };
}

function tick(seq: number, flows: LiveFlow[], paused = false): LiveTick {
  return { type: "tick", paused, seq, scenario: "zero_day", phase: { index: 0, name: "p", progress: 0 }, flows, stats: STATS };
}

describe("liveReducer", () => {
  it("keeps the feed newest-first and capped", () => {
    let s = initialLiveState;
    for (let i = 0; i < 30; i++) {
      const flows = Array.from({ length: 10 }, (_, j) => flow(i * 10 + j + 1));
      s = liveReducer(s, { type: "message", msg: tick(i + 1, flows) });
    }
    expect(s.feed).toHaveLength(FEED_CAP);
    expect(s.feed[0].id).toBe(300);
    expect(s.history.length).toBeLessThanOrEqual(HISTORY_CAP);
    expect(s.history.at(-1)!.benign).toBe(20); // 10 flows per 0.5 s tick
  });

  it("collects gate-only catches and zero-day anomalies as alerts (capped)", () => {
    let s = initialLiveState;
    const gateOnly = flow(1, { truth: "Infiltration", unseen_family: true, outcome: "caught_gate_only" });
    const zeroDay = flow(2, { gate: { label: "ZERO-DAY-ANOMALY", alert: true, novel: true, p_value: 0.001, summary: "", top_deviations: [] }, outcome: "false_alarm" });
    s = liveReducer(s, { type: "message", msg: tick(1, [gateOnly, zeroDay, flow(3)]) });
    expect(s.alerts.map((f) => f.id)).toEqual([2, 1]);
    for (let i = 0; i < ALERT_CAP + 5; i++) s = liveReducer(s, { type: "message", msg: tick(i + 2, [flow(100 + i, { outcome: "caught_gate_only" })]) });
    expect(s.alerts).toHaveLength(ALERT_CAP);
  });

  it("paused ticks update stats without touching buffers", () => {
    let s = liveReducer(initialLiveState, { type: "message", msg: tick(1, [flow(1)]) });
    s = liveReducer(s, { type: "message", msg: tick(2, [], true) });
    expect(s.tick?.paused).toBe(true);
    expect(s.feed).toHaveLength(1);
    expect(s.history).toHaveLength(1);
  });

  it("records server errors", () => {
    const s = liveReducer(initialLiveState, { type: "message", msg: { type: "error", code: "BAD_SCENARIO", message: "nope" } });
    expect(s.error).toEqual({ code: "BAD_SCENARIO", message: "nope" });
  });
});

class MockSocket {
  static instances: MockSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  closed = false;
  constructor(public url: string) {
    MockSocket.instances.push(this);
  }
  send(d: string) {
    this.sent.push(d);
  }
  close() {
    this.closed = true;
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  emit(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
  drop(code = 1006) {
    this.readyState = 3;
    this.onclose?.({ code });
  }
}

describe("useLiveStream", () => {
  beforeEach(() => {
    MockSocket.instances = [];
    vi.useFakeTimers();
    vi.stubGlobal("WebSocket", MockSocket);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("connects with scenario/rate, sends commands and closes on unmount", () => {
    const { result, unmount } = renderHook(() => useLiveStream({ scenario: "zero_day", rate: 40 }));
    const ws = MockSocket.instances[0];
    expect(ws.url).toContain("/api/ws/live?scenario=zero_day&rate=40");
    act(() => ws.open());
    expect(result.current.connection).toBe("open");
    act(() => result.current.pause());
    act(() => result.current.setRate(80));
    expect(ws.sent.map((s) => JSON.parse(s))).toEqual([{ action: "pause" }, { action: "set", rate: 80 }]);
    act(() => ws.emit(tick(1, [flow(1)])));
    expect(result.current.feed).toHaveLength(1);
    act(() => result.current.reset());
    expect(result.current.feed).toHaveLength(0);
    unmount();
    expect(ws.closed).toBe(true);
  });

  it("reconnects with backoff after an unexpected close", () => {
    const { result } = renderHook(() => useLiveStream({ scenario: "ddos_wave", rate: 20 }));
    act(() => MockSocket.instances[0].open());
    act(() => MockSocket.instances[0].drop());
    expect(result.current.connection).toBe("reconnecting");
    expect(MockSocket.instances).toHaveLength(1);
    act(() => vi.advanceTimersByTime(1000));
    expect(MockSocket.instances).toHaveLength(2);
  });

  it("stops retrying on fatal errors", () => {
    const { result } = renderHook(() => useLiveStream({ scenario: "ddos_wave", rate: 20 }));
    const ws = MockSocket.instances[0];
    act(() => ws.open());
    act(() => ws.emit({ type: "error", code: "POOL_MISSING", message: "Replay pool missing" }));
    act(() => ws.drop(1011));
    expect(result.current.connection).toBe("error");
    act(() => vi.advanceTimersByTime(60_000));
    expect(MockSocket.instances).toHaveLength(1);
  });
});
