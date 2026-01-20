/**
 * Frame for signed-in pages: waits for the session, sends signed-out visitors to /signin and back afterwards,
 * renders the query strip with the box for the current scope, and refuses pages the role can't open.
 */
import { Navigate, useLocation, useNavigate } from "@solidjs/router";
import { Show, createResource, type JSX } from "solid-js";
import { Title } from "@solidjs/meta";
import { meta } from "~/lib/endpoints";
import { useSession } from "~/lib/session";
import { PageLoading } from "~/ui/States";
import { EmptyState } from "~/ui/States";
import { QueryStrip, type Scope } from "./QueryStrip";
import { SearchBox } from "./SearchBox";

export interface AppPageProps {
  title: string;
  scope: Scope;
  permission?: string;
  placeholder?: string;
  boxLabel?: string;
  query?: string;
  /** Search handler for non-Answer scopes; Answer classifies. */
  onSearch?: (q: string) => void;
  children: JSX.Element;
}

export function AppPage(props: AppPageProps) {
  const { session, me, can } = useSession();
  const location = useLocation();
  const navigate = useNavigate();
  const classify = () => props.scope === "answer" || props.scope === "none" ? !props.onSearch : false;
  const [recent] = createResource(
    () => (me() && classify() ? true : null),
    async () => {
      const [home, m] = await Promise.all([meta.home().catch(() => null), meta.get().catch(() => null)]);
      return { suggestions: home?.recent.map((r) => r.queryText) ?? [], origins: m?.origins ?? [] };
    },
  );

  const box = () => (
    <SearchBox
      id="q"
      mode={classify() ? "classify" : "search"}
      size="strip"
      label={props.boxLabel ?? (classify() ? "Describe what you're importing" : "Search")}
      placeholder={props.placeholder ?? "Describe what you're importing…"}
      value={props.query}
      suggestions={recent()?.suggestions}
      origins={recent()?.origins}
      allowFiles={classify() && can("classify:run")}
      onSubmit={(text, opts) => {
        if (!classify()) return props.onSearch?.(text);
        if (!can("classify:run")) return;
        const ev = opts.evidence.map((e) => e.id).join(",");
        const params = new URLSearchParams({ q: text, into: opts.into.join(","), from: opts.madeIn });
        if (ev) params.set("ev", ev);
        navigate(`/answer?${params.toString()}`);
      }}
    />
  );

  return (
    <Show when={!session.loading || session.latest} fallback={<PageLoading label="Opening Tariff Compass…" />}>
      <Show when={me()} fallback={<Navigate href={`/signin?next=${encodeURIComponent(location.pathname + location.search)}`} />}>
        <Title>{`${props.title} · Tariff Compass`}</Title>
        <QueryStrip scope={props.scope} box={box()} />
        <main id="main" tabIndex={-1} class="outline-none">
          <Show
            when={!props.permission || can(props.permission)}
            fallback={
              <div class="gm py-12">
                <div class="gl" />
                <div class="gm-body">
                  <EmptyState title="This page isn't part of your role">
                    {me()?.membership?.roleLabel} accounts don't open this page. An administrator can change your role in Settings.
                  </EmptyState>
                </div>
              </div>
            }
          >
            {props.children}
          </Show>
        </main>
      </Show>
    </Show>
  );
}

