import { Title } from "@solidjs/meta";
import { A } from "@solidjs/router";
import { HttpStatusCode } from "@solidjs/start";
import { PublicBar } from "~/components/landing/Public";
import { CompassMark } from "~/ui/Compass";
import { button } from "~/ui/recipes";

export default function NotFound() {
  return (
    <>
      <Title>Not found · Tariff Compass</Title>
      <HttpStatusCode code={404} />
      <PublicBar />
      <main id="main" class="mx-auto max-w-[520px] px-4 py-24 text-center">
        <CompassMark size={48} class="mx-auto text-ink" state="waver" bearing={0} />
        <h1 class="page-title mt-5">Page not found</h1>
        <p class="mt-1.5 text-[14.5px] text-muted">The link may be old.</p>
        <div class="mt-6 flex justify-center gap-2">
          <A href="/home" class={button()}>
            Home
          </A>
          <A href="/" class={button({ tone: "outline" })}>
            Try a sample
          </A>
        </div>
      </main>
    </>
  );
}
