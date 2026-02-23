/**
 * The compass: logo, the "o" of the wordmark, the loading state (Seek) and the confidence signal
 * (Settle for a strong match, Waver between two headings when a broker is needed).
 */
import { Show } from "solid-js";
import { TypedRule } from "./Type";

export type NeedleState = "still" | "seek" | "settle" | "waver";

export function CompassMark(props: { bearing?: number; state?: NeedleState; size?: number; class?: string; title?: string }) {
  const bearing = () => props.bearing ?? 32;
  return (
    <svg
      class={`mark ${props.state ?? "still"} ${props.class ?? ""}`}
      viewBox="0 0 32 32"
      width={props.size ?? 28}
      height={props.size ?? 28}
      role={props.title ? "img" : undefined}
      aria-hidden={props.title ? undefined : "true"}
      style={{ "--bearing": `${bearing()}deg`, "--b1": `${bearing() - 26}deg`, "--b2": `${bearing() + 26}deg` }}
    >
      <Show when={props.title}>
        <title>{props.title}</title>
      </Show>
      <circle cx="16" cy="16" r="13.6" fill="none" stroke="currentColor" stroke-width="2.2" />
      <path d="M16 3.6v3.2M16 25.2v3.2M3.6 16h3.2M25.2 16h3.2" stroke="currentColor" stroke-width="1.6" />
      <g class="needle">
        <path class="n-north" d="M16 6.2 L19.2 16 L12.8 16Z" stroke-width="1.3" stroke-linejoin="round" />
        <path class="n-south" d="M16 25.8 L12.8 16 L19.2 16Z" />
      </g>
      <circle class="hub" cx="16" cy="16" r="1.5" />
    </svg>
  );
}

/**
 * The letterhead: "TARIFF C◎MPASS" typed in bold capitals with the compass as its "O", over a typed double rule,
 * as at the head of a ruling letter.
 */
export function Wordmark(props: { size?: "xl" | "lg"; state?: NeedleState; bearing?: number }) {
  return (
    <h1 class="ty-letterhead mx-auto w-fit" aria-label="Tariff Compass">
      <span class="flex items-center justify-center whitespace-nowrap" aria-hidden="true">
        Tariff&nbsp;C
        <CompassMark size={0} class="h-[0.6em] w-[0.6em] shrink-0 translate-y-[-0.01em]" state={props.state} bearing={props.bearing} />
        mpass
      </span>
      <TypedRule double class="mt-[0.22em] text-[clamp(14px,1.5vw,18px)] text-ink" />
    </h1>
  );
}

/** The strip's brand: the compass and the name typed in letter-spaced capitals. */
export function Brand(props: { compact?: boolean }) {
  return (
    <span class="inline-flex items-center gap-2.5 whitespace-nowrap font-type text-[17px] font-[700] uppercase tracking-[0.08em] text-ink max-sm:gap-2 max-sm:text-[14px] max-sm:tracking-[0.04em]">
      <CompassMark size={30} />
      <span classList={{ "sr-only": props.compact }}>Tariff Compass</span>
    </span>
  );
}
