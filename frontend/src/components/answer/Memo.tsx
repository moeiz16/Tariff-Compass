/** A memo row: gutter label (¶ number + small-caps heading) and the body on the measure. */
import type { JSX } from "solid-js";

export function MemoRow(props: { n?: string; label: string; note?: JSX.Element; id?: string; wide?: boolean; children: JSX.Element; class?: string }) {
  return (
    <section id={props.id} aria-labelledby={props.id ? `${props.id}-h` : undefined} class={`gm border-b border-rule py-9 max-md:py-7 ${props.class ?? ""}`} data-rise>
      <div class="gl">
        {props.n ? <span>{props.n}</span> : null}
        <h2 id={props.id ? `${props.id}-h` : undefined} class="not-italic">
          <b>{props.label}</b>
        </h2>
        {props.note ? <span class="gl-extra block">{props.note}</span> : null}
      </div>
      <div class={props.wide ? "gm-wide" : "gm-body"}>{props.children}</div>
    </section>
  );
}

/** Text with ten-digit codes set in mono ("…subheading 9617.00.10.00, HTSUS…"). */
export function WithCodes(props: { text: string }) {
  const parts = () => props.text.split(/(\d{4}\.\d{2}(?:\.\d{2}){0,2})/g);
  return (
    <>
      {parts().map((p, i) => (i % 2 === 1 ? <span class="font-code text-[0.94em]">{p}</span> : p))}
    </>
  );
}
