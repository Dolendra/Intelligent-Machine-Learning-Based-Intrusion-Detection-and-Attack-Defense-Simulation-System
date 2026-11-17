import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { AppProviders } from "../app/AppProviders";

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const body = url.includes("/api/health")
        ? { status: "ok", models_loaded: true, version: "1.1.0" }
        : url.includes("/api/security/status")
          ? { auth: { enabled: false } }
          : url.includes("/api/auth/me")
            ? { authenticated: false, auth_enabled: false, permissions: ["admin"] }
            : {};
      return { ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body) };
    })
  );
}

function renderLayout(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<div>Home content</div>} />
            <Route path="*" element={<div>Other</div>} />
          </Route>
        </Routes>
      </AppProviders>
    </MemoryRouter>
  );
}

describe("AppLayout", () => {
  beforeEach(mockFetch);

  it("renders brand, grouped nav from the route config, and model status", async () => {
    renderLayout();
    expect(screen.getByText("Aegis")).toBeTruthy();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.textContent).toContain("Dashboard");
    expect(nav.textContent).toContain("Detection");
    expect(nav.textContent).toContain("System");
    expect(screen.getByRole("group", { name: "Operations" })).toBeTruthy();
    expect(screen.getByText("Home content")).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/Models online/i)).toBeTruthy());
  });

  it("opens the command palette with Ctrl+K and filters pages", async () => {
    renderLayout();
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const input = await screen.findByRole("combobox", { name: /search pages/i });
    fireEvent.change(input, { target: { value: "drift" } });
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(1);
    expect(options[0].textContent).toContain("Models");
    await waitFor(() => expect(screen.getByText(/Models online/i)).toBeTruthy());
  });

  it("collapses the sidebar and remembers it", async () => {
    const { container } = renderLayout();
    const shell = container.querySelector(".app-shell")!;
    expect(shell.getAttribute("data-collapsed")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: /collapse sidebar/i }));
    expect(shell.getAttribute("data-collapsed")).toBe("true");
    expect(window.localStorage.getItem("aegis_sidebar_collapsed")).toBe("1");
    await waitFor(() => expect(screen.getByText(/Models online/i)).toBeTruthy());
  });
});
