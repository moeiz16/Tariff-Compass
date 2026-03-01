import { Title } from "@solidjs/meta";
import { A, Navigate, useSearchParams } from "@solidjs/router";
import { For, Match, Show, Switch, createResource, createSignal, onMount } from "solid-js";
import { AnswerLoading, AnswerView } from "~/components/answer/AnswerView";
import { PublicBar, PublicFooter } from "~/components/landing/Public";
import { SearchBox } from "~/components/shell/SearchBox";
import { ApiProblem } from "~/lib/api";
import { publicApi } from "~/lib/endpoints";
import { useSession } from "~/lib/session";
import type { AnswerOut } from "~/lib/types";
import { ScaleIcon, StackIcon, UserCheckIcon } from "~/ui/Icons";
import { button } from "~/ui/recipes";
import { EmptyState, ErrorSlip } from "~/ui/States";

/** The public demo knows only the sample products; don't send text that shares no word with any of them. */
function knownToDemo(text: string, samples: { title: string; query: string }[]): boolean {
  const words = (s: string) => new Set(s.toLowerCase().match(/[a-z]{4,}/g) ?? []);
  const asked = words(text);
  return samples.some((s) => [...words(`${s.title} ${s.query}`)].some((w) => asked.has(w)));
}

const FEATURES = [
  { icon: ScaleIcon, title: "Cited rulings", text: "Every answer names the customs rulings behind it." },
  { icon: StackIcon, title: "Every duty", text: "Each charge with its source and the date it took effect." },
  { icon: UserCheckIcon, title: "Broker sign-off", text: "A licensed broker approves each code before it is used." },
];

export default function Landing() {
  const { me, session } = useSession();
  const [params, setParams] = useSearchParams<{ q?: string }>();
  const [samples] = createResource(() => publicApi.samples().catch(() => []));
  const [answer, setAnswer] = createSignal<AnswerOut | null>(null);
  const [active, setActive] = createSignal<string | null>(null);
  const [problem, setProblem] = createSignal<unknown>(null);
  const [notInDemo, setNotInDemo] = createSignal(false);
  const [busy, setBusy] = createSignal(false);

  const classifyPublic = async (text: string) => {
    const known = samples() ?? (await publicApi.samples().catch(() => []));
    if (known.length && !knownToDemo(text, known)) throw new ApiProblem({ type: "about:blank", title: "Not in the demo", status: 404, code: "not_in_demo", detail: "" });
    return publicApi.classify(text);
  };

  const run = async (kind: "sample" | "text", value: string) => {
    if (busy()) return;
    setBusy(true);
    setProblem(null);
    setNotInDemo(false);
    setActive(kind === "sample" ? value : null);
    try {
      const a =
        kind === "sample"
          ? await publicApi.sample(value).catch((e) => {
              if (e instanceof ApiProblem && e.status === 404) return classifyPublic(value);
              throw e;
            })
          : await classifyPublic(value);
      setAnswer(null);
      setAnswer(a);
    } catch (e) {
      if (e instanceof ApiProblem && e.code === "not_in_demo") setNotInDemo(true);
      else setProblem(e);
    } finally {
      setBusy(false);
    }
  };

  onMount(() => {
    // A sample key ("tumbler", "sleeping-bag") opens that sample; anything else is classified as text.
    // With no question, the tumbler's answer is shown as the preview.
    void (async () => {
      const list = await publicApi.samples().catch(() => []);
      const key = params.q ?? list[0]?.key;
      if (key) void run(list.some((s) => s.key === key) ? "sample" : "text", key);
    })();
  });

  return (
    <Show when={!session.loading || session.latest} fallback={<div class="min-h-dvh" />}>
      <Show when={!me()} fallback={<Navigate href="/home" />}>
        <Title>Tariff Compass · US and Canadian tariff codes with the rulings behind them</Title>
        <PublicBar
          onBrand={() => {
            setParams({ q: undefined });
            window.scrollTo({ top: 0 });
          }}
        />
        <main id="main">
          <section class="mx-auto max-w-[820px] px-6 pb-10 pt-[clamp(40px,9vh,104px)] text-center max-sm:px-4">
            <h1 class="text-balance text-display font-[600] tracking-[-0.035em]">The right tariff code, with the rulings behind it.</h1>
            <p class="mx-auto mt-4 max-w-[560px] text-[17px] leading-[1.55] text-muted">US and Canadian codes, every duty it will carry, and a broker's sign-off.</p>
            <div class="mx-auto mt-8 text-left">
              <SearchBox
                id="q-hero"
                mode="classify"
                size="hero"
                label="Describe what you're importing"
                placeholder="Describe what you're importing…"
                busy={busy()}
                suggestions={samples()?.map((s) => s.query)}
                onSubmit={(text) => {
                  const s = samples()?.find((x) => x.query === text || x.title === text);
                  setParams({ q: s ? s.key : text });
                  void run(s ? "sample" : "text", s ? s.key : text);
                }}
              />
            </div>
            <div class="mt-4 flex flex-wrap items-center justify-center gap-2">
              <span class="text-[13px] text-muted">Try</span>
              <For each={samples() ?? []}>
                {(s) => (
                  <button
                    type="button"
                    aria-pressed={active() === s.key}
                    class="h-8 rounded-full border border-rule bg-card px-3.5 text-[13.5px] font-[550] text-ink-2 hover:border-rule-2 hover:text-ink disabled:opacity-60 aria-pressed:border-ink aria-pressed:text-ink"
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
          </section>

          <section aria-label="Sample answer" class="mx-auto max-w-[820px] px-6 pb-20 max-sm:px-4">
            <Switch>
              <Match when={notInDemo()}>
                <div class="rounded-[var(--radius-card)] border border-rule bg-card">
                  <EmptyState
                    title="The demo knows three sample products"
                    action={
                      <>
                        <button type="button" class={button({ size: "sm" })} onClick={() => void run("sample", "tumbler")}>
                          Try the tumbler
                        </button>
                        <A href="/signin" class={button({ tone: "outline", size: "sm" })}>
                          Sign in
                        </A>
                      </>
                    }
                  />
                </div>
              </Match>
              <Match when={problem()}>
                <ErrorSlip error={problem()} retry={() => void run("sample", params.q ?? "tumbler")} />
              </Match>
              <Match when={answer() && !busy()}>
                <Show when={answer()} keyed>
                  {(a) => (
                    <AnswerView
                      answer={a}
                      label="Sample answer"
                      caps={{ live: false, canConfirm: false, canSend: false, canFlag: false, brokerName: "Driftwood" }}
                      actions={
                        <A href="/signin" class={button({ size: "md" })}>
                          Classify your own
                        </A>
                      }
                    />
                  )}
                </Show>
              </Match>
              <Match when={busy() || !answer()}>
                <AnswerLoading />
              </Match>
            </Switch>
          </section>

          <section aria-label="What you get" class="border-t border-rule bg-card">
            <ul class="mx-auto grid max-w-[1120px] grid-cols-3 gap-10 px-6 py-16 max-md:grid-cols-1 max-md:gap-8 max-sm:px-4">
              <For each={FEATURES}>
                {(f) => (
                  <li>
                    <span class="grid h-10 w-10 place-items-center rounded-[10px] bg-paper-2 text-ink">
                      <f.icon size={19} />
                    </span>
                    <p class="mt-4 text-[16px] font-[600]">{f.title}</p>
                    <p class="mt-1 text-[14.5px] leading-[1.55] text-muted">{f.text}</p>
                  </li>
                )}
              </For>
            </ul>
          </section>
        </main>
        <PublicFooter />
      </Show>
    </Show>
  );
}
