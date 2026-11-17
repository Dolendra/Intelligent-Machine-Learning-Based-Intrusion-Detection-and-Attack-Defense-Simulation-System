import { afterEach, describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { THEME_STORAGE_KEY, ThemeProvider } from "./theme";
import { ThemeToggle } from "../components/layout/ThemeToggle";

const originalMatchMedia = window.matchMedia;

function mockPrefersLight(light: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: light && query.includes("light"),
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}

afterEach(() => {
  window.matchMedia = originalMatchMedia;
});

function renderToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>
  );
}

describe("theme", () => {
  it("defaults to dark when the OS has no light preference", () => {
    mockPrefersLight(false);
    renderToggle();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeTruthy();
  });

  it("follows prefers-color-scheme: light when nothing is stored", () => {
    mockPrefersLight(true);
    renderToggle();
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggles and persists the choice to localStorage", () => {
    mockPrefersLight(false);
    renderToggle();
    fireEvent.click(screen.getByTestId("theme-toggle"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    fireEvent.click(screen.getByTestId("theme-toggle"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("an explicit stored theme wins over the OS preference", () => {
    mockPrefersLight(true);
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    renderToggle();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
