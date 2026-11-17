import { describe, expect, it } from "vitest";
import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { TabPanel, Tabs } from "./Tabs";

type Id = "a" | "b" | "c" | "d";

function Harness() {
  const [v, setV] = useState<Id>("a");
  return (
    <>
      <Tabs<Id>
        id="t"
        label="Sections"
        value={v}
        onChange={setV}
        items={[
          { id: "a", label: "Alpha" },
          { id: "b", label: "Bravo" },
          { id: "c", label: "Charlie", disabled: true },
          { id: "d", label: "Delta" },
        ]}
      />
      {(["a", "b", "c", "d"] as Id[]).map((id) => (
        <TabPanel key={id} tabsId="t" value={id} active={v}>
          Panel {id}
        </TabPanel>
      ))}
    </>
  );
}

describe("Tabs", () => {
  it("wires ARIA roles and roving tabindex", () => {
    render(<Harness />);
    expect(screen.getByRole("tablist", { name: "Sections" })).toBeTruthy();
    const alpha = screen.getByRole("tab", { name: "Alpha" });
    const bravo = screen.getByRole("tab", { name: "Bravo" });
    expect(alpha.getAttribute("aria-selected")).toBe("true");
    expect(alpha.tabIndex).toBe(0);
    expect(bravo.tabIndex).toBe(-1);
    const panel = screen.getByRole("tabpanel");
    expect(panel.getAttribute("aria-labelledby")).toBe(alpha.id);
    expect(alpha.getAttribute("aria-controls")).toBe(panel.id);
  });

  it("moves selection and focus with arrow keys, skipping disabled tabs and wrapping", () => {
    render(<Harness />);
    const alpha = screen.getByRole("tab", { name: "Alpha" });
    alpha.focus();
    fireEvent.keyDown(alpha, { key: "ArrowRight" });
    const bravo = screen.getByRole("tab", { name: "Bravo" });
    expect(bravo.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(bravo);
    expect(screen.getByRole("tabpanel").textContent).toBe("Panel b");

    // Charlie is disabled → jump to Delta.
    fireEvent.keyDown(bravo, { key: "ArrowRight" });
    const delta = screen.getByRole("tab", { name: "Delta" });
    expect(delta.getAttribute("aria-selected")).toBe("true");

    // Wrap around to Alpha.
    fireEvent.keyDown(delta, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Alpha" }).getAttribute("aria-selected")).toBe("true");

    // ArrowLeft from Alpha wraps to Delta.
    fireEvent.keyDown(screen.getByRole("tab", { name: "Alpha" }), { key: "ArrowLeft" });
    expect(screen.getByRole("tab", { name: "Delta" }).getAttribute("aria-selected")).toBe("true");
  });

  it("supports Home and End", () => {
    render(<Harness />);
    const alpha = screen.getByRole("tab", { name: "Alpha" });
    fireEvent.keyDown(alpha, { key: "End" });
    expect(screen.getByRole("tab", { name: "Delta" }).getAttribute("aria-selected")).toBe("true");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Delta" }), { key: "Home" });
    expect(screen.getByRole("tab", { name: "Alpha" }).getAttribute("aria-selected")).toBe("true");
  });
});
