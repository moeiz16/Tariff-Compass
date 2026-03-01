/**
 * The answer, first: one card with how sure it is, the two codes and one line of why. Everything else is a layer
 * you open: Why this code · Rulings · Landed cost · Facts · Law text. A ruling opens in the ruling drawer.
 */
import { Accordion } from "@ark-ui/solid/accordion";
import { Clipboard } from "@ark-ui/solid/clipboard";
import { For, Show, onCleanup, onMount, untrack, type JSX } from "solid-js";
import { createCitationState, moveBetweenChips } from "~/lib/citations";
import { dateWithDay, money } from "~/lib/format";
import { rise } from "~/lib/motion";
import type { AnswerOut, CodeOut } from "~/lib/types";
import { depthWords, digitTreatment } from "~/lib/verdict";
import { CodeDigits } from "~/ui/Code";
import { CompassMark } from "~/ui/Compass";
import { AskIcon, ChevronIcon, CopyIcon, DocIcon, ListIcon, OkIcon, PathIcon, ScaleIcon, StackIcon } from "~/ui/Icons";
import { card, tag } from "~/ui/recipes";
import { ErrorSlip, SkeletonLines } from "~/ui/States";
import { Tip } from "~/ui/Tip";
import { RulingDrawer } from "./Citations";
import { CostLayer, useLandedCost } from "./Landed";
import { Claim, DecidingQuestion, FactsLayer, LawLayer, RulingsLayer, WhyLayer } from "./Sections";

export interface AnswerCapabilities {
  live: boolean; // signed in: landed cost restacks through the API
  canConfirm: boolean;
  canSend: boolean;
  canFlag: boolean;
  brokerName: string;
}

function CodeBlock(props: { code: CodeOut; words: ReturnType<typeof depthWords>; lock: boolean }) {
  return (
    <div class="min-w-0">
      <p class="flex items-center gap-2 text-[13px] font-[550] text-muted">
        {props.code.countryLabel}
        <Show when={props.code.leaning}>
          <span class="text-warn">· leaning</span>
        </Show>
      </p>
      <div class="mt-2 flex items-center gap-2">
        <CodeDigits code={props.code.code} treatment={digitTreatment(props.code, props.words)} lock={props.lock} size="xl" />
        <Clipboard.Root value={props.code.code}>
          <Clipboard.Trigger class="grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-paper-2 hover:text-ink" aria-label={`Copy ${props.code.code}`}>
            <Clipboard.Indicator copied={<OkIcon size={14} class="text-ok" />}>
              <CopyIcon size={15} />
            </Clipboard.Indicator>
          </Clipboard.Trigger>
        </Clipboard.Root>
      </div>
    </div>
  );
}

/** The verdict word with its icon; the sentence behind it on hover, and the word at each depth when they differ. */
export function VerdictLine(props: { answer: AnswerOut }) {
  const v = () => props.answer.verdict;
  const strong = () => v().word === "strong";
  return (
    <div class="flex flex-wrap items-center gap-2.5">
      <Tip label={v().sentence}>
        <span class={tag({ tone: strong() ? "ok" : "warn", class: "px-3 py-1 text-[13px]" })}>
          {strong() ? <OkIcon size={14} /> : <AskIcon size={14} />}
          {v().wordLabel}
        </span>
      </Tip>
      <Show when={v().byDepth?.length}>
        <dl class="flex flex-wrap items-center gap-x-3 text-[12.5px] text-muted" aria-label="The confidence word at each depth">
          <For each={v().byDepth}>
            {(d) => (
              <div class="flex items-center gap-1">
                <dt>{d.levelLabel}</dt>
                <dd class="flex items-center" classList={{ "text-ok": d.word === "strong", "text-warn": d.word !== "strong" }}>
                  {d.word === "strong" ? <OkIcon size={12} title={d.wordLabel} /> : <AskIcon size={12} title={d.wordLabel} />}
                </dd>
              </div>
            )}
          </For>
        </dl>
      </Show>
    </div>
  );
}

/** Layer 1: the answer card. */
export function AnswerCard(props: {
  answer: AnswerOut;
  state: ReturnType<typeof createCitationState>;
  caps?: AnswerCapabilities;
  actions?: JSX.Element;
  label?: JSX.Element;
  lock?: boolean;
  onAnswer?: (a: AnswerOut) => void;
  onSend?: () => void;
}) {
  const a = () => props.answer;
  const strong = () => a().verdict.word === "strong";
  const words = () => depthWords(a().verdict);
  const first = () => a().reason[0];
  return (
    <section aria-label="Answer" class={card({ class: "p-7 max-sm:p-5" })} data-rise>
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-2.5">
          <CompassMark size={24} bearing={strong() ? 32 : 18} state={strong() ? "settle" : "waver"} class="shrink-0 text-ink" title={strong() ? "The needle has settled" : "The needle wavers between two headings"} />
          <VerdictLine answer={a()} />
        </div>
        <span class="text-[12.5px] text-muted">{props.label ?? dateWithDay(a().createdAt)}</span>
      </div>
      <div class="mt-6 grid grid-cols-2 gap-x-8 gap-y-5 max-md:grid-cols-1">
        <Show when={a().us}>{(c) => <CodeBlock code={c()} words={words()} lock={!!props.lock} />}</Show>
        <Show when={a().ca}>{(c) => <CodeBlock code={c()} words={words()} lock={!!props.lock} />}</Show>
      </div>
      <p class="mt-5 max-w-[640px] text-[17px] leading-[1.55] text-ink">
        <Show when={strong() && first()} fallback={a().verdict.sentence}>
          <Claim text={first()!.text} cites={first()!.cites} answer={a()} state={props.state} />
        </Show>
      </p>
      <Show when={a().alternative}>
        {(alt) => (
          <p class="mt-2 text-[14px] text-muted">
            Also possible <span class="font-code text-ink-2">{alt().code.code}</span>, {alt().condition}
            <Show when={alt().dutyAtStake}> · {alt().dutyAtStake}</Show>
          </p>
        )}
      </Show>
      <Show when={!strong() && props.caps}>
        <div class="mt-5">
          <DecidingQuestion
            answer={a()}
            canConfirm={props.caps!.canConfirm}
            canSend={props.caps!.canSend}
            brokerName={props.caps!.brokerName}
            onAnswer={(x) => props.onAnswer?.(x)}
            onSend={() => props.onSend?.()}
          />
        </div>
      </Show>
      <Show when={props.actions}>
        <div class="mt-6 flex flex-wrap items-center gap-2.5">{props.actions}</div>
      </Show>
    </section>
  );
}

function LayerRow(props: { value: string; icon: JSX.Element; label: string; summary?: JSX.Element; children: JSX.Element }) {
  return (
    <Accordion.Item value={props.value} class="border-b border-rule last:border-b-0">
      <Accordion.ItemTrigger class="group flex w-full items-center gap-3 px-5 py-4 text-left hover:bg-paper-2/60 max-sm:px-4">
        <span class="grid h-8 w-8 shrink-0 place-items-center rounded-[8px] bg-paper-2 text-ink-2">{props.icon}</span>
        <span class="flex-1 text-[15px] font-[600]">{props.label}</span>
        <span class="text-right text-[13.5px] text-muted">{props.summary}</span>
        <Accordion.ItemIndicator class="text-muted transition-transform duration-200 data-[state=open]:rotate-180">
          <ChevronIcon size={16} />
        </Accordion.ItemIndicator>
      </Accordion.ItemTrigger>
      <Accordion.ItemContent class="fold">
        <div class="px-5 pb-6 pt-1 sm:pl-[64px] max-sm:px-4">{props.children}</div>
      </Accordion.ItemContent>
    </Accordion.Item>
  );
}

/** The full answer: the card, then the layers, then the ruling drawer. */
export function AnswerView(props: {
  answer: AnswerOut;
  caps: AnswerCapabilities;
  actions?: JSX.Element;
  label?: JSX.Element;
  openCite?: number;
  /** Layers open on arrival (the landing opens none). */
  open?: string[];
  onAnswer?: (a: AnswerOut) => void;
  onSend?: () => void;
}) {
  const state = createCitationState(untrack(() => props.openCite) ?? null);
  const landed = useLandedCost(() => props.answer, untrack(() => props.caps.live));
  const a = () => props.answer;
  const soft = () => a().facts.filter((f) => f.source !== "stated").length;
  let root!: HTMLDivElement;
  onMount(() => {
    rise(root);
    const onKey = (e: KeyboardEvent) => moveBetweenChips(e, root);
    window.addEventListener("keydown", onKey);
    onCleanup(() => window.removeEventListener("keydown", onKey));
  });
  return (
    <div ref={root} class="space-y-4">
      <AnswerCard answer={a()} state={state} caps={props.caps} actions={props.actions} label={props.label} lock onAnswer={props.onAnswer} onSend={props.onSend} />
      <section aria-label="Detail" class={card({ class: "overflow-hidden" })} data-rise>
        <Accordion.Root multiple collapsible lazyMount defaultValue={props.open ?? []}>
          <LayerRow value="why" icon={<PathIcon size={17} />} label="Why this code" summary={`${a().path.length} steps`}>
            <WhyLayer answer={a()} state={state} skipFirstReason={a().verdict.word === "strong"} />
          </LayerRow>
          <LayerRow value="rulings" icon={<ScaleIcon size={17} />} label="Rulings" summary={a().verdict.cited ? `${a().verdict.agreeing} of ${a().verdict.cited} agree` : `${a().rulings.length}`}>
            <RulingsLayer answer={a()} state={state} />
          </LayerRow>
          <LayerRow
            value="cost"
            icon={<StackIcon size={17} />}
            label="Landed cost"
            summary={
              <Show when={landed.cost()} fallback="Add a shipment">
                {(c) => (
                  <span>
                    <span class="font-code text-ink-2">{money(c().chargesTotal)}</span> · {c().country === "US" ? "US" : "Canada"}
                  </span>
                )}
              </Show>
            }
          >
            <CostLayer answer={a()} live={props.caps.live} state={landed} />
          </LayerRow>
          <LayerRow value="facts" icon={<ListIcon size={17} />} label="Facts" summary={soft() ? `${soft()} to check` : `${a().facts.length}`}>
            <FactsLayer answer={a()} />
          </LayerRow>
          <LayerRow value="law" icon={<DocIcon size={17} />} label="Law text" summary={`${a().tariffAuthorities.length}`}>
            <LawLayer answer={a()} />
          </LayerRow>
        </Accordion.Root>
      </section>
      <p class="px-1 text-[12.5px] text-muted">{a().snapshotLabel} · A licensed broker approves every code before it is used.</p>
      <RulingDrawer rulings={a().rulings} state={state} answerId={a().sample ? undefined : a().id} canFlag={props.caps.canFlag} sample={a().sample} />
    </div>
  );
}

/** While the classifier works: the card frame with the needle seeking. */
export function AnswerLoading(props: { label?: string }) {
  return (
    <div aria-busy="true" class="space-y-4">
      <section class={card({ class: "p-7 max-sm:p-5" })}>
        <p role="status" class="flex items-center gap-2.5 text-[14.5px] text-muted">
          <CompassMark size={24} state="seek" class="text-ink" />
          {props.label ?? "Reading the tariff…"}
        </p>
        <div class="mt-7 grid grid-cols-2 gap-8 max-md:grid-cols-1">
          <div class="skeleton h-9 w-[80%]" />
          <div class="skeleton h-9 w-[80%]" />
        </div>
        <SkeletonLines lines={2} class="mt-6" />
      </section>
      <section class={card({ class: "p-5" })}>
        <SkeletonLines lines={5} />
      </section>
    </div>
  );
}

export function AnswerError(props: { error: unknown; retry: () => void; brokerName?: string }) {
  return (
    <ErrorSlip error={props.error} retry={props.retry}>
      <p class="ml-7 mt-1 text-[14px] text-muted">Your question is saved. Nothing was sent to {props.brokerName ?? "your broker"} and nothing was filed.</p>
    </ErrorSlip>
  );
}
