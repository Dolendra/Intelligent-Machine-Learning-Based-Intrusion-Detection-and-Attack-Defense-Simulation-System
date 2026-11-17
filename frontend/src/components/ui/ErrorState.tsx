import { RefreshCw, ServerCrash, TriangleAlert } from "lucide-react";
import { describeError } from "../../lib/errors";

export interface ErrorStateProps {
  /** Anything thrown: ApiError, Error, fetch TypeError, raw `{"detail": ...}` text or a string. */
  error: unknown;
  /** Overrides the derived title. */
  title?: string;
  onRetry?: () => void;
  retrying?: boolean;
}

/** Friendly error panel — parses FastAPI `{detail}` payloads, validation lists and network failures. */
export function ErrorState({ error, title, onRetry, retrying }: ErrorStateProps) {
  const info = describeError(error);
  const Icon = info.offline ? ServerCrash : TriangleAlert;
  return (
    <div className="error-state" role="alert" data-offline={info.offline || undefined}>
      <Icon size={20} className="error-icon" aria-hidden />
      <div className="grow">
        <div className="error-title">
          {title ?? info.title}
          {info.status ? <span className="badge badge-sm mono">HTTP {info.status}</span> : null}
        </div>
        <div className="error-message">{info.message}</div>
        {info.details.length > 0 && (
          <ul className="error-details">
            {info.details.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        )}
      </div>
      {onRetry ? (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry} disabled={retrying}>
          <RefreshCw size={14} className={retrying ? "spin" : undefined} aria-hidden />
          Retry
        </button>
      ) : null}
    </div>
  );
}
