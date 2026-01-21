/**
 * The open docket row unfolds into a decision record in three bands: Facts · The code · Reason. The broker
 * approves, corrects (PinInput + reason + what the next training round will learn) or asks the importer.
 */
import { RadioGroup } from "@ark-ui/solid/radio-group";
import { Checkbox } from "@ark-ui/solid/checkbox";
import { For, Show, createEffect, createResource, createSignal, on, onCleanup, onMount } from "solid-js";
import { checkCorrection, canadaFor } from "~/lib/docket";
import { review, tariff } from "~/lib/endpoints";
import { dateShort, digitsOf, groupCode } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import type { DecisionOut, DecisionRecord as Record_, ReasonKind } from "~/lib/types";
import { Kbd, Marked } from "~/ui/Marked";
import { button, radioCard } from "~/ui/recipes";
import { RulingStatus } from "~/ui/Status";
import { CodePins } from "./CodePins";

const REASONS: { value: ReasonKind; label: string }[] = [
  { value: "facts_differ", label: "The product facts differ" },
  { value: "ruling_elsewhere", label: "A ruling points elsewhere" },
  { value: "heading_misread", label: "A heading was read wrongly" },
];

export interface RecordHandle {
  approve: () => void;
  correct: () => void;
  ask: () => void;
}

export function DecisionRecordView(props: {
  record: Record_;
  canDecide: boolean;
  canAnswer: boolean;
  importerName: string;
  onDecided: (d: DecisionOut) => void;
  onAsk: () => void;
  onConflict: (message: string) => void;
  handle: (h: RecordHandle) => void;
}) {
  const r = () => props.record;
  const proposed = () => r().row.proposedUs?.code ?? r().row.proposedCa?.code ?? "";
  const [pins, setPins] = createSignal<string[]>(Array(10).fill(""));
  const [reasonKind, setReasonKind] = createSignal<ReasonKind | null>(null);
  const [reason, setReason] = createSignal("");
  const [alsoCa, setAlsoCa] = createSignal(true);
  const [errors, setErrors] = createSignal<Record<string, string>>({});
  const [busy, setBusy] = createSignal<string | null>(null);
  const [answer, setAnswer] = createSignal("");
  let firstPin: HTMLInputElement | undefined;
  let reasonBox: HTMLTextAreaElement | undefined;

  const typed = () => pins().join("");
  const [line] = createResource(
    () => (typed().length === 10 ? { code: typed(), country: (r().row.proposedUs ? "US" : "CA") as "US" | "CA" } : null),
    (k) => tariff.line(k.country, k.code).catch(() => null),
  );

  // What the next training round will learn, refreshed as the broker types (no side effects on the server).
  const [lesson, setLesson] = createSignal("");
  let timer: ReturnType<typeof setTimeout> | undefined;
  createEffect(
    on([typed, reasonKind, reason], ([code, kind, why]) => {
      clearTimeout(timer);
      if (!props.canDecide || !kind || (code.length < 10 && why.trim().length < 10)) return;
      timer = setTimeout(async () => {
        try {
          const out = await review.lesson(r().row.id, { usCode: code.length === 10 ? groupCode(code) : undefined, reasonKind: kind, reason: why });
          setLesson(out.lesson);
        } catch {
          /* the preview is a convenience; the decision itself reports errors */
        }
      }, 450);
    }, { defer: true }),
  );
  onCleanup(() => clearTimeout(timer));

  const decide = async (verb: "approve" | "correct") => {
    setErrors({});
    if (verb === "correct") {
      const check = checkCorrection({ proposed: proposed(), pins: pins(), reasonKind: reasonKind(), reason: reason(), alsoChangeCa: alsoCa() });
      if (!check.ok) {
        setErrors(check.errors as Record<string, string>);
        if (check.errors.code) firstPin?.focus();
        else reasonBox?.focus();
        return;
      }
    }
    setBusy(verb);
    try {
      const out =
        verb === "approve"
          ? await review.approve(r().row.id)
          : await review.correct(r().row.id, {
              usCode: r().row.proposedUs ? groupCode(typed()) : undefined,
              caCode: !r().row.proposedUs ? groupCode(typed()) : alsoCa() ? canadaFor(typed()) : undefined,
              reasonKind: reasonKind()!,
              reason: reason().trim(),
              alsoChangeCa: !!r().row.proposedUs && alsoCa(),
            });
      props.onDecided(out);
    } catch (e) {
      const p = plainProblem(e);
      if (p.code === "already_decided") props.onConflict(p.message);
      else setErrors({ ...Object.fromEntries(Object.entries(p.fields).map(([k, v]) => [k === "usCode" || k === "caCode" ? "code" : k, v])), form: Object.keys(p.fields).length ? "" : p.message });
    } finally {
      setBusy(null);
    }
  };

  const sendAnswer = async () => {
    if (!answer().trim()) return;
    setBusy("answer");
    try {
      props.onDecided(await review.answer(r().row.id, answer().trim()));
    } catch (e) {
      setErrors({ form: plainProblem(e).message });
    } finally {
      setBusy(null);
    }
  };

  onMount(() => props.handle({
    approve: () => props.canDecide && void decide("approve"),
    correct: () => {
      if (!props.canDecide) return;
      if (typed().length === 10 && reason().trim().length >= 10 && reasonKind()) void decide("correct");
      else firstPin?.focus();
    },
    ask: () => props.canDecide && props.onAsk(),
  }));

  const specPhrases = () => r().decidingPhrases.filter((d) => d.source === "spec_sheet").map((d) => d.span);
  const listingPhrases = () => r().decidingPhrases.filter((d) => d.source === "listing").map((d) => d.span);
  const rc = radioCard();

  return (
    <div class="border-y border-rule bg-paper-2 anim-drawer" role="region" aria-label={`Decision record for ${r().row.productTitle}`}>
      <div class="grid grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,1fr)] max-xl:grid-cols-2 max-md:grid-cols-1">
        <section class="border-r border-rule px-6 py-5 max-md:border-r-0 max-md:border-b max-md:px-4" aria-label="Facts">
          <h3 class="text-[13px] font-[750] uppercase tracking-[0.08em] text-ink-2">Facts</h3>
          <p class="mt-3 text-[14px] text-muted">Listing says</p>
          <p class="font-law text-[17px] leading-[1.5]">
            “<Marked text={r().listing} spans={listingPhrases()} />”
          </p>
          <Show when={r().specSheetFile}>
            <p class="mt-4 text-[14px] text-muted">Spec sheet says</p>
            <p class="font-law text-[17px] leading-[1.5]">
              “<Marked text={r().specSheet} spans={specPhrases()} />”
            </p>
            <p class="mt-1 text-[13.5px] text-muted">
              {r().specSheetFile}
              {r().uploadedBy ? ` · uploaded by ${r().uploadedBy}` : ""}
              {r().uploadedAt ? `, ${dateShort(r().uploadedAt!)}` : ""}
            </p>
          </Show>
          <Show when={r().misread}>
            <p class="mt-4 text-[16px] leading-[1.55]">{r().misread}</p>
          </Show>
          <Show when={r().rulingChange}>
            {(c) => (
              <p class="mt-4 text-[15px]">
                <RulingStatus status={c()} long />
              </p>
            )}
          </Show>
          <Show when={r().rule}>
            <p class="mt-4 text-[15px]">
              <b>Always reviewed:</b> {r().rule}
            </p>
          </Show>
          <Show when={r().questions.length}>
            <div class="mt-4 border-t border-rule pt-3">
              <For each={r().questions}>
                {(q) => (
                  <div class="mb-3 text-[15px]">
                    <p>
                      <b>{q.askedBy}</b> asked: “{q.text}”
                    </p>
                    <Show when={q.answer} fallback={<p class="text-warn">Waiting for {props.importerName}'s answer.</p>}>
                      <p>
                        <b>{q.answeredBy}</b> answered: “{q.answer}”
                      </p>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </section>

        <section class="border-r border-rule px-6 py-5 max-xl:border-r-0 max-md:border-b max-md:px-4" aria-label="The code">
          <h3 class="text-[13px] font-[750] uppercase tracking-[0.08em] text-ink-2">The code</h3>
          <Show
            when={props.canDecide}
            fallback={
              <p class="mt-3 font-code text-[22px] font-[600]">
                {proposed()} <span class="block font-voice text-[14px] font-[400] text-muted">proposed; a licensed broker decides</span>
              </p>
            }
          >
            <div class="mt-3">
              <CodePins proposed={proposed()} value={pins()} onChange={setPins} invalid={!!errors().code} describedBy="pin-help" ref={(el) => (firstPin = el)} />
              <p id="pin-help" class="mt-2 text-[13px]" classList={{ "text-bad font-[600]": !!errors().code, "text-muted": !errors().code }}>
                {errors().code ?? "Type or paste your ten digits; the dots are automatic."}
              </p>
            </div>
            <div class="mt-3 space-y-1 text-[15.5px]">
              <Show when={typed().length === 10 && digitsOf(proposed()) !== typed()}>
                <p class="font-law text-muted line-through">{r().row.proposedUs?.text ?? r().row.proposedCa?.text}</p>
                <p class="font-law">{line()?.line.fullText ?? (line.loading ? "Looking up that line…" : "That line wasn't found in the tariff in force.")}</p>
              </Show>
            </div>
            <Show when={r().row.proposedUs && r().row.into !== "US"}>
              <Checkbox.Root checked={alsoCa()} onCheckedChange={(d) => setAlsoCa(d.checked === true)} class="mt-3 flex cursor-pointer items-center gap-2.5 text-[15px]">
                <Checkbox.Control class="grid h-[18px] w-[18px] place-items-center rounded-[3px] border-[1.5px] border-ink bg-paper data-[state=checked]:bg-ink data-[state=checked]:text-paper">
                  <Checkbox.Indicator>✓</Checkbox.Indicator>
                </Checkbox.Control>
                <Checkbox.Label>
                  Also change Canada to <span class="font-code">{typed().length === 10 ? canadaFor(typed()) : "the matching item"}</span>
                </Checkbox.Label>
                <Checkbox.HiddenInput />
              </Checkbox.Root>
            </Show>
            <Show when={r().rulingsRelied.length}>
              <p class="mt-3 text-[15px] text-muted">
                Relied on{" "}
                <For each={r().rulingsRelied}>
                  {(x) => <span class="ml-1 rounded-[var(--radius-btn)] border-[1.5px] border-ink px-2 py-0.5 font-code text-[13px] font-[650] text-ink">{x.id}</span>}
                </For>
              </p>
            </Show>
          </Show>
        </section>

        <section class="px-6 py-5 max-xl:col-span-2 max-xl:border-t max-xl:border-rule max-md:col-span-1 max-md:px-4" aria-label="Reason">
          <h3 class="text-[13px] font-[750] uppercase tracking-[0.08em] text-ink-2">Reason</h3>
          <Show
            when={props.canDecide}
            fallback={
              <Show when={props.canAnswer && r().questions.some((q) => !q.answer)} fallback={<p class="mt-3 text-[15.5px] text-ink-2">{r().row.detail}</p>}>
                <form
                  class="mt-3 space-y-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void sendAnswer();
                  }}
                >
                  <label for="answer-box" class="text-[14px] font-[650]">
                    Your answer to the broker
                  </label>
                  <textarea id="answer-box" value={answer()} onInput={(e) => setAnswer(e.currentTarget.value)} class="min-h-[90px] w-full rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper px-3 py-2 text-[15.5px]" />
                  <button type="submit" class={button({ size: "sm" })} disabled={busy() === "answer"}>
                    Send the answer
                  </button>
                </form>
              </Show>
            }
          >
            <RadioGroup.Root value={reasonKind() ?? undefined} onValueChange={(d) => setReasonKind(d.value as ReasonKind)} class={`${rc.root()} mt-3`} aria-invalid={!!errors().reasonKind}>
              <RadioGroup.Label class="sr-only">What kind of correction</RadioGroup.Label>
              <For each={REASONS}>
                {(o) => (
                  <RadioGroup.Item value={o.value} class={rc.item()}>
                    <RadioGroup.ItemControl class={rc.control()} />
                    <RadioGroup.ItemText>{o.label}</RadioGroup.ItemText>
                    <RadioGroup.ItemHiddenInput />
                  </RadioGroup.Item>
                )}
              </For>
            </RadioGroup.Root>
            <Show when={errors().reasonKind}>
              <p class="mt-1 text-[13px] font-[600] text-bad">{errors().reasonKind}</p>
            </Show>
            <label for={`reason-${r().row.id}`} class="mt-3 block text-[13px] font-[650] text-ink-2">
              Reason (required for a correction)
            </label>
            <textarea
              ref={reasonBox}
              id={`reason-${r().row.id}`}
              value={reason()}
              onInput={(e) => setReason(e.currentTarget.value)}
              aria-invalid={!!errors().reason}
              aria-describedby={errors().reason ? `reason-err-${r().row.id}` : undefined}
              placeholder="Spec sheet says air-insulated, not vacuum-sealed…"
              class="mt-1 min-h-[96px] w-full rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper px-3 py-2 text-[15.5px] leading-[1.5]"
            />
            <Show when={errors().reason}>
              <p id={`reason-err-${r().row.id}`} class="mt-1 text-[13px] font-[600] text-bad">
                {errors().reason}
              </p>
            </Show>
            <div class="mt-4 border-l-[3px] border-ink pl-4">
              <p class="text-[12.5px] font-[750] uppercase tracking-[0.08em] text-ink-2">The next training round will learn</p>
              <p class="mt-1 text-[15.5px] leading-[1.55]" aria-live="polite">
                {lesson() || "Type your code and a reason; the lesson it teaches appears here."}
              </p>
            </div>
          </Show>
        </section>
      </div>
      <Show when={errors().form}>
        <p role="alert" class="px-6 pb-2 text-[14.5px] font-[600] text-bad">
          {errors().form}
        </p>
      </Show>
      <Show when={props.canDecide}>
        <footer class="flex flex-wrap items-center gap-3 border-t border-rule px-6 py-3.5 max-md:px-4">
          <button type="button" class={button({ tone: "ghost", size: "md" })} disabled={!!busy()} onClick={() => void decide("approve")}>
            Approve as proposed <Kbd>A</Kbd>
          </button>
          <button type="button" class={button({ tone: "ghost", size: "md" })} onClick={() => props.onAsk()}>
            Ask {props.importerName} a question <Kbd>Q</Kbd>
          </button>
          <span class="ml-auto text-[14px] text-muted max-md:ml-0 max-md:w-full">Recorded in the binder with your name and licence</span>
          <button type="button" class={button({ size: "md" })} disabled={!!busy()} onClick={() => void decide("correct")}>
            {busy() === "correct" ? "Saving…" : "Save correction"} <Kbd>C</Kbd>
          </button>
        </footer>
      </Show>
    </div>
  );
}
