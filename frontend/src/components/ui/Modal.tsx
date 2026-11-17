import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  /** Accessible name when no visible title is rendered. */
  ariaLabel?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg";
  /** Hide the default header (custom layouts like the command palette). */
  bare?: boolean;
  /** "right" renders a full-height side drawer. */
  placement?: "center" | "right";
  /** Optional line under the title. */
  subtitle?: ReactNode;
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Accessible dialog: portal, Escape/backdrop close, focus trap, focus restore. */
export function Modal({ open, onClose, title, ariaLabel, children, footer, size = "md", bare, placement = "center", subtitle }: ModalProps) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const node = ref.current;
    const first = node?.querySelector<HTMLElement>("[data-autofocus]") ?? node?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        closeRef.current();
        return;
      }
      if (e.key !== "Tab" || !node) return;
      const items = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!items.length) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      previous?.focus?.();
    };
  }, [open]);

  if (!open) return null;
  return createPortal(
    <div
      className="modal-backdrop"
      data-placement={placement}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className="modal"
        data-size={size}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title && !bare ? titleId : undefined}
        aria-label={!title || bare ? ariaLabel : undefined}
      >
        {!bare && (
          <div className="modal-header">
            <div style={{ minWidth: 0 }}>
              <h3 id={titleId}>{title}</h3>
              {subtitle ? <div className="card-subtitle">{subtitle}</div> : null}
            </div>
            <button type="button" className="btn btn-ghost btn-icon btn-sm" aria-label="Close dialog" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        )}
        {bare ? children : <div className="modal-body">{children}</div>}
        {footer ? <div className="modal-footer">{footer}</div> : null}
      </div>
    </div>,
    document.body
  );
}

/** Right-hand side panel with the same focus trap / Escape / backdrop behaviour as Modal. */
export function Drawer(props: Omit<ModalProps, "placement" | "size">) {
  return <Modal {...props} placement="right" />;
}
