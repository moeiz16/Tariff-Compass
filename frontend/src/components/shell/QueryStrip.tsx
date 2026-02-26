/**
 * The query strip on every app page: the mark in the 280 px gutter, the box across the measure, the person at
 * the right, and the scopes printed on the strip's lower edge (Ark Tabs as links, highlighter underline).
 */
import { Menu } from "@ark-ui/solid/menu";
import { Tabs } from "@ark-ui/solid/tabs";
import { A, useNavigate } from "@solidjs/router";
import { For, Show, createResource, type JSX } from "solid-js";
import { Portal } from "solid-js/web";
import { meta } from "~/lib/endpoints";
import { initials } from "~/lib/format";
import { SCOPE_PERMISSION, useSession } from "~/lib/session";
import { theme, toggleTheme } from "~/lib/theme";
import { Brand } from "~/ui/Compass";
import { MoonIcon, SunIcon } from "~/ui/Icons";
import { floating, tabs } from "~/ui/recipes";

export type Scope = "answer" | "rulings" | "tariff" | "products" | "review" | "watch" | "lab" | "none";

const SCOPES: { key: Exclude<Scope, "none">; label: string; href: string; count?: "rulings" | "products" | "review" | "watch" }[] = [
  { key: "answer", label: "Answer", href: "/answer" },
  { key: "rulings", label: "Rulings", href: "/rulings", count: "rulings" },
  { key: "tariff", label: "Tariff text", href: "/tariff" },
  { key: "products", label: "My products", href: "/products", count: "products" },
  { key: "review", label: "Review", href: "/review", count: "review" },
  { key: "watch", label: "Watch", href: "/watch", count: "watch" },
  { key: "lab", label: "Lab", href: "/lab" },
];

export function ThemeButton() {
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme() === "light" ? "Switch to night reading" : "Switch to paper"}
      aria-pressed={theme() === "dark"}
      class="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-rule text-ink hover:border-ink"
    >
      <Show when={theme() === "light"} fallback={<SunIcon size={18} />}>
        <MoonIcon size={18} />
      </Show>
    </button>
  );
}

export function PersonMenu() {
  const { me, can, signOut } = useSession();
  const navigate = useNavigate();
  return (
    <Show when={me()}>
      {(m) => (
        <Menu.Root positioning={{ placement: "bottom-end", gutter: 8 }} onSelect={(d) => {
          if (d.value === "signout") void signOut();
          else navigate(d.value);
        }}>
          <Menu.Trigger class="flex items-center gap-3 rounded-full text-right" aria-label={`Account: ${m().user.fullName}`}>
            <span class="whitespace-nowrap leading-tight max-lg:hidden">
              <span class="block text-[14.5px] font-[700]">{m().user.fullName}</span>
              <span class="block text-[13px] text-muted">
                {m().orgs.find((o) => o.id === m().activeOrg?.id)?.viaBroker ?? m().activeOrg?.name}
              </span>
            </span>
            <span class="grid h-11 w-11 place-items-center rounded-full bg-ink font-type text-[14px] font-[700] text-paper">{initials(m().user.fullName)}</span>
          </Menu.Trigger>
          <Portal>
            <Menu.Positioner class="z-50">
              <Menu.Content class={floating({ class: "min-w-[240px] py-1.5" })}>
                <div class="border-b border-rule px-3.5 pb-2 pt-1 text-[13px]">
                  <p class="font-[700] text-ink">{m().user.fullName}</p>
                  <p class="text-muted">
                    {m().membership?.roleLabel} · {m().activeOrg?.name}
                  </p>
                </div>
                <Menu.Item value="/settings" class="cursor-pointer px-3.5 py-2 text-[15px] data-[highlighted]:bg-paper-2">
                  Settings
                </Menu.Item>
                <Show when={can("audit:read")}>
                  <Menu.Item value="/activity" class="cursor-pointer px-3.5 py-2 text-[15px] data-[highlighted]:bg-paper-2">
                    Activity record
                  </Menu.Item>
                </Show>
                <Show when={m().orgs.length > 1}>
                  <Menu.Item value="/settings?switch=1" class="cursor-pointer px-3.5 py-2 text-[15px] data-[highlighted]:bg-paper-2">
                    Switch organisation
                  </Menu.Item>
                </Show>
                <Menu.Separator class="my-1 border-rule" />
                <Menu.Item value="signout" class="cursor-pointer px-3.5 py-2 text-[15px] data-[highlighted]:bg-paper-2">
                  Sign out
                </Menu.Item>
              </Menu.Content>
            </Menu.Positioner>
          </Portal>
        </Menu.Root>
      )}
    </Show>
  );
}

export function Scopes(props: { active: Scope }) {
  const { can, me } = useSession();
  const [counts] = createResource(() => (me() ? true : null), () => meta.counts().catch(() => null));
  const visible = () => SCOPES.filter((s) => can(SCOPE_PERMISSION[s.key]!));
  const t = tabs();
  return (
    <Tabs.Root value={props.active === "none" ? null : props.active} activationMode="manual" class="min-w-0">
      <Tabs.List class={t.list()} aria-label="Search in">
        <For each={visible()}>
          {(s) => (
            <Tabs.Trigger
              value={s.key}
              asChild={(p) => (
                <A {...p()} href={s.href} class={t.trigger()} aria-current={props.active === s.key ? "page" : undefined}>
                  {s.label}
                  <Show when={s.count && counts()?.[s.count] !== undefined}>
                    <span class={t.count({ class: props.active === s.key ? "hl px-0.5" : "" })}>{counts()![s.count!]}</span>
                  </Show>
                </A>
              )}
            />
          )}
        </For>
        <Tabs.Indicator class={t.indicator({ class: "w-[var(--width)] left-[var(--left)]" })} />
      </Tabs.List>
    </Tabs.Root>
  );
}

export function QueryStrip(props: { scope: Scope; box: JSX.Element }) {
  return (
    <header class="border-b-[1.5px] border-ink bg-paper">
      <a href="#main" class="sr-only-focusable absolute left-2 top-2 z-50 rounded bg-ink px-3 py-2 text-paper">
        Skip to the content
      </a>
      <div class="grid grid-cols-[var(--spacing-gutter)_minmax(0,880px)_1fr] items-center gap-y-2 px-8 pt-3.5 max-[960px]:grid-cols-[1fr_auto] max-[960px]:px-4 max-[960px]:pt-2.5">
        <A href="/home" class="w-fit no-underline" aria-label="Tariff Compass front page">
          <span class="max-[960px]:hidden">
            <Brand />
          </span>
          <span class="hidden max-[960px]:inline">
            <Brand compact />
          </span>
        </A>
        <div class="min-w-0 max-[960px]:col-span-2 max-[960px]:row-start-2">{props.box}</div>
        <div class="flex items-center justify-end gap-4 pl-6 max-[960px]:col-start-2 max-[960px]:row-start-1 max-[960px]:pl-0">
          <ThemeButton />
          <PersonMenu />
        </div>
      </div>
      <div class="grid grid-cols-[var(--spacing-gutter)_minmax(0,1fr)] px-8 pt-2 max-[960px]:grid-cols-1 max-[960px]:px-4">
        <span class="max-[960px]:hidden" />
        <Scopes active={props.scope} />
      </div>
    </header>
  );
}
