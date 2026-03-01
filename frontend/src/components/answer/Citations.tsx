/**
 * Citations open in the ruling drawer. A numbered chip in a sentence (with a hover peek, Ark HoverCard) or a row in
 * the Rulings layer opens one ruling: its holding with the supporting words marked, your facts against the ruling's,
 * and the ways on (compare side by side, read the ruling, or flag it as not applying).
 */
import { HoverCard } from "@ark-ui/solid/hover-card";
import { A } from "@solidjs/router";
import { For, Show, createSignal } from "solid-js";
import { Portal } from "solid-js/web";
import type { CitationState } from "~/lib/citations";
import { answers } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import type { CitedRulingOut } from "~/lib/types";
import { ExternalIcon } from "~/ui/Icons";
import { Marked } from "~/ui/Marked";
import { button, floating } from "~/ui/recipes";
import { Drawer } from "~/ui/Sheet";
import { MatchMark, RulingStatus } from "~/ui/Status";
import { notify } from "~/ui/Toast";

export function CitationChip(props: { n: number; ruling?: CitedRulingOut; state: CitationState }) {
  const open = () => props.state.isOpen(props.n);
  const chip = (
    <button
      type="button"
      data-cite-chip
      aria-haspopup="dialog"
      aria-expanded={open()}
      aria-label={`Citation ${props.n}${props.ruling ? `: ${props.ruling.id}` : ""}. Open the ruling`}
      onClick={() => props.state.show(props.n)}
      class="relative -top-[0.4em] mx-[1px] inline-grid h-[1.25em] min-w-[1.25em] place-items-center rounded-full bg-paper-2 px-[4px] align-baseline font-code text-[0.62em] font-[600] leading-none text-ink-2 transition-colors hover:bg-ink hover:text-card"
      classList={{ "bg-ink text-card": open() }}
    >
      {props.n}
    </button>
  );
  return (
    <Show when={props.ruling} fallback={chip}>
      {(r) => (
        <HoverCard.Root openDelay={400} closeDelay={120} positioning={{ placement: "top", gutter: 8 }}>
          <HoverCard.Trigger asChild={(p) => <span {...p()}>{chip}</span>} />
          <Portal>
            <HoverCard.Positioner class="z-50 max-md:hidden">
              <HoverCard.Content class={floating({ class: "w-[min(340px,90vw)] p-3.5 text-[13.5px]" })}>
                <p class="flex flex-wrap items-center gap-2">
                  <span class="font-code font-[600]">{r().id}</span>
                  <RulingStatus status={r().status} />
                </p>
                <p class="mt-1.5 line-clamp-3 text-ink-2">{r().subject}</p>
              </HoverCard.Content>
            </HoverCard.Positioner>
          </Portal>
        </HoverCard.Root>
      )}
    </Show>
  );
}

/** The ruling drawer: one ruling, in layers. */
export function RulingDrawer(props: {
  rulings: CitedRulingOut[];
  state: CitationState;
  answerId?: string;
  canFlag?: boolean;
  sample?: boolean;
}) {
  const r = () => props.rulings.find((x) => x.n === props.state.open()) ?? null;
  return (
    <Drawer
      open={!!r()}
      onOpenChange={(o) => !o && props.state.close()}
      label={r() ? `Citation ${r()!.n}, ${r()!.id}` : "Ruling"}
      title={
        <span class="flex items-center gap-2.5">
          <span class="grid h-6 min-w-6 place-items-center rounded-full bg-paper-2 px-1.5 font-code text-[12px] font-[600] text-ink-2">{r()?.n}</span>
          <span class="font-code font-[600]">{r()?.id}</span>
        </span>
      }
      meta={
        <Show when={r()}>
          {(x) => (
            <>
              <RulingStatus status={x().status} long />
              <span aria-hidden="true">·</span>
              <span>{dateShort(x().date)}</span>
            </>
          )}
        </Show>
      }
      footer={<Show when={r()} keyed>{(x) => <RulingActions ruling={x} answerId={props.answerId} canFlag={props.canFlag} sample={props.sample} />}</Show>}
    >
      <Show when={r()} keyed>
        {(x) => (
          <div class="space-y-7">
            <p class="text-[14.5px] text-ink-2">{x.subject}</p>
            <section aria-label="Holding">
              <p class="label">Holding</p>
              <p class="mt-2 border-l-2 border-hi pl-3.5 text-[15.5px] leading-[1.6] text-ink">
                <Marked text={x.holding} spans={x.markedSpans} />
              </p>
              <Show when={x.matchLabels.length}>
                <p class="mt-2 text-[12.5px] text-muted">{x.matchLabels.join(" · ")}</p>
              </Show>
            </section>
            <Show when={x.factCompare.length}>
              <section aria-label="Your facts against the ruling's">
                <p class="label">Your product vs the ruling</p>
                <table class="mt-2 w-full text-[14px]">
                  <caption class="sr-only">Your facts against the ruling's</caption>
                  <thead>
                    <tr class="border-b border-rule text-left text-[12px] text-muted">
                      <th class="pb-1.5 pr-3 font-[600]">Fact</th>
                      <th class="pb-1.5 pr-3 font-[600]">Yours</th>
                      <th class="pb-1.5 pr-3 font-[600]">The ruling's</th>
                      <th class="pb-1.5 font-[600]">
                        <span class="sr-only">Match</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <For each={x.factCompare}>
                      {(f) => (
                        <tr class="border-b border-rule align-top last:border-b-0">
                          <td class="py-2 pr-3 text-muted">{f.fact}</td>
                          <td class="py-2 pr-3">{f.yours}</td>
                          <td class="py-2 pr-3">{f.theirs}</td>
                          <td class="py-2 text-right">
                            <MatchMark match={f.match} label={f.matchLabel} />
                          </td>
                        </tr>
                      )}
                    </For>
                  </tbody>
                </table>
              </section>
            </Show>
          </div>
        )}
      </Show>
    </Drawer>
  );
}

function RulingActions(props: { ruling: CitedRulingOut; answerId?: string; canFlag?: boolean; sample?: boolean }) {
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
      notify(`Recorded · ruling ${r().n} doesn't apply`, "It becomes a correction for the next training round.");
    } catch (e) {
      setError(plainProblem(e).message);
    }
  };
  return (
    <div class="w-full">
      <Show when={flagging()}>
        <form
          class="mb-3 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void flag();
          }}
        >
          <label class="flex min-w-[220px] flex-1 flex-col gap-1 text-[12.5px] font-[600] text-ink-2">
            Why doesn't it apply?
            <input
              value={reason()}
              onInput={(e) => setReason(e.currentTarget.value)}
              class="h-9 rounded-[var(--radius-btn)] border border-rule-2 bg-card px-3 text-[14px] font-[400] text-ink outline-none focus:border-ink"
              placeholder="The ruling's bottle has a vacuum; ours doesn't"
            />
          </label>
          <button type="submit" class={button({ size: "sm" })}>
            Record
          </button>
          <Show when={error()}>
            <p role="alert" class="w-full text-[13px] font-[600] text-bad">
              {error()}
            </p>
          </Show>
        </form>
      </Show>
      <div class="flex flex-wrap items-center gap-2">
        <Show when={!props.sample && props.answerId}>
          <A href={`/rulings/${r().key}?answerId=${props.answerId}&n=${r().n}`} class={button({ size: "sm" })}>
            Compare side by side
          </A>
        </Show>
        <Show
          when={!props.sample}
          fallback={
            <a class={button({ tone: "outline", size: "sm" })} href={r().url} target="_blank" rel="noreferrer">
              Read on CBP CROSS <ExternalIcon size={13} />
            </a>
          }
        >
          <A href={`/rulings/${r().key}`} class={button({ tone: "outline", size: "sm" })}>
            Read the ruling
          </A>
        </Show>
        <Show when={props.canFlag && !flagged()}>
          <button type="button" class={button({ tone: "ghost", size: "sm", class: "ml-auto" })} aria-expanded={flagging()} onClick={() => setFlagging((v) => !v)}>
            Doesn't apply
          </button>
        </Show>
        <Show when={flagged()}>
          <span class="ml-auto text-[12.5px] text-muted">Recorded for the next round</span>
        </Show>
      </div>
    </div>
  );
}
