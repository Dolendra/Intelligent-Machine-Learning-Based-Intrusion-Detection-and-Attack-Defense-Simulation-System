import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  Clock,
  Info,
  Search,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  XCircle,
} from "lucide-react";
import type { SeverityLevel } from "../../services/api";
import { humanize } from "../../lib/format";
import { normalizeSeverity } from "../../lib/severity";

export type BadgeTone =
  | "neutral"
  | "accent"
  | "ok"
  | "warn"
  | "danger"
  | "info"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "info-sev"
  | "novel";

export interface BadgeProps {
  tone?: BadgeTone;
  icon?: LucideIcon;
  /** Small coloured dot instead of an icon. */
  dot?: boolean;
  size?: "sm" | "md";
  title?: string;
  children: ReactNode;
}

export function Badge({ tone, icon: Icon, dot, size = "md", title, children }: BadgeProps) {
  return (
    <span className={`badge${size === "sm" ? " badge-sm" : ""}`} data-tone={tone} title={title}>
      {Icon ? <Icon size={size === "sm" ? 11 : 13} aria-hidden /> : dot ? <span className="badge-dot" aria-hidden /> : null}
      {children}
    </span>
  );
}

export const SEVERITY_META: Record<SeverityLevel, { label: string; icon: LucideIcon; tone: BadgeTone }> = {
  CRITICAL: { label: "Critical", icon: AlertOctagon, tone: "critical" },
  HIGH: { label: "High", icon: ShieldAlert, tone: "high" },
  MEDIUM: { label: "Medium", icon: AlertTriangle, tone: "medium" },
  LOW: { label: "Low", icon: Info, tone: "low" },
  INFO: { label: "Info", icon: ShieldCheck, tone: "info-sev" },
};

/** Severity with icon + text (never colour alone). Accepts any casing ("High", "HIGH"). */
export function SeverityBadge({ severity, size }: { severity: unknown; size?: "sm" | "md" }) {
  const sev = normalizeSeverity(severity);
  const meta = SEVERITY_META[sev];
  return (
    <Badge tone={meta.tone} icon={meta.icon} size={size} title={`Severity: ${meta.label}`}>
      {meta.label}
    </Badge>
  );
}

const STATUS_META: Array<{ match: RegExp; tone: BadgeTone; icon: LucideIcon }> = [
  { match: /resolv|recover|verified|succeed|approved|ok|ready|healthy|done|contained/i, tone: "ok", icon: CheckCircle2 },
  { match: /false.?positive|reject|fail|error|expired|offline/i, tone: "danger", icon: XCircle },
  { match: /investigat|triag|review|pending|proposed|dry.?run|simulat/i, tone: "warn", icon: Search },
  { match: /defen|mitigat|executing|active|running/i, tone: "info", icon: ShieldQuestion },
  { match: /detect|new|open/i, tone: "accent", icon: CircleDot },
  { match: /degraded|queued|waiting/i, tone: "warn", icon: Clock },
];

/** Lifecycle / workflow status badge with a heuristic tone + icon and humanised text. */
export function StatusBadge({ status, size }: { status: unknown; size?: "sm" | "md" }) {
  const s = String(status ?? "");
  const meta = STATUS_META.find((m) => m.match.test(s));
  return (
    <Badge tone={meta?.tone ?? "neutral"} icon={meta?.icon ?? CircleDot} size={size}>
      {humanize(s)}
    </Badge>
  );
}
