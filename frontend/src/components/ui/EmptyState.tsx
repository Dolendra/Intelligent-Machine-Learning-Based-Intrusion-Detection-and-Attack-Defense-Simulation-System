import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

export interface EmptyStateProps {
  title: string;
  description?: ReactNode;
  icon?: LucideIcon;
  /** Buttons / links. */
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ title, description, icon: Icon = Inbox, action, compact }: EmptyStateProps) {
  return (
    <div className={`empty-state${compact ? " compact" : ""}`}>
      {!compact && (
        <span className="empty-icon" aria-hidden>
          <Icon size={22} />
        </span>
      )}
      <strong>{title}</strong>
      {description ? <p>{description}</p> : null}
      {action ? <div className="empty-actions">{action}</div> : null}
    </div>
  );
}
