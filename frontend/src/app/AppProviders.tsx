import type { ReactNode } from "react";
import { ThemeProvider } from "./theme";
import { AuthProvider } from "./auth";
import { LiveProvider } from "./live";
import { ToastProvider } from "../components/ui/Toast";

/** Theme → toasts → auth → live connection. Wrap the router (and tests) with this. */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <LiveProvider>{children}</LiveProvider>
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
