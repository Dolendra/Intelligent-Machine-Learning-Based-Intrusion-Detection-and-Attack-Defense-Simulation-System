import { useMemo, useState, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { CornerDownLeft, LogIn, Moon, Search, Sun } from "lucide-react";
import { NAV_ROUTES } from "../../app/routes";
import { useTheme } from "../../app/theme";
import { useAuth } from "../../app/auth";
import { Modal } from "../ui/Modal";

interface PaletteItem {
  id: string;
  group: "Pages" | "Actions";
  label: string;
  description?: string;
  icon: LucideIcon;
  keywords: string;
  run: () => void;
}

/** Ctrl/Cmd+K launcher — pages come from APP_ROUTES, so new routes show up automatically. */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { needsLogin } = useAuth();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);

  const items = useMemo<PaletteItem[]>(() => {
    const pages: PaletteItem[] = NAV_ROUTES.map((r) => ({
      id: r.path,
      group: "Pages",
      label: r.label,
      description: r.description,
      icon: r.icon,
      keywords: [r.label, r.section, r.description ?? "", ...(r.keywords ?? [])].join(" ").toLowerCase(),
      run: () => navigate(r.path),
    }));
    const actions: PaletteItem[] = [
      {
        id: "theme",
        group: "Actions",
        label: theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
        icon: theme === "dark" ? Sun : Moon,
        keywords: "theme dark light appearance",
        run: toggleTheme,
      },
    ];
    if (needsLogin) {
      actions.push({ id: "login", group: "Actions", label: "Sign in", icon: LogIn, keywords: "login sign in auth", run: () => navigate("/login") });
    }
    return [...pages, ...actions];
  }, [navigate, theme, toggleTheme, needsLogin]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    const terms = q.split(/\s+/);
    return items.filter((it) => terms.every((t) => it.keywords.includes(t)));
  }, [items, query]);

  const close = () => {
    setQuery("");
    setActive(0);
    onClose();
  };

  function run(item: PaletteItem | undefined) {
    if (!item) return;
    close();
    item.run();
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (filtered.length ? (a + 1) % filtered.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (filtered.length ? (a - 1 + filtered.length) % filtered.length : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      run(filtered[active]);
    }
  }

  let lastGroup = "";
  const listId = "cmdk-list";

  return (
    <Modal open={open} onClose={close} bare ariaLabel="Command palette">
      <div className="cmdk-input-row">
        <Search size={18} aria-hidden />
        <input
          className="cmdk-input"
          data-autofocus
          role="combobox"
          aria-expanded="true"
          aria-controls={listId}
          aria-activedescendant={filtered[active] ? `cmdk-${filtered[active].id}` : undefined}
          aria-label="Search pages and actions"
          placeholder="Jump to a page or run an action…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
        />
        <kbd>Esc</kbd>
      </div>
      <ul className="cmdk-list" id={listId} role="listbox" aria-label="Results">
        {filtered.length === 0 && <li className="cmdk-empty">No results for “{query}”</li>}
        {filtered.map((it, i) => {
          const header = it.group !== lastGroup ? it.group : null;
          lastGroup = it.group;
          const Icon = it.icon;
          return (
            <li key={it.id} role="presentation">
              {header && (
                <div className="cmdk-group" role="presentation">
                  {header}
                </div>
              )}
              <div
                id={`cmdk-${it.id}`}
                role="option"
                aria-selected={i === active}
                className="cmdk-item"
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => run(it)}
              >
                <Icon size={18} aria-hidden />
                <div className="grow">
                  <div>{it.label}</div>
                  {it.description ? <div className="cmdk-item-desc">{it.description}</div> : null}
                </div>
                {i === active ? <CornerDownLeft size={14} aria-hidden /> : null}
              </div>
            </li>
          );
        })}
      </ul>
    </Modal>
  );
}
