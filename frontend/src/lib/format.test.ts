import { describe, expect, it } from "vitest";
import { formatPct, formatRisk } from "./format";

describe("format helpers", () => {
  it("formats percentages", () => {
    expect(formatPct(0.84)).toBe("84%");
    expect(formatPct("bad")).toBe("—");
  });

  it("formats risk scores", () => {
    expect(formatRisk(91.4)).toBe("91");
    expect(formatRisk(undefined)).toBe("—");
  });
});
