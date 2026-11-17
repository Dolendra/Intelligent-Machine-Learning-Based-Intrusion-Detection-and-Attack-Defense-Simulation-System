import { useEffect, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  /** Small uppercase kicker above the title. */
  eyebrow?: ReactNode;
  icon?: LucideIcon;
  actions?: ReactNode;
  /** Also sets document.title (default true). */
  setDocumentTitle?: boolean;
}

export function PageHeader({ title, subtitle, eyebrow, icon: Icon, actions, setDocumentTitle = true }: PageHeaderProps) {
  useEffect(() => {
    if (!setDocumentTitle) return;
    const prev = document.title;
    document.title = `${title} · Aegis IDS`;
    return () => {
      document.title = prev;
    };
  }, [title, setDocumentTitle]);

  return (
    <header className="page-header rise">
      <div className="page-header-text">
        {eyebrow || Icon ? (
          <div className="page-eyebrow">
            {Icon ? <Icon size={14} aria-hidden /> : null}
            {eyebrow}
          </div>
        ) : null}
        <h2>{title}</h2>
        {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}
