/**
 * A training round in layers: one sentence first, then tabs for accuracy by depth, the confidence word, chapters,
 * what it learned from brokers, and the two-signature sign-off.
 */
import { Steps } from "@ark-ui/solid/steps";
import { Tabs } from "@ark-ui/solid/tabs";
import { createSolidTable, getCoreRowModel, getSortedRowModel, type SortingState } from "@tanstack/solid-table";
import { A } from "@solidjs/router";
import { For, Show, createSignal } from "solid-js";
import { lab } from "~/lib/endpoints";
import { dateShort, dateTime } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import type { ChapterRow, LabOut, RoundOut } from "~/lib/types";
import { FailIcon, OkIcon, PassIcon } from "~/ui/Icons";
import { button, card, field, tabs } from "~/ui/recipes";
import { Sheet } from "~/ui/Sheet";
import { notify } from "~/ui/Toast";
import { DepthPlot, FrequencyGrid } from "./Charts";

export function RoundsStrip(props: { lab: LabOut; current: number }) {
  const idx = () => Math.max(0, props.lab.rounds.findIndex((r) => r.n === props.current));
  return (
    <Steps.Root count={props.lab.rounds.length} step={idx()} aria-label="Training rounds">
      <Steps.List class="flex flex-wrap gap-2">
        <For each={props.lab.rounds}>
          {(r, i) => (
            <Steps.Item index={i()}>
              <A
                href={`/lab/rounds/${r.n}`}
                class="flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[13.5px] no-underline"
                classList={{ "border-ink bg-ink text-card": r.n === props.current, "border-rule bg-card text-ink-2 hover:border-rule-2": r.n !== props.current }}
                aria-current={r.n === props.current ? "page" : undefined}
                title={r.note}
              >
                <span class="font-[600]">Round {r.n}</span>
                <span
                  class="text-[12px]"
                  classList={{
                    "opacity-70": r.n === props.current,
                    "text-ok": r.n !== props.current && r.status === "live",
                    "text-warn": r.n !== props.current && r.status === "waiting_signoff",
                    "text-muted": r.n !== props.current && r.status !== "live" && r.status !== "waiting_signoff",
                  }}
                >
                  {r.statusLabel}
                </span>
              </A>
            </Steps.Item>
          )}
        </For>
      </Steps.List>
    </Steps.Root>
  );
}

function ChapterTable(props: { rows: ChapterRow[] }) {
  const [sorting, setSorting] = createSignal<SortingState>([{ id: "change", desc: true }]);
  const table = createSolidTable({
    get data() {
      return props.rows;
    },
    columns: [
      { id: "chapter", accessorKey: "chapter", header: "Chapter" },
      { id: "tested", accessorKey: "tested", header: "Tested" },
      { id: "after", accessorKey: "after", header: "Right of 100" },
      { id: "change", accessorKey: "change", header: "Change" },
      { id: "newRulings", accessorKey: "newRulings", header: "New rulings" },
    ],
    state: {
      get sorting() {
        return sorting();
      },
    },
    onSortingChange: (u) => setSorting(typeof u === "function" ? u(sorting()) : u),
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  return (
    <div class={card({ class: "overflow-x-auto" })}>
      <table class="w-full min-w-[680px] border-collapse text-left">
        <caption class="sr-only">Accuracy by chapter, the live round against this round</caption>
        <thead>
          <tr class="border-b border-rule bg-paper-2/50 text-[12.5px] text-muted">
            <For each={table.getFlatHeaders()}>
              {(h) => (
                <th scope="col" class="px-4 py-2.5 font-[600]" aria-sort={h.column.getIsSorted() ? (h.column.getIsSorted() === "desc" ? "descending" : "ascending") : undefined}>
                  <button type="button" class="inline-flex items-center gap-1 font-[600] hover:text-ink" onClick={h.column.getToggleSortingHandler()}>
                    {h.column.columnDef.header as string}
                    <span aria-hidden="true">{h.column.getIsSorted() === "asc" ? "↑" : h.column.getIsSorted() === "desc" ? "↓" : ""}</span>
                  </button>
                </th>
              )}
            </For>
          </tr>
        </thead>
        <tbody>
          <For each={table.getRowModel().rows}>
            {(row) => {
              const c = row.original;
              return (
                <tr class="border-b border-rule last:border-b-0">
                  <td class="px-4 py-2.5 text-[14px]">
                    <span class="font-code font-[600]">{c.chapter}</span> <span class="text-ink-2">{c.title}</span>
                  </td>
                  <td class="px-4 py-2.5 font-code text-[13.5px]">{c.tested}</td>
                  <td class="px-4 py-2.5">
                    <span class="flex items-center gap-3">
                      <span class="relative h-[8px] w-[140px] overflow-hidden rounded-full bg-paper-3" aria-hidden="true">
                        <span class="absolute inset-y-0 left-0 bg-ink" style={{ width: `${Math.min(c.before, c.after)}%` }} />
                        <span
                          class="absolute inset-y-0"
                          classList={{ "bg-hi": c.after >= c.before, "border-[1.5px] border-bad": c.after < c.before }}
                          style={{ left: `${Math.min(c.before, c.after)}%`, width: `${Math.abs(c.after - c.before)}%` }}
                        />
                      </span>
                      <span class="font-code text-[13.5px]">
                        {c.before} → <b class="font-[600]">{c.after}</b>
                      </span>
                    </span>
                  </td>
                  <td class="px-4 py-2.5 font-code text-[13.5px]" classList={{ "text-ok": c.change > 0, "text-bad": c.change < 0 }}>
                    {c.changeLabel}
                  </td>
                  <td class="px-4 py-2.5 text-[13.5px]">
                    <span class="font-code">{c.newRulings}</span>
                    <Show when={c.moving}>
                      <span class="ml-2 rounded-full bg-warn-soft px-2 py-0.5 text-[11.5px] font-[600] text-warn">moving</span>
                    </Show>
                  </td>
                </tr>
              );
            }}
          </For>
        </tbody>
      </table>
    </div>
  );
}

function highlightLede(lede: string) {
  const m = lede.match(/(\d+ in 100)/);
  if (!m) return <>{lede}</>;
  const [before, after] = lede.split(m[1]!);
  return (
    <>
      {before}
      <span class="hl">{m[1]}</span>
      {after}
    </>
  );
}

export function LabReport(props: { lab: LabOut; round: RoundOut; me: string; onSigned: (r: RoundOut) => void }) {
  const r = () => props.round;
  const [signing, setSigning] = createSignal(false);
  const [statement, setStatement] = createSignal("");
  const [error, setError] = createSignal("");
  const [busy, setBusy] = createSignal(false);
  let nameInput: HTMLInputElement | undefined;
  const allPassed = () => r().checks.every((c) => c.passed);
  const liveRound = () => props.lab.live ?? props.lab.rounds.find((x) => x.status === "live")?.n ?? null;
  const t = tabs();

  const sign = async () => {
    setError("");
    if (statement().trim().toLowerCase() !== props.me.toLowerCase()) {
      setError(`Type your full name, “${props.me}”, to sign.`);
      return;
    }
    setBusy(true);
    try {
      const out = await lab.sign(r().n, statement().trim());
      setSigning(false);
      setStatement("");
      notify(out.status === "live" ? `Round ${out.n} is live` : `Signed round ${out.n}`, out.status === "live" ? out.signOff.note : "It goes live with a second signature from someone else.");
      props.onSigned(out);
    } catch (e) {
      const p = plainProblem(e);
      setError(p.fields.statement ?? p.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section class={card({ class: "mt-4 p-6 max-sm:p-5" })} aria-label={`Round ${r().n}`}>
        <p class="max-w-[720px] text-[19px] font-[550] leading-[1.45] tracking-[-0.01em]">{highlightLede(r().lede)}</p>
        <p class="mt-2 text-[12.5px] text-muted">
          {r().testCount.toLocaleString("en-US")} rulings it hasn't seen · {dateShort(r().testFrom)} – {dateShort(r().testTo)} · snapshot <span class="font-code">{r().snapshot}</span>
        </p>
      </section>

      <Tabs.Root defaultValue={r().status === "waiting_signoff" && r().signOff.canSign ? "signoff" : "depth"} class="mt-8">
        <Tabs.List class={t.list()}>
          <Tabs.Trigger value="depth" class={t.trigger()}>
            Accuracy
          </Tabs.Trigger>
          <Tabs.Trigger value="confidence" class={t.trigger()}>
            Confidence
          </Tabs.Trigger>
          <Tabs.Trigger value="chapters" class={t.trigger()}>
            Chapters <span class={t.count()}>{r().byChapter.length}</span>
          </Tabs.Trigger>
          <Tabs.Trigger value="learned" class={t.trigger()}>
            Learned
          </Tabs.Trigger>
          <Tabs.Trigger value="signoff" class={t.trigger()}>
            Sign-off <span class={t.count()}>{r().signOff.signatures.length} of 2</span>
          </Tabs.Trigger>
          <Tabs.Indicator class={t.indicator({ class: "w-[var(--width)] left-[var(--left)]" })} />
        </Tabs.List>
        <Tabs.Content value="depth" class="mt-4">
          <div class={card({ class: "p-6 max-sm:p-4" })}>
            <DepthPlot rows={r().byDepth} liveN={liveRound() !== r().n ? liveRound() : null} n={r().n} />
          </div>
        </Tabs.Content>
        <Tabs.Content value="confidence" class="mt-4">
          <div class={card({ class: "grid grid-cols-2 gap-10 p-6 max-lg:grid-cols-1 max-sm:p-4" })}>
            <Show when={r().confidence.strong}>{(c) => <FrequencyGrid cell={c()} label="Strong match" filledMeans="right" restMeans="wrong" />}</Show>
            <Show when={r().confidence.broker}>
              {(c) => <FrequencyGrid cell={c()} label="Needs a broker" filledMeans="first guess wrong, broker needed" restMeans="first guess right" />}
            </Show>
          </div>
        </Tabs.Content>
        <Tabs.Content value="chapters" class="mt-4">
          <ChapterTable rows={r().byChapter} />
          <Show when={r().drift.sentence}>
            <p class="mt-3 max-w-[760px] text-[13px] text-muted">{String(r().drift.sentence ?? "")}</p>
          </Show>
        </Tabs.Content>
        <Tabs.Content value="learned" class="mt-4">
          <ol class={card({ class: "divide-y divide-rule" })}>
            <For each={r().learned}>
              {(l, i) => (
                <li class="flex gap-3 px-5 py-3.5 text-[14.5px] leading-[1.55]">
                  <span class="font-code text-[12.5px] text-muted">{i() + 1}</span>
                  {l}
                </li>
              )}
            </For>
          </ol>
        </Tabs.Content>
        <Tabs.Content value="signoff" class="mt-4">
          <section class={card({ class: "overflow-hidden" })} aria-labelledby="signoff-h">
            <h2 id="signoff-h" class="sr-only">
              Sign-off
            </h2>
            <ul class="divide-y divide-rule">
              <For each={r().checks}>
                {(c) => (
                  <li class="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3 text-[14px]">
                    <span classList={{ "text-ok": c.passed, "text-bad": !c.passed }} class="inline-flex items-center gap-1.5 text-[12.5px] font-[600]">
                      {c.passed ? <PassIcon size={15} /> : <FailIcon size={15} />}
                      {c.passed ? "Passed" : "Not passed"}
                    </span>
                    <span class="flex-1">{c.label}</span>
                    <span class="font-code text-[12.5px] text-muted">
                      {c.value} ({c.threshold})
                    </span>
                  </li>
                )}
              </For>
            </ul>
            <div class="grid grid-cols-2 border-t border-rule max-md:grid-cols-1">
              <For each={[0, 1]}>
                {(i) => {
                  const s = () => r().signOff.signatures[i];
                  return (
                    <div class="min-h-[120px] px-5 py-4" classList={{ "border-l border-rule max-md:border-l-0 max-md:border-t": i === 1 }}>
                      <p class="label">Signature {i + 1}</p>
                      <Show
                        when={s()}
                        fallback={
                          <div class="mt-3">
                            <Show
                              when={r().signOff.canSign && i === r().signOff.signatures.length}
                              fallback={<p class="text-[13.5px] text-muted">{r().status === "waiting_signoff" ? "Waiting for a second person" : "Not needed"}</p>}
                            >
                              <button type="button" class={button({ size: "md" })} disabled={!allPassed()} onClick={() => setSigning(true)}>
                                {r().signOff.willPromote ? `Sign and make round ${r().n} live` : `Sign round ${r().n}`}
                              </button>
                              <Show when={!allPassed()}>
                                <p class="mt-2 text-[13px] text-bad">A check didn't pass.</p>
                              </Show>
                            </Show>
                          </div>
                        }
                      >
                        {(sig) => (
                          <div class="mt-2">
                            <p class="text-[18px] italic">{sig().statement}</p>
                            <p class="text-[12.5px] text-muted">
                              {sig().name}, {sig().roleLabel.toLowerCase()} · {dateTime(sig().signedAt)}
                            </p>
                          </div>
                        )}
                      </Show>
                    </div>
                  );
                }}
              </For>
            </div>
            <p class="flex items-center gap-1.5 border-t border-rule bg-paper-2/50 px-5 py-3 text-[12.5px] text-muted">
              <OkIcon size={13} />
              {r().signOff.note}
            </p>
          </section>
        </Tabs.Content>
      </Tabs.Root>
      <Sheet
        open={signing()}
        onOpenChange={setSigning}
        role="alertdialog"
        title={r().signOff.willPromote ? `Make round ${r().n} live?` : `Sign round ${r().n}?`}
        description={r().signOff.willPromote ? `New questions will use round ${r().n}. Type your name to sign.` : "The first of two signatures. Type your name to sign."}
        initialFocus={() => nameInput ?? null}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void sign();
          }}
        >
          <label for="sign-name" class="sr-only">
            Your full name
          </label>
          <input
            ref={nameInput}
            id="sign-name"
            value={statement()}
            onInput={(e) => setStatement(e.currentTarget.value)}
            placeholder={props.me}
            autocomplete="name"
            aria-invalid={!!error()}
            class={field().input({ class: "h-11" })}
          />
          <Show when={error()}>
            <p role="alert" class="mt-2 text-[13.5px] font-[600] text-bad">
              {error()}
            </p>
          </Show>
          <div class="mt-4 flex justify-end gap-2">
            <button type="button" class={button({ tone: "ghost" })} onClick={() => setSigning(false)}>
              Cancel
            </button>
            <button type="submit" class={button()} disabled={busy()}>
              {r().signOff.willPromote ? "Sign and make it live" : "Sign"}
            </button>
          </div>
        </form>
      </Sheet>
    </>
  );
}
