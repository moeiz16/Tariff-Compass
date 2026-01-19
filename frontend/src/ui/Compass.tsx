/**
 * The compass: logo, the "o" of the wordmark, the loading state (Seek) and the confidence signal
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

/** "Tariff C◎mpass": Tariff in light italic, Compass in heavy roman with the compass as its "o". */
export function Wordmark(props: { size?: "xl" | "lg"; state?: NeedleState; bearing?: number }) {
  const big = () => (props.size ?? "xl") === "xl";
  return (
    <h1
      class={`flex items-center justify-center whitespace-nowrap leading-none tracking-[-0.02em] ${
        big() ? "text-[clamp(46px,10.5vw,128px)]" : "text-[clamp(40px,8vw,96px)]"
      }`}
      aria-label="Tariff Compass"
    >
      <span class="font-[300] italic" aria-hidden="true">
        Tariff
      </span>
      <span class="ml-[0.18em] inline-flex items-center font-[800]" aria-hidden="true">
        C
        <CompassMark size={0} class="mx-[0.02em] h-[0.66em] w-[0.66em] translate-y-[0.06em]" state={props.state} bearing={props.bearing} />
        mpass
      </span>
    </h1>
  );
}

export function Brand(props: { compact?: boolean }) {
  return (
    <span class="inline-flex items-center gap-2.5 text-[22px] font-[750] tracking-[-0.01em] text-ink">
      <CompassMark size={30} />
      <span classList={{ "sr-only": props.compact }}>Tariff Compass</span>
    </span>
  );
}
