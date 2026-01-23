import { MetaProvider, Title } from "@solidjs/meta";
import { Router } from "@solidjs/router";
import { FileRoutes } from "@solidjs/start/router";
import { ErrorBoundary, onMount } from "solid-js";
import { SessionProvider } from "~/lib/session";
import { applyTheme } from "~/lib/theme";
import { ErrorSlip } from "~/ui/States";
import { AppToaster } from "~/ui/Toast";
import "./styles/app.css";

export default function App() {
  onMount(() => applyTheme());
  return (
    <Router
      root={(props) => (
        <MetaProvider>
          <Title>Tariff Compass</Title>
          <SessionProvider>
            {/* No root Suspense: every screen draws its own loading state, and lists keep their rows while they refresh. */}
            <ErrorBoundary
              fallback={(err, reset) => (
                <main class="mx-auto max-w-[720px] px-4 py-20">
                  <ErrorSlip error={err} retry={reset} />
                </main>
              )}
            >
              {props.children}
            </ErrorBoundary>
            <AppToaster />
          </SessionProvider>
        </MetaProvider>
      )}
    >
      <FileRoutes />
    </Router>
  );
}
