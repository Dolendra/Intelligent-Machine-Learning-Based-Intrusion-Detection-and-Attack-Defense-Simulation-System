import type { HTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

export interface CardProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  title?: ReactNode;
  subtitle?: ReactNode;
  icon?: LucideIcon;
  /** Right-aligned header content (buttons, filters, badges). */
  actions?: ReactNode;
  footer?: ReactNode;
  /** Remove body padding (tables that bleed to the edge). */
  flush?: boolean;
  tone?: "default" | "danger" | "accent";
  as?: "section" | "div" | "article";
  children?: ReactNode;
}

/** Surface container with optional header (icon, title, subtitle, actions) and footer. `Panel` is an alias. */
export function Card({
  title,
  subtitle,
  icon: Icon,
  actions,
  footer,
  flush,
  tone,
  as: Tag = "section",
  className,
  children,
  ...rest
}: CardProps) {
  const hasHeader = Boolean(title || subtitle || actions);
  return (
    <Tag className={`card${className ? ` ${className}` : ""}`} data-tone={tone && tone !== "default" ? tone : undefined} {...rest}>
      {hasHeader && (
        <div className="card-header">
          <div className="card-title">
            {Icon ? (
              <span className="card-title-icon" aria-hidden>
                <Icon size={16} />
              </span>
            ) : null}
            <div style={{ minWidth: 0 }}>
              {title ? <h3>{title}</h3> : null}
              {subtitle ? <div className="card-subtitle">{subtitle}</div> : null}
            </div>
          </div>
          {actions ? <div className="card-actions">{actions}</div> : null}
        </div>
      )}
      <div className={`card-body${flush ? " flush" : ""}`}>{children}</div>
      {footer ? <div className="card-footer">{footer}</div> : null}
    </Tag>
  );
}

export const Panel = Card;

export type CalloutTone = "info" | "warn" | "danger" | "ok" | "neutral";
const CALLOUT_ICON: Record<CalloutTone, LucideIcon> = {
  info: Info,
  warn: AlertTriangle,
  danger: XCircle,
  ok: CheckCircle2,
  neutral: Info,
};

/** Inline notice row (advisory disclaimers, offline banners). */
export function Callout({
  tone = "info",
  title,
  children,
  icon,
  action,
}: {
  tone?: CalloutTone;
  title?: ReactNode;
  children?: ReactNode;
  icon?: LucideIcon;
  action?: ReactNode;
}) {
  const Icon = icon ?? CALLOUT_ICON[tone];
  return (
    <div className="callout" data-tone={tone === "neutral" ? undefined : tone}>
      <Icon size={18} aria-hidden />
      <div className="grow">
        {title ? <strong>{title}</strong> : null}
        {children ? <div className={title ? "muted small" : undefined} style={title ? { marginTop: 2 } : undefined}>{children}</div> : null}
      </div>
      {action}
    </div>
  );
}
