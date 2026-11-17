import { Link, useLocation } from "react-router-dom";
import { Command, Home } from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";

export function NotFoundPage() {
  const { pathname } = useLocation();
  return (
    <div className="notfound">
      <div className="stack" style={{ alignItems: "center" }}>
        <div className="notfound-code" aria-hidden>
          404
        </div>
        <PageHeader title="Page not found" subtitle={<>Nothing lives at <code>{pathname}</code>.</>} />
        <div className="row" style={{ justifyContent: "center" }}>
          <Link className="btn btn-primary" to="/">
            <Home size={16} aria-hidden /> Go to dashboard
          </Link>
          <span className="muted small row" style={{ gap: 6 }}>
            <Command size={14} aria-hidden /> or press Ctrl/⌘ K to search
          </span>
        </div>
      </div>
    </div>
  );
}
