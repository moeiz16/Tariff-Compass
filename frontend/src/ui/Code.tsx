/**
 * Tariff codes in Reddit Mono, grouped 4.2.2.2. The heading digits are ink on the highlighter band; the rest are
 * softer. A leaning code (needs a broker) gets a dashed amber underline instead of the highlighter.
 */
import { For, Show, createSignal, onMount, untrack } from "solid-js";
import { codeSegments } from "~/lib/format";
import { reducedMotion } from "~/lib/motion";
import type { DigitTreatment } from "~/lib/verdict";

export function CodeDigits(props: {
  code: string;
  leaning?: boolean;
  /** Overrides `leaning`: how to draw the heading digits and the rest (from the confidence word at each depth). */
  treatment?: { heading: DigitTreatment; rest: DigitTreatment };
  /** Sweep the highlighter in once when the code first appears. */
  lock?: boolean;
  size?: "xl" | "lg" | "md" | "sm";
  class?: string;
}) {
  const segs = () => codeSegments(props.code);
  const size = () =>
    ({ xl: "text-[clamp(28px,2.6vw,36px)] font-[500] tracking-[-0.02em]", lg: "text-[24px] font-[500] tracking-[-0.01em]", md: "text-[16px] font-[500]", sm: "text-[14px] font-[500]" })[
      props.size ?? "md"
    ];
  const [lit, setLit] = createSignal(!untrack(() => props.lock) || reducedMotion());
  onMount(() => {
    if (!lit()) requestAnimationFrame(() => setTimeout(() => setLit(true), 120));
  });
  const treat = (heading: boolean): DigitTreatment => {
    // In lists (small codes) the code stays plain: the row's badge already says how sure it is.
    if (props.size === "sm") return "plain";
    const t = props.treatment ?? { heading: props.leaning ? "dashed" : "hl", rest: "plain" };
    return heading ? t.heading : t.rest;
  };
  return (
    <span class={`font-code leading-none whitespace-nowrap ${size()} ${props.class ?? ""}`} aria-label={props.code}>
      <For each={segs()}>
        {(seg, i) => (
          <>
            <Show when={i() > 0}>
              <span class="text-muted" aria-hidden="true">
                .
              </span>
            </Show>
            <span
              aria-hidden="true"
              data-treatment={treat(seg.heading)}
              data-lit={treat(seg.heading) === "hl" ? String(lit()) : undefined}
              classList={{
                "hl-sweep": treat(seg.heading) === "hl",
                hl: treat(seg.heading) === "hl" && !props.lock,
                "text-ink": seg.heading,
                "text-ink-2": !seg.heading,
                "border-b-2 border-dashed border-warn": treat(seg.heading) === "dashed",
              }}
            >
              {seg.text}
            </span>
          </>
        )}
      </For>
    </span>
  );
}

/** A code inside prose. */
export function InlineCode(props: { children: string; class?: string }) {
  return <span class={`font-code text-[0.94em] whitespace-nowrap ${props.class ?? ""}`}>{props.children}</span>;
}
