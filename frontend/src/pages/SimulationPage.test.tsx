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
    expect(await screen.findByRole("heading", { name: /Attack Storyboard/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Run simulation/i })).toBeTruthy();
    // the storyboard must point users to the measured cyber range
    expect(screen.getByRole("link", { name: /Cyber Range/i }).getAttribute("href")).toBe("/range");
  });
});
