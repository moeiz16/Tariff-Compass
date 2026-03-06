import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { createSolidTable, flexRender, getCoreRowModel, getSortedRowModel, type ColumnDef, type SortingState } from "@tanstack/solid-table";
import { useSearchParams } from "@solidjs/router";
import { For, Show, createEffect, createResource, createSignal, onCleanup, onMount } from "solid-js";
import { DecisionRecordView, type RecordHandle } from "~/components/review/DecisionRecord";
import { AppPage, PageHead, PageSearch } from "~/components/shell/AppPage";
import { docketKeyAction, isTyping } from "~/lib/docket";
import { review } from "~/lib/endpoints";
import { money } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession, useSigned } from "~/lib/session";
import type { DocketFilter, ReviewRow } from "~/lib/types";
import { CodeDigits } from "~/ui/Code";
import { button, card, chip, field } from "~/ui/recipes";
import { Drawer, Sheet } from "~/ui/Sheet";
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

/** The reason in plain words ("Classifier unsure" → "Unsure"). */
const kindWord = (label: string) => label.replace(/^Classifier unsure$/i, "Unsure");

const FILTERS: { value: DocketFilter; label: string; count: "all" | "unsure" | "differs" | "rulingChanged" | "always" | "ca" }[] = [
  { value: "all", label: "All", count: "all" },
  { value: "unsure", label: "Unsure", count: "unsure" },
  { value: "differs", label: "Differs", count: "differs" },
  { value: "ruling_changed", label: "Ruling changed", count: "rulingChanged" },
  { value: "always", label: "Always", count: "always" },
  { value: "ca", label: "Canada", count: "ca" },
];

export default function ReviewPage() {
  const signed = useSigned();
  const { can, me } = useSession();
  const [params, setParams] = useSearchParams<{ filter?: string; q?: string; open?: string }>();
  const filter = () => (params.filter as DocketFilter) ?? "all";
  const [docket, { refetch }] = createResource(signed(() => ({ filter: filter(), q: params.q ?? "" })), (k) => review.docket(k));
  const [sorting, setSorting] = createSignal<SortingState>([{ id: "waiting", desc: false }]);
  const [shown, setShown] = createSignal(15);
  const openId = () => params.open ?? null;
  const [record, { refetch: refetchRecord }] = createResource(signed(() => openId()), (id) => review.get(id));
  const [asking, setAsking] = createSignal(false);
  const [question, setQuestion] = createSignal("");
  const [options, setOptions] = createSignal("");
  const [askError, setAskError] = createSignal("");
  let handle: RecordHandle | null = null;
  const canDecide = () => can("review:decide");
  const fl = field();
  const importerName = () => me()?.activeOrg?.name.split(" ")[0] ?? "the importer";

  const columns: ColumnDef<ReviewRow>[] = [
    { id: "product", header: "Product", accessorFn: (r) => r.productTitle },
    { id: "proposed", header: "Proposed", accessorFn: (r) => r.proposedUs?.code ?? r.proposedCa?.code ?? "", enableSorting: false },
    { id: "why", header: "Why", accessorFn: (r) => r.kindLabel, enableSorting: false },
    { id: "waiting", header: "Waiting", accessorFn: (r) => r.waitingSince, sortingFn: "alphanumeric" },
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
  };
  const move = (delta: number) => {
    const list = rows().map((r) => r.original.id);
    if (!list.length) return;
    const at = openId() ? list.indexOf(openId()!) : -1;
    const next = list[Math.max(0, Math.min(list.length - 1, at + delta))] ?? list[0]!;
    open(next);
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
  const openRow = () => (openId() ? (d()?.items.find((r) => r.id === openId()) ?? record()?.row ?? null) : null);
  return (
    <AppPage title="Review" place="review" permission="review:read" width="wide">
      <PageHead
        title="Review"
        meta={
          <Show when={d()}>
            {(x) => (
              <>
                <span>{x().counts.all} waiting</span>
                <span aria-hidden="true">·</span>
                <span>{x().oldestLabel}</span>
              </>
            )}
          </Show>
        }
        actions={<PageSearch label="Search the queue" placeholder="Product, SKU or code" value={params.q} onSearch={(q) => setParams({ q: q || undefined, open: undefined })} />}
      />
      <ToggleGroup.Root
        value={[filter()]}
        onValueChange={(v) => setParams({ filter: v.value[0] && v.value[0] !== "all" ? v.value[0] : undefined, open: undefined })}
        class="mb-4 flex flex-wrap gap-2"
        aria-label="Filter the queue"
      >
        <For each={FILTERS}>
          {(f) => (
            <ToggleGroup.Item value={f.value} class={chip()}>
              {f.label}
              <span class="text-[11.5px] opacity-70">{d()?.counts[f.count] ?? ""}</span>
            </ToggleGroup.Item>
          )}
        </For>
      </ToggleGroup.Root>

      <Show when={!docket.error} fallback={<ErrorSlip error={docket.error} retry={refetch} />}>
        <Show when={d()} fallback={<SkeletonLines lines={10} />}>
          <Show
            when={d()!.items.length}
            fallback={
              <div class={card()}>
                <EmptyState title={params.q || filter() !== "all" ? "Nothing matches" : "All clear"}>{params.q || filter() !== "all" ? undefined : d()!.emptyMessage}</EmptyState>
              </div>
            }
          >
            <div class={card({ class: "overflow-hidden" })}>
              <table class="w-full border-collapse text-left max-md:block">
                <caption class="sr-only">Review queue, oldest first. Select a row to open its decision.</caption>
                <thead class="max-md:hidden">
                  <For each={table.getHeaderGroups()}>
                    {(hg) => (
                      <tr class="border-b border-rule bg-paper-2/50 text-[12.5px] text-muted">
                        <For each={hg.headers.filter((h) => ["product", "proposed", "why", "waiting"].includes(h.id))}>
                          {(h) => (
                            <th
                              scope="col"
                              class="px-5 py-2.5 font-[600]"
                              classList={{ "text-right": h.id === "waiting" }}
                              aria-sort={h.column.getIsSorted() ? (h.column.getIsSorted() === "desc" ? "descending" : "ascending") : undefined}
                            >
                              <Show when={h.column.getCanSort()} fallback={flexRender(h.column.columnDef.header, h.getContext())}>
                                <button type="button" class="inline-flex items-center gap-1 font-[600] hover:text-ink" onClick={h.column.getToggleSortingHandler()}>
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
                        <tr
                          id={`row-${r.id}`}
                          tabIndex={0}
                          aria-expanded={selected()}
                          aria-label={`${r.productTitle}, waiting ${r.waitingLabel}, ${r.kindLabel}`}
                          onClick={() => open(r.id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              open(r.id);
                            }
                          }}
                          class="cursor-pointer border-b border-rule align-middle last:border-b-0 hover:bg-paper-2/60 max-md:grid max-md:grid-cols-[1fr_auto] max-md:gap-x-3 max-md:gap-y-1.5 max-md:px-4 max-md:py-3"
                          classList={{ "bg-paper-2": selected() }}
                        >
                          <td class="px-5 py-3.5 max-md:col-span-2 max-md:p-0">
                            <span class="block text-[14.5px] font-[600]">{r.productTitle}</span>
                            <span class="font-code text-[12px] text-muted">{r.sku}</span>
                          </td>
                          <td class="px-5 py-3.5 max-md:p-0">
                            <Show when={r.proposedUs ?? r.proposedCa}>{(c) => <CodeDigits code={c().code} size="sm" leaning={c().leaning} />}</Show>
                          </td>
                          <td class="px-5 py-3.5 max-md:order-first max-md:hidden">
                            <KindTag tone={tone.tone} icon={tone.icon}>
                              {kindWord(r.kindLabel)}
                            </KindTag>
                          </td>
                          <td class="whitespace-nowrap px-5 py-3.5 text-right text-[13px] text-muted max-md:p-0">{r.waitingLabel}</td>
                          <td class="hidden max-md:col-span-2 max-md:block max-md:p-0">
                            <KindTag tone={tone.tone} icon={tone.icon}>
                              {kindWord(r.kindLabel)}
                            </KindTag>
                          </td>
                        </tr>
                      );
                    }}
                  </For>
                </tbody>
              </table>
            </div>
            <Show when={table.getRowModel().rows.length > shown()}>
              <button type="button" class={button({ tone: "outline", size: "sm", class: "mt-4" })} onClick={() => setShown((n) => n + 15)}>
                Show {Math.min(15, table.getRowModel().rows.length - shown())} more
              </button>
            </Show>
          </Show>
          <p class="mt-4 text-[12.5px] text-muted">
            This week {d()!.week.approved ?? 0} approved · {d()!.week.corrected ?? 0} corrected · {d()!.nextRound.correctionsWaiting ?? 0} corrections for round {d()!.nextRound.round}
          </p>
        </Show>
      </Show>

      <Drawer
        open={!!openId()}
        onOpenChange={(o) => !o && open(null)}
        width={620}
        label={openRow() ? `Decision for ${openRow()!.productTitle}` : "Decision"}
        title={openRow()?.productTitle ?? "Opening…"}
        meta={
          <Show when={openRow()}>
            {(r) => (
              <>
                <span class="font-code">{r().sku}</span>
                <span aria-hidden="true">·</span>
                <span>Into {r().intoLabel}</span>
                <Show when={r().value}>
                  <span aria-hidden="true">·</span>
                  <span>Shipment {money(r().value!, { cents: false })}</span>
                </Show>
                <span aria-hidden="true">·</span>
                <KindTag tone={KIND_TONE[r().kind].tone} icon={KIND_TONE[r().kind].icon}>
                  {kindWord(r().kindLabel)}
                </KindTag>
              </>
            )}
          </Show>
        }
      >
        <Show when={openRow()?.detail}>
          <p class="mb-6 text-[14px] text-ink-2">{openRow()!.detail}</p>
        </Show>
        <Show
          when={record()?.row.id === openId() ? record() : undefined}
          keyed
          fallback={
            <Show when={record.error} fallback={<SkeletonLines lines={6} />}>
              <ErrorSlip error={record.error} retry={refetchRecord} />
            </Show>
          }
        >
          {(rec) => (
            <DecisionRecordView
              record={rec}
              canDecide={canDecide()}
              canAnswer={can("review:answer")}
              importerName={importerName()}
              detail={openRow()?.detail}
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
      </Drawer>
      <Sheet open={asking()} onOpenChange={setAsking} title={`Ask ${importerName()}`} description="The item waits for their answer.">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void ask();
          }}
          class="space-y-3"
        >
          <label class={fl.label({ class: "block" })}>
            Question
            <input value={question()} onInput={(e) => setQuestion(e.currentTarget.value)} class={fl.input({ class: "mt-1 font-[400]" })} placeholder="Is the space between the walls vacuum-sealed?" />
          </label>
          <label class={fl.label({ class: "block" })}>
            Answers to pick from (optional, one per line)
            <textarea value={options()} onInput={(e) => setOptions(e.currentTarget.value)} class={fl.textarea({ class: "mt-1 min-h-[72px] font-[400]" })} placeholder={"Yes, vacuum-sealed\nNo, only air"} />
          </label>
          <Show when={askError()}>
            <p role="alert" class="text-[14px] font-[600] text-bad">
              {askError()}
            </p>
          </Show>
          <div class="flex justify-end gap-2">
            <button type="button" class={button({ tone: "ghost" })} onClick={() => setAsking(false)}>
              Cancel
            </button>
            <button type="submit" class={button()}>
              Send
            </button>
          </div>
        </form>
      </Sheet>
    </AppPage>
  );
}
