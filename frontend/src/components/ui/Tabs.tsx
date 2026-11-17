import { useRef, type KeyboardEvent, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export interface TabItem<T extends string = string> {
  id: T;
  label: ReactNode;
  icon?: LucideIcon;
  /** Small count chip after the label. */
  count?: number;
  disabled?: boolean;
}

export interface TabsProps<T extends string> {
  /** Unique prefix used to wire tab ↔ panel ids (`${id}-tab-x`, `${id}-panel-x`). */
  id: string;
  /** Accessible name of the tablist. */
  label: string;
  items: TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  variant?: "underline" | "pill";
}

/**
 * WAI-ARIA tabs (automatic activation): roving tabindex, ←/→ (and ↑/↓) move + select,
 * Home/End jump, disabled tabs are skipped. Pair with <TabPanel tabsId={id} value=... active=...>.
 */
export function Tabs<T extends string>({ id, label, items, value, onChange, variant = "underline" }: TabsProps<T>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  function focusAt(index: number) {
    const item = items[index];
    if (!item) return;
    onChange(item.id);
    refs.current[index]?.focus();
  }

  function onKeyDown(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    const enabled = items.map((t, i) => (t.disabled ? -1 : i)).filter((i) => i >= 0);
    if (!enabled.length) return;
    const pos = enabled.indexOf(index);
    let next: number | null = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = enabled[(pos + 1) % enabled.length];
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = enabled[(pos - 1 + enabled.length) % enabled.length];
    else if (e.key === "Home") next = enabled[0];
    else if (e.key === "End") next = enabled[enabled.length - 1];
    if (next !== null) {
      e.preventDefault();
      focusAt(next);
    }
  }

  const selectedEnabled = items.some((t) => t.id === value && !t.disabled);

  return (
    <div className="tabs" role="tablist" aria-label={label} data-variant={variant === "pill" ? "pill" : undefined}>
      {items.map((t, i) => {
        const selected = t.id === value;
        const firstEnabled = items.findIndex((x) => !x.disabled);
        const tabbable = selected ? !t.disabled : !selectedEnabled && i === firstEnabled;
        const Icon = t.icon;
        return (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${id}-tab-${t.id}`}
            aria-selected={selected}
            aria-controls={`${id}-panel-${t.id}`}
            tabIndex={tabbable ? 0 : -1}
            disabled={t.disabled}
            className="tab"
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {Icon ? <Icon size={15} aria-hidden /> : null}
            {t.label}
            {t.count != null ? <span className="tab-count">{t.count}</span> : null}
          </button>
        );
      })}
    </div>
  );
}

export interface TabPanelProps<T extends string> {
  tabsId: string;
  value: T;
  active: T;
  children: ReactNode;
  className?: string;
}

/** Renders only when `active === value`; wired to its tab via aria-labelledby. */
export function TabPanel<T extends string>({ tabsId, value, active, children, className }: TabPanelProps<T>) {
  if (value !== active) return null;
  return (
    <div
      role="tabpanel"
      id={`${tabsId}-panel-${value}`}
      aria-labelledby={`${tabsId}-tab-${value}`}
      tabIndex={0}
      className={`tabpanel${className ? ` ${className}` : ""}`}
    >
      {children}
    </div>
  );
}
