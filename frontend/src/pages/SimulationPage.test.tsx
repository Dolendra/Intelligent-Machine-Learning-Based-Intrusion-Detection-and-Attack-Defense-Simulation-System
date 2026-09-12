import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({
  api: {
    listSims: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

import { SimulationPage } from "./SimulationPage";

describe("SimulationPage", () => {
  it("renders simulation controls", async () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>
    );
    expect(await screen.findByRole("heading", { name: /Attack–Defense Simulation/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Run simulation/i })).toBeTruthy();
  });
});
