/**
 * The 97: every chapter of the tariff in its 21 section columns. A teaching device and the stage for Narrow:
 * the chapters dim, the candidates outline and name themselves, the losers are struck and the winner takes the
 * highlighter.
 */
import { For, Show } from "solid-js";
import type { SectionOut } from "~/lib/types";

export interface NarrowState {
  phase: "idle" | "dim" | "candidates" | "struck" | "chosen";
  winner?: string;
  losers: string[];
}

function tileClass(ch: string, reserved: boolean, n: NarrowState): string {
  const base = "relative block h-[22px] rounded-[2px] text-center font-code text-[12.5px] leading-[22px] transition-[opacity,background-color,box-shadow] duration-300";
  if (reserved) return `${base} border border-dashed border-muted text-muted`;
  const isWinner = n.winner === ch;
  const isLoser = n.losers.includes(ch);
  if (n.phase === "idle") return `${base} bg-paper-2 text-ink-2`;
  if (isWinner && (n.phase === "chosen")) return `${base} bg-hi text-hi-ink font-[700] shadow-[0_0_0_1.5px_var(--color-ink)]`;
  if ((isWinner || isLoser) && n.phase !== "dim") return `${base} bg-paper text-ink font-[650] shadow-[0_0_0_1.5px_var(--color-ink)] ${isLoser && (n.phase === "struck" || n.phase === "chosen") ? "line-through decoration-bad decoration-2 opacity-70" : ""}`;
  return `${base} bg-paper-2 text-ink-2 opacity-25`;
}

export function The97(props: { sections: SectionOut[]; narrow: NarrowState; caption?: string }) {
  const chapters = () => props.sections.flatMap((s) => s.chapters.map((c) => ({ ...c, section: s.section })));
  const titleOf = (ch: string) => chapters().find((c) => c.chapter === ch)?.title ?? "";
  return (
    <figure class="mx-auto w-full max-w-[1000px]" aria-label="The whole tariff: 97 chapters in 21 sections">
      <figcaption class="mb-2.5 flex flex-wrap justify-between gap-2 text-[13.5px] text-muted" aria-live="polite">
        <span>
          <Show
            when={props.narrow.phase !== "idle" && props.caption}
            fallback={
              <>
                <b class="font-type font-[700] uppercase tracking-[0.03em] text-ink">The whole tariff:</b> 97 chapters in 21 sections. Every answer narrows to one.
              </>
            }
          >
            <b class="font-[650] text-ink-2">{props.caption}</b>
          </Show>
        </span>
        <span>Chapter 77 is held in reserve.</span>
      </figcaption>
      {/* Desktop: 21 section columns */}
      <div class="grid grid-cols-[repeat(21,minmax(0,1fr))] gap-x-2 max-md:hidden" aria-hidden="true">
        <For each={props.sections}>
          {(s) => (
            <div class="min-w-0">
              <p class="border-b-[1.5px] border-ink pb-1 text-center font-code text-[11.5px] font-[600] text-ink-2" title={s.title}>
                {s.section}
              </p>
              <div class="mt-1.5 flex flex-col gap-[3px]">
                <For each={s.chapters}>{(c) => <span class={tileClass(c.chapter, c.reserved, props.narrow)}>{c.chapter}</span>}</For>
              </div>
            </div>
          )}
        </For>
      </div>
      {/* Phone: seven tiles per row */}
      <div class="hidden grid-cols-7 gap-[3px] max-md:grid" aria-hidden="true">
        <For each={chapters()}>{(c) => <span class={tileClass(c.chapter, c.reserved, props.narrow)}>{c.chapter}</span>}</For>
      </div>
      <Show when={props.narrow.phase !== "idle" && props.narrow.phase !== "dim"}>
        <ul class="mt-3 flex flex-wrap justify-center gap-x-5 gap-y-1 text-[14px]">
          <For each={[...props.narrow.losers, ...(props.narrow.winner ? [props.narrow.winner] : [])]}>
            {(ch) => (
              <li classList={{ "line-through decoration-bad text-muted": props.narrow.losers.includes(ch) && props.narrow.phase !== "candidates", "font-[700]": ch === props.narrow.winner }}>
                <span class="font-code">{ch}</span> {titleOf(ch)}
              </li>
            )}
          </For>
        </ul>
      </Show>
    </figure>
  );
}

/** The candidate chapters for Narrow, read from the answer: the winner and the neighbours it set aside. */
export function narrowFrom(answer: { us: { digits: string } | null; ca: { digits: string } | null; path: { notNeighbours: { code: string }[] }[]; alternative?: { code: { digits: string } } | null }) {
  const winner = (answer.us ?? answer.ca)?.digits.slice(0, 2);
  const others = new Set<string>();
  for (const s of answer.path) for (const n of s.notNeighbours) others.add(n.code.replace(/\D/g, "").slice(0, 2));
  if (answer.alternative) others.add(answer.alternative.code.digits.slice(0, 2));
  if (winner) others.delete(winner);
  return { winner, losers: [...others].filter(Boolean).slice(0, 3) };
}
