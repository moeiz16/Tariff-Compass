import { Title } from "@solidjs/meta";
import { A } from "@solidjs/router";
import { HttpStatusCode } from "@solidjs/start";
import { Brand, CompassMark } from "~/ui/Compass";
import { button } from "~/ui/recipes";

export default function NotFound() {
  return (
    <>
      <Title>Not found · Tariff Compass</Title>
      <HttpStatusCode code={404} />
      <header class="px-8 pt-5 max-md:px-4">
        <A href="/" class="no-underline">
          <Brand />
        </A>
      </header>
      <main id="main" class="mx-auto max-w-[640px] px-4 py-24 text-center">
        <CompassMark size={64} class="mx-auto" state="waver" bearing={0} />
        <h1 class="mt-6 text-[32px] font-[800] tracking-[-0.02em]">We couldn't find that page.</h1>
        <p class="mt-2 text-[17px] text-ink-2">The needle has nothing to point at here. The link may be old, or the page may have moved.</p>
        <div class="mt-6 flex justify-center gap-2">
          <A href="/home" class={button()}>
            Go to your front page
          </A>
          <A href="/" class={button({ tone: "ghost" })}>
            Try a sample
          </A>
        </div>
      </main>
    </>
  );
}
