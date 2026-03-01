/**
 * Frame for signed-in pages: waits for the session, sends signed-out visitors to /signin and back afterwards,
 * renders the top bar, and refuses pages the role can't open. Pages put one title in a PageHead.
 */
import { Navigate, useLocation } from "@solidjs/router";
import { Show, createSignal, createEffect, on, untrack, type JSX } from "solid-js";
import { Title } from "@solidjs/meta";
import { useSession } from "~/lib/session";
import { SearchIcon } from "~/ui/Icons";
import { EmptyState, PageLoading } from "~/ui/States";
import { TopBar, type Place } from "./TopBar";

export interface AppPageProps {
  title: string;
  place: Place;
  permission?: string;
  /** Content width: narrow for reading (answer, binder), wide for tables. */
  width?: "narrow" | "default" | "wide";
  children: JSX.Element;
}

const WIDTH = { narrow: "max-w-[820px]", default: "max-w-[1040px]", wide: "max-w-[1280px]" };

export function AppPage(props: AppPageProps) {
  const { session, me, can } = useSession();
  const location = useLocation();
  return (
    <Show when={!session.loading || session.latest} fallback={<PageLoading label="Opening Tariff Compass…" />}>
      <Show when={me()} fallback={<Navigate href={`/signin?next=${encodeURIComponent(location.pathname + location.search)}`} />}>
        <Title>{`${props.title} · Tariff Compass`}</Title>
        <TopBar active={props.place} />
        <main id="main" tabIndex={-1} class={`mx-auto w-full px-6 pb-20 pt-8 outline-none max-sm:px-4 max-sm:pt-5 ${WIDTH[props.width ?? "default"]}`}>
          <Show
            when={!props.permission || can(props.permission)}
            fallback={
              <EmptyState title="Not part of your role">
                {me()?.membership?.roleLabel} accounts don't open this page. An administrator can change your role in Settings.
              </EmptyState>
            }
          >
            {props.children}
          </Show>
        </main>
      </Show>
    </Show>
  );
}

/** The one title on a screen, with an optional line of meta under it and actions on the right. */
export function PageHead(props: { title: JSX.Element; meta?: JSX.Element; actions?: JSX.Element; class?: string }) {
  return (
    <div class={`mb-6 flex flex-wrap items-end justify-between gap-x-6 gap-y-3 max-sm:flex-col max-sm:items-stretch ${props.class ?? ""}`}>
      <div class="min-w-0 flex-1">
        <h1 class="page-title">{props.title}</h1>
        <Show when={props.meta}>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13.5px] text-muted">{props.meta}</div>
        </Show>
      </div>
      <Show when={props.actions}>
        <div class="flex flex-wrap items-center gap-2">{props.actions}</div>
      </Show>
    </div>
  );
}

/** A search field for a list page. Enter searches; clearing it searches for everything again. */
export function PageSearch(props: { label: string; placeholder: string; value?: string; onSearch: (q: string) => void; class?: string }) {
  const [text, setText] = createSignal(untrack(() => props.value) ?? "");
  createEffect(on(() => props.value, (v) => setText(v ?? ""), { defer: true }));
  return (
    <form
      role="search"
      class={`relative ${props.class ?? "w-[320px] max-sm:w-full"}`}
      onSubmit={(e) => {
        e.preventDefault();
        props.onSearch(text().trim());
      }}
    >
      <label class="sr-only" for="page-search">
        {props.label}
      </label>
      <SearchIcon size={15} class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
      <input
        id="page-search"
        type="search"
        value={text()}
        onInput={(e) => {
          setText(e.currentTarget.value);
          if (!e.currentTarget.value) props.onSearch("");
        }}
        placeholder={props.placeholder}
        autocomplete="off"
        class="h-10 w-full rounded-[var(--radius-btn)] border border-rule-2 bg-card pl-9 pr-3 text-[14.5px] text-ink outline-none placeholder:text-muted focus:border-ink"
      />
    </form>
  );
}
