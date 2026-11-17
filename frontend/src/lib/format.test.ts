import { describe, expect, it } from "vitest";
import { formatDuration, formatPct, formatRisk, humanize, parseTimestamp } from "./format";
import { mergeSeverityCounts, normalizeRisk, normalizeSeverity } from "./severity";
import { bucketByTime } from "./timeseries";

describe("format helpers", () => {
  it("formats percentages", () => {
    expect(formatPct(0.84)).toBe("84%");
    expect(formatPct(0.8456, 1)).toBe("84.6%");
    expect(formatPct("bad")).toBe("—");
  });

  it("formats risk scores", () => {
    expect(formatRisk(91.4)).toBe("91");
    expect(formatRisk(undefined)).toBe("—");
  });

  it("humanizes internal identifiers", () => {
    expect(humanize("DefenseApplied")).toBe("Defense applied");
    expect(humanize("pcap_extractor")).toBe("PCAP extractor");
    expect(humanize("ids_alert")).toBe("IDS alert");
    expect(humanize("attack_start")).toBe("Attack start");
  });

  it("treats naive backend timestamps as UTC", () => {
    expect(parseTimestamp("2026-09-14T19:58:41.552951")?.toISOString()).toBe("2026-09-14T19:58:41.552Z");
    expect(parseTimestamp("2026-09-22T17:32:09+00:00")?.toISOString()).toBe("2026-09-22T17:32:09.000Z");
    expect(parseTimestamp("nope")).toBeNull();
  });

  it("formats durations", () => {
    expect(formatDuration(4.08)).toBe("4.1 s");
    expect(formatDuration(600)).toBe("10 min");
  });
});

describe("severity helpers", () => {
  it("normalises mixed-case severities and merges buckets", () => {
    expect(normalizeSeverity("High")).toBe("HIGH");
    expect(mergeSeverityCounts({ HIGH: 14, High: 97, Medium: 2 })).toMatchObject({ HIGH: 111, MEDIUM: 2, CRITICAL: 0 });
  });

  it("normalises 0–1 risk to 0–100", () => {
    expect(normalizeRisk(0.8)).toBe(80);
    expect(normalizeRisk(76.2)).toBe(76.2);
  });
});

describe("bucketByTime", () => {
  it("fills gaps with zero buckets", () => {
    const rows = [
      { t: "2026-09-14T10:05:00Z", k: "a" as const },
      { t: "2026-09-14T13:05:00Z", k: "a" as const },
      { t: "2026-09-14T13:10:00Z", k: "b" as const },
    ];
    const { unit, buckets } = bucketByTime(rows, (r) => r.t, (r) => r.k, ["a", "b"] as const, 48, 1);
    expect(unit).toBe("hour");
    expect(buckets).toHaveLength(4);
    expect(buckets.map((b) => b.total)).toEqual([1, 0, 0, 2]);
    expect(buckets[3].counts).toEqual({ a: 1, b: 1 });
  });

  it("pads short bursts to the minimum bucket count", () => {
    const { buckets } = bucketByTime([{ t: "2026-09-14T10:05:00Z" }], (r) => r.t, () => "a" as const, ["a"] as const);
    expect(buckets).toHaveLength(8);
    expect(buckets[7].total).toBe(1);
  });
});
