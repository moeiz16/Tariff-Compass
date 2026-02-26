/** ¶0 In short, ¶1 Facts, ¶2 Issue, ¶3 Law and analysis, ¶5 Authorities cited. */
import { Accordion } from "@ark-ui/solid/accordion";
import { A } from "@solidjs/router";
import { For, Show, createMemo, createSignal } from "solid-js";
import type { CitationState } from "~/lib/citations";
import { answers } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import type { AnswerOut, CitedRulingOut, FactOut } from "~/lib/types";
import { AskIcon, ChevronIcon } from "~/ui/Icons";
import { button } from "~/ui/recipes";
import { RulingStatus } from "~/ui/Status";
import { Tip } from "~/ui/Tip";
import { CitationChip, CitationDrawer } from "./Citations";
import { MemoRow } from "./Memo";

function Chips(props: { cites: number[]; rulings: CitedRulingOut[]; state: CitationState; anchor: string }) {
  return (
    <For each={props.cites}>
      {(n) => <CitationChip n={n} ruling={props.rulings.find((r) => r.n === n)} state={props.state} anchor={props.anchor} />}
    </For>
  );
}

function Drawers(props: { cites: number[]; answer: AnswerOut; state: CitationState; anchor: string; canFlag: boolean }) {
  return (
    <For each={props.cites}>
      {(n) => (
        <Show when={props.answer.rulings.find((r) => r.n === n)}>
          {(r) => <CitationDrawer ruling={r()} state={props.state} anchor={props.anchor} answerId={props.answer.id} canFlag={props.canFlag} sample={props.answer.sample} />}
        </Show>
      )}
    </For>
  );
}

export function InShort(props: { answer: AnswerOut; state: CitationState; canFlag: boolean }) {
  const all = createMemo(() => [...new Set(props.answer.reason.flatMap((c) => c.cites))].sort((a, b) => a - b));
  const [lit, setLit] = createSignal<number | null>(null);
  return (
    <MemoRow n="¶ 0" label="In short" id="p0">
      <p class="text-[19px] leading-[1.62] max-md:text-[17px]">
        <For each={props.answer.reason}>
          {(c, i) => (
            <>
              <span
                class="claim"
                data-lit={lit() === i() || c.cites.some((n) => props.state.isOpen(n))}
                onFocusIn={() => setLit(i())}
                onFocusOut={() => setLit(null)}
                onMouseEnter={() => setLit(i())}
                onMouseLeave={() => setLit(null)}
              >
                {c.text}
                <Chips cites={c.cites} rulings={props.answer.rulings} state={props.state} anchor="p0" />
              </span>{" "}
            </>
          )}
        </For>
      </p>
      <Drawers cites={all()} answer={props.answer} state={props.state} anchor="p0" canFlag={props.canFlag} />
    </MemoRow>
  );
}

/** "your description", "read from 'insulated'", "assumed: nothing mentions one", "not stated: …" */
export function factNote(f: Pick<FactOut, "source" | "sourceLabel" | "sourceNote">): string {
  const note = f.sourceNote.trim();
  const label = f.sourceLabel.toLowerCase();
  if (f.source === "stated" || !label) return note;
  if (!note) return label;
  return note.toLowerCase().startsWith(label.split(" ")[0]!) ? note : `${label}: ${note}`;
}

function FactRow(props: { fact: FactOut }) {
  const f = () => props.fact;
  const soft = () => f().source === "read" || f().source === "assumed" || f().source === "unknown";
  return (
    <div class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-b border-rule py-2.5 max-sm:grid-cols-1">
      <dt class="text-[15px] text-muted">{f().label}</dt>
      <dd class="text-[16px]">
        <span classList={{ "font-[650]": f().decides }}>{f().value}</span>
        <span class="ml-2 text-[14px]" classList={{ "text-warn": soft(), "text-muted": !soft() }}>
          <Show when={soft()}>
            <span aria-hidden="true">◇ </span>
          </Show>
          {factNote(f())}
        </span>
        <Show when={f().decides}>
          <span class="ml-2 rounded-[3px] bg-hi px-1.5 py-0.5 text-[12px] font-[700] text-hi-ink">decides it</span>
        </Show>
      </dd>
    </div>
  );
}

export function Facts(props: { answer: AnswerOut; canConfirm: boolean; canSend: boolean; brokerName: string; onAnswer: (a: AnswerOut) => void; onSend: () => void }) {
  const [busy, setBusy] = createSignal<string | null>(null);
  const [error, setError] = createSignal("");
  const q = () => props.answer.decidingQuestion;
  const softFact = () => props.answer.facts.find((f) => f.decides && (f.source === "read" || f.source === "assumed"));
  const confirm = async (key: string, answer: string) => {
    setBusy(answer);
    setError("");
    try {
      props.onAnswer(await answers.confirmFact(props.answer.id, { key, answer }));
    } catch (e) {
      setError(plainProblem(e).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <MemoRow n="¶ 1" label="Facts" id="p1" note="what the answer rests on, and where each fact came from">
      <dl class="border-t border-rule">
        <For each={props.answer.facts}>{(f) => <FactRow fact={f} />}</For>
      </dl>
      <Show when={q() || softFact()}>
        <div class="mt-5 rounded-[var(--radius-box)] border-[1.5px] border-warn bg-paper px-4 py-3.5">
          <h3 class="ty-sub flex items-center gap-2 text-[13.5px] text-warn">
            <AskIcon size={16} /> The fact that decides it
          </h3>
          <p class="mt-1 text-[16px]">{q()?.question ?? `Is it right that ${softFact()!.label.toLowerCase()}: ${softFact()!.value.toLowerCase()}?`}</p>
          <Show when={props.canConfirm && !props.answer.sample} fallback={<p class="mt-2 text-[14px] text-muted">{props.answer.sample ? "Sign in to answer it; the answer is re-run and recorded in the binder." : "Only people who classify can answer it."}</p>}>
            <div class="mt-3 flex flex-wrap gap-2">
              <Show
                when={q()}
                fallback={
                  <>
                    <button type="button" class={button({ tone: "ghost", size: "sm" })} disabled={!!busy()} onClick={() => void confirm(softFact()!.key, "confirmed")}>
                      Yes, that's right
                    </button>
                    <button type="button" class={button({ tone: "ghost", size: "sm" })} disabled={!!busy()} onClick={() => void confirm(softFact()!.key, "not_so")}>
                      No, it isn't
                    </button>
                  </>
                }
              >
                <For each={q()!.options}>
                  {(o) => (
                    <button type="button" class={button({ tone: "ghost", size: "sm" })} disabled={!!busy()} onClick={() => void confirm(q()!.factKey, o.key)}>
                      {busy() === o.key ? "Re-running…" : o.label}
                      <Show when={o.leadsTo}>
                        <span class="font-code text-[12px] text-muted">→ {o.leadsTo}</span>
                      </Show>
                    </button>
                  )}
                </For>
              </Show>
              <Show when={props.canSend}>
                <button type="button" class={button({ size: "sm" })} onClick={() => props.onSend()}>
                  {q()?.notSureLabel ?? `Not sure: send to ${props.brokerName}`}
                </button>
              </Show>
            </div>
          </Show>
          <Show when={error()}>
            <p role="alert" class="mt-2 text-[14px] font-[600] text-bad">
              {error()}
            </p>
          </Show>
        </div>
      </Show>
    </MemoRow>
  );
}

export function Issue(props: { answer: AnswerOut }) {
  return (
    <MemoRow n="¶ 2" label="Issue" id="p2">
      <p class="font-type text-[19px] leading-[1.55] max-md:text-[16.5px]">{props.answer.issue}</p>
    </MemoRow>
  );
}

const LEVEL_INDENT = 30;

export function Analysis(props: { answer: AnswerOut; state: CitationState; canFlag: boolean }) {
  const steps = () => props.answer.path;
  const headingStep = () => steps().findIndex((s) => s.level === "heading");
  const [open, setOpen] = createSignal<string[]>([`s${Math.max(0, headingStep())}`]);
  return (
    <section id="p3" aria-labelledby="p3-h" class="ty-ruled py-9 max-md:py-7" data-rise>
      <div class="gm">
        <div class="gl">
          <span>¶ 3</span>
          <h2 id="p3-h" class="not-italic">
            <b>Law and analysis</b>
          </h2>
        </div>
        <p class="gm-body text-[16px] text-ink-2">
          Each step names the rule it applied. Open a step to see the reasoning and the neighbour it set aside.
        </p>
      </div>
      <Accordion.Root multiple collapsible value={open()} onValueChange={(d) => setOpen(d.value)} class="mt-4">
        <For each={steps()}>
          {(s, i) => {
            const last = () => i() === steps().length - 1;
            return (
              <Accordion.Item value={`s${i()}`} class="gm">
                <div class="relative min-h-[64px] max-[960px]:hidden" aria-hidden="true" style={{ "padding-left": `${i() * LEVEL_INDENT}px` }}>
                  <span class="absolute top-0 h-full w-[2px] bg-ink" style={{ left: `${i() * LEVEL_INDENT + 6}px`, top: i() === 0 ? "22px" : "0", height: last() ? "22px" : "100%" }} />
                  <span
                    class="absolute top-[15px] h-[14px] w-[14px] rounded-full border-[2px] border-ink"
                    classList={{ "bg-hi": last(), "bg-paper": !last() }}
                    style={{ left: `${i() * LEVEL_INDENT}px` }}
                  />
                  <span class="block pl-6 pt-2.5">
                    <span class="block font-type text-[13px] text-muted">
                      3.{i() + 1} {s.levelLabel}
                    </span>
                    <span class="inline-block font-code text-[19px] font-[700]" classList={{ hl: last() }}>
                      {s.code.length > 6 && !last() ? s.code : last() && s.level === "suffix" ? `.${s.code.split(".").pop()}` : s.code}
                    </span>
                  </span>
                </div>
                <div class="gm-body border-b border-rule">
                  <Accordion.ItemTrigger class="flex w-full items-start gap-3 py-4 text-left">
                    <span class="min-w-0 flex-1">
                      <span class="hidden font-type text-[13px] text-muted max-[960px]:block">
                        3.{i() + 1} {s.levelLabel} · <span class="font-[700]">{s.code}</span>
                      </span>
                      <span class="block font-law text-[16.5px] leading-[1.45]">{s.text}</span>
                    </span>
                    <Tip label={s.griLabel}>
                      <span class="rounded-[var(--radius-btn)] border-[1.5px] border-ink px-2 py-0.5 font-code text-[12.5px] font-[650]">{s.gri}</span>
                    </Tip>
                    <Accordion.ItemIndicator class="mt-1 transition-transform data-[state=open]:rotate-180">
                      <ChevronIcon size={16} />
                    </Accordion.ItemIndicator>
                  </Accordion.ItemTrigger>
                  <Accordion.ItemContent class="pb-5">
                    <p class="text-[17px] leading-[1.6]">
                      {s.why}
                      <Show when={s.cites.length}>
                        <span class="ml-1 whitespace-nowrap text-[15px] text-muted">
                          Supported by <Chips cites={s.cites} rulings={props.answer.rulings} state={props.state} anchor={`p3-${i()}`} />
                        </span>
                      </Show>
                    </p>
                    <Show when={s.notNeighbours.length}>
                      <ul class="mt-3 space-y-2">
                        <For each={s.notNeighbours}>
                          {(nn) => (
                            <li class="grid grid-cols-[110px_minmax(0,1fr)] gap-x-4 text-[15.5px] max-sm:grid-cols-1">
                              <span class="font-code text-muted">
                                <span class="sr-only">Not </span>
                                <s>not {nn.code}</s>
                              </span>
                              <span>
                                <span class="font-law text-ink-2">{nn.text}.</span> <b class="font-[650]">{nn.reason}</b>
                                <Show when={nn.cite}>
                                  <Chips cites={[nn.cite!]} rulings={props.answer.rulings} state={props.state} anchor={`p3-${i()}`} />
                                </Show>
                              </span>
                            </li>
                          )}
                        </For>
                      </ul>
                    </Show>
                    <Show when={s.countryNote}>
                      <p class="mt-3 text-[15px] text-ink-2">
                        <span class="mr-1 rounded-[3px] border-[1.5px] border-ink px-1 font-code text-[11px] font-[650]">CA</span>
                        {s.countryNote}
                      </p>
                    </Show>
                    <Drawers
                      cites={[...new Set([...s.cites, ...s.notNeighbours.flatMap((n) => (n.cite ? [n.cite] : []))])]}
                      answer={props.answer}
                      state={props.state}
                      anchor={`p3-${i()}`}
                      canFlag={props.canFlag}
                    />
                  </Accordion.ItemContent>
                </div>
              </Accordion.Item>
            );
          }}
        </For>
      </Accordion.Root>
    </section>
  );
}

export function Authorities(props: { answer: AnswerOut }) {
  return (
    <MemoRow n="¶ 5" label="Authorities cited" id="p5" wide>
      <div class="grid max-w-[1100px] grid-cols-2 gap-x-10 gap-y-6 max-lg:grid-cols-1">
        <div>
          <h3 class="ty-head block border-b-[1.5px] border-ink pb-2 no-underline">Customs rulings</h3>
          <ol>
            <For each={props.answer.rulings}>
              {(r) => (
                <li class="grid grid-cols-[28px_minmax(0,1fr)] gap-x-2 border-b border-rule py-2.5">
                  <span class="font-code text-[13px] text-muted">[{r.n}]</span>
                  <span>
                    <Show when={!props.answer.sample} fallback={<a href={r.url} target="_blank" rel="noreferrer" class="font-code font-[650] underline decoration-rule underline-offset-4">{r.id}</a>}>
                      <A href={`/rulings/${r.key}`} class="font-code font-[650] underline decoration-rule underline-offset-4 hover:decoration-ink">
                        {r.id}
                      </A>
                    </Show>
                    <span class="ml-2 text-[14px] text-muted">{dateShort(r.date)}</span>
                    <span class="ml-2">
                      <RulingStatus status={r.status} />
                    </span>
                    <span class="block text-[14.5px] text-ink-2">{r.subject}</span>
                  </span>
                </li>
              )}
            </For>
          </ol>
        </div>
        <div>
          <h3 class="ty-head block border-b-[1.5px] border-ink pb-2 no-underline">Tariff texts and rules relied on</h3>
          <ul>
            <For each={props.answer.tariffAuthorities}>
              {(t) => (
                <li class="border-b border-rule py-2.5">
                  <span class="text-[15px] font-[650]">{t.ref}</span>
                  <span class="ty-law block text-ink-2">“{t.quote}”</span>
                </li>
              )}
            </For>
          </ul>
        </div>
      </div>
    </MemoRow>
  );
}
