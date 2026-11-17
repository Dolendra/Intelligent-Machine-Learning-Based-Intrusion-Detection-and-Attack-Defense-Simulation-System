import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { GateLabelBadge, GateVerdictPanel, PValueMeter, formatP } from "./GateVisuals";
import type { ZeroDayResult } from "../../services/api";
import { formatCI } from "../../lib/format";

const base: ZeroDayResult = {
  label: "ZERO-DAY-ANOMALY",
  alert: true,
  novel: true,
  summary: "Novel behaviour",
  p_value: 0.0004,
  alpha: 0.01,
  fused_surprisal: 12.3,
  evidence: { supervised: { p_attack: 0.1, surprisal: 1.2 }, novelty: { knn_distance: 4.2, surprisal: 11.1 } },
  family: { predicted: "DoS", probability: 0.6, conformity_p: 0.002 },
  top_deviations: [{ feature: "Flow Duration", value: 9e7, benign_neighbor_value: 1e3, deviation_sigma: 3.4 }],
};

describe("Zero-Day Gate visuals", () => {
  it("labels gate verdicts with icon + text", () => {
    render(
      <>
        <GateLabelBadge label="ZERO-DAY-ANOMALY" />
        <GateLabelBadge label="UNKNOWN-ATTACK" />
        <GateLabelBadge label="BENIGN" />
        <GateLabelBadge label={null} />
      </>
    );
    expect(screen.getByText("Zero-day anomaly")).toBeTruthy();
    expect(screen.getByText("Unknown attack")).toBeTruthy();
    expect(screen.getByText("Benign")).toBeTruthy();
    expect(screen.getByText("Unavailable")).toBeTruthy();
  });

  it("highlights a possible zero-day the frozen model missed", () => {
    render(<GateVerdictPanel result={base} frozenIsAttack={false} alphaFamily={0.01} />);
    expect(screen.getByText(/frozen model missed it/i)).toBeTruthy();
    expect(screen.getByText("Why it looks novel")).toBeTruthy();
    expect(screen.getByText("Flow Duration")).toBeTruthy();
  });

  it("does not warn when the frozen model also alerted", () => {
    render(<GateVerdictPanel result={base} frozenIsAttack={true} />);
    expect(screen.queryByText(/frozen model missed it/i)).toBeNull();
  });

  it("shows an unavailable notice when the gate result is null", () => {
    render(<GateVerdictPanel result={null} frozenIsAttack={false} />);
    expect(screen.getByText(/Zero-Day Gate unavailable/i)).toBeTruthy();
  });

  it("describes p versus alpha accessibly", () => {
    render(<PValueMeter p={0.2} alpha={0.01} />);
    expect(screen.getByRole("img").getAttribute("aria-label")).toMatch(/no alert/);
    expect(formatP(0.0004)).toBe("4.00e-4");
    expect(formatP(0.25)).toBe("0.2500");
  });

  it("formats confidence intervals", () => {
    expect(formatCI({ mean: 0.6958, low: 0.65, high: 0.72, n: 5 })).toBe("69.6% [65.0–72.0]");
    expect(formatCI({ mean: 0.6958, low: 0.6958, high: 0.6958, n: 1 })).toBe("69.6% (n=1)");
    expect(formatCI(null)).toBe("—");
  });
});
