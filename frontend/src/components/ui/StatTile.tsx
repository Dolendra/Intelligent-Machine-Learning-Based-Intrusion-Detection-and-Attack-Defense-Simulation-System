import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { Sparkline } from "../charts/Sparkline";
import { Skeleton } from "./Skeleton";

export interface StatDelta {
  /** Signed change; rendered with a sign. */
  value: number;
  /** e.g. "%", " pts". */
  suffix?: string;
  label?: string;
  /** Which direction is good (colours the delta). Default "up". */
  goodWhen?: "up" | "down" | "neutral";
}

export interface StatTileProps {
  label: string;
  value: ReactNode;
  icon?: LucideIcon;
  /** CSS colour (usually a token like "var(--sev-critical)") for the accent strip + icon. */
  tone?: string;
  hint?: ReactNode;
  delta?: StatDelta;
  sparkline?: number[];
  /** Smaller value text for long strings. */
  compact?: boolean;
  loading?: boolean;
  /** Makes the tile a toggle button. */
  onClick?: () => void;
  active?: boolean;
}

function DeltaView({ delta }: { delta: StatDelta }) {
  const dir = delta.value > 0 ? "up" : delta.value < 0 ? "down" : "flat";
  const good =
    delta.goodWhen === "neutral" || dir === "flat" ? "neutral" : String((delta.goodWhen ?? "up") === dir);
  const Icon = dir === "up" ? ArrowUpRight : dir === "down" ? ArrowDownRight : ArrowRight;
  const sign = delta.value > 0 ? "+" : "";
  return (
    <span className="delta" data-good={good}>
      <Icon size={13} aria-hidden />
      {sign}
      {Number.isInteger(delta.value) ? delta.value : delta.value.toFixed(1)}
      {delta.suffix ?? ""}
      {delta.label ? <span className="muted" style={{ fontWeight: 400 }}>&nbsp;{delta.label}</span> : null}
    </span>
  );
}

export function StatTile({ label, value, icon: Icon, tone, hint, delta, sparkline, compact, loading, onClick, active }: StatTileProps) {
  const style = tone ? { ["--tile-tone" as string]: tone } : undefined;
  const body = (
    <>
      <div className="stat-head">
        <span className="stat-label">{label}</span>
        {Icon ? <Icon size={16} className="stat-icon" aria-hidden /> : null}
      </div>
      {loading ? (
        <Skeleton width="55%" height={28} />
      ) : (
        <div className={`stat-value${compact ? " sm" : ""}`}>{value}</div>
      )}
      {(hint || delta || (sparkline && sparkline.length > 1)) && !loading ? (
        <div className="stat-foot">
          <div className="stat-hint">{delta ? <DeltaView delta={delta} /> : hint}</div>
          {sparkline && sparkline.length > 1 ? (
            <Sparkline data={sparkline} color={tone ?? "var(--accent)"} width={84} height={26} />
          ) : null}
        </div>
      ) : null}
    </>
  );
  if (onClick) {
    return (
      <button type="button" className="stat-tile" style={style} onClick={onClick} aria-pressed={Boolean(active)}>
        {body}
      </button>
    );
  }
  return (
    <div className="stat-tile" style={style}>
      {body}
    </div>
  );
}
