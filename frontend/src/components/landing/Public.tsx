/** The public pages' bar and footer: the brand, the theme switch and sign-in; the compliance line once. */
import { A } from "@solidjs/router";
import type { JSX } from "solid-js";
import { ThemeButton } from "~/components/shell/TopBar";
import { Brand } from "~/ui/Compass";
import { button } from "~/ui/recipes";

export function PublicBar(props: { onBrand?: () => void; right?: JSX.Element }) {
  return (
    <header class="mx-auto flex h-[64px] max-w-[1120px] items-center justify-between px-6 max-sm:px-4">
      <A href="/" class="no-underline" aria-label="Tariff Compass" onClick={() => props.onBrand?.()}>
        <Brand />
      </A>
      <div class="flex items-center gap-2">
        <ThemeButton />
        {props.right ?? (
          <A href="/signin" class={button({ tone: "outline", size: "sm" })}>
            Sign in
          </A>
        )}
      </div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer class="border-t border-rule">
      <div class="mx-auto flex max-w-[1120px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-8 text-[12.5px] text-muted max-sm:px-4">
        <span class="inline-flex items-center gap-2 text-ink-2">
          <Brand compact /> Tariff Compass
        </span>
        <span class="max-w-[640px]">
          Designed to support reasonable-care record keeping (19 U.S.C. 1484). Not legal advice; a licensed customs broker approves every code. Samples use
          Northbound Goods Co., a sample importer; rulings cited are real CBP rulings.
        </span>
      </div>
    </footer>
  );
}
