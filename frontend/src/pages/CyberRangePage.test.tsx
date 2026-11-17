import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../components/ui/Toast";

const { scenario, defenses, view, respond } = vi.hoisted(() => {
  const scenario = {
    id: "dos", name: "Controlled DoS", family: "DoS", research_focus: "Detection and mitigation latency",
    description: "A single host floods the web server.", base_rate: 24, attackers: 1, target: "web",
    stages: [], internal_attacker: false, difficulty: "medium", version: 1, attack_seconds: 54,
  };
  const defenses = {
    recommended: { title: "Recommended", effect: "x" },
    block_source: { title: "Block source", effect: "Firewall drops every flow from each detected source." },
    rate_limit: { title: "Rate limit", effect: "20%" },
  };
  const view = {
    run_id: "r1", created_at: "", scenario, t: 16, duration_s: 86, done: false, state: "RESPONSE_OPTIONS",
    stage: "ATTACK_INITIATED", awaiting_decision: true, recommended: "block_source", chosen: null, detected_family: "DoS",
    config: { scenario: "dos", seed: 1, intensity: 1, attackers: null, detector: "union", alert_threshold: 3, alert_window_s: 5,
              response_mode: "manual", defense: "recommended", approval_delay_s: 3, benign_rate: 30, capacity: 60, duration_s: null, explain: true },
    controls: { policy: null, blocked: [], rate_limited: [], isolated: false, inspection: false },
    marks: { attack_start: 15, detected: 16, defense: null },
    attackers: [{ ip: "203.0.113.24", detected_at: 16, first_alert_at: 15 }],
    telemetry: [], events: [{ event_id: "e1", run_id: "r1", event_type: "detection.created", timestamp: "", sim_time_s: 16,
                              sequence: 1, schema_version: 1, payload: { source: "203.0.113.24", true_attacker: true } }],
    event_count: 1, recent_flows: [], explanation: null,
    metrics: { detection_latency_s: 1, time_to_mitigate_s: null, attack_success_rate: 1, attack_success_after_defense: null,
               availability_min_during_attack: 0.7, collateral_rate: 0, collateral_benign_blocked: 0, false_positive_alerts: 0,
               false_incidents: 0, fpr_flows: 0, defense_applied: null, outcome: "" },
    topology: { nodes: [], edges: [] }, models: { frozen: true, gate: true }, defenses,
  };
  const respond = vi.fn().mockResolvedValue({ ...view, awaiting_decision: false, chosen: "block_source", state: "MITIGATING", events: [] });
  return { scenario, defenses, view, respond };
});

vi.mock("../services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/api")>()),
  api: {
    rangeScenarios: vi.fn().mockResolvedValue({ items: [scenario], defenses, detectors: ["frozen", "gate", "union"] }),
    rangeCreate: vi.fn(() => Promise.resolve(view)),
    rangeStep: vi.fn(() => Promise.resolve({ ...view, events: [] })),
    rangeRespond: (...a: unknown[]) => respond(...a),
    rangeComplete: vi.fn(() => Promise.resolve(view)),
    rangeExperiments: vi.fn().mockRejectedValue(new Error("none")),
    rangeSweep: vi.fn(),
  },
}));
vi.mock("../components/NetworkTopology", () => ({ NetworkTopology: () => <div>topology</div> }));

import { CyberRangePage } from "./CyberRangePage";

describe("CyberRangePage", () => {
  it("starts a run, shows the decision panel and applies the chosen defense", async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <CyberRangePage />
        </ToastProvider>
      </MemoryRouter>
    );
    await screen.findByRole("option", { name: "Controlled DoS" });
    fireEvent.click(screen.getByRole("button", { name: /Start run/i }));
    expect(await screen.findByText("3 · Your decision")).toBeTruthy();
    expect(screen.getByText(/Incident for 203.0.113.24 \(real attacker\)/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Block source · recommended/i }));
    await waitFor(() => expect(respond).toHaveBeenCalledWith("r1", "block_source"));
  });
});
