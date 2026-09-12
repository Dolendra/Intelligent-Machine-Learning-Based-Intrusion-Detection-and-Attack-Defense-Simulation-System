import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";

describe("AppLayout", () => {
  it("renders brand and primary nav", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", models_loaded: true, version: "1.1.0" }),
      })
    );

    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<div>Home content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Aegis")).toBeTruthy();
    expect(screen.getByText("Dashboard")).toBeTruthy();
    expect(screen.getByText("Detection")).toBeTruthy();
    expect(screen.getByText("Home content")).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/Models online/i)).toBeTruthy());
  });
});
