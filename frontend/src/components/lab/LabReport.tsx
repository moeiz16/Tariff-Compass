/**
 * The optimisation lab as a report: a strip of training rounds, then numbered sections (in one sentence, by depth,
 * the confidence word, by chapter, drift, what it learned from brokers) and a two-signature sign-off form.
 */
import { Steps } from "@ark-ui/solid/steps";
import { createSolidTable, getCoreRowModel, getSortedRowModel, type SortingState } from "@tanstack/solid-table";
import { A } from "@solidjs/router";
import { For, Show, createSignal, type JSX } from "solid-js";
import { lab } from "~/lib/endpoints";
import { dateShort, dateTime } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import type { ChapterRow, LabOut, RoundOut } from "~/lib/types";
import { FailIcon, OkIcon, PassIcon } from "~/ui/Icons";
import { button } from "~/ui/recipes";
import { Sheet } from "~/ui/Sheet";
import { notify } from "~/ui/Toast";
import { DepthPlot, FrequencyGrid } from "./Charts";

function Section(props: { n: string; label: string; note?: string; children: JSX.Element }) {
  return (
    <section class="gm ty-ruled py-9 max-md:py-7">
      <div class="gl">
        <span>{props.n}</span>
        <h2 class="not-italic">
          <b>{props.label}</b>
        </h2>
        <Show when={props.note}>
          <span class="gl-extra block">{props.note}</span>
        </Show>
      </div>
      <div class="gm-wide max-w-[1160px]">{props.children}</div>
    </section>
  );
}

export function RoundsStrip(props: { lab: LabOut; current: number }) {
  const idx = () => Math.max(0, props.lab.rounds.findIndex((r) => r.n === props.current));
  return (
    <Steps.Root count={props.lab.rounds.length} step={idx()} class="px-8 pt-5 max-md:px-4" aria-label="Training rounds">
      <Steps.List class="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] overflow-hidden rounded-[var(--radius-box)] border-[1.5px] border-ink max-md:grid-cols-1">
        <For each={props.lab.rounds}>
          {(r, i) => (
            <Steps.Item index={i()} class="border-r border-rule last:border-r-0 max-md:border-b max-md:border-r-0 max-md:last:border-b-0" classList={{ "bg-hi text-hi-ink": r.status === "waiting_signoff" }}>
              <A href={`/lab/rounds/${r.n}`} class="block h-full px-5 py-3.5 no-underline hover:bg-paper-2" classList={{ "hover:bg-hi": r.status === "waiting_signoff", "outline outline-2 -outline-offset-4 outline-ink": r.n === props.current }} aria-current={r.n === props.current ? "page" : undefined}>
                <span class="flex items-baseline justify-between gap-3">
                  <b class="font-type text-[17px] font-[700] uppercase tracking-[0.03em]">Round {r.n}</b>
                  <span class="text-[15px] font-[650]" classList={{ "text-ok": r.status === "live", "text-muted": r.status === "retired" || r.status === "not_made_live" }}>
                    {r.statusLabel}
                  </span>
                </span>
                <span class="mt-1 block text-[14.5px]" classList={{ "text-ink-2": r.status !== "waiting_signoff" }}>
                  {r.trainedOn ? dateShort(r.trainedOn) : "–"} · {r.note}
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
    <div class="overflow-x-auto">
      <table class="w-full min-w-[720px] border-collapse text-left">
        <caption class="sr-only">Accuracy by chapter, the live round against this round</caption>
        <thead>
          <tr class="border-b-[1.5px] border-ink text-[14px] text-ink-2">
            <For each={table.getFlatHeaders()}>
              {(h) => (
                <th scope="col" class="px-3 py-2 font-[650]" aria-sort={h.column.getIsSorted() ? (h.column.getIsSorted() === "desc" ? "descending" : "ascending") : undefined}>
                  <button type="button" class="inline-flex items-center gap-1 font-[650]" onClick={h.column.getToggleSortingHandler()}>
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
                <tr class="border-b border-rule">
                  <td class="px-3 py-2.5 text-[15.5px]">
                    <span class="font-code font-[650]">{c.chapter}</span> {c.title}
                  </td>
                  <td class="px-3 py-2.5 font-code text-[14.5px]">{c.tested}</td>
                  <td class="px-3 py-2.5">
                    <span class="flex items-center gap-3">
                      <span class="relative h-[10px] w-[160px] bg-paper-3" aria-hidden="true">
                        <span class="absolute inset-y-0 left-0 bg-ink" style={{ width: `${Math.min(c.before, c.after)}%` }} />
                        <span
                          class="absolute inset-y-0"
                          classList={{ "bg-hi": c.after >= c.before, "border-[1.5px] border-bad": c.after < c.before }}
                          style={{ left: `${Math.min(c.before, c.after)}%`, width: `${Math.abs(c.after - c.before)}%` }}
                        />
                      </span>
                      <span class="font-code text-[14.5px]">
                        {c.before} → <b>{c.after}</b>
                      </span>
                    </span>
                  </td>
                  <td class="px-3 py-2.5 font-code text-[14.5px]" classList={{ "text-ok": c.change > 0, "text-bad": c.change < 0 }}>
                    {c.changeLabel}
                  </td>
                  <td class="px-3 py-2.5 text-[14.5px]">
                    <span class="font-code">{c.newRulings}</span>
                    <Show when={c.moving}>
                      <span class="ml-2 rounded-[3px] border border-warn px-1.5 text-[12.5px] font-[650] text-warn">moving</span>
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
      <Section n={`Report · round ${r().n}`} label="In one sentence">
        <p class="max-w-[860px] font-type text-[clamp(23px,2.6vw,33px)] font-[700] leading-[1.28] tracking-[-0.015em]">{highlightLede(r().lede)}</p>
        <p class="mt-4 max-w-[820px] text-[17px] leading-[1.6] text-ink-2">
          Tested on {r().testCount.toLocaleString("en-US")} rulings issued {dateShort(r().testFrom)} – {dateShort(r().testTo)}, newer than anything it learned from. Data snapshot{" "}
          <span class="font-code">{r().snapshot}</span>. {r().rerunNote}
        </p>
        <p class="mt-2 text-[15px] text-muted">Answers written by: {r().runBy}.</p>
      </Section>
      <Section n="§ 1" label="By depth" note="out of 100 test rulings">
        <DepthPlot rows={r().byDepth} liveN={liveRound() !== r().n ? liveRound() : null} n={r().n} />
      </Section>
      <Section n="§ 2" label="The confidence word" note="each dot is one ruling in a hundred">
        <div class="grid grid-cols-2 gap-10 border-t-[1.5px] border-ink pt-5 max-lg:grid-cols-1">
          <Show when={r().confidence.strong}>{(c) => <FrequencyGrid cell={c()} label="Strong match" filledMeans="right" restMeans="wrong" />}</Show>
          <Show when={r().confidence.broker}>
            {(c) => <FrequencyGrid cell={c()} label="Needs a broker" filledMeans="its first guess was wrong, so the broker was needed" restMeans="its first guess was right" />}
          </Show>
        </div>
      </Section>
      <Section n="§ 3" label="By chapter" note="every chapter with test rulings">
        <ChapterTable rows={r().byChapter} />
        <p class="mt-4 max-w-[820px] text-[16px] leading-[1.6] text-ink-2">
          <b class="text-ink">Drift as tariffs and rulings change:</b> {String(r().drift.sentence ?? "")}
        </p>
      </Section>
      <Section n="§ 4" label="Learned from brokers">
        <ol class="max-w-[820px] list-decimal space-y-2 pl-5 text-[17px] leading-[1.55]">
          <For each={r().learned}>{(l) => <li>{l}</li>}</For>
        </ol>
      </Section>
      <section class="gm py-9" aria-labelledby="signoff-h">
        <div class="gl">
          <span>§ 5</span>
          <h2 id="signoff-h" class="not-italic">
            <b>Sign-off</b>
          </h2>
          <span class="gl-extra block">two signatures, two people</span>
        </div>
        <div class="gm-wide max-w-[1160px] rounded-[var(--radius-box)] border-[1.5px] border-ink">
          <ul class="border-b border-rule px-5 py-4">
            <For each={r().checks}>
              {(c) => (
                <li class="flex flex-wrap items-baseline gap-x-3 py-1.5 text-[16px]">
                  <span classList={{ "text-ok": c.passed, "text-bad": !c.passed }} class="inline-flex items-center gap-1.5 font-[650]">
                    {c.passed ? <PassIcon size={15} /> : <FailIcon size={15} />}
                    {c.passed ? "Passed" : "Not passed"}
                  </span>
                  <span>{c.label}</span>
                  <span class="font-code text-[14px] text-ink-2">
                    {c.value} ({c.threshold})
                  </span>
                </li>
              )}
            </For>
          </ul>
          <div class="grid grid-cols-2 max-md:grid-cols-1">
            <For each={[0, 1]}>
              {(i) => {
                const s = () => r().signOff.signatures[i];
                return (
                  <div class="min-h-[140px] px-5 py-4" classList={{ "border-l border-rule max-md:border-l-0 max-md:border-t": i === 1 }}>
                    <p class="ty-head">Signature {i + 1}</p>
                    <Show
                      when={s()}
                      fallback={
                        <div class="mt-3">
                          <Show
                            when={r().signOff.canSign && i === r().signOff.signatures.length}
                            fallback={<p class="text-[15.5px] text-muted">{r().status === "waiting_signoff" ? "Waiting for a second person with sign-off rights." : "Not needed for this round."}</p>}
                          >
                            <button type="button" class={button({ size: "lg" })} disabled={!allPassed()} onClick={() => setSigning(true)}>
                              {r().signOff.willPromote ? `Sign and make round ${r().n} live` : `Sign round ${r().n}`}
                            </button>
                            <Show when={!allPassed()}>
                              <p class="mt-2 text-[14px] text-bad">A check didn't pass, so this round can't be signed.</p>
                            </Show>
                          </Show>
                        </div>
                      }
                    >
                      {(sig) => (
                        <div class="mt-3">
                          <p class="font-law text-[22px] italic">{sig().statement}</p>
                          <p class="text-[14.5px] text-ink-2">
                            {sig().name}, {sig().roleLabel.toLowerCase()} · signed {dateTime(sig().signedAt)}
                          </p>
                        </div>
                      )}
                    </Show>
                  </div>
                );
              }}
            </For>
          </div>
          <p class="border-t border-rule px-5 py-3 text-[15px] text-ink-2">
            <OkIcon size={14} class="mr-1.5 inline text-muted" />
            {r().signOff.note}
          </p>
        </div>
      </section>
      <Sheet
        open={signing()}
        onOpenChange={setSigning}
        role="alertdialog"
        title={r().signOff.willPromote ? `Make round ${r().n} live for Northbound?` : `Sign round ${r().n}?`}
        description={
          r().signOff.willPromote
            ? `New questions will be answered by round ${r().n} from now on. Round ${liveRound() ?? "the live round"} stays available to switch back. Type your name to sign.`
            : "Your signature is the first of two. The round goes live when someone else signs too. Type your name to sign."
        }
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
            class="h-12 w-full rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-3 text-[17px]"
          />
          <Show when={error()}>
            <p role="alert" class="mt-2 text-[14px] font-[600] text-bad">
              {error()}
            </p>
          </Show>
          <div class="mt-4 flex gap-2">
            <button type="submit" class={button({ size: "lg" })} disabled={busy()}>
              {r().signOff.willPromote ? "Sign and make it live" : "Sign"}
            </button>
            <button type="button" class={button({ tone: "ghost", size: "lg" })} onClick={() => setSigning(false)}>
              Not yet
            </button>
          </div>
        </form>
      </Sheet>
    </>
  );
}
