import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Command, LogIn, LogOut, Monitor, Moon, Sun } from "lucide-react";
import { useAuth } from "../../app/auth";
import { useTheme } from "../../app/theme";
import { useToast } from "../ui/Toast";
import { humanize } from "../../lib/format";

export function UserMenu({ onOpenPalette }: { onOpenPalette: () => void }) {
  const { me, authEnabled, logout, needsLogin } = useAuth();
  const { theme, toggleTheme, useSystemTheme, explicit } = useTheme();
  const toast = useToast();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        btnRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    ref.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const name = me?.authenticated ? me.username ?? "analyst" : authEnabled ? "Signed out" : "Demo analyst";
  const role = me?.authenticated ? humanize(me.role) : authEnabled ? "Sign in required" : "Open access · auth disabled";
  const initials = (me?.authenticated ? me.username ?? "A" : authEnabled ? "?" : "DA").slice(0, 2).toUpperCase();

  function onMenuKey(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const items = Array.from(ref.current?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? []);
    const idx = items.indexOf(document.activeElement as HTMLElement);
    const next = e.key === "ArrowDown" ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
    items[next]?.focus();
  }

  const item = (label: string, Icon: typeof Sun, onClick: () => void) => (
    <button
      type="button"
      role="menuitem"
      className="menu-item"
      onClick={() => {
        setOpen(false);
        onClick();
      }}
    >
      <Icon size={16} aria-hidden />
      {label}
    </button>
  );

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        ref={btnRef}
        type="button"
        className="user-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account menu for ${name}`}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="avatar" aria-hidden>
          {initials}
        </span>
        <ChevronDown size={14} aria-hidden className="desktop-only" />
      </button>
      {open && (
        <div className="menu" role="menu" aria-label="Account" onKeyDown={onMenuKey}>
          <div className="menu-header">
            <div style={{ fontWeight: 600 }}>{name}</div>
            <div className="muted small">{role}</div>
          </div>
          {needsLogin && item("Sign in", LogIn, () => navigate("/login"))}
          {authEnabled &&
            me?.authenticated &&
            item("Sign out", LogOut, () => {
              void logout().then(() => toast.info("Signed out"));
            })}
          {item(theme === "dark" ? "Light theme" : "Dark theme", theme === "dark" ? Sun : Moon, toggleTheme)}
          {explicit && item("Follow system theme", Monitor, useSystemTheme)}
          {item("Command palette", Command, onOpenPalette)}
        </div>
      )}
    </div>
  );
}
