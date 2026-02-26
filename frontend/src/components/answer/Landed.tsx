/**
 * ¶4 Landed cost: Into / Made in switches (Ark SegmentGroup), the shipment (Ark Popover), the stacked bar, the
 * receipt slip and its lettered reasons, the USMCA origin questions (Ark Checkbox) and what could change the total.
 */
import { Checkbox } from "@ark-ui/solid/checkbox";
import { Popover } from "@ark-ui/solid/popover";
import { SegmentGroup } from "@ark-ui/solid/segment-group";
import { For, Show, createEffect, createSignal, on, untrack } from "solid-js";
import { Portal } from "solid-js/web";
import { answers } from "~/lib/endpoints";
import { dateShort, money, subtractMoney } from "~/lib/format";
import { renderableLines, stackSegments } from "~/lib/landed";
import { plainProblem } from "~/lib/problem";
import type { AnswerOut, Country, LandedCostOut, Transport } from "~/lib/types";
import { SkeletonLines } from "~/ui/States";
import { WarnIcon } from "~/ui/Icons";
import { button, floating, segment } from "~/ui/recipes";
import { MemoRow } from "./Memo";
import { TypedRule } from "~/ui/Type";

const ORIGINS = [
  { value: "CN", label: "China" },
  { value: "VN", label: "Vietnam" },
  { value: "MX", label: "Mexico" },
];
const COUNTRY_LABEL: Record<Country, string> = { US: "the US", CA: "Canada" };

function Segmented(props: { label: string; value: string; items: { value: string; label: string }[]; onChange: (v: string) => void; disabled?: boolean }) {
  const s = segment();
  return (
    <SegmentGroup.Root value={props.value} onValueChange={(d) => d.value && props.onChange(d.value)} disabled={props.disabled} class="flex flex-col gap-1.5">
      <SegmentGroup.Label class="text-[13px] font-[700] text-ink-2">{props.label}</SegmentGroup.Label>
      <div class={s.root()}>
        <SegmentGroup.Indicator class={s.indicator()} />
        <For each={props.items}>
          {(it) => (
            <SegmentGroup.Item value={it.value} class={s.item()}>
              <SegmentGroup.ItemText>{it.label}</SegmentGroup.ItemText>
              <SegmentGroup.ItemControl />
              <SegmentGroup.ItemHiddenInput />
            </SegmentGroup.Item>
          )}
        </For>
      </div>
    </SegmentGroup.Root>
  );
}

export function Receipt(props: { cost: LandedCostOut }) {
  const c = () => props.cost;
  const lines = () => renderableLines(c().lines);
  const valuePerUnit = () => ({ amount: (Number(c().value.amount) / Math.max(1, c().quantity)).toFixed(2), currency: c().value.currency });
  return (
    <div class="receipt" role="group" aria-label={`Landed cost receipt, into ${c().countryLabel}`}>
      <p class="text-center text-[15px] font-[700] tracking-[0.12em] underline underline-offset-4">LANDED COST</p>
      <p class="mb-3 text-center text-[12px] text-muted">
        Into {COUNTRY_LABEL[c().country]} · from {c().madeInLabel} · tariffs as of {dateShort(c().tariffsAsOf)}
      </p>
      <div class="grid grid-cols-[18px_1fr_auto] gap-x-2 py-0.5">
        <span />
        <span>Goods, customs value</span>
        <span class="text-right">{money(c().value)}</span>
      </div>
      <TypedRule class="my-2 text-ink" />
      <For each={lines().shown}>
        {(l) => (
          <div class="grid grid-cols-[18px_1fr_auto_auto] gap-x-2 py-0.5">
            <span class="text-muted">{l.letter}</span>
            <span>{l.name}</span>
            <span class="min-w-[56px] text-right text-muted">{l.rate.split(" ")[0]}</span>
            <span class="min-w-[92px] text-right">
              {money(l.amount)}
              <Show when={l.legalStatusOpen}>
                <span class="text-warn" aria-label="legal status open">
                  {" "}⚠
                </span>
              </Show>
            </span>
          </div>
        )}
      </For>
      <For each={c().notApplied}>
        {(n) => (
          <div class="grid grid-cols-[18px_1fr_auto_auto] gap-x-2 py-0.5 text-muted">
            <span>–</span>
            <span>{n.name}</span>
            <span class="min-w-[56px] text-right">n/a</span>
            <span class="min-w-[92px] text-right line-through">{money({ amount: "0.00", currency: c().value.currency })}</span>
          </div>
        )}
      </For>
      <TypedRule class="my-2 text-ink" />
      <div class="flex justify-between text-[16px] font-[700]">
        <span>Charges</span>
        <span>{money(c().chargesTotal)}</span>
      </div>
      <div class="flex justify-between text-ink-2">
        <span>Duties alone</span>
        <span>{c().effectiveRate} of value</span>
      </div>
      <div class="flex justify-between text-ink-2">
        <span>Landed</span>
        <span>{money(c().landedTotal)}</span>
      </div>
      <div class="flex justify-between text-ink-2">
        <span>Per unit</span>
        <span>
          {money(c().perUnit)} (was {money(valuePerUnit())})
        </span>
      </div>
      <p class="mt-3 text-center text-[11.5px] text-muted">⚠ = legal status open · {c().quantity.toLocaleString("en-US")} units, {c().transportLabel.toLowerCase()}</p>
    </div>
  );
}

function StackBar(props: { cost: LandedCostOut }) {
  const segs = () => stackSegments(props.cost);
  return (
    <div>
      <div class="flex h-[46px] w-full gap-[2px]" aria-hidden="true">
        <For each={segs()}>
          {(s) => <span class={`h-full seg-${s.kind}`} style={{ width: `${Math.max(0.4, s.share * 100)}%` }} title={s.label} />}
        </For>
      </div>
      <p class="mt-1 flex justify-between font-code text-[12px] text-muted" aria-hidden="true">
        <span>$0</span>
        <span>goods {money(props.cost.value, { cents: false })}</span>
        <span>landed {money(props.cost.landedTotal, { cents: false })}</span>
      </p>
      <p class="sr-only">
        Goods value {money(props.cost.value)} plus charges {money(props.cost.chargesTotal)} makes {money(props.cost.landedTotal)} landed.
      </p>
    </div>
  );
}

function Reasons(props: { cost: LandedCostOut }) {
  const lines = () => renderableLines(props.cost.lines);
  return (
    <div>
      <ol>
        <For each={lines().shown}>
          {(l) => (
            <li class="grid grid-cols-[22px_minmax(0,1fr)] gap-x-2 border-b border-rule py-3">
              <span class="pt-0.5 font-code text-[13px] text-muted">{l.letter}</span>
              <div>
                <p class="text-[16px] leading-snug">
                  <span class={`mr-2 inline-block h-3 w-3 align-[-1px] seg-${l.kind}`} aria-hidden="true" />
                  <b class="font-[700]">{l.name}.</b> {l.plain}
                </p>
                <p class="mt-1 text-[13.5px] text-muted">
                  Source{" "}
                  <a href={l.sourceUrl} target="_blank" rel="noreferrer" class="font-code text-[12.5px] text-ink-2 underline decoration-rule underline-offset-2 hover:decoration-ink">
                    {l.source}
                  </a>
                  <Show when={l.chapter99}>
                    {" "}· <span class="font-code text-[12.5px]">{l.chapter99}</span>
                  </Show>{" "}
                  · {l.rate} · in force from {dateShort(l.effectiveFrom)}
                  <Show when={l.effectiveTo}> until {dateShort(l.effectiveTo)}</Show>
                </p>
                <Show when={l.legalStatusOpen && l.legalStatus}>
                  <p class="mt-2 inline-flex items-start gap-2 rounded-[var(--radius-btn)] border-[1.5px] border-warn px-2.5 py-1 text-[14px] font-[650] text-warn">
                    <WarnIcon size={15} class="mt-0.5 shrink-0" />
                    {l.legalStatus}. Still collected; the decision is not yet known.
                  </p>
                </Show>
              </div>
            </li>
          )}
        </For>
        <For each={props.cost.notApplied}>
          {(n) => (
            <li class="grid grid-cols-[22px_minmax(0,1fr)] gap-x-2 border-b border-rule py-3 text-[15.5px]">
              <span class="text-muted">–</span>
              <p>
                <b class="font-[700]">{n.name}.</b> <span class="text-ink-2">Does not apply: {n.why}</span>
              </p>
            </li>
          )}
        </For>
      </ol>
      <Show when={lines().refused.length}>
        <p role="note" class="mt-3 text-[14px] text-warn">
          {lines().refused.length} charge{lines().refused.length > 1 ? "s were" : " was"} left out because the source or effective date was missing. Ask your broker before relying on this total.
        </p>
      </Show>
      <Show when={props.cost.whatCouldChange.length}>
        <p class="mt-4 text-[16px] leading-[1.6]">
          <b>What could change this total: </b>
          <For each={props.cost.whatCouldChange}>
            {(w, i) => (
              <>
                {i() > 0 ? "; " : ""}
                {w.label.charAt(0).toLowerCase() + w.label.slice(1)}, charges would be{" "}
                <span class="font-code">{money(w.chargesTotal)}</span>
                <Show when={Number(subtractMoney(w.chargesTotal, props.cost.chargesTotal).amount) < 0}>
                  {" "}(<span class="font-code">{money(subtractMoney(props.cost.chargesTotal, w.chargesTotal))}</span> less)
                </Show>
              </>
            )}
          </For>
          .
        </p>
      </Show>
    </div>
  );
}

function ShipmentPopover(props: { cost: LandedCostOut | null; onApply: (v: { value: string; quantity: number; transport: Transport }) => void; disabled?: boolean }) {
  const initial = untrack(() => props.cost);
  const [value, setValue] = createSignal(initial?.value.amount ?? "12500.00");
  const [qty, setQty] = createSignal(initial?.quantity ?? 1000);
  const [transport, setTransport] = createSignal<Transport>((initial?.transport as Transport) ?? "ocean");
  const [open, setOpen] = createSignal(false);
  return (
    <div class="flex flex-col gap-1.5">
      <span class="text-[13px] font-[700] text-ink-2">Shipment</span>
      <div class="flex flex-wrap items-center gap-2 text-[16.5px]">
        <Show when={props.cost} fallback={<span class="text-muted">No shipment yet</span>}>
          {(c) => (
            <span>
              {c().quantity.toLocaleString("en-US")} units at {money(c().perUnit.currency === c().value.currency ? { amount: (Number(c().value.amount) / Math.max(1, c().quantity)).toFixed(2), currency: c().value.currency } : c().value)} · {c().transportLabel.toLowerCase()}
            </span>
          )}
        </Show>
        <Show when={!props.disabled}>
          <Popover.Root open={open()} onOpenChange={(d) => setOpen(d.open)} positioning={{ placement: "bottom-start", gutter: 8 }}>
            <Popover.Trigger class={button({ tone: "quiet", size: "xs" })}>Change</Popover.Trigger>
            <Portal>
              <Popover.Positioner class="z-50">
                <Popover.Content class={floating({ class: "w-[300px] p-4" })}>
                  <Popover.Title class="ty-sub text-ink">The shipment</Popover.Title>
                  <form
                    class="mt-3 space-y-3"
                    onSubmit={(e) => {
                      e.preventDefault();
                      props.onApply({ value: Number(value()).toFixed(2), quantity: qty(), transport: transport() });
                      setOpen(false);
                    }}
                  >
                    <label class="block text-[13px] font-[650] text-ink-2">
                      Customs value ({props.cost?.value.currency ?? "USD"})
                      <input inputmode="decimal" value={value()} onInput={(e) => setValue(e.currentTarget.value)} class="mt-1 h-10 w-full rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-3 font-code text-[15px] text-ink" />
                    </label>
                    <label class="block text-[13px] font-[650] text-ink-2">
                      Units
                      <input type="number" min="1" value={qty()} onInput={(e) => setQty(Math.max(1, Number(e.currentTarget.value) || 1))} class="mt-1 h-10 w-full rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-3 font-code text-[15px] text-ink" />
                    </label>
                    <label class="block text-[13px] font-[650] text-ink-2">
                      Arrives by
                      <select value={transport()} onChange={(e) => setTransport(e.currentTarget.value as Transport)} class="mt-1 h-10 w-full rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-2 text-[15px] text-ink">
                        <option value="ocean">Ocean freight</option>
                        <option value="air">Air freight</option>
                        <option value="truck">Truck</option>
                        <option value="rail">Rail</option>
                        <option value="courier">Courier</option>
                      </select>
                    </label>
                    <button type="submit" class={button({ size: "sm", class: "w-full" })}>
                      Restack the receipt
                    </button>
                  </form>
                </Popover.Content>
              </Popover.Positioner>
            </Portal>
          </Popover.Root>
        </Show>
      </div>
    </div>
  );
}

export function LandedCost(props: { answer: AnswerOut; live: boolean }) {
  const countries = () => {
    const fromLanded = props.answer.landed.map((l) => l.country);
    const fromQuery = props.answer.query.into;
    return [...new Set([...fromLanded, ...fromQuery])].filter((c) => (c === "US" ? props.answer.us : props.answer.ca));
  };
  const [country, setCountry] = createSignal<Country>(countries()[0] ?? "US");
  const [madeIn, setMadeIn] = createSignal(untrack(() => props.answer.query.madeIn));
  const [usmca, setUsmca] = createSignal<Record<string, boolean>>({});
  const [cost, setCost] = createSignal<LandedCostOut | null>(untrack(() => props.answer.landed.find((l) => l.country === country())) ?? null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  let shipment: { value: string; quantity: number; transport: Transport } | null = null;

  const restack = async () => {
    const code = country() === "US" ? props.answer.us : props.answer.ca;
    const base = cost() ?? props.answer.landed[0] ?? null;
    if (!code) return;
    if (!props.live) {
      setCost(props.answer.landed.find((l) => l.country === country()) ?? null);
      return;
    }
    const value = shipment?.value ?? base?.value.amount ?? props.answer.query.shipment?.value.amount;
    if (!value) return;
    setLoading(true);
    setError("");
    try {
      setCost(
        await answers.landedCost({
          country: country(),
          code: code.code,
          madeIn: madeIn(),
          value: { amount: value, currency: country() === "US" ? "USD" : "CAD" },
          quantity: shipment?.quantity ?? base?.quantity ?? props.answer.query.shipment?.quantity ?? 1,
          transport: shipment?.transport ?? (base?.transport as Transport) ?? props.answer.query.shipment?.transport ?? "ocean",
          usmcaAnswers: usmca(),
        }),
      );
    } catch (e) {
      setError(plainProblem(e).message);
    } finally {
      setLoading(false);
    }
  };

  createEffect(on([country, madeIn, usmca], () => void restack(), { defer: true }));

  return (
    <MemoRow n="¶ 4" label="Landed cost" id="p4" wide note={<span class="italic">each charge on the same value; they add, they don't compound</span>}>
      <div class="max-w-[1160px]">
        <div class="flex flex-wrap items-end gap-x-8 gap-y-4">
          <Show when={countries().length > 1}>
            <Segmented label="Into" value={country()} onChange={(v) => setCountry(v as Country)} items={countries().map((c) => ({ value: c, label: c === "US" ? "the US · Seattle" : "Canada · Vancouver" }))} />
          </Show>
          <Show when={props.live}>
            <Segmented label="Made in" value={madeIn()} onChange={(v) => setMadeIn(v)} items={ORIGINS.some((o) => o.value === madeIn()) ? ORIGINS : [...ORIGINS, { value: madeIn(), label: props.answer.madeInLabel }]} />
          </Show>
          <ShipmentPopover
            cost={cost()}
            disabled={!props.live}
            onApply={(v) => {
              shipment = v;
              void restack();
            }}
          />
        </div>

        <Show when={cost()?.questions.length}>
          <fieldset class="mt-6 rounded-[var(--radius-box)] border-[1.5px] border-ink px-4 py-3.5">
            <legend class="ty-sub px-1 text-ink">Before the USMCA preference: three origin questions</legend>
            <div class="space-y-2.5">
              <For each={cost()!.questions}>
                {(q) => (
                  <Checkbox.Root
                    checked={!!usmca()[q.key]}
                    onCheckedChange={(d) => setUsmca((u) => ({ ...u, [q.key]: d.checked === true }))}
                    class="flex cursor-pointer items-start gap-2.5 text-[15.5px]"
                  >
                    <Checkbox.Control class="mt-1 grid h-[18px] w-[18px] shrink-0 place-items-center rounded-[3px] border-[1.5px] border-ink bg-paper data-[state=checked]:bg-ink data-[state=checked]:text-paper">
                      <Checkbox.Indicator>✓</Checkbox.Indicator>
                    </Checkbox.Control>
                    <Checkbox.Label>{q.question}</Checkbox.Label>
                    <Checkbox.HiddenInput />
                  </Checkbox.Root>
                )}
              </For>
            </div>
            <p class="mt-2 text-[13.5px] text-muted">Yes to all three removes the duties the agreement waives. The broker checks the certification before the claim is made.</p>
          </fieldset>
        </Show>

        <Show when={error()}>
          <p role="alert" class="mt-4 text-[15px] font-[600] text-bad">
            {error()}
          </p>
        </Show>

        <Show
          when={cost()}
          fallback={
            <p class="mt-6 text-[16px] text-ink-2">
              {props.live ? "Add a shipment (value, units and how it arrives) to see every duty it will carry." : "The landed cost appears when the answer has a shipment."}
            </p>
          }
        >
          {(c) => (
            <div aria-busy={loading()} classList={{ "opacity-60": loading() }} class="transition-opacity">
              <div class="mt-6">
                <StackBar cost={c()} />
              </div>
              <div class="mt-6 grid grid-cols-[minmax(0,560px)_minmax(0,1fr)] gap-x-10 gap-y-8 max-lg:grid-cols-1">
                <div>
                  <Show when={!loading()} fallback={<SkeletonLines lines={8} />}>
                    <Receipt cost={c()} />
                  </Show>
                </div>
                <Reasons cost={c()} />
              </div>
            </div>
          )}
        </Show>
      </div>
    </MemoRow>
  );
}
