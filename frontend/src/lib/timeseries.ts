import { parseTimestamp } from "./format";

export type BucketUnit = "hour" | "day" | "week";

export interface TimeBucket<K extends string> {
  /** Bucket start (ms epoch). */
  t: number;
  label: string;
  counts: Record<K, number>;
  total: number;
}

const HOUR = 3600_000;
const DAY = 24 * HOUR;

function floorTo(t: number, unit: BucketUnit): number {
  const d = new Date(t);
  if (unit === "hour") {
    d.setMinutes(0, 0, 0);
  } else {
    d.setHours(0, 0, 0, 0);
    if (unit === "week") d.setDate(d.getDate() - d.getDay());
  }
  return d.getTime();
}

function step(unit: BucketUnit) {
  return unit === "hour" ? HOUR : unit === "day" ? DAY : 7 * DAY;
}

function labelFor(t: number, unit: BucketUnit): string {
  const d = new Date(t);
  if (unit === "hour") return d.toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short" });
}

/**
 * Bucket timestamped rows into a gap-free series. The bucket unit adapts to the data's span
 * (hourly ≤ 2 days, daily ≤ 120 days, weekly beyond), is capped at `maxBuckets` trailing buckets and
 * padded backwards to at least `minBuckets` so short bursts still read as a trend.
 */
export function bucketByTime<T, K extends string>(
  rows: T[],
  getTime: (row: T) => unknown,
  getKey: (row: T) => K,
  keys: readonly K[],
  maxBuckets = 48,
  minBuckets = 8
): { unit: BucketUnit; buckets: TimeBucket<K>[] } {
  const stamped = rows
    .map((r) => ({ r, d: parseTimestamp(getTime(r)) }))
    .filter((x): x is { r: T; d: Date } => x.d !== null);
  if (!stamped.length) return { unit: "day", buckets: [] };
  const times = stamped.map((x) => x.d.getTime());
  const min = Math.min(...times);
  const max = Math.max(...times);
  const span = max - min;
  const unit: BucketUnit = span <= 2 * DAY ? "hour" : span <= 120 * DAY ? "day" : "week";
  const size = step(unit);
  const end = floorTo(max, unit);
  let start = floorTo(min, unit);
  if ((end - start) / size + 1 > maxBuckets) start = end - (maxBuckets - 1) * size;
  if ((end - start) / size + 1 < minBuckets) start = end - (Math.max(1, minBuckets) - 1) * size;

  const zero = () => Object.fromEntries(keys.map((k) => [k, 0])) as Record<K, number>;
  const buckets: TimeBucket<K>[] = [];
  const index = new Map<number, TimeBucket<K>>();
  for (let t = start; t <= end; t += size) {
    // DST shifts can move day boundaries; re-floor to stay aligned.
    const ft = floorTo(t, unit);
    if (index.has(ft)) continue;
    const b = { t: ft, label: labelFor(ft, unit), counts: zero(), total: 0 };
    buckets.push(b);
    index.set(ft, b);
  }
  for (const { r, d } of stamped) {
    const b = index.get(floorTo(d.getTime(), unit));
    if (!b) continue;
    b.counts[getKey(r)] += 1;
    b.total += 1;
  }
  return { unit, buckets };
}
