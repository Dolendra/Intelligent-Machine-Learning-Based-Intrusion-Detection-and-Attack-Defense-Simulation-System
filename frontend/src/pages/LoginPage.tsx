import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Loader2, LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "../app/auth";
import { Callout, Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { useToast } from "../components/ui/Toast";
import { ThemeToggle } from "../components/layout/ThemeToggle";

function safeNext(raw: string | null): string {
  // Only allow in-app relative paths.
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/login")) return "/";
  return raw;
}

export function LoginPage() {
  const { login, authEnabled, me, loading } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      setPassword("");
      toast.success(`Signed in as ${username}`);
      navigate(next, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <div style={{ position: "fixed", top: 12, right: 12 }}>
        <ThemeToggle />
      </div>
      <div className="auth-card stack rise">
        <div className="row" style={{ justifyContent: "center", gap: 12 }}>
          <span className="brand-shield" aria-hidden>
            <ShieldCheck size={20} />
          </span>
          <div>
            <div className="brand-name">Aegis IDS</div>
            <div className="muted small">Security operations console</div>
          </div>
        </div>

        <Card title="Sign in" subtitle="Use your analyst credentials." icon={LogIn}>
          {!loading && !authEnabled ? (
            <div className="stack">
              <Callout tone="info" title="Authentication is disabled">
                This server runs in open demo mode — no sign-in needed.
              </Callout>
              <Link className="btn btn-primary" to={next}>
                Continue to console
              </Link>
            </div>
          ) : me?.authenticated ? (
            <div className="stack">
              <Callout tone="ok" title={`Signed in as ${me.username}`}>
                Role: {me.role}
              </Callout>
              <Link className="btn btn-primary" to={next}>
                Continue
              </Link>
            </div>
          ) : (
            <form className="stack" onSubmit={(e) => void onSubmit(e)} noValidate>
              <div className="field">
                <label className="field-label" htmlFor="login-username">
                  Username
                </label>
                <input
                  id="login-username"
                  className="input"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                  autoFocus
                />
              </div>
              <div className="field">
                <label className="field-label" htmlFor="login-password">
                  Password
                </label>
                <input
                  id="login-password"
                  className="input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
              {error ? <ErrorState error={error} title="Sign-in failed" /> : null}
              <button className="btn btn-primary" type="submit" disabled={busy || !username || !password}>
                {busy ? <Loader2 size={16} className="spin" aria-hidden /> : <LogIn size={16} aria-hidden />}
                {busy ? "Signing in…" : "Sign in"}
              </button>
              <p className="muted small">The API enforces role-based access; the UI only hides actions you cannot perform.</p>
            </form>
          )}
        </Card>
        <Link to="/" className="row small" style={{ justifyContent: "center", gap: 6 }}>
          <ArrowLeft size={14} aria-hidden /> Back to dashboard
        </Link>
      </div>
    </div>
  );
}
