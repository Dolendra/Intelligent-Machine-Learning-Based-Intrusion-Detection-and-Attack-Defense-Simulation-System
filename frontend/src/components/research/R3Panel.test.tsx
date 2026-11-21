import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { api, ApiError, type FrameworkModules, type R3Results } from "../../services/api";
import { R3Panel } from "./R3Panel";

const r3: R3Results = {
  analysis: "campaign_a+campaign_b",
  meta: { seeds: [101, 102], models: ["xgb_ref", "dt"] },
  hypotheses: {
    A1: {
      description: "LOAFO: Fisher - arm B",
      verdict: "supported",
      per_model: { xgb_ref: { mean: 0.21, holm_p: 0.002, hierarchical_bootstrap_95ci: [0.08, 0.39], n_seeds: 2 } },
    },
    A4: {
      description: "validity",
      verdict: "supported",
      per_model: { "xgb_ref | Aegis-OSR": { realised_fpr_smoothed: 0.0101, realised_fpr_deterministic: 0.0098, in_band: true } },
    },
    A5: { description: "cross", verdict: "rejected", per_model: {} },
  },
  reliability: {
    RS1: { rho: -0.21, day_cluster_ci95: [-0.6, 0.2], n: 80, verdict: "inconclusive" },
    RS2: { rho: 0.05, day_cluster_ci95: [-0.3, 0.4], n: 70, verdict: "rejected" },
    phase7_gate_open: false,
  },
};

const fw: FrameworkModules = {
  modules: {
    detector: [{ name: "frozen_v11", description: "d", status: "IMPLEMENTED AND VERIFIED" }],
    open_set: [{ name: "aegis_osr_gate", description: "g", status: "IMPLEMENTED AND VERIFIED" }],
    adapter: [{ name: "conformal_recalibration", description: "a", status: "IMPLEMENTED BUT NOT FULLY VERIFIED" }],
    explainer: [{ name: "shap", description: "s", status: "IMPLEMENTED AND VERIFIED" }],
    policy: [{ name: "frozen", description: "p", status: "IMPLEMENTED AND VERIFIED" }],
  },
  active: { detector: "frozen_v11", open_set: "aegis_osr_gate", policy: "frozen", explainer: "shap", adapter: null },
};

afterEach(() => vi.restoreAllMocks());

describe("R3Panel", () => {
  it("shows pre-registered verdicts, signed effects with intervals, validity and the closed Phase 7 gate", async () => {
    vi.spyOn(api, "researchR3").mockResolvedValue(r3);
    vi.spyOn(api, "frameworkModules").mockResolvedValue(fw);
    render(<R3Panel />);
    expect(await screen.findByText(/A1: LOAFO/)).toBeTruthy();
    expect(screen.getAllByText("supported").length).toBe(2);
    expect(screen.getAllByText("rejected").length).toBe(2); // A5 and RS2
    expect(screen.getByText("+0.210")).toBeTruthy();
    expect(screen.getByText("[+0.080, +0.390]")).toBeTruthy();
    expect(screen.getByText("1.01 %")).toBeTruthy();
    expect(screen.getByText("closed")).toBeTruthy();
    expect(await screen.findByText("conformal_recalibration")).toBeTruthy();
  });

  it("shows an empty state, not an error, before the analysis exists", async () => {
    vi.spyOn(api, "researchR3").mockRejectedValue(new ApiError({ status: 404, message: "NOT_RUN", path: "/api/research/r3" }));
    vi.spyOn(api, "frameworkModules").mockResolvedValue(fw);
    render(<R3Panel />);
    expect(await screen.findByText("R3 analysis not generated yet")).toBeTruthy();
  });
});
