/**
 * Lab charts, monochrome first with the highlighter as the only "look here" colour. Marks are told apart by shape
 * (ring, half, filled), values are printed beside them, and every chart has a table view.
 */
import { For, Show } from "solid-js";
import type { ConfidenceCell, DepthRow } from "~/lib/types";

const LEVEL_NOTE: Record<string, string> = { chapter: "first 2 digits", heading: "first 4", subheading: "first 6", full_code: "all 10" };

function Mark(props: { kind: "ring" | "half" | "filled"; at: number }) {
  return (
    <span class="absolute top-1/2 h-[15px] w-[15px] -translate-x-1/2 -translate-y-1/2 rounded-full border-[2px] border-ink" style={{ left: `${props.at}%` }} classList={{ "bg-paper": props.kind === "ring", "bg-ink": props.kind === "filled" }}>
      <Show when={props.kind === "half"}>
        <span class="absolute inset-y-0 left-0 w-1/2 rounded-l-full bg-ink" />
      </Show>
    </span>
  );
}

export function DepthPlot(props: { rows: DepthRow[]; liveN: number | null; n: number }) {
  return (
    <figure>
      <figcaption class="flex flex-wrap gap-x-6 gap-y-1 text-[15px]">
        <span class="inline-flex items-center gap-2">
          <span class="h-3 w-3 rounded-full border-[2px] border-ink" /> Word matching (the yardstick)
        </span>
        <Show when={props.liveN}>
          <span class="inline-flex items-center gap-2">
            <span class="relative h-3 w-3 overflow-hidden rounded-full border-[2px] border-ink">
              <span class="absolute inset-y-0 left-0 w-1/2 bg-ink" />
            </span>{" "}
            Round {props.liveN}, live now
          </span>
        </Show>
        <span class="inline-flex items-center gap-2">
          <span class="h-3 w-3 rounded-full bg-ink" /> Round {props.n}
        </span>
        <span class="inline-flex items-center gap-2">
          <span class="h-2.5 w-5 bg-hi" /> What round {props.n} adds
        </span>
        <Show when={props.rows.some((r) => r.candidate < (r.live ?? r.wordMatching))}>
          <span class="inline-flex items-center gap-2">
            <span class="h-2.5 w-5 border-[1.5px] border-bad" /> What it loses
          </span>
        </Show>
      </figcaption>
      <div class="mt-5" aria-hidden="true">
        <For each={props.rows}>
          {(r) => {
            // The gain is measured against what is in use: the live round, or word matching when no round is live.
            const base = () => r.live ?? r.wordMatching;
            const lo = () => Math.min(base(), r.candidate);
            const hi = () => Math.max(base(), r.candidate);
            return (
              <div class="grid grid-cols-[150px_minmax(0,1fr)_150px] items-center gap-x-6 border-b border-rule py-3.5 max-md:grid-cols-[96px_minmax(0,1fr)] max-md:gap-x-3">
                <div>
                  <p class="font-type text-[15px] font-[700] uppercase tracking-[0.03em]">{r.levelLabel}</p>
                  <p class="text-[14px] text-muted">{LEVEL_NOTE[r.level]}</p>
                </div>
                <div class="relative h-[20px]">
                  <span class="absolute inset-x-0 top-1/2 h-px bg-rule" />
                  <Show when={r.live !== null && r.live !== undefined}>
                    <span class="absolute top-1/2 h-[2px] -translate-y-1/2 bg-muted" style={{ left: `${Math.min(r.wordMatching, lo())}%`, width: `${Math.abs(lo() - r.wordMatching)}%` }} />
                  </Show>
                  <span
                    class="absolute top-1/2 h-[9px] -translate-y-1/2"
                    classList={{ "bg-hi": r.candidate >= base(), "border-[1.5px] border-bad bg-paper": r.candidate < base() }}
                    style={{ left: `${lo()}%`, width: `${hi() - lo()}%` }}
                  />
                  <Mark kind="ring" at={r.wordMatching} />
                  <Show when={r.live !== null && r.live !== undefined}>
                    <Mark kind="half" at={r.live!} />
                  </Show>
                  <Mark kind="filled" at={r.candidate} />
                </div>
                <p class="text-right font-code text-[16px] max-md:col-span-2 max-md:text-left max-md:text-[14px]">
                  {Math.round(r.wordMatching)} · {r.live === null || r.live === undefined ? "–" : Math.round(r.live)} · <b>{Math.round(r.candidate)}</b>
                </p>
              </div>
            );
          }}
        </For>
        <div class="grid grid-cols-[150px_minmax(0,1fr)_150px] gap-x-6 pt-2 font-code text-[12.5px] text-muted max-md:grid-cols-[96px_minmax(0,1fr)] max-md:gap-x-3">
          <span />
          <span class="relative h-4">
            <For each={[0, 25, 50, 75, 100]}>{(t) => <span class="absolute -translate-x-1/2" style={{ left: `${t}%` }}>{t}</span>}</For>
          </span>
        </div>
      </div>
      <details class="mt-4">
        <summary class="cursor-pointer text-[14.5px] text-ink-2 underline underline-offset-4">Table view, with the classifier before training</summary>
        <table class="mt-2 w-full max-w-[640px] border-collapse text-left text-[15px]">
          <thead>
            <tr class="border-b-[1.5px] border-ink text-[13.5px] text-ink-2">
              <th class="py-1.5 pr-3 font-[650]">Depth</th>
              <th class="py-1.5 pr-3 text-right font-[650]">Word matching</th>
              <th class="py-1.5 pr-3 text-right font-[650]">Before training</th>
              <th class="py-1.5 pr-3 text-right font-[650]">Round {props.liveN ?? "live"}</th>
              <th class="py-1.5 text-right font-[650]">Round {props.n}</th>
            </tr>
          </thead>
          <tbody>
            <For each={props.rows}>
              {(r) => (
                <tr class="border-b border-rule">
                  <th scope="row" class="py-1.5 pr-3 font-[600]">{r.levelLabel}</th>
                  <td class="py-1.5 pr-3 text-right font-code">{Math.round(r.wordMatching)}</td>
                  <td class="py-1.5 pr-3 text-right font-code">{r.unoptimised === null || r.unoptimised === undefined ? "–" : Math.round(r.unoptimised)}</td>
                  <td class="py-1.5 pr-3 text-right font-code">{r.live === null || r.live === undefined ? "–" : Math.round(r.live)}</td>
                  <td class="py-1.5 text-right font-code font-[650]">{Math.round(r.candidate)}</td>
                </tr>
              )}
            </For>
          </tbody>
        </table>
        <p class="mt-1 text-[13.5px] text-muted">Right out of 100 rulings it hasn't seen.</p>
      </details>
    </figure>
  );
}

/** 100 dots: filled = the outcome named in the sentence, ringed in red = the rest. */
export function FrequencyGrid(props: { cell: ConfidenceCell; label: string; filledMeans: string; restMeans: string }) {
  return (
    <figure>
      <figcaption class="text-[15.5px] text-ink-2">
        When it said <b class="text-ink">{props.label}</b> ({props.cell.said.toLocaleString("en-US")} times)
      </figcaption>
      <p class="ty-title mt-1 text-[clamp(21px,2.2vw,27px)]">{props.cell.sentence.split(": ").pop()}</p>
      <div class="mt-3 grid w-fit grid-cols-[repeat(20,10px)] gap-[5px]" role="img" aria-label={`${props.cell.per100} of 100 ${props.filledMeans}; the rest ${props.restMeans}`}>
        <For each={Array.from({ length: 100 }, (_, i) => i)}>
          {(i) => <span class="h-[10px] w-[10px] rounded-full" classList={{ "bg-ink": i < props.cell.per100, "border-[1.5px] border-bad": i >= props.cell.per100 }} />}
        </For>
      </div>
      <p class="mt-2 text-[13.5px] text-muted">
        Filled: {props.filledMeans}. Red ring: {props.restMeans}.
      </p>
    </figure>
  );
}
