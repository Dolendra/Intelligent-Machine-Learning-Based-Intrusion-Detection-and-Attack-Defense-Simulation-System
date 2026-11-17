import { useId, useRef, useState, type DragEvent, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Loader2, UploadCloud } from "lucide-react";

export interface FileDropzoneProps {
  /** `accept` attribute, e.g. ".csv,text/csv". */
  accept: string;
  onFile: (file: File) => void;
  label: string;
  description?: ReactNode;
  icon?: LucideIcon;
  disabled?: boolean;
  busy?: boolean;
  /** Text for the browse button. */
  buttonLabel?: string;
}

function matchesAccept(file: File, accept: string): boolean {
  const rules = accept
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (!rules.length) return true;
  const name = file.name.toLowerCase();
  const type = (file.type || "").toLowerCase();
  return rules.some((r) => (r.startsWith(".") ? name.endsWith(r) : r.endsWith("/*") ? type.startsWith(r.slice(0, -1)) : type === r));
}

/**
 * Drag-and-drop target with a real <button> for keyboard/screen-reader users
 * (the native file input stays visually hidden but is labelled).
 */
export function FileDropzone({
  accept,
  onFile,
  label,
  description,
  icon: Icon = UploadCloud,
  disabled,
  busy,
  buttonLabel = "Choose file",
}: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState<string | null>(null);
  const hintId = useId();
  const inactive = disabled || busy;

  function take(file: File | undefined | null) {
    if (!file || inactive) return;
    if (!matchesAccept(file, accept)) {
      setRejected(`“${file.name}” is not an accepted file type (${accept}).`);
      return;
    }
    setRejected(null);
    onFile(file);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    take(e.dataTransfer.files?.[0]);
  }

  return (
    <div
      className="dropzone"
      data-dragging={dragging || undefined}
      data-disabled={inactive || undefined}
      onDragOver={(e) => {
        e.preventDefault();
        if (!inactive) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <span className="dropzone-icon" aria-hidden>
        {busy ? <Loader2 size={22} className="spin" /> : <Icon size={22} />}
      </span>
      <div className="dropzone-title">{busy ? "Processing…" : label}</div>
      <div className="dropzone-hint" id={hintId}>
        {description ?? "Drag & drop a file here, or browse."}
      </div>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={inactive}
        aria-describedby={hintId}
        onClick={() => inputRef.current?.click()}
      >
        {buttonLabel}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        tabIndex={-1}
        aria-label={label}
        disabled={inactive}
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = "";
          take(f);
        }}
      />
      {rejected ? (
        <div className="small" role="alert" style={{ color: "var(--danger)" }}>
          {rejected}
        </div>
      ) : null}
    </div>
  );
}
