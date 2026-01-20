import { MetaProvider, Title } from "@solidjs/meta";
import { Router } from "@solidjs/router";
import { FileRoutes } from "@solidjs/start/router";
import { Suspense, onMount } from "solid-js";
import { SessionProvider } from "~/lib/session";
import { applyTheme } from "~/lib/theme";
import { PageLoading } from "~/ui/States";
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
            <Suspense fallback={<PageLoading />}>{props.children}</Suspense>
            <AppToaster />
          </SessionProvider>
        </MetaProvider>
      )}
    >
      <FileRoutes />
    </Router>
  );
}
