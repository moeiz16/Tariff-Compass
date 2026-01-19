/**
 * Tariff codes in Spline Sans Mono, grouped 4.2.2.2. The heading digits sit on the highlighter; a leaning code
 * (needs a broker) gets a dashed amber underline instead. "Lock" drops each digit in with a slight overshoot.
 */
import { For, Show } from "solid-js";
import { codeSegments } from "~/lib/format";
import { reducedMotion } from "~/lib/motion";

export function CodeDigits(props: { code: string; leaning?: boolean; lock?: boolean; size?: "xl" | "lg" | "md" | "sm"; class?: string }) {
  const segs = () => codeSegments(props.code);
  const size = () =>
    ({ xl: "text-[clamp(30px,2.65vw,40px)] font-[600]", lg: "text-[28px] font-[600]", md: "text-[17px] font-[550]", sm: "text-[14.5px] font-[500]" })[
      props.size ?? "md"
    ];
  const lock = () => !!props.lock && !reducedMotion();
  let digit = 0;
  return (
    <span class={`font-code tracking-[-0.01em] leading-none whitespace-nowrap ${size()} ${props.class ?? ""}`} aria-label={props.code}>
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
              classList={{
                hl: seg.heading && !props.leaning,
                "underline decoration-dashed decoration-warn decoration-2 underline-offset-[0.18em]": seg.heading && !!props.leaning,
              }}
            >
              <For each={seg.text.split("")}>
                {(ch) => {
                  const n = digit++;
                  return (
                    <span class={lock() ? "anim-lock" : undefined} style={lock() ? { "animation-delay": `${n * 50}ms` } : undefined}>
                      {ch}
                    </span>
                  );
                }}
              </For>
            </span>
          </>
        )}
      </For>
    </span>
  );
}

/** A code inside prose: mono, no highlighter. */
export function InlineCode(props: { children: string; class?: string }) {
  return <span class={`font-code text-[0.94em] whitespace-nowrap ${props.class ?? ""}`}>{props.children}</span>;
}
