/**
 * The holding band (full bleed, paper-2): gutter label and the large compass (Settle or Waver), the US and Canada
 * code cards, the verdict with the ruling-agreement bar, the holding sentence and the actions.
 */
import { Clipboard } from "@ark-ui/solid/clipboard";
import { For, Show, type JSX } from "solid-js";
import { dateWithDay } from "~/lib/format";
import type { AnswerOut, CodeOut } from "~/lib/types";
import { CodeDigits } from "~/ui/Code";
import { CompassMark } from "~/ui/Compass";
import { AskIcon, OkIcon } from "~/ui/Icons";
import { WithCodes } from "./Memo";

function CodeCard(props: { code: CodeOut; source: string; lock: boolean }) {
  return (
    <div class="min-w-0">
      <p class="flex items-center gap-2 text-[14.5px] font-[700] text-ink-2">
        <span class="rounded-[3px] border-[1.5px] border-ink px-1 font-code text-[11.5px] font-[650] text-ink">{props.code.country}</span>
        {props.code.countryLabel} · {props.source}
        <Show when={props.code.leaning}>
          <span class="font-[550] italic text-warn">leaning</span>
        </Show>
      </p>
      <div class="mt-2">
        <CodeDigits code={props.code.code} leaning={props.code.leaning} lock={props.lock} size="xl" />
      </div>
      <p class="mt-2 max-w-[400px] font-law text-[16.5px] leading-snug text-ink-2">{props.code.text}</p>
      <Clipboard.Root value={props.code.code} class="mt-1.5">
        <Clipboard.Trigger class="text-[13px] text-muted underline decoration-rule underline-offset-4 hover:text-ink" aria-label={`Copy ${props.code.code}`}>
          <Clipboard.Indicator copied={<span>Copied</span>}>Copy code</Clipboard.Indicator>
        </Clipboard.Trigger>
      </Clipboard.Root>
    </div>
  );
}

export function HoldingBand(props: { answer: AnswerOut; actions?: JSX.Element; lock?: boolean }) {
  const a = () => props.answer;
  const strong = () => a().verdict.word === "strong";
  const bearing = () => (strong() ? 32 : 18);
  return (
    <section aria-labelledby="holding-h" class="border-b border-rule bg-paper-2" data-rise>
      <div class="gm py-9 max-md:py-6">
        <div class="gl">
          <span>Answer · {dateWithDay(a().createdAt)}</span>
          <h2 id="holding-h" class="not-italic">
            <b>Holding</b>
          </h2>
          <span class="gl-extra mt-5 block text-ink">
            <CompassMark size={92} bearing={bearing()} state={strong() ? "settle" : "waver"} title={strong() ? "The needle has settled" : "The needle wavers between two headings"} />
          </span>
        </div>
        <div class="gm-wide">
          <div class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(240px,0.9fr)] gap-x-8 gap-y-7 max-xl:grid-cols-2 max-md:grid-cols-1">
            <Show when={a().us}>{(c) => <CodeCard code={c()} source="HTSUS" lock={!!props.lock} />}</Show>
            <Show when={a().ca}>{(c) => <CodeCard code={c()} source="Customs Tariff" lock={!!props.lock} />}</Show>
            <div class="border-l-[1.5px] border-ink pl-8 max-xl:col-span-2 max-xl:border-l-0 max-xl:border-t max-xl:border-rule max-xl:pl-0 max-xl:pt-5 max-md:col-span-1">
              <p class="flex items-center gap-2 text-[19px] font-[750]" classList={{ "text-ok": strong(), "text-warn": !strong() }}>
                {strong() ? <OkIcon size={20} /> : <AskIcon size={20} />}
                {a().verdict.wordLabel}
              </p>
              <p class="mt-2.5 text-[16px] leading-[1.55] text-ink-2">{a().verdict.sentence}</p>
              <div class="mt-5" aria-label={`Rulings reaching the same heading: ${a().verdict.agreeing} of ${a().verdict.cited}`}>
                <div class="flex gap-[3px]" aria-hidden="true">
                  <For each={a().verdict.agreementBar}>
                    {(s) => (
                      <span
                        class="h-[9px] flex-1 rounded-[1px]"
                        classList={{ "bg-ink": s.kind === "same", "border-[1.5px] border-dashed border-muted": s.kind !== "same" }}
                      />
                    )}
                  </For>
                </div>
                <p class="mt-1.5 flex justify-between gap-3 text-[14px] text-muted">
                  Rulings reaching the same heading
                  <span class="font-code font-[650] text-ink">
                    {a().verdict.agreeing} of {a().verdict.cited}
                  </span>
                </p>
              </div>
              <Show when={a().alternative}>
                {(alt) => (
                  <p class="mt-4 border-t border-rule pt-3 text-[15px]">
                    <span class="font-[700]">Also possible: </span>
                    <CodeDigits code={alt().code.code} leaning size="sm" />, {alt().condition}.
                    <Show when={alt().dutyAtStake}>
                      <span class="block text-[14px] text-muted">Duty at stake: {alt().dutyAtStake}</span>
                    </Show>
                  </p>
                )}
              </Show>
            </div>
          </div>
          <p class="mt-8 max-w-[1040px] text-[21px] leading-[1.5] max-md:text-[18px]">
            <WithCodes text={a().holdingSentence} />
          </p>
          <Show when={props.actions}>
            <div class="mt-6 flex flex-wrap items-center gap-3">{props.actions}</div>
          </Show>
        </div>
      </div>
    </section>
  );
}
