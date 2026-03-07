/**
 * The decision drawer's body: Facts, Your code and Reason, with the actions in a footer that stays in view.
 * The broker approves, corrects (PinInput + reason + what the next training round will learn) or asks the importer.
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
import { button, checkbox, field, radioCard } from "~/ui/recipes";
import { RulingStatus } from "~/ui/Status";
import { CodeDigits } from "~/ui/Code";
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
  /** The queue row's one-line reason, already shown above the record. */
  detail?: string;
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
  // The correction form stays folded until the broker chooses to correct.
  const [correcting, setCorrecting] = createSignal(false);
  const startCorrecting = () => {
    setCorrecting(true);
    queueMicrotask(() => firstPin?.focus());
  };
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
      if (!correcting()) return startCorrecting();
      if (typed().length === 10 && reason().trim().length >= 10 && reasonKind()) void decide("correct");
      else firstPin?.focus();
    },
    ask: () => props.canDecide && props.onAsk(),
  }));

  const specPhrases = () => r().decidingPhrases.filter((d) => d.source === "spec_sheet").map((d) => d.span);
  const listingPhrases = () => r().decidingPhrases.filter((d) => d.source === "listing").map((d) => d.span);
  const rc = radioCard();
  const ch = checkbox();
  const f = field();
  const quote = "mt-1.5 rounded-[8px] bg-paper-2 px-3.5 py-2.5 text-[14.5px] leading-[1.6] text-ink";

  return (
    <div class="flex min-h-full flex-col" role="region" aria-label={`Decision record for ${r().row.productTitle}`}>
      <div class="flex-1 space-y-8 pb-6">
        <section aria-label="Facts">
          <p class="label">Listing</p>
          <p class={quote}>
            <Marked text={r().listing} spans={listingPhrases()} />
          </p>
          <Show when={r().specSheetFile}>
            <p class="label mt-4 flex flex-wrap items-baseline justify-between gap-2">
              Spec sheet
              <span class="text-[12px] font-[450]">
                {r().specSheetFile}
                {r().uploadedBy ? ` · ${r().uploadedBy}` : ""}
                {r().uploadedAt ? `, ${dateShort(r().uploadedAt!)}` : ""}
              </span>
            </p>
            <p class={quote}>
              <Marked text={r().specSheet} spans={specPhrases()} />
            </p>
          </Show>
          <Show when={r().misread}>
            <p class="mt-3 text-[14px] text-ink-2">{r().misread}</p>
          </Show>
          <Show when={r().rulingChange?.byId && props.detail?.includes(r().rulingChange!.byId!) ? null : r().rulingChange}>
            {(c) => (
              <p class="mt-3 text-[14px]">
                <RulingStatus status={c()} long />
              </p>
            )}
          </Show>
          <Show when={r().rule && !props.detail?.toLowerCase().includes(r().rule!.toLowerCase())}>
            <p class="mt-3 text-[14px] text-ink-2">Always reviewed: {r().rule}</p>
          </Show>
          <Show when={r().questions.length}>
            <div class="mt-4 space-y-3">
              <For each={r().questions}>
                {(q) => (
                  <div class="text-[14px]">
                    <p>
                      <span class="font-[600]">{q.askedBy}</span>: “{q.text}”
                    </p>
                    <Show when={q.answer} fallback={<p class="mt-0.5 text-warn">Waiting for {props.importerName}</p>}>
                      <p class="mt-0.5">
                        <span class="font-[600]">{q.answeredBy}</span>: “{q.answer}”
                      </p>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </section>

        <section aria-label="The code">
          <Show when={!correcting()}>
          <p class="label">Proposed</p>
          <div class="mt-2 grid grid-cols-2 gap-4 max-sm:grid-cols-1">
            <Show when={r().row.proposedUs}>
              {(c) => (
                <div>
                  <p class="text-[12px] text-muted">United States</p>
                  <CodeDigits code={c().code} size="lg" leaning={c().leaning} />
                </div>
              )}
            </Show>
            <Show when={r().row.proposedCa}>
              {(c) => (
                <div>
                  <p class="text-[12px] text-muted">Canada</p>
                  <CodeDigits code={c().code} size="lg" leaning={c().leaning} />
                </div>
              )}
            </Show>
          </div>
          </Show>
          <Show when={r().rulingsRelied.length && !correcting()}>
            <p class="mt-3 flex flex-wrap items-center gap-1.5 text-[13px] text-muted">
              {r().rulingChange ? "Now supported by" : "Relied on"}
              <For each={r().rulingsRelied}>{(x) => <span class="rounded-full bg-paper-2 px-2 py-0.5 font-code text-[12px] text-ink-2">{x.id}</span>}</For>
            </p>
          </Show>
          <Show when={props.canDecide && correcting()}>
            <div class="mt-5">
              <CodePins proposed={proposed()} value={pins()} onChange={setPins} invalid={!!errors().code} describedBy="pin-help" ref={(el) => (firstPin = el)} />
              <p id="pin-help" class="mt-2 text-[12.5px]" classList={{ "text-bad font-[600]": !!errors().code, "text-muted": !errors().code }}>
                {errors().code ?? "Type or paste ten digits."}
              </p>
            </div>
            <Show when={typed().length === 10 && digitsOf(proposed()) !== typed()}>
              <div class="mt-3 space-y-1 text-[14px]">
                <p class="text-muted line-through">{r().row.proposedUs?.text ?? r().row.proposedCa?.text}</p>
                <p>{line()?.line.fullText ?? (line.loading ? "Looking up that line…" : "That line isn't in the tariff in force.")}</p>
              </div>
            </Show>
            <Show when={r().row.proposedUs && r().row.into !== "US"}>
              <Checkbox.Root checked={alsoCa()} onCheckedChange={(d) => setAlsoCa(d.checked === true)} class={`${ch.root()} mt-3`}>
                <Checkbox.Control class={ch.control()}>
                  <Checkbox.Indicator>✓</Checkbox.Indicator>
                </Checkbox.Control>
                <Checkbox.Label>
                  Also change Canada
                  <Show when={typed().length === 10}>
                    {" "}to <span class="font-code">{canadaFor(typed())}</span>
                  </Show>
                </Checkbox.Label>
                <Checkbox.HiddenInput />
              </Checkbox.Root>
            </Show>
          </Show>
        </section>

        <section aria-label="Reason">
          <Show
            when={props.canDecide && correcting()}
            fallback={
              <Show when={!props.canDecide && props.canAnswer && r().questions.some((q) => !q.answer)}>
                <form
                  class="space-y-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void sendAnswer();
                  }}
                >
                  <label for="answer-box" class={f.label()}>
                    Your answer
                  </label>
                  <textarea id="answer-box" value={answer()} onInput={(e) => setAnswer(e.currentTarget.value)} class={f.textarea()} />
                  <button type="submit" class={button({ size: "sm" })} disabled={busy() === "answer"}>
                    Send the answer
                  </button>
                </form>
              </Show>
            }
          >
            <p class="label">Reason</p>
            <RadioGroup.Root value={reasonKind() ?? undefined} onValueChange={(d) => setReasonKind(d.value as ReasonKind)} class={`${rc.root()} mt-2`} aria-invalid={!!errors().reasonKind}>
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
            <label for={`reason-${r().row.id}`} class="sr-only">
              Reason (required for a correction)
            </label>
            <textarea
              ref={reasonBox}
              id={`reason-${r().row.id}`}
              value={reason()}
              onInput={(e) => setReason(e.currentTarget.value)}
              aria-invalid={!!errors().reason}
              aria-describedby={errors().reason ? `reason-err-${r().row.id}` : undefined}
              placeholder="What the facts or the ruling show…"
              class={`${f.textarea()} mt-2.5`}
            />
            <Show when={errors().reason}>
              <p id={`reason-err-${r().row.id}`} class="mt-1 text-[13px] font-[600] text-bad">
                {errors().reason}
              </p>
            </Show>
            <Show when={lesson()}>
              <div class="mt-3 rounded-[8px] bg-hi-soft px-3.5 py-2.5">
                <p class="text-[12.5px] font-[600] text-ink-2">Next round learns</p>
                <p class="mt-0.5 text-[14px] leading-[1.55]" aria-live="polite">
                  {lesson()}
                </p>
              </div>
            </Show>
          </Show>
        </section>
        <Show when={errors().form}>
          <p role="alert" class="text-[14px] font-[600] text-bad">
            {errors().form}
          </p>
        </Show>
      </div>
      <Show when={props.canDecide}>
        <footer class="sticky bottom-0 -mx-6 -mb-5 flex flex-wrap items-center gap-2 border-t border-rule bg-card px-6 py-3.5 max-sm:-mx-4 max-sm:px-4">
          <Show
            when={correcting()}
            fallback={
              <>
                <button type="button" class={button({ tone: "ghost", size: "md" })} onClick={() => props.onAsk()}>
                  Ask <Kbd>Q</Kbd>
                </button>
                <button type="button" class={button({ tone: "outline", size: "md", class: "ml-auto" })} onClick={startCorrecting}>
                  Correct <Kbd>C</Kbd>
                </button>
                <button type="button" class={button({ size: "md" })} disabled={!!busy()} onClick={() => void decide("approve")}>
                  {busy() === "approve" ? "Approving…" : "Approve"} <Kbd class="border-white/30 bg-transparent text-card/80">A</Kbd>
                </button>
              </>
            }
          >
            <button type="button" class={button({ tone: "ghost", size: "md" })} onClick={() => setCorrecting(false)}>
              Cancel
            </button>
            <button type="button" class={button({ size: "md", class: "ml-auto" })} disabled={!!busy()} onClick={() => void decide("correct")}>
              {busy() === "correct" ? "Saving…" : "Save correction"} <Kbd class="border-white/30 bg-transparent text-card/80">C</Kbd>
            </button>
          </Show>
        </footer>
      </Show>
    </div>
  );
}
