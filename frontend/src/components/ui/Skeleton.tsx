import type { CSSProperties } from "react";

export interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  className?: string;
  style?: CSSProperties;
}

export function Skeleton({ width = "100%", height = 14, radius, className, style }: SkeletonProps) {
  return (
    <span
      className={`skeleton${className ? ` ${className}` : ""}`}
      aria-hidden
      style={{ width, height, borderRadius: radius, ...style }}
    />
  );
}

/** Several text lines of decreasing width. */
export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="stack-sm" aria-hidden>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} width={`${92 - i * 14}%`} />
      ))}
    </div>
  );
}

/** Card-shaped placeholder (e.g. while a chart loads). */
export function SkeletonCard({ height = 220 }: { height?: number }) {
  return (
    <div className="card" aria-hidden>
      <div className="card-body stack">
        <Skeleton width="35%" height={16} />
        <Skeleton height={height} radius={10} />
      </div>
    </div>
  );
}

/** Full-page placeholder used as the lazy-route Suspense fallback. */
export function PageSkeleton() {
  return (
    <div className="page" role="status" aria-live="polite" aria-label="Loading page">
      <div className="stack-sm">
        <Skeleton width={120} height={12} />
        <Skeleton width="min(420px, 80%)" height={30} />
        <Skeleton width="min(560px, 90%)" height={14} />
      </div>
      <div className="grid grid-stats">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} height={96} radius={12} />
        ))}
      </div>
      <div className="grid grid-2">
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
