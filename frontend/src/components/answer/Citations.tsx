/**
 * Citations open where you read. A chip in the sentence (with a hover/focus peek, Ark HoverCard) toggles an
 * inline drawer under the paragraph (Ark Collapsible, never portalled): ruling number, date, status, the holding
 * with its supporting words marked, and a small "your facts against the ruling's" table.
 */
import { Collapsible } from "@ark-ui/solid/collapsible";
import { HoverCard } from "@ark-ui/solid/hover-card";
import { A } from "@solidjs/router";
import { For, Show, createSignal } from "solid-js";
import { Portal } from "solid-js/web";
import type { CitationState } from "~/lib/citations";
import { answers } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import type { CitedRulingOut } from "~/lib/types";
import { Marked } from "~/ui/Marked";
import { button, floating } from "~/ui/recipes";
import { MatchMark, RulingStatus } from "~/ui/Status";
import { notify } from "~/ui/Toast";

export function CitationChip(props: { n: number; ruling?: CitedRulingOut; state: CitationState; anchor: string }) {
  const open = () => props.state.isOpen(props.n);
  const chip = (
    <button
      type="button"
      data-cite-chip
      aria-expanded={open()}
      aria-controls={`${props.anchor}-cite-${props.n}`}
      aria-label={`Citation ${props.n}${props.ruling ? `: ${props.ruling.id}` : ""}. ${open() ? "Close" : "Open"} it under this paragraph`}
      onClick={() => props.state.toggle(props.n)}
      class="relative -top-[0.45em] mx-[1px] inline-grid h-[1.15em] min-w-[1.15em] place-items-center rounded-[var(--radius-chip)] border-[1.5px] border-ink px-[3px] align-baseline font-code text-[0.62em] font-[600] leading-none transition-colors"
      classList={{ "bg-ink text-paper": open(), "bg-paper text-ink hover:bg-paper-2": !open() }}
    >
      {props.n}
    </button>
  );
  return (
    <Show when={props.ruling} fallback={chip}>
      {(r) => (
        <HoverCard.Root openDelay={350} closeDelay={120} positioning={{ placement: "top", gutter: 8 }}>
          <HoverCard.Trigger asChild={(p) => <span {...p()}>{chip}</span>} />
          <Portal>
            <HoverCard.Positioner class="z-50 max-md:hidden">
              <HoverCard.Content class={floating({ class: "w-[min(380px,90vw)] p-3.5 text-[14px]" })}>
                <p class="flex flex-wrap items-baseline gap-2">
                  <span class="font-code font-[650]">{r().id}</span>
                  <span class="text-muted">{dateShort(r().date)}</span>
                  <RulingStatus status={r().status} />
                </p>
                <p class="mt-1.5 font-law text-[15px] leading-snug">
                  <Marked text={r().holding} spans={r().markedSpans} />
                </p>
                <p class="mt-1.5 text-[12.5px] text-muted">Press the number to open it under the sentence.</p>
              </HoverCard.Content>
            </HoverCard.Positioner>
          </Portal>
        </HoverCard.Root>
      )}
    </Show>
  );
}

export function CitationDrawer(props: {
  ruling: CitedRulingOut;
  state: CitationState;
  anchor: string;
  answerId?: string;
  canFlag?: boolean;
  sample?: boolean;
}) {
  const [flagging, setFlagging] = createSignal(false);
  const [reason, setReason] = createSignal("");
  const [flagged, setFlagged] = createSignal(false);
  const [error, setError] = createSignal("");
  const r = () => props.ruling;
  const flag = async () => {
    if (!props.answerId) return;
    setError("");
    try {
      await answers.citationFeedback(props.answerId, r().n, reason().trim() || "This ruling doesn't apply");
      setFlagged(true);
      setFlagging(false);
      notify(`Recorded · ruling [${r().n}] doesn't apply`, "It becomes a correction for the next training round.");
    } catch (e) {
      setError(plainProblem(e).message);
    }
  };
  return (
    <Collapsible.Root open={props.state.isOpen(r().n)} onOpenChange={(d) => (d.open ? props.state.show(r().n) : props.state.close(r().n))} lazyMount unmountOnExit>
      <Collapsible.Content
        id={`${props.anchor}-cite-${r().n}`}
        class="anim-drawer my-4 overflow-hidden rounded-r-[var(--radius-box)] border-[1.5px] border-l-[6px] border-ink border-l-hi bg-paper"
        role="region"
        aria-label={`Citation ${r().n}, ${r().id}`}
      >
        <header class="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-rule px-4 py-2.5">
          <span class="hl grid h-6 min-w-6 place-items-center rounded-[var(--radius-chip)] border-[1.5px] border-ink font-code text-[12px] font-[650]">{r().n}</span>
          <span class="font-code text-[16px] font-[650]">{r().id}</span>
          <span class="text-[14px] text-muted">{dateShort(r().date)}</span>
          <RulingStatus status={r().status} long />
          <span class="text-[13px] text-muted">{r().matchLabels.join(" · ")}</span>
          <button type="button" class="ml-auto text-[14px] text-muted underline underline-offset-4 hover:text-ink" onClick={() => props.state.close(r().n)}>
            Close
          </button>
        </header>
        <div class="grid grid-cols-[1.15fr_1fr] max-md:grid-cols-1">
          <div class="px-4 py-3.5">
            <p class="font-law text-[16.5px] leading-[1.5]">
              <Marked text={r().holding} spans={r().markedSpans} />
            </p>
            <p class="mt-2 text-[13.5px] text-muted">The marked words support the sentence above.</p>
          </div>
          <div class="border-l border-rule bg-paper-2 px-3.5 py-3 max-md:border-l-0 max-md:border-t">
            <Show when={r().factCompare.length} fallback={<p class="text-[14px] text-muted">No facts to compare for this ruling.</p>}>
              <table class="w-full text-[14px]">
                <caption class="sr-only">Your facts against the ruling's</caption>
                <thead>
                  <tr class="text-left text-[12.5px] text-muted">
                    <th class="pb-1 pr-2 font-[650]">Fact</th>
                    <th class="pb-1 pr-2 font-[650]">Yours</th>
                    <th class="pb-1 pr-2 font-[650]">The ruling's</th>
                    <th class="pb-1 font-[650]"><span class="sr-only">Match</span></th>
                  </tr>
                </thead>
                <tbody>
                  <For each={r().factCompare}>
                    {(f) => (
                      <tr class="border-t border-rule align-top">
                        <td class="py-1.5 pr-2">{f.fact}</td>
                        <td class="py-1.5 pr-2">{f.yours}</td>
                        <td class="py-1.5 pr-2">{f.theirs}</td>
                        <td class="py-1.5 text-right">
                          <MatchMark match={f.match} label={f.matchLabel} />
                        </td>
                      </tr>
                    )}
                  </For>
                </tbody>
              </table>
            </Show>
          </div>
        </div>
        <footer class="flex flex-wrap items-center gap-2 border-t border-rule px-4 py-2.5">
          <Show when={!props.sample && props.answerId}>
            <A href={`/rulings/${r().key}?answerId=${props.answerId}&n=${r().n}`} class={button({ tone: "ink", size: "xs" })}>
              Compare side by side
            </A>
          </Show>
          <Show when={!props.sample} fallback={<a class={button({ tone: "ghost", size: "xs" })} href={r().url} target="_blank" rel="noreferrer">Read the ruling on CBP CROSS</a>}>
            <A href={`/rulings/${r().key}`} class={button({ tone: "ghost", size: "xs" })}>
              Read the ruling
            </A>
          </Show>
          <Show when={props.canFlag && !flagged()}>
            <button type="button" class={button({ tone: "quiet", size: "xs", class: "ml-auto" })} aria-expanded={flagging()} onClick={() => setFlagging((v) => !v)}>
              This ruling doesn't apply
            </button>
          </Show>
          <Show when={flagged()}>
            <span class="ml-auto text-[13px] text-muted">Recorded for the next training round.</span>
          </Show>
        </footer>
        <Show when={flagging()}>
          <form
            class="flex flex-wrap items-end gap-2 border-t border-rule bg-paper-2 px-4 py-3"
            onSubmit={(e) => {
              e.preventDefault();
              void flag();
            }}
          >
            <label class="flex min-w-[240px] flex-1 flex-col gap-1 text-[13px] font-[650] text-ink-2">
              Why doesn't it apply?
              <input
                value={reason()}
                onInput={(e) => setReason(e.currentTarget.value)}
                class="h-10 rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-3 text-[15px] font-[400] text-ink"
                placeholder="The ruling's bottle has a vacuum; ours doesn't"
              />
            </label>
            <button type="submit" class={button({ size: "sm" })}>
              Record it
            </button>
            <Show when={error()}>
              <p role="alert" class="w-full text-[13px] font-[600] text-bad">
                {error()}
              </p>
            </Show>
          </form>
        </Show>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
