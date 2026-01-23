import { Title } from "@solidjs/meta";
import { A, Navigate, useSearchParams } from "@solidjs/router";
import { For, Match, Show, Switch, createResource, createSignal, onMount } from "solid-js";
import { AnswerMemo } from "~/components/answer/AnswerMemo";
import { The97, narrowFrom, type NarrowState } from "~/components/landing/The97";
import { PublicFooter, Story } from "~/components/landing/Story";
import { ThemeButton } from "~/components/shell/QueryStrip";
import { SearchBox } from "~/components/shell/SearchBox";
import { ApiProblem } from "~/lib/api";
import { meta, publicApi } from "~/lib/endpoints";
import { reducedMotion } from "~/lib/motion";
import { useSession } from "~/lib/session";
import type { AnswerOut } from "~/lib/types";
import { Brand, Wordmark, type NeedleState } from "~/ui/Compass";
import { button } from "~/ui/recipes";
import { EmptyState, ErrorSlip } from "~/ui/States";

const wait = (ms: number) => new Promise((r) => setTimeout(r, reducedMotion() ? 0 : ms));

function TopLinks() {
  return (
    <nav aria-label="About Tariff Compass" class="flex items-center justify-end gap-7 px-8 pt-5 text-[16px] max-md:gap-4 max-md:px-4 max-md:text-[15px]">
      <a href="#why" class="text-ink-2 no-underline hover:text-ink max-md:hidden">
        Why now
      </a>
      <a href="#brokers" class="text-ink-2 no-underline hover:text-ink max-md:hidden">
        For brokers
      </a>
      <a href="#measure" class="text-ink-2 no-underline hover:text-ink max-md:hidden">
        How we measure
      </a>
      <ThemeButton />
      <A href="/signin" class="font-[700] text-ink underline underline-offset-[6px]">
        Broker sign-in
      </A>
    </nav>
  );
}

export default function Landing() {
  const { me, session } = useSession();
  const [params, setParams] = useSearchParams<{ q?: string }>();
  const [sections] = createResource(() => meta.sections().catch(() => []));
  const [samples] = createResource(() => publicApi.samples().catch(() => []));
  const [narrow, setNarrow] = createSignal<NarrowState>({ phase: "idle", losers: [] });
  const [needle, setNeedle] = createSignal<NeedleState>("still");
  const [answer, setAnswer] = createSignal<AnswerOut | null>(null);
  const [problem, setProblem] = createSignal<unknown>(null);
  const [notInDemo, setNotInDemo] = createSignal(false);
  const [busy, setBusy] = createSignal(false);
  const [docked, setDocked] = createSignal(false);
  const [caption, setCaption] = createSignal("");

  const dock = async () => {
    const el = document.querySelector("[data-flip-id=box]");
    if (!el || reducedMotion()) {
      setDocked(true);
      window.scrollTo({ top: 0 });
      return;
    }
    const [{ gsap }, { Flip }] = await Promise.all([import("gsap"), import("gsap/Flip")]);
    gsap.registerPlugin(Flip);
    const state = Flip.getState(el);
    setDocked(true);
    window.scrollTo({ top: 0 });
    requestAnimationFrame(() => Flip.from(state, { targets: "[data-flip-id=box]", duration: 0.46, ease: "power3.out" }));
  };

  const run = async (kind: "sample" | "text", value: string) => {
    if (busy()) return;
    setBusy(true);
    setProblem(null);
    setNotInDemo(false);
    setDocked(false);
    setAnswer(null);
    setNeedle("seek");
    setNarrow({ phase: "dim", losers: [] });
    setCaption("Reading the tariff…");
    try {
      const a =
        kind === "sample"
          ? await publicApi.sample(value).catch((e) => {
              if (e instanceof ApiProblem && e.status === 404) return publicApi.classify(value);
              throw e;
            })
          : await publicApi.classify(value);
      const { winner, losers } = narrowFrom(a);
      setNarrow({ phase: "candidates", winner, losers });
      setCaption(`${losers.length + 1} chapters could hold it…`);
      await wait(700);
      setNarrow({ phase: "struck", winner, losers });
      await wait(650);
      setNarrow({ phase: "chosen", winner, losers });
      setCaption(`…one does: Chapter ${winner}.`);
      setNeedle(a.verdict.word === "strong" ? "settle" : "waver");
      await wait(900);
      setAnswer(a);
      await dock();
    } catch (e) {
      setNeedle("still");
      setNarrow({ phase: "idle", losers: [] });
      if (e instanceof ApiProblem && e.code === "not_in_demo") setNotInDemo(true);
      else setProblem(e);
    } finally {
      setBusy(false);
    }
  };

  onMount(() => {
    const key = params.q;
    // A sample key ("tumbler", "bike-light") opens that sample; anything else is classified as text.
    if (key) void run(/^[a-z][a-z-]*$/.test(key) ? "sample" : "text", key);
  });

  const reset = () => {
    setDocked(false);
    setAnswer(null);
    setNarrow({ phase: "idle", losers: [] });
    setNeedle("still");
    setParams({ q: undefined });
  };

  const box = (hero: boolean) => (
    <div data-flip-id="box">
      <SearchBox
        id={hero ? "q-hero" : "q-strip"}
        mode="classify"
        size={hero ? "hero" : "strip"}
        label="Describe what you're importing"
        placeholder="Describe what you're importing…"
        value={answer()?.query.text}
        busy={busy()}
        suggestions={samples()?.map((s) => s.query)}
        onSubmit={(text) => {
          const s = samples()?.find((x) => x.query === text || x.title === text);
          setParams({ q: s ? s.key : text });
          void run(s ? "sample" : "text", s ? s.key : text);
        }}
      />
    </div>
  );

  return (
    <Show when={!session.loading || session.latest} fallback={<div class="min-h-dvh" />}>
    <Show when={!me()} fallback={<Navigate href="/home" />}>
      <Title>Tariff Compass · US and Canadian tariff codes with the rulings behind them</Title>
      <div id="top" />
      <Show
        when={docked() && answer()}
        fallback={
          <>
            <TopLinks />
            <main id="main" class="px-8 pb-16 pt-[clamp(32px,9vh,110px)] max-md:px-4">
              <div class="mx-auto max-w-[1060px] text-center">
                <Wordmark state={needle()} bearing={32} />
                <p class="mx-auto mt-8 max-w-[760px] text-[clamp(17px,1.6vw,21px)] font-[300] leading-[1.55] text-ink-2">
                  Describe a product. Get its <b class="font-[700] text-ink">US and Canadian tariff codes</b>, the <b class="font-[700] text-ink">customs rulings</b>{" "}
                  that back them, and <b class="font-[700] text-ink">every duty</b> it will carry.
                </p>
                <div class="mx-auto mt-8 max-w-[1060px] text-left">{box(true)}</div>
                <div class="mt-4 flex flex-wrap items-baseline justify-center gap-x-6 gap-y-2 text-[17px]">
                  <span class="text-muted">Try a sample:</span>
                  <For each={samples() ?? []}>
                    {(s) => (
                      <button
                        type="button"
                        class="underline decoration-rule decoration-[3px] underline-offset-[7px] hover:decoration-ink disabled:opacity-60"
                        disabled={busy()}
                        onClick={() => {
                          setParams({ q: s.key });
                          void run("sample", s.key);
                        }}
                      >
                        {s.title}
                      </button>
                    )}
                  </For>
                </div>
              </div>
              <div class="mx-auto mt-12 max-w-[1000px]">
                <Switch>
                  <Match when={notInDemo()}>
                    <EmptyState
                      title="The public demo only knows Northbound's sample products."
                      action={
                        <>
                          <button type="button" class={button({ size: "md" })} onClick={() => void run("sample", "tumbler")}>
                            Try the tumbler
                          </button>
                          <A href="/signin" class={button({ tone: "ghost", size: "md" })}>
                            Sign in
                          </A>
                        </>
                      }
                    >
                      Sign in to classify your own products and keep each answer in an audit binder.
                    </EmptyState>
                  </Match>
                  <Match when={problem()}>
                    <ErrorSlip error={problem()} retry={() => (params.q ? void run("sample", params.q) : undefined)} />
                  </Match>
                  <Match when={sections()?.length}>
                    <The97 sections={sections()!} narrow={narrow()} caption={caption()} />
                  </Match>
                </Switch>
              </div>
            </main>
            <Story />
            <PublicFooter />
          </>
        }
      >
        <header class="border-b-[1.5px] border-ink">
          <div class="grid grid-cols-[var(--spacing-gutter)_minmax(0,880px)_1fr] items-center gap-y-2 px-8 py-3.5 max-[960px]:grid-cols-[1fr_auto] max-[960px]:px-4">
            <button type="button" onClick={reset} class="w-fit text-left" aria-label="Back to the front page">
              <Brand />
            </button>
            <div class="min-w-0 max-[960px]:col-span-2 max-[960px]:row-start-2">{box(false)}</div>
            <div class="flex items-center justify-end gap-4 pl-6 max-[960px]:col-start-2 max-[960px]:row-start-1">
              <ThemeButton />
              <A href="/signin" class="font-[700] underline underline-offset-[6px]">
                Broker sign-in
              </A>
            </div>
          </div>
        </header>
        <main id="main">
          <AnswerMemo
            answer={answer()!}
            openCites={[1]}
            caps={{ live: false, canConfirm: false, canSend: false, canFlag: false, brokerName: "Driftwood" }}
            banner={
              <div class="gm border-b border-rule bg-paper py-4">
                <span class="gl">Sample</span>
                <p class="gm-wide text-[16px]">
                  This is a sample answer for a product from Northbound Goods Co.{" "}
                  <A href="/signin" class="font-[700] underline underline-offset-4">
                    Sign in
                  </A>{" "}
                  to classify your own and keep each answer in an audit binder.
                </p>
              </div>
            }
          />
        </main>
        <PublicFooter />
      </Show>
    </Show>
    </Show>
  );
}
