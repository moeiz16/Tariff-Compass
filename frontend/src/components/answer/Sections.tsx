/** The answer's layers: Why this code (the path), Rulings, Facts, Law text, and the question that decides it. */
import { Accordion } from "@ark-ui/solid/accordion";
import { For, Show, createSignal } from "solid-js";
import type { CitationState } from "~/lib/citations";
import { answers } from "~/lib/endpoints";
import { plainProblem } from "~/lib/problem";
import type { AnswerOut, CitedRulingOut, FactOut } from "~/lib/types";
import { AskIcon, ChevronIcon } from "~/ui/Icons";
import { button, tag } from "~/ui/recipes";
import { RulingStatus } from "~/ui/Status";
import { Tip } from "~/ui/Tip";
import { plain } from "~/lib/words";
import { CitationChip } from "./Citations";

export function Chips(props: { cites: number[]; rulings: CitedRulingOut[]; state: CitationState }) {
  return (
    <For each={props.cites}>
      {(n) => <CitationChip n={n} ruling={props.rulings.find((r) => r.n === n)} state={props.state} />}
    </For>
  );
}

/** A sentence with its citation numbers. */
export function Claim(props: { text: string; cites: number[]; answer: AnswerOut; state: CitationState }) {
  return (
    <>
      {plain(props.text)}
      <Chips cites={props.cites} rulings={props.answer.rulings} state={props.state} />
    </>
  );
}

/** Why this code: the rest of the reasoning, then the path from section to suffix; each step opens in place. */
export function WhyLayer(props: { answer: AnswerOut; state: CitationState; skipFirstReason: boolean }) {
  const more = () => (props.skipFirstReason ? props.answer.reason.slice(1) : props.answer.reason);
  return (
    <div class="space-y-5">
      <Show when={more().length}>
        <ul class="space-y-2 text-[15px] leading-[1.6] text-ink-2">
          <For each={more()}>
            {(c) => (
              <li class="flex gap-2.5">
                <span class="mt-[9px] h-1 w-1 shrink-0 rounded-full bg-muted" aria-hidden="true" />
                <span>
                  <Claim text={c.text} cites={c.cites} answer={props.answer} state={props.state} />
                </span>
              </li>
            )}
          </For>
        </ul>
      </Show>
      <Accordion.Root multiple collapsible class="relative" aria-label="Classification path">
        <For each={props.answer.path}>
          {(s, i) => {
            const last = () => i() === props.answer.path.length - 1;
            return (
              <Accordion.Item value={`s${i()}`} class="relative pl-7">
                <span
                  aria-hidden="true"
                  class="absolute left-[7px] w-px bg-rule-2"
                  style={{ top: i() === 0 ? "22px" : "0", bottom: last() ? "calc(100% - 22px)" : "0" }}
                />
                <span
                  aria-hidden="true"
                  class="absolute left-0 top-[15px] h-[15px] w-[15px] rounded-full border-2"
                  classList={{ "border-ink bg-hi": last(), "border-rule-2 bg-card": !last() }}
                />
                <Accordion.ItemTrigger class="group flex w-full items-start gap-3 rounded-[8px] px-2 py-2.5 text-left hover:bg-paper-2">
                  <span class="min-w-0 flex-1">
                    <span class="flex flex-wrap items-baseline gap-x-2.5">
                      <span class="text-[12.5px] font-[550] text-muted">{s.levelLabel}</span>
                      <span class="font-code text-[14.5px] font-[600] text-ink">{s.code}</span>
                    </span>
                    <span class="mt-0.5 block text-[14.5px] leading-[1.45] text-ink-2 group-data-[state=closed]:line-clamp-1">{s.text}</span>
                  </span>
                  <Tip label={s.griLabel}>
                    <span class="mt-0.5 rounded-full bg-paper-2 px-2 py-0.5 font-code text-[11.5px] font-[500] text-ink-2">{s.gri}</span>
                  </Tip>
                  <Accordion.ItemIndicator class="mt-1 text-muted transition-transform duration-200 data-[state=open]:rotate-180">
                    <ChevronIcon size={15} />
                  </Accordion.ItemIndicator>
                </Accordion.ItemTrigger>
                <Accordion.ItemContent class="fold">
                  <div class="space-y-3 px-2 pb-4 pt-1 text-[14.5px] leading-[1.6]">
                    <p>
                      <Claim text={s.why} cites={s.cites} answer={props.answer} state={props.state} />
                    </p>
                    <Show when={s.notNeighbours.length}>
                      <ul class="space-y-1.5">
                        <For each={s.notNeighbours}>
                          {(nn) => (
                            <li class="flex flex-wrap items-baseline gap-x-2.5 text-ink-2">
                              <s class="font-code text-[13.5px] text-muted">
                                <span class="sr-only">Not </span>
                                {nn.code}
                              </s>
                              <span>
                                {nn.reason.replace(/^Set aside:\s*/i, "")}
                                <Show when={nn.cite}>
                                  <Chips cites={[nn.cite!]} rulings={props.answer.rulings} state={props.state} />
                                </Show>
                              </span>
                            </li>
                          )}
                        </For>
                      </ul>
                    </Show>
                    <Show when={s.countryNote}>
                      <p class="flex items-baseline gap-2 text-ink-2">
                        <span class="rounded-[4px] bg-paper-2 px-1.5 font-code text-[11px] font-[600]">CA</span>
                        {s.countryNote!.replace(/^Canada:\s*/i, "")}
                      </p>
                    </Show>
                  </div>
                </Accordion.ItemContent>
              </Accordion.Item>
            );
          }}
        </For>
      </Accordion.Root>
    </div>
  );
}

/** Rulings: one row per cited ruling; a row opens the ruling drawer. */
export function RulingsLayer(props: { answer: AnswerOut; state: CitationState }) {
  return (
    <ul class="-mx-2">
      <For each={props.answer.rulings}>
        {(r) => (
          <li>
            <button
              type="button"
              onClick={() => props.state.show(r.n)}
              class="flex w-full items-start gap-3 rounded-[8px] px-2 py-2.5 text-left hover:bg-paper-2"
              aria-label={`Open ruling ${r.n}, ${r.id}`}
            >
              <span class="mt-0.5 grid h-5 min-w-5 place-items-center rounded-full bg-paper-2 px-1 font-code text-[11px] font-[600] text-ink-2">{r.n}</span>
              <span class="min-w-0 flex-1">
                <span class="flex flex-wrap items-center gap-x-3 gap-y-0.5">
                  <span class="font-code text-[14.5px] font-[600]">{r.id}</span>
                  <RulingStatus status={r.status} />
                </span>
                <span class="mt-0.5 block truncate text-[14px] text-muted">{r.subject}</span>
              </span>
              <ChevronIcon size={15} class="mt-1.5 -rotate-90 text-muted" />
            </button>
          </li>
        )}
      </For>
    </ul>
  );
}

const SOURCE_TONE: Record<FactOut["source"], "ink" | "warn" | "muted"> = { stated: "muted", read: "warn", assumed: "warn", unknown: "warn" };

/** Facts: what the answer rests on, each with where it came from. */
export function FactsLayer(props: { answer: AnswerOut }) {
  return (
    <dl class="divide-y divide-rule">
      <For each={props.answer.facts}>
        {(f) => (
          <div class="grid grid-cols-[180px_minmax(0,1fr)] items-baseline gap-x-5 py-2.5 max-sm:grid-cols-1">
            <dt class="text-[13.5px] text-muted">{f.label}</dt>
            <dd class="flex flex-wrap items-center gap-2 text-[14.5px]">
              <span classList={{ "font-[600]": f.decides, "text-muted": f.decides && f.source !== "stated" }}>{f.value}</span>
              <Show
                when={f.decides && f.source !== "stated"}
                fallback={
                  <Tip label={f.sourceNote || f.sourceLabel}>
                    <span class={tag({ tone: SOURCE_TONE[f.source] })}>{f.sourceLabel || "Stated"}</span>
                  </Tip>
                }
              >
                <Tip label={f.sourceNote || f.sourceLabel}>
                  <span class={tag({ tone: "warn" })}>To check · decides it</span>
                </Tip>
              </Show>
              <Show when={f.decides && f.source === "stated"}>
                <span class={tag({ tone: "hi", class: "font-sans" })}>Decides it</span>
              </Show>
            </dd>
          </div>
        )}
      </For>
    </dl>
  );
}

/** Law text: the tariff texts and rules relied on, quoted. */
export function LawLayer(props: { answer: AnswerOut }) {
  return (
    <ul class="space-y-4">
      <For each={props.answer.tariffAuthorities}>
        {(t) => (
          <li>
            <p class="text-[13px] font-[600] text-ink">{t.ref}</p>
            <p class="mt-1 border-l-2 border-rule-2 pl-3 text-[14.5px] leading-[1.6] text-ink-2">{t.quote}</p>
          </li>
        )}
      </For>
    </ul>
  );
}

/** The one question that decides a needs-a-broker answer, with its answers. Answering re-runs the answer. */
export function DecidingQuestion(props: {
  answer: AnswerOut;
  canConfirm: boolean;
  canSend: boolean;
  brokerName: string;
  onAnswer: (a: AnswerOut, said: string) => void;
  onSend: () => void;
}) {
  const [busy, setBusy] = createSignal<string | null>(null);
  const [error, setError] = createSignal("");
  const q = () => props.answer.decidingQuestion;
  const softFact = () => props.answer.facts.find((f) => f.decides && (f.source === "read" || f.source === "assumed"));
  const confirm = async (key: string, answer: string, said: string) => {
    setBusy(answer);
    setError("");
    try {
      props.onAnswer(await answers.confirmFact(props.answer.id, { key, answer }), said);
    } catch (e) {
      setError(plainProblem(e).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <Show when={q() || softFact()}>
      <div class="rounded-[var(--radius-box)] bg-warn-soft px-4 py-3.5">
        <p class="flex items-start gap-2 text-[15px] font-[600] text-ink">
          <AskIcon size={17} class="mt-0.5 shrink-0 text-warn" />
          <span>{(q()?.question ?? `Is it right that ${softFact()!.label.toLowerCase()}: ${softFact()!.value.toLowerCase()}?`).replace(/\s*The description says:[^.?]*[.?]?\s*$/i, "")}</span>
        </p>
        <Show
          when={props.canConfirm && !props.answer.sample}
          fallback={<p class="mt-1.5 pl-[25px] text-[13px] text-muted max-sm:pl-0">{props.answer.sample ? "Sign in to answer it." : "Only people who classify can answer it."}</p>}
        >
          <div class="mt-3 flex flex-wrap gap-2 pl-[25px] max-sm:pl-0">
            <Show
              when={q()}
              fallback={
                <>
                  <button type="button" class={button({ tone: "outline", size: "sm" })} disabled={!!busy()} onClick={() => void confirm(softFact()!.key, "confirmed", "Yes")}>
                    Yes
                  </button>
                  <button type="button" class={button({ tone: "outline", size: "sm" })} disabled={!!busy()} onClick={() => void confirm(softFact()!.key, "not_so", "No")}>
                    No
                  </button>
                </>
              }
            >
              <For each={q()!.options}>
                {(o) => (
                  <button
                    type="button"
                    title={o.label}
                    class={button({ tone: "outline", size: "sm", class: "h-auto min-h-9 max-w-full whitespace-normal py-1.5 text-left max-sm:w-full max-sm:justify-between" })}
                    disabled={!!busy()}
                    onClick={() => void confirm(q()!.factKey, o.key, o.label)}
                  >
                    <span class="min-w-0">{busy() === o.key ? "Re-running…" : o.label.length > 56 ? `${o.label.slice(0, 54)}…` : o.label}</span>
                  </button>
                )}
              </For>
            </Show>
            <Show when={props.canSend}>
              <button type="button" class={button({ tone: "ghost", size: "sm" })} onClick={() => props.onSend()}>
                Not sure: ask {props.brokerName}
              </button>
            </Show>
          </div>
        </Show>
        <Show when={error()}>
          <p role="alert" class="mt-2 pl-[25px] text-[13px] font-[600] text-bad">
            {error()}
          </p>
        </Show>
      </div>
    </Show>
  );
}
