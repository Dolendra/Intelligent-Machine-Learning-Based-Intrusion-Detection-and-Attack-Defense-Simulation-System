import { LIVE_LABEL, useLive } from "../../app/live";

/** Top-bar pill showing the WebSocket event-stream state. */
export function LiveIndicator() {
  const { status } = useLive();
  const dot = status === "live" ? "live" : status === "offline" ? "off" : status === "paused" ? undefined : "warn";
  const title =
    status === "live"
      ? "Event stream connected (WebSocket)"
      : status === "offline"
        ? "API unreachable"
        : status === "paused"
          ? "Live updates paused"
          : "WebSocket unavailable — pages fall back to polling";
  return (
    <span className="live-pill" title={title} role="status" aria-live="polite">
      <span className="status-dot" data-state={dot} aria-hidden />
      <span className="live-label">{LIVE_LABEL[status]}</span>
    </span>
  );
}
