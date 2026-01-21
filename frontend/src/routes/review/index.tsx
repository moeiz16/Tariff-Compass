import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { createSolidTable, flexRender, getCoreRowModel, getSortedRowModel, type ColumnDef, type SortingState } from "@tanstack/solid-table";
import { useSearchParams } from "@solidjs/router";
import { For, Show, createEffect, createResource, createSignal, onCleanup, onMount } from "solid-js";
import { DecisionRecordView, type RecordHandle } from "~/components/review/DecisionRecord";
import { AppPage } from "~/components/shell/AppPage";
import { docketKeyAction, isTyping } from "~/lib/docket";
import { review } from "~/lib/endpoints";
import { money } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { DocketFilter, ReviewRow } from "~/lib/types";
import { CodeDigits } from "~/ui/Code";
import { Kbd } from "~/ui/Marked";
import { button, chip } from "~/ui/recipes";
import { Sheet } from "~/ui/Sheet";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { KindTag } from "~/ui/Status";
import { notify } from "~/ui/Toast";

const KIND_TONE: Record<ReviewRow["kind"], { tone: "warn" | "ink" | "bad" | "muted"; icon: "ask" | "modified" | "warn" | "ok" }> = {
  unsure: { tone: "warn", icon: "ask" },
  differs: { tone: "bad", icon: "warn" },
  ruling_changed: { tone: "ink", icon: "modified" },
  always_review: { tone: "muted", icon: "ok" },
  requested: { tone: "ink", icon: "ask" },
};

const FILTERS: { value: DocketFilter; label: string; count: "all" | "unsure" | "differs" | "rulingChanged" | "always" | "ca" }[] = [
  { value: "all", label: "All", count: "all" },
  { value: "unsure", label: "Classifier unsure", count: "unsure" },
  { value: "differs", label: "Differs from last code", count: "differs" },
  { value: "ruling_changed", label: "Ruling changed", count: "rulingChanged" },
  { value: "always", label: "Always reviewed", count: "always" },
  { value: "ca", label: "Into Canada", count: "ca" },
];

export default function ReviewPage() {
  const { can, me } = useSession();
  const [params, setParams] = useSearchParams<{ filter?: string; q?: string; open?: string }>();
  const filter = () => (params.filter as DocketFilter) ?? "all";
  const [docket, { refetch }] = createResource(() => ({ filter: filter(), q: params.q ?? "" }), (k) => review.docket(k));
  const [sorting, setSorting] = createSignal<SortingState>([{ id: "waiting", desc: false }]);
  const [shown, setShown] = createSignal(15);
  const openId = () => params.open ?? null;
  const [record, { refetch: refetchRecord }] = createResource(() => openId(), (id) => review.get(id));
  const [asking, setAsking] = createSignal(false);
  const [question, setQuestion] = createSignal("");
  const [options, setOptions] = createSignal("");
  const [askError, setAskError] = createSignal("");
  let handle: RecordHandle | null = null;
  const canDecide = () => can("review:decide");
  const importerName = () => me()?.activeOrg?.name.split(" ")[0] ?? "the importer";

  const columns: ColumnDef<ReviewRow>[] = [
    { id: "waiting", header: "Waiting", accessorFn: (r) => r.waitingSince, sortingFn: "alphanumeric" },
    { id: "product", header: "Product", accessorFn: (r) => r.productTitle },
    { id: "into", header: "Into", accessorFn: (r) => r.intoLabel, enableSorting: false },
    { id: "proposed", header: "Proposed", accessorFn: (r) => r.proposedUs?.code ?? r.proposedCa?.code ?? "", enableSorting: false },
    { id: "why", header: "Why it's here", accessorFn: (r) => r.kindLabel, enableSorting: false },
    { id: "value", header: "Value", accessorFn: (r) => Number(r.value?.amount ?? 0) },
    { id: "with", header: "With", accessorFn: (r) => r.withName ?? "", enableSorting: false },
  ];
  const table = createSolidTable({
    get data() {
      return docket()?.items ?? [];
    },
    columns,
    state: {
      get sorting() {
        return sorting();
      },
    },
    onSortingChange: (u) => setSorting(typeof u === "function" ? u(sorting()) : u),
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  const rows = () => table.getRowModel().rows.slice(0, shown());

  const open = (id: string | null) => {
    setParams({ open: id ?? undefined }, { replace: true });
    if (id) queueMicrotask(() => document.getElementById(`row-${id}`)?.scrollIntoView({ block: "nearest" }));
  };
  const move = (delta: number) => {
    const list = rows().map((r) => r.original.id);
    if (!list.length) return;
    const at = openId() ? list.indexOf(openId()!) : -1;
    const next = list[Math.max(0, Math.min(list.length - 1, at + delta))] ?? list[0]!;
    open(next);
    queueMicrotask(() => document.getElementById(`row-${next}`)?.focus());
  };

  onMount(() => {
    const onKey = (e: KeyboardEvent) => {
      const action = docketKeyAction(e, { typing: isTyping(document.activeElement), canDecide: canDecide(), open: !!openId() });
      if (!action) return;
      e.preventDefault();
      if (action === "next") move(1);
      else if (action === "prev") move(-1);
      else if (action === "close") open(null);
      else if (action === "approve") handle?.approve();
      else if (action === "correct") handle?.correct();
      else if (action === "ask") handle?.ask();
    };
    window.addEventListener("keydown", onKey);
    onCleanup(() => window.removeEventListener("keydown", onKey));
  });

  createEffect(() => {
    if (!openId()) setAsking(false);
  });

  const afterDecision = (toast: string) => {
    notify(toast);
    const list = rows().map((r) => r.original.id);
    const at = list.indexOf(openId() ?? "");
    const next = list[at + 1] ?? null;
    void refetch();
    open(next);
  };

  const ask = async () => {
    if (!openId() || question().trim().length < 5) {
      setAskError("Write the question in a sentence.");
      return;
    }
    try {
      const out = await review.ask(
        openId()!,
        question().trim(),
        options()
          .split("\n")
          .map((o) => o.trim())
          .filter(Boolean),
      );
      setAsking(false);
      setQuestion("");
      setOptions("");
      afterDecision(out.toast);
    } catch (e) {
      setAskError(plainProblem(e).message);
    }
  };

  const d = () => docket();
  return (
    <AppPage title="Review" scope="review" permission="review:read" query={params.q} placeholder="Search the docket: product, SKU, code or ruling" boxLabel="Search the review docket" onSearch={(q) => setParams({ q: q || undefined, open: undefined })}>
      <div class="px-8 py-6 max-md:px-4">
        <p class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[16.5px]">
          <Show when={d()} fallback="Opening the docket…">
            {(x) => (
              <>
                <b>{x().counts.all} waiting</b>
                <span class="text-ink-2">
                  for {me()?.orgs.find((o) => o.id === me()?.activeOrg?.id)?.viaBroker ?? "your broker"} · {me()?.activeOrg?.name} · {x().oldestLabel}
                </span>
                <Show when={canDecide()}>
                  <span class="text-ink-2 max-md:hidden">
                    · <Kbd>J</Kbd> <Kbd>K</Kbd> move, <Kbd>A</Kbd> approve, <Kbd>C</Kbd> correct, <Kbd>Q</Kbd> ask
                  </span>
                </Show>
              </>
            )}
          </Show>
        </p>
        <ToggleGroup.Root value={[filter()]} onValueChange={(v) => setParams({ filter: v.value[0] && v.value[0] !== "all" ? v.value[0] : undefined, open: undefined })} class="mt-4 flex flex-wrap gap-2" aria-label="Filter the docket">
          <For each={FILTERS}>
            {(f) => (
              <ToggleGroup.Item value={f.value} class={chip()}>
                {f.label} <span class="font-code text-[11.5px] font-[600] text-muted">{d()?.counts[f.count] ?? ""}</span>
              </ToggleGroup.Item>
            )}
          </For>
        </ToggleGroup.Root>

        <Show when={!docket.error} fallback={<div class="mt-6"><ErrorSlip error={docket.error} retry={refetch} /></div>}>
          <Show when={d()} fallback={<SkeletonLines class="mt-6" lines={10} />}>
            <Show when={d()!.items.length} fallback={<div class="mt-6"><EmptyState title={params.q || filter() !== "all" ? "Nothing in the docket matches that" : "The docket is clear"}>{params.q || filter() !== "all" ? "Clear the search or choose All." : d()!.emptyMessage}</EmptyState></div>}>
              <div class="mt-5">
                <table class="w-full border-collapse text-left max-md:block">
                  <caption class="sr-only">Review docket, oldest first. Select a row to open its decision record.</caption>
                  <thead class="max-md:hidden">
                    <For each={table.getHeaderGroups()}>
                      {(hg) => (
                        <tr class="border-b-[1.5px] border-ink text-[14px] text-ink-2">
                          <For each={hg.headers}>
                            {(h) => (
                              <th
                                scope="col"
                                class="px-3 py-2.5 font-[650]"
                                classList={{ "text-right": h.id === "value" }}
                                aria-sort={h.column.getIsSorted() ? (h.column.getIsSorted() === "desc" ? "descending" : "ascending") : undefined}
                              >
                                <Show when={h.column.getCanSort()} fallback={flexRender(h.column.columnDef.header, h.getContext())}>
                                  <button type="button" class="inline-flex items-center gap-1 font-[650]" onClick={h.column.getToggleSortingHandler()}>
                                    {flexRender(h.column.columnDef.header, h.getContext())}
                                    <span aria-hidden="true">{h.column.getIsSorted() === "asc" ? "↓" : h.column.getIsSorted() === "desc" ? "↑" : ""}</span>
                                  </button>
                                </Show>
                              </th>
                            )}
                          </For>
                        </tr>
                      )}
                    </For>
                  </thead>
                  <tbody class="max-md:block">
                    <For each={rows()}>
                      {(row) => {
                        const r = row.original;
                        const selected = () => openId() === r.id;
                        const tone = KIND_TONE[r.kind];
                        return (
                          <>
                            <tr
                              id={`row-${r.id}`}
                              tabIndex={0}
                              aria-expanded={selected()}
                              aria-label={`${r.productTitle}, waiting ${r.waitingLabel}, ${r.kindLabel}`}
                              onClick={() => open(selected() ? null : r.id)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  open(selected() ? null : r.id);
                                }
                              }}
                              class="cursor-pointer border-b border-rule align-top hover:bg-paper-2 max-md:grid max-md:grid-cols-[1fr_auto] max-md:gap-x-3 max-md:px-2 max-md:py-3"
                              classList={{ "bg-paper-2 shadow-[inset_4px_0_0_var(--color-hi)]": selected() }}
                            >
                              <td class="whitespace-nowrap px-3 py-3.5 font-code text-[15px] max-md:order-2 max-md:p-0 max-md:text-right">{r.waitingLabel}</td>
                              <td class="px-3 py-3.5 max-md:order-1 max-md:p-0">
                                <span class="block text-[16.5px] font-[700]">{r.productTitle}</span>
                                <span class="font-code text-[13px] text-ink-2">{r.sku}</span>
                              </td>
                              <td class="px-3 py-3.5 text-[15px] max-md:hidden">{r.intoLabel}</td>
                              <td class="px-3 py-3.5 max-md:order-3 max-md:col-span-2 max-md:p-0 max-md:pt-1">
                                <Show when={r.proposedUs ?? r.proposedCa}>{(c) => <CodeDigits code={c().code} size="sm" leaning={c().leaning} />}</Show>
                              </td>
                              <td class="px-3 py-3.5 max-md:order-4 max-md:col-span-2 max-md:p-0 max-md:pt-1.5">
                                <KindTag tone={tone.tone} icon={tone.icon}>
                                  {r.kindLabel}
                                </KindTag>
                                <span class="mt-1 block text-[14px] text-ink-2">{r.detail}</span>
                              </td>
                              <td class="whitespace-nowrap px-3 py-3.5 text-right font-code text-[15px] max-md:hidden">{money(r.value, { cents: false })}</td>
                              <td class="whitespace-nowrap px-3 py-3.5 text-[15px] max-md:hidden">{r.withName}</td>
                            </tr>
                            <Show when={selected()}>
                              <tr class="max-md:block">
                                <td colSpan={7} class="p-0 max-md:block">
                                  <Show when={record()} fallback={<div class="bg-paper-2 px-6 py-6"><Show when={record.error} fallback={<SkeletonLines lines={4} />}><ErrorSlip error={record.error} retry={refetchRecord} /></Show></div>}>
                                    {(rec) => (
                                      <DecisionRecordView
                                        record={rec()}
                                        canDecide={canDecide()}
                                        canAnswer={can("review:answer")}
                                        importerName={importerName()}
                                        handle={(h) => (handle = h)}
                                        onAsk={() => setAsking(true)}
                                        onDecided={(out) => afterDecision(out.toast)}
                                        onConflict={(m) => {
                                          notify("Already decided", m, "error");
                                          void refetch();
                                          void refetchRecord();
                                        }}
                                      />
                                    )}
                                  </Show>
                                </td>
                              </tr>
                            </Show>
                          </>
                        );
                      }}
                    </For>
                  </tbody>
                </table>
                <Show when={table.getRowModel().rows.length > shown()}>
                  <button type="button" class={button({ tone: "ghost", size: "sm", class: "mt-4" })} onClick={() => setShown((n) => n + 15)}>
                    Show {Math.min(15, table.getRowModel().rows.length - shown())} more
                  </button>
                </Show>
              </div>
            </Show>
            <div class="mt-8 flex flex-wrap gap-x-10 gap-y-2 border-t border-rule pt-4 text-[15px] text-ink-2">
              <span>
                This week: <b class="font-code">{d()!.week.approved ?? 0}</b> approved · <b class="font-code">{d()!.week.corrected ?? 0}</b> corrected ·{" "}
                <b class="font-code">{d()!.week.questions ?? 0}</b> questions
              </span>
              <span>
                <b class="font-code">{d()!.nextRound.correctionsWaiting ?? 0}</b> corrections waiting for training round {d()!.nextRound.round}
              </span>
            </div>
          </Show>
        </Show>
      </div>
      <Sheet open={asking()} onOpenChange={setAsking} title={`Ask ${importerName()} a question`} description="The item waits for their answer. Their answer is recorded in the binder.">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void ask();
          }}
          class="space-y-3"
        >
          <label class="block text-[13px] font-[650] text-ink-2">
            Question
            <input value={question()} onInput={(e) => setQuestion(e.currentTarget.value)} class="mt-1 h-11 w-full rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-3 text-[15.5px] font-[400] text-ink" placeholder="Is the space between the walls vacuum-sealed?" />
          </label>
          <label class="block text-[13px] font-[650] text-ink-2">
            Answers they can pick (one per line, optional)
            <textarea value={options()} onInput={(e) => setOptions(e.currentTarget.value)} class="mt-1 min-h-[72px] w-full rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper px-3 py-2 text-[15.5px] font-[400] text-ink" placeholder={"Yes, vacuum-sealed\nNo, only air"} />
          </label>
          <Show when={askError()}>
            <p role="alert" class="text-[14px] font-[600] text-bad">
              {askError()}
            </p>
          </Show>
          <div class="flex gap-2">
            <button type="submit" class={button()}>
              Send the question
            </button>
            <button type="button" class={button({ tone: "ghost" })} onClick={() => setAsking(false)}>
              Not yet
            </button>
          </div>
        </form>
      </Sheet>
    </AppPage>
  );
}
