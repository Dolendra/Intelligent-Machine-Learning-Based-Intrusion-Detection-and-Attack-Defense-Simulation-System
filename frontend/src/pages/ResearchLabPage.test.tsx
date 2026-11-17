import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { api, type ProtocolBlock, type ResearchOverview } from "../services/api";

const ci = (mean: number, n = 1) => ({ mean, low: mean, high: mean, n });

const loafo: ProtocolBlock = {
  methods: [
    {
      method: "Aegis-OSR",
      group: "proposed",
      evidence: ["sup", "knn"],
      fusion: "fisher",
      zero_day_recall: ci(0.6958),
      zero_day_recall_at_0_001: ci(0.28),
      zero_day_recall_at_0_05: ci(0.82),
      auroc_unknown: ci(0.94),
      auprc_unknown: ci(0.67),
      known_recall: ci(0.9999),
      fpr: ci(0.0106),
    },
    {
      method: "Closed-set XGB",
      group: "baseline",
      evidence: ["sup"],
      fusion: "fisher",
      zero_day_recall: ci(0.4946),
      zero_day_recall_at_0_001: null,
      zero_day_recall_at_0_05: null,
      auroc_unknown: ci(0.93),
      auprc_unknown: null,
      known_recall: ci(0.99),
      fpr: ci(0.0102),
    },
  ],
  folds: [{ fold: "Bot", methods: { "Aegis-OSR": { zero_day_recall: ci(0.02), fpr: ci(0.01), auroc_unknown: ci(0.8) } } }],
  per_family: {},
  significance: [{ metric: "zero_day_recall", versus: "Closed-set XGB", n: 6, mean_diff: 0.2, diff_ci_low: 0.15, diff_ci_high: 0.25, n_seeds: 5, positive_seeds: 5, wins: 6, losses: 0, ties: 0, test: "paired t over seeds", p_value: 0.0004 }],
  adaptation: [],
  attribution: {},
  meta: { seeds: [1, 2, 3, 4, 5], alpha: 0.01, generated_at: "2026-11-06T07:36:41Z", git_commit: "775e9a9" },
};

const overview: ResearchOverview = {
  proposed: "Aegis-OSR",
  baseline: "Closed-set XGB",
  methods_catalog: [{ method: "Aegis-OSR", group: "proposed", evidence: ["sup", "knn"], fusion: "fisher" }],
  status: { loafo: true, temporal: false, cross: false, gate: false, frozen_2018: false },
  loafo,
  temporal: null,
  cross: null,
  gate: null,
  frozen_v11_on_cic2018: null,
  headline: {
    loafo: {
      proposed_zero_day_recall: 0.6958,
      baseline_zero_day_recall: 0.4946,
      proposed_fpr: 0.0106,
      baseline_fpr: 0.0102,
      proposed_auroc: 0.943,
      baseline_auroc: 0.931,
    },
  },
};

import { ResearchLabPage } from "./ResearchLabPage";

describe("ResearchLabPage", () => {
  it("shows headline results, the honesty note and protocol tabs", async () => {
    vi.spyOn(api, "researchOverview").mockResolvedValue(overview);
    render(
      <MemoryRouter>
        <ResearchLabPage />
      </MemoryRouter>
    );
    expect(await screen.findByText(/catches/)).toBeTruthy();
    expect(screen.getByText(/selected on pilot seed 0/i)).toBeTruthy();
    expect(screen.getByText(/1 of 5 completed/)).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: /LOAFO/ }));
    expect(screen.getByText("Zero-day recall by method")).toBeTruthy();
    expect(screen.getAllByText("69.6% (n=1)").length).toBeGreaterThan(0);
    expect(screen.getByText("p < 0.05")).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: /Temporal/ }));
    expect(screen.getByText(/Temporal results not generated yet/)).toBeTruthy();
    expect(screen.getByText(/--protocol temporal/)).toBeTruthy();
  });
});

describe("ResearchLabPage temporal adaptation", () => {
  it("renders adaptation charts when the temporal block has adaptation rows", async () => {
    const temporal: ProtocolBlock = {
      ...loafo,
      folds: [{ fold: "Fri", methods: loafo.folds[0].methods }],
      adaptation: ["recal", "recal+ref", "oracle"].flatMap((variant) =>
        [500, 2000].map((window) => ({
          key: `${variant}@${window}`,
          variant,
          window,
          fold: "Fri",
          method: "Aegis-OSR",
          zero_day_recall: ci(0.6),
          fpr: ci(0.011),
        }))
      ),
    };
    vi.spyOn(api, "researchOverview").mockResolvedValue({ ...overview, temporal, status: { ...overview.status, temporal: true } });
    render(
      <MemoryRouter>
        <ResearchLabPage />
      </MemoryRouter>
    );
    await screen.findByText(/catches/);
    fireEvent.click(screen.getByRole("tab", { name: /Temporal/ }));
    expect(screen.getByText("Benign FPR vs warm-up window")).toBeTruthy();
    expect(screen.getByText(/breaks the conformal false-alarm guarantee/)).toBeTruthy();
  });
});
