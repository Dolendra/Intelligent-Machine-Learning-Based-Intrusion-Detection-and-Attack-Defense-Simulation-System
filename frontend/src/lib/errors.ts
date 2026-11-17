import { ApiError, detailToMessage } from "../services/api";

export interface ErrorInfo {
  title: string;
  message: string;
  status?: number;
  /** Extra lines such as validation issues. */
  details: string[];
  /** True when the API could not be reached at all. */
  offline: boolean;
}

function tryParseJson(text: string): unknown {
  const t = text.trim();
  if (!t.startsWith("{") && !t.startsWith("[")) return undefined;
  try {
    return JSON.parse(t);
  } catch {
    return undefined;
  }
}

function titleForStatus(status: number): string {
  if (status === 400) return "Request rejected";
  if (status === 401) return "Sign-in required";
  if (status === 403) return "Permission denied";
  if (status === 404) return "Not found";
  if (status === 409) return "Conflict";
  if (status === 413) return "Upload too large";
  if (status === 422) return "Invalid input";
  if (status === 429) return "Rate limit reached";
  if (status === 503) return "Service unavailable";
  if (status >= 500) return "Server error";
  return "Request failed";
}

function validationDetails(detail: unknown): string[] {
  if (!Array.isArray(detail)) return [];
  return detail
    .map((d) => {
      if (d && typeof d === "object") {
        const o = d as Record<string, unknown>;
        const loc = Array.isArray(o.loc) ? o.loc.filter((x) => x !== "body").join(" › ") : "";
        return `${loc ? `${loc}: ` : ""}${String(o.msg ?? "")}`;
      }
      return String(d);
    })
    .filter(Boolean);
}

/**
 * Normalise anything thrown (ApiError, Error, fetch TypeError, raw `{detail}` JSON text, strings)
 * into a human-readable shape for ErrorState / toasts.
 */
export function describeError(error: unknown): ErrorInfo {
  if (error instanceof ApiError) {
    const details = validationDetails(error.detail);
    const message =
      details.length > 1 ? "Some fields failed validation." : detailToMessage(error.detail) || error.message || "Unknown error";
    return { title: titleForStatus(error.status), message, status: error.status, details: details.length > 1 ? details : [], offline: false };
  }

  if (error instanceof TypeError && /fetch|network|load failed/i.test(error.message)) {
    return {
      title: "Can't reach the Aegis API",
      message: "The backend did not respond. Start it with `uvicorn backend.main:app --port 8000` and retry.",
      details: [],
      offline: true,
    };
  }

  const raw = error instanceof Error ? error.message : typeof error === "string" ? error : "";
  const parsed = raw ? tryParseJson(raw) : undefined;
  if (parsed && typeof parsed === "object") {
    const detail = "detail" in (parsed as object) ? (parsed as { detail: unknown }).detail : parsed;
    const details = validationDetails(detail);
    return {
      title: details.length ? "Invalid input" : "Request failed",
      message: (details.length > 1 ? "Some fields failed validation." : detailToMessage(detail)) || raw,
      details: details.length > 1 ? details : [],
      offline: false,
    };
  }

  if (error && typeof error === "object" && !(error instanceof Error) && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    return { title: "Request failed", message: detailToMessage(detail) || "Unknown error", details: validationDetails(detail), offline: false };
  }

  return { title: "Something went wrong", message: raw || "Unknown error", details: [], offline: false };
}

/** One-line message for toasts. */
export function errorMessage(error: unknown): string {
  const info = describeError(error);
  return info.message;
}
