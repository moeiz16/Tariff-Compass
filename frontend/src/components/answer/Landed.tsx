/**
 * Landed cost: Into / Made in switches (Ark SegmentGroup), the shipment (Ark Popover), three totals, one stacked bar
 * and the charge lines. A line's source, Chapter 99 number, dates and legal status open from its info button.
 * Charges that don't apply, the USMCA questions and what could change the total stay folded until needed.
 */
import { Checkbox } from "@ark-ui/solid/checkbox";
import { Collapsible } from "@ark-ui/solid/collapsible";
import { Popover } from "@ark-ui/solid/popover";
import { SegmentGroup } from "@ark-ui/solid/segment-group";
import { For, Show, createEffect, createSignal, on, untrack } from "solid-js";
import { Portal } from "solid-js/web";
import { answers } from "~/lib/endpoints";
import { dateShort, money, subtractMoney } from "~/lib/format";
import { renderableLines, stackSegments } from "~/lib/landed";
import { plainProblem } from "~/lib/problem";
import type { AnswerOut, Country, LandedCostOut, LayerLineOut, Transport } from "~/lib/types";
import { ChevronIcon, InfoIcon, WarnIcon } from "~/ui/Icons";
import { button, checkbox, floating, segment } from "~/ui/recipes";
import { SkeletonLines } from "~/ui/States";

const ORIGINS = [
  { value: "CN", label: "China" },
  { value: "VN", label: "Vietnam" },
  { value: "MX", label: "Mexico" },
];

function Segmented(props: { label: string; value: string; items: { value: string; label: string }[]; onChange: (v: string) => void; disabled?: boolean }) {
  const s = segment();
  return (
    <SegmentGroup.Root value={props.value} onValueChange={(d) => d.value && props.onChange(d.value)} disabled={props.disabled} class="flex items-center gap-2">
      <SegmentGroup.Label class="text-[12.5px] font-[550] text-muted">{props.label}</SegmentGroup.Label>
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

/** Where a charge comes from: source, Chapter 99 number, rate, dates and any open legal question. */
function LineSource(props: { line: LayerLineOut }) {
  const l = () => props.line;
  return (
    <Popover.Root positioning={{ placement: "bottom-end", gutter: 6 }}>
      <Popover.Trigger class="grid h-6 w-6 place-items-center rounded-full text-muted hover:bg-paper-2 hover:text-ink" aria-label={`Where ${l().name} comes from`}>
        <InfoIcon size={14} />
      </Popover.Trigger>
      <Portal>
        <Popover.Positioner class="z-50">
          <Popover.Content class={floating({ class: "w-[min(340px,90vw)] p-4 text-[13.5px]" })}>
            <Popover.Title class="font-[600] text-ink">{l().name}</Popover.Title>
            <Popover.Description class="mt-1 text-ink-2">{l().plain}</Popover.Description>
            <dl class="mt-3 grid grid-cols-[88px_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-[13px]">
              <dt class="text-muted">Source</dt>
              <dd>
                <a href={l().sourceUrl} target="_blank" rel="noreferrer" class="font-code text-[12.5px] underline decoration-rule-2 underline-offset-2 hover:decoration-ink">
                  {l().source}
                </a>
              </dd>
              <Show when={l().chapter99}>
                <dt class="text-muted">Chapter 99</dt>
                <dd class="font-code text-[12.5px]">{l().chapter99}</dd>
              </Show>
              <dt class="text-muted">Rate</dt>
              <dd>{l().rate}</dd>
              <dt class="text-muted">In force</dt>
              <dd>
                from {dateShort(l().effectiveFrom)}
                <Show when={l().effectiveTo}> until {dateShort(l().effectiveTo)}</Show>
              </dd>
            </dl>
            <Show when={l().legalStatusOpen && l().legalStatus}>
              <p class="mt-3 flex items-start gap-2 rounded-[8px] bg-warn-soft px-2.5 py-2 text-[12.5px] text-warn">
                <WarnIcon size={14} class="mt-0.5 shrink-0" />
                <span>{l().legalStatus}. Still collected; the decision is not yet known.</span>
              </p>
            </Show>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
}

/** The charge lines: name, rate and amount, each with its source behind an info button. */
export function Receipt(props: { cost: LandedCostOut }) {
  const c = () => props.cost;
  const lines = () => renderableLines(c().lines);
  return (
    <div role="group" aria-label={`Landed cost receipt, into ${c().countryLabel}`}>
      <div class="grid grid-cols-[minmax(0,1fr)_auto_auto_24px] items-center gap-x-4 border-b border-rule py-2 text-[14.5px]">
        <span class="text-muted">Goods, customs value</span>
        <span />
        <span class="font-code">{money(c().value)}</span>
        <span />
      </div>
      <For each={lines().shown}>
        {(l) => (
          <div class="grid grid-cols-[minmax(0,1fr)_auto_auto_24px] items-center gap-x-4 border-b border-rule py-2 text-[14.5px]">
            <span class="flex min-w-0 items-center gap-2.5">
              <span class={`inline-block h-2.5 w-2.5 shrink-0 rounded-[3px] seg-${l.kind}`} aria-hidden="true" />
              <span class="truncate">{l.name}</span>
            </span>
            <span class="font-code text-[13px] text-muted">{l.rate.split(" ")[0]}</span>
            <span class="font-code">
              {money(l.amount)}
              <Show when={l.legalStatusOpen}>
                <span class="ml-1 text-warn" aria-label="legal status open" title="Legal status open">
                  ⚠
                </span>
              </Show>
            </span>
            <LineSource line={l} />
          </div>
        )}
      </For>
      <Show when={c().notApplied.length}>
        <Collapsible.Root lazyMount>
          <Collapsible.Trigger class="group flex items-center gap-1.5 py-2 text-[13px] text-muted hover:text-ink">
            {c().notApplied.length} don't apply
            <ChevronIcon size={13} class="transition-transform group-data-[state=open]:rotate-180" />
          </Collapsible.Trigger>
          <Collapsible.Content class="fold">
            <For each={c().notApplied}>
              {(n) => (
                <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 border-b border-rule py-1.5 text-[13.5px] text-muted last:border-b-0">
                  <span>
                    <span class="text-ink-2">{n.name}</span> · {n.why}
                  </span>
                  <span class="font-code line-through">{money({ amount: "0.00", currency: c().value.currency })}</span>
                </div>
              )}
            </For>
          </Collapsible.Content>
        </Collapsible.Root>
      </Show>
      <Show when={lines().refused.length}>
        <p role="note" class="mt-2 text-[13px] text-warn">
          {lines().refused.length} charge{lines().refused.length > 1 ? "s" : ""} left out: no source or date. Check with your broker.
        </p>
      </Show>
    </div>
  );
}

function Totals(props: { cost: LandedCostOut }) {
  const c = () => props.cost;
  const stat = "min-w-0";
  return (
    <dl class="grid grid-cols-3 gap-4 max-sm:grid-cols-2">
      <div class={stat}>
        <dt class="text-[12.5px] font-[550] text-muted">Duties and fees</dt>
        <dd class="mt-0.5 font-code text-[24px] font-[500] tracking-[-0.02em]">{money(c().chargesTotal)}</dd>
        <dd class="text-[12.5px] text-muted">Duties alone {c().effectiveRate}</dd>
      </div>
      <div class={stat}>
        <dt class="text-[12.5px] font-[550] text-muted">Landed</dt>
        <dd class="mt-0.5 font-code text-[24px] font-[500] tracking-[-0.02em] text-ink-2">{money(c().landedTotal)}</dd>
      </div>
      <div class={stat}>
        <dt class="text-[12.5px] font-[550] text-muted">Per unit</dt>
        <dd class="mt-0.5 font-code text-[24px] font-[500] tracking-[-0.02em] text-ink-2">{money(c().perUnit)}</dd>
      </div>
    </dl>
  );
}

function StackBar(props: { cost: LandedCostOut }) {
  const segs = () => stackSegments(props.cost);
  return (
    <div>
      <div class="flex h-3 w-full gap-[2px] overflow-hidden rounded-full" aria-hidden="true">
        <For each={segs()}>{(s) => <span class={`h-full seg-${s.kind}`} style={{ width: `${Math.max(0.5, s.share * 100)}%` }} title={s.label} />}</For>
      </div>
      <p class="sr-only">
        Goods value {money(props.cost.value)} plus charges {money(props.cost.chargesTotal)} makes {money(props.cost.landedTotal)} landed.
      </p>
    </div>
  );
}

function ShipmentPopover(props: { cost: LandedCostOut | null; onApply: (v: { value: string; quantity: number; transport: Transport }) => void; disabled?: boolean }) {
  const initial = untrack(() => props.cost);
  const [value, setValue] = createSignal(initial?.value.amount ?? "12500.00");
  const [qty, setQty] = createSignal(initial?.quantity ?? 1000);
  const [transport, setTransport] = createSignal<Transport>((initial?.transport as Transport) ?? "ocean");
  const [open, setOpen] = createSignal(false);
  const input = "mt-1 h-9 w-full rounded-[var(--radius-btn)] border border-rule-2 bg-card px-3 text-[14px] text-ink outline-none focus:border-ink";
  return (
    <div class="flex items-center gap-2 text-[13.5px]">
      <Show when={props.cost} fallback={<span class="text-muted">No shipment yet</span>}>
        {(c) => (
          <span class="text-ink-2">
            {c().quantity.toLocaleString("en-US")} units · {money({ amount: (Number(c().value.amount) / Math.max(1, c().quantity)).toFixed(2), currency: c().value.currency })} each ·{" "}
            {c().transportLabel.toLowerCase()}
          </span>
        )}
      </Show>
      <Show when={!props.disabled}>
        <Popover.Root open={open()} onOpenChange={(d) => setOpen(d.open)} positioning={{ placement: "bottom-start", gutter: 8 }}>
          <Popover.Trigger class={button({ tone: "quiet", size: "xs" })}>Change</Popover.Trigger>
          <Portal>
            <Popover.Positioner class="z-50">
              <Popover.Content class={floating({ class: "w-[280px] p-4" })}>
                <Popover.Title class="text-[14px] font-[600]">Shipment</Popover.Title>
                <form
                  class="mt-3 space-y-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    props.onApply({ value: Number(value()).toFixed(2), quantity: qty(), transport: transport() });
                    setOpen(false);
                  }}
                >
                  <label class="block text-[12.5px] font-[600] text-ink-2">
                    Customs value ({props.cost?.value.currency ?? "USD"})
                    <input inputmode="decimal" value={value()} onInput={(e) => setValue(e.currentTarget.value)} class={`${input} font-code`} />
                  </label>
                  <label class="block text-[12.5px] font-[600] text-ink-2">
                    Units
                    <input type="number" min="1" value={qty()} onInput={(e) => setQty(Math.max(1, Number(e.currentTarget.value) || 1))} class={`${input} font-code`} />
                  </label>
                  <label class="block text-[12.5px] font-[600] text-ink-2">
                    Arrives by
                    <select value={transport()} onChange={(e) => setTransport(e.currentTarget.value as Transport)} class={input}>
                      <option value="ocean">Ocean freight</option>
                      <option value="air">Air freight</option>
                      <option value="truck">Truck</option>
                      <option value="rail">Rail</option>
                      <option value="courier">Courier</option>
                    </select>
                  </label>
                  <button type="submit" class={button({ size: "sm", class: "w-full" })}>
                    Update
                  </button>
                </form>
              </Popover.Content>
            </Popover.Positioner>
          </Portal>
        </Popover.Root>
      </Show>
    </div>
  );
}

/** The landed cost for the answer, restacked through the API when signed in. */
export function useLandedCost(answer: () => AnswerOut, live: boolean) {
  const countries = () => {
    const fromLanded = answer().landed.map((l) => l.country);
    const fromQuery = answer().query.into;
    return [...new Set([...fromLanded, ...fromQuery])].filter((c) => (c === "US" ? answer().us : answer().ca));
  };
  const [country, setCountry] = createSignal<Country>(untrack(countries)[0] ?? "US");
  const [madeIn, setMadeIn] = createSignal(untrack(() => answer().query.madeIn));
  const [usmca, setUsmca] = createSignal<Record<string, boolean>>({});
  const [cost, setCost] = createSignal<LandedCostOut | null>(untrack(() => answer().landed.find((l) => l.country === country())) ?? null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  let shipment: { value: string; quantity: number; transport: Transport } | null = null;

  const restack = async () => {
    const a = answer();
    const code = country() === "US" ? a.us : a.ca;
    const base = cost() ?? a.landed[0] ?? null;
    if (!code) return;
    if (!live) {
      setCost(a.landed.find((l) => l.country === country()) ?? null);
      return;
    }
    const value = shipment?.value ?? base?.value.amount ?? a.query.shipment?.value.amount;
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
          quantity: shipment?.quantity ?? base?.quantity ?? a.query.shipment?.quantity ?? 1,
          transport: shipment?.transport ?? (base?.transport as Transport) ?? a.query.shipment?.transport ?? "ocean",
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
  return {
    countries,
    country,
    setCountry,
    madeIn,
    setMadeIn,
    usmca,
    setUsmca,
    cost,
    loading,
    error,
    applyShipment: (v: { value: string; quantity: number; transport: Transport }) => {
      shipment = v;
      void restack();
    },
  };
}
export type LandedState = ReturnType<typeof useLandedCost>;

export function CostLayer(props: { answer: AnswerOut; live: boolean; state: LandedState }) {
  const st = () => props.state;
  const ch = checkbox();
  return (
    <div class="space-y-5">
      <div class="flex flex-wrap items-center gap-x-6 gap-y-3">
        <Show when={st().countries().length > 1}>
          <Segmented label="Into" value={st().country()} onChange={(v) => st().setCountry(v as Country)} items={st().countries().map((c) => ({ value: c, label: c === "US" ? "US" : "Canada" }))} />
        </Show>
        <Show when={props.live}>
          <Segmented
            label="Made in"
            value={st().madeIn()}
            onChange={(v) => st().setMadeIn(v)}
            items={ORIGINS.some((o) => o.value === st().madeIn()) ? ORIGINS : [...ORIGINS, { value: st().madeIn(), label: props.answer.madeInLabel }]}
          />
        </Show>
        <ShipmentPopover cost={st().cost()} disabled={!props.live} onApply={(v) => st().applyShipment(v)} />
      </div>

      <Show when={st().cost()?.questions.length}>
        <fieldset class="rounded-[var(--radius-box)] bg-paper-2 px-4 py-3">
          <legend class="sr-only">USMCA origin questions</legend>
          <p class="text-[13px] font-[600]">USMCA: three questions</p>
          <div class="mt-2 space-y-2">
            <For each={st().cost()!.questions}>
              {(q) => (
                <Checkbox.Root checked={!!st().usmca()[q.key]} onCheckedChange={(d) => st().setUsmca((u) => ({ ...u, [q.key]: d.checked === true }))} class={`${ch.root()} items-start text-[14px]`}>
                  <Checkbox.Control class={`${ch.control()} mt-0.5`}>
                    <Checkbox.Indicator>✓</Checkbox.Indicator>
                  </Checkbox.Control>
                  <Checkbox.Label>{q.question}</Checkbox.Label>
                  <Checkbox.HiddenInput />
                </Checkbox.Root>
              )}
            </For>
          </div>
        </fieldset>
      </Show>

      <Show when={st().error()}>
        <p role="alert" class="text-[14px] font-[600] text-bad">
          {st().error()}
        </p>
      </Show>

      <Show
        when={st().cost()}
        fallback={<p class="text-[14px] text-muted">{props.live ? "Add a shipment to see every duty it will carry." : "The landed cost appears when the answer has a shipment."}</p>}
      >
        {(c) => (
          <div aria-busy={st().loading()} classList={{ "opacity-60": st().loading() }} class="space-y-5 transition-opacity">
            <Totals cost={c()} />
            <StackBar cost={c()} />
            <Show when={!st().loading()} fallback={<SkeletonLines lines={6} />}>
              <Receipt cost={c()} />
            </Show>
            <Show when={c().whatCouldChange.length}>
              <p class="text-[13px] text-muted">
                <For each={c().whatCouldChange}>
                  {(w, i) => (
                    <>
                      {i() > 0 ? " · " : ""}
                      {w.label}: <span class="font-code">{money(w.chargesTotal)}</span>
                      <Show when={Number(subtractMoney(w.chargesTotal, c().chargesTotal).amount) < 0}>
                        {" "}
                        ({money(subtractMoney(c().chargesTotal, w.chargesTotal))} less)
                      </Show>
                    </>
                  )}
                </For>
              </p>
            </Show>
          </div>
        )}
      </Show>
    </div>
  );
}
