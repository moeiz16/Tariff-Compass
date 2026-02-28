/** Plain text with marked spans (untrusted text is never turned into HTML). */
import { For } from "solid-js";
import { markSpans } from "~/lib/format";
import type { Span } from "~/lib/types";

export function Marked(props: { text: string; spans?: Span[]; lit?: boolean; class?: string }) {
  return (
    <span class={props.class}>
      <For each={markSpans(props.text, props.spans)}>
        {(p) => (p.marked ? <mark class="hl-sweep bg-transparent text-inherit" data-lit={props.lit ?? true}>{p.text}</mark> : <>{p.text}</>)}
      </For>
    </span>
  );
}

export function Kbd(props: { children: string; class?: string }) {
  return (
    <kbd
      class={`inline-grid min-w-[20px] place-items-center rounded-[4px] border border-rule-2 bg-card px-1 font-code text-[11px] font-[500] leading-[18px] text-muted ${props.class ?? ""}`}
    >
      {props.children}
    </kbd>
  );
}
