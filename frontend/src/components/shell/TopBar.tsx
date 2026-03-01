/**
 * The top bar on every signed-in page: the brand, six places (role-gated), the theme switch and the person.
 * On phones the places move into a menu.
 */
import { Menu } from "@ark-ui/solid/menu";
import { A, useNavigate } from "@solidjs/router";
import { For, Show, createResource } from "solid-js";
import { Portal } from "solid-js/web";
import { meta } from "~/lib/endpoints";
import { initials } from "~/lib/format";
import { SCOPE_PERMISSION, useSession } from "~/lib/session";
import { theme, toggleTheme } from "~/lib/theme";
import { Brand } from "~/ui/Compass";
import { MenuIcon, MoonIcon, SunIcon } from "~/ui/Icons";
import { floating } from "~/ui/recipes";

export type Place = "classify" | "review" | "products" | "library" | "watch" | "lab" | "none";

export const PLACES: { key: Exclude<Place, "none">; label: string; href: string; permission: string }[] = [
  { key: "classify", label: "Classify", href: "/home", permission: SCOPE_PERMISSION.answer! },
  { key: "review", label: "Review", href: "/review", permission: SCOPE_PERMISSION.review! },
  { key: "products", label: "Products", href: "/products", permission: SCOPE_PERMISSION.products! },
  { key: "library", label: "Library", href: "/rulings", permission: SCOPE_PERMISSION.rulings! },
  { key: "watch", label: "Watch", href: "/watch", permission: SCOPE_PERMISSION.watch! },
  { key: "lab", label: "Lab", href: "/lab", permission: SCOPE_PERMISSION.lab! },
];

const item = "cursor-pointer rounded-[6px] px-2.5 py-2 text-[14px] data-[highlighted]:bg-paper-2";

export function ThemeButton() {
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme() === "light" ? "Switch to dark" : "Switch to light"}
      aria-pressed={theme() === "dark"}
      class="grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink-2 hover:bg-paper-2 hover:text-ink"
    >
      <Show when={theme() === "light"} fallback={<SunIcon size={17} />}>
        <MoonIcon size={17} />
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
        <Menu.Root
          positioning={{ placement: "bottom-end", gutter: 8 }}
          onSelect={(d) => {
            if (d.value === "signout") void signOut();
            else navigate(d.value);
          }}
        >
          <Menu.Trigger class="grid h-9 w-9 place-items-center rounded-full bg-ink text-[12.5px] font-[650] text-card hover:opacity-90" aria-label={`Account: ${m().user.fullName}`}>
            {initials(m().user.fullName)}
          </Menu.Trigger>
          <Portal>
            <Menu.Positioner class="z-50">
              <Menu.Content class={floating({ class: "min-w-[240px] p-1.5" })}>
                <div class="px-2.5 pb-2 pt-1.5">
                  <p class="text-[14px] font-[600] text-ink">{m().user.fullName}</p>
                  <p class="text-[12.5px] text-muted">
                    {m().membership?.roleLabel} · {m().activeOrg?.name}
                  </p>
                </div>
                <Menu.Separator class="my-1 border-rule" />
                <Menu.Item value="/settings" class={item}>
                  Settings
                </Menu.Item>
                <Show when={can("audit:read")}>
                  <Menu.Item value="/activity" class={item}>
                    Activity
                  </Menu.Item>
                </Show>
                <Show when={m().orgs.length > 1}>
                  <Menu.Item value="/settings?switch=1" class={item}>
                    Switch organisation
                  </Menu.Item>
                </Show>
                <Menu.Separator class="my-1 border-rule" />
                <Menu.Item value="signout" class={item}>
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

/** The six places, filtered by role. Review carries its waiting count. */
export function Nav(props: { active: Place }) {
  const { can, me } = useSession();
  const [counts] = createResource(() => (me() && can("review:read") ? true : null), () => meta.counts().catch(() => null));
  const visible = () => PLACES.filter((p) => can(p.permission));
  return (
    <nav aria-label="Places" class="flex items-center gap-1 max-[860px]:hidden">
      <For each={visible()}>
        {(p) => (
          <A
            href={p.href}
            aria-current={props.active === p.key ? "page" : undefined}
            class="relative inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-[14px] font-[550] text-muted no-underline hover:bg-paper-2 hover:text-ink aria-[current=page]:bg-paper-2 aria-[current=page]:text-ink"
          >
            {p.label}
            <Show when={p.key === "review" && counts()?.review}>
              <span class="rounded-full bg-ink px-1.5 text-[11px] font-[650] leading-[17px] text-card">{counts()!.review}</span>
            </Show>
          </A>
        )}
      </For>
    </nav>
  );
}

function PhoneNav(props: { active: Place }) {
  const { can } = useSession();
  const navigate = useNavigate();
  return (
    <Menu.Root positioning={{ placement: "bottom-end", gutter: 8 }} onSelect={(d) => navigate(d.value)}>
      <Menu.Trigger class="hidden h-9 w-9 place-items-center rounded-full text-ink-2 hover:bg-paper-2 max-[860px]:grid" aria-label="Places">
        <MenuIcon size={18} />
      </Menu.Trigger>
      <Portal>
        <Menu.Positioner class="z-50">
          <Menu.Content class={floating({ class: "min-w-[200px] p-1.5" })}>
            <For each={PLACES.filter((p) => can(p.permission))}>
              {(p) => (
                <Menu.Item value={p.href} class={`${item} ${props.active === p.key ? "font-[650]" : ""}`}>
                  {p.label}
                </Menu.Item>
              )}
            </For>
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>
  );
}

export function TopBar(props: { active: Place }) {
  return (
    <header class="sticky top-0 z-30 border-b border-rule bg-card/90 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <a href="#main" class="sr-only-focusable absolute left-2 top-2 z-50 rounded bg-ink px-3 py-2 text-card">
        Skip to the content
      </a>
      <div class="mx-auto flex h-[60px] max-w-[1280px] items-center gap-6 px-6 max-sm:gap-3 max-sm:px-4">
        <A href="/home" class="no-underline" aria-label="Tariff Compass home">
          <Brand />
        </A>
        <div class="flex flex-1 justify-center">
          <Nav active={props.active} />
        </div>
        <div class="flex items-center gap-1.5">
          <PhoneNav active={props.active} />
          <ThemeButton />
          <PersonMenu />
        </div>
      </div>
    </header>
  );
}
