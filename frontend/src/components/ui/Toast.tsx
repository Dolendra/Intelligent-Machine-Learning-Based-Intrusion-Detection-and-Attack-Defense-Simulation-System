import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import { describeError } from "../../lib/errors";

export type ToastTone = "success" | "error" | "info" | "warning";

export interface ToastOptions {
  tone?: ToastTone;
  title: string;
  description?: string;
  /** ms; 0 keeps it until dismissed. Default 5000 (errors 8000). */
  duration?: number;
}

interface ToastItem extends Required<Omit<ToastOptions, "description">> {
  id: number;
  description?: string;
}

export interface ToastApi {
  push: (opts: ToastOptions) => number;
  dismiss: (id: number) => void;
  success: (title: string, description?: string) => number;
  info: (title: string, description?: string) => number;
  warning: (title: string, description?: string) => number;
  /** Accepts a string or any thrown value (ApiError etc.) and renders a friendly message. */
  error: (titleOrError: unknown, description?: string) => number;
}

const ToastContext = createContext<ToastApi | null>(null);

const TONE_ICON = { success: CheckCircle2, error: XCircle, info: Info, warning: AlertTriangle } as const;
const TONE_VAR = { success: "var(--ok)", error: "var(--danger)", info: "var(--info)", warning: "var(--warn)" } as const;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, number>());

  const dismiss = useCallback((id: number) => {
    setItems((cur) => cur.filter((t) => t.id !== id));
    const handle = timers.current.get(id);
    if (handle) window.clearTimeout(handle);
    timers.current.delete(id);
  }, []);

  const push = useCallback(
    (opts: ToastOptions) => {
      const id = nextId.current++;
      const tone = opts.tone ?? "info";
      const duration = opts.duration ?? (tone === "error" ? 8000 : 5000);
      setItems((cur) => [...cur.slice(-3), { id, tone, title: opts.title, description: opts.description, duration }]);
      if (duration > 0) timers.current.set(id, window.setTimeout(() => dismiss(id), duration));
      return id;
    },
    [dismiss]
  );

  useEffect(() => {
    const map = timers.current;
    return () => map.forEach((h) => window.clearTimeout(h));
  }, []);

  const api = useMemo<ToastApi>(
    () => ({
      push,
      dismiss,
      success: (title, description) => push({ tone: "success", title, description }),
      info: (title, description) => push({ tone: "info", title, description }),
      warning: (title, description) => push({ tone: "warning", title, description }),
      error: (titleOrError, description) => {
        if (typeof titleOrError === "string") return push({ tone: "error", title: titleOrError, description });
        const info = describeError(titleOrError);
        return push({ tone: "error", title: description ?? info.title, description: info.message });
      },
    }),
    [push, dismiss]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-region" role="region" aria-label="Notifications" aria-live="polite">
        {items.map((t) => {
          const Icon = TONE_ICON[t.tone];
          return (
            <div
              key={t.id}
              className="toast"
              role={t.tone === "error" ? "alert" : "status"}
              style={{ ["--toast-tone" as string]: TONE_VAR[t.tone] }}
            >
              <Icon size={18} aria-hidden />
              <div className="grow">
                <div className="toast-title">{t.title}</div>
                {t.description ? <div className="toast-desc">{t.description}</div> : null}
              </div>
              <button type="button" className="btn btn-ghost btn-icon btn-sm" aria-label="Dismiss notification" onClick={() => dismiss(t.id)}>
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

const NOOP_TOASTS: ToastApi = {
  push: () => 0,
  dismiss: () => undefined,
  success: () => 0,
  info: () => 0,
  warning: () => 0,
  error: () => 0,
};

/** Toast API. Outside a provider (isolated tests) it degrades to no-ops. */
export function useToast(): ToastApi {
  return useContext(ToastContext) ?? NOOP_TOASTS;
}
