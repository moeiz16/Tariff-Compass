/**
 * The compass: the logo and the loading state (Seek), and the confidence signal on an answer
 * (Settle for a strong match, Waver between two headings when a broker is needed).
 */
import { Show } from "solid-js";

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
      <circle cx="16" cy="16" r="13.8" fill="none" stroke="currentColor" stroke-width="1.8" />
      <path d="M16 4v2.6M16 25.4V28M4 16h2.6M25.4 16H28" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      <g class="needle">
        <path class="n-north" d="M16 6.6 L19 16 L13 16Z" stroke-width="1.2" stroke-linejoin="round" />
        <path class="n-south" d="M16 25.4 L13 16 L19 16Z" />
      </g>
      <circle class="hub" cx="16" cy="16" r="1.4" />
    </svg>
  );
}

/** The brand: the compass and the name, sentence case. */
export function Brand(props: { compact?: boolean; state?: NeedleState }) {
  return (
    <span class="inline-flex items-center gap-2.5 whitespace-nowrap text-[16px] font-[650] tracking-[-0.015em] text-ink">
      <CompassMark size={26} state={props.state} />
      <span classList={{ "sr-only": props.compact }}>Tariff Compass</span>
    </span>
  );
}
