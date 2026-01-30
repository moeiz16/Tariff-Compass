import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { createSolidTable, flexRender, getCoreRowModel, type ColumnDef } from "@tanstack/solid-table";
import { A, useSearchParams } from "@solidjs/router";
import { For, Show, createResource } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { useSigned } from "~/lib/session";
import { products } from "~/lib/endpoints";
import { dateShort, plural } from "~/lib/format";
import type { ProductSummary } from "~/lib/types";
import { CodeDigits } from "~/ui/Code";
import { Pager } from "~/ui/Pager";
import { chip } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { StandingTag } from "~/ui/Standing";

const STANDINGS = [
  { value: "", label: "Every product" },
  { value: "approved", label: "Approved" },
  { value: "in_review", label: "With the broker" },
  { value: "needs_recheck", label: "Needs a re-check" },
  { value: "proposed", label: "Proposed" },
];

export default function ProductsPage() {
  const signed = useSigned();
  const [params, setParams] = useSearchParams<{ q?: string; standing?: string; page?: string }>();
  const page = () => Number(params.page ?? 1);
  const [list, { refetch }] = createResource(signed(() => ({ q: params.q ?? "", standing: params.standing ?? "", page: page() })), (k) => products.list({ ...k, pageSize: 25 }));
  const columns: ColumnDef<ProductSummary>[] = [
    { id: "product", header: "Product", cell: (c) => c.row.original.title },
    { id: "us", header: "US code" },
    { id: "ca", header: "Canada code" },
    { id: "standing", header: "Standing" },
    { id: "versions", header: "Versions" },
    { id: "last", header: "Last decided" },
  ];
  const table = createSolidTable({
    get data() {
      return list()?.items ?? [];
    },
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
  return (
    <AppPage title="My products" scope="products" permission="products:read" query={params.q} placeholder="Search your products: name, SKU or code" boxLabel="Search your products" onSearch={(q) => setParams({ q: q || undefined, page: undefined })}>
      <div class="px-8 py-6 max-md:px-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-[16.5px]" aria-live="polite">
            <Show when={list()} fallback="Opening your products…">
              {(l) => (
                <>
                  <b>{plural(l().total, "product")}</b>
                  <span class="text-ink-2"> · each keeps a binder, its reasonable-care record</span>
                </>
              )}
            </Show>
          </p>
          <ToggleGroup.Root value={[params.standing ?? ""]} onValueChange={(d) => setParams({ standing: d.value[0] || undefined, page: undefined })} class="flex flex-wrap gap-2" aria-label="Filter by standing">
            <For each={STANDINGS}>
              {(s) => (
                <ToggleGroup.Item value={s.value} class={chip()}>
                  {s.label}
                </ToggleGroup.Item>
              )}
            </For>
          </ToggleGroup.Root>
        </div>
        <Show when={!list.error} fallback={<div class="mt-6"><ErrorSlip error={list.error} retry={refetch} /></div>}>
          <Show when={list()} fallback={<SkeletonLines class="mt-6" lines={10} />}>
            {(l) => (
              <Show when={l().items.length} fallback={<div class="mt-6"><EmptyState title="No products match that">Clear the search, or classify a product and save it to a binder.</EmptyState></div>}>
                <div class="mt-5 overflow-x-auto">
                  <table class="w-full min-w-[860px] border-collapse text-left max-md:min-w-0">
                    <caption class="sr-only">Your products and their current codes</caption>
                    <thead class="max-md:hidden">
                      <For each={table.getHeaderGroups()}>
                        {(hg) => (
                          <tr class="border-b-[1.5px] border-ink text-[14px] text-ink-2">
                            <For each={hg.headers}>{(h) => <th scope="col" class="px-3 py-2.5 font-[650]">{flexRender(h.column.columnDef.header, h.getContext())}</th>}</For>
                          </tr>
                        )}
                      </For>
                    </thead>
                    <tbody>
                      <For each={table.getRowModel().rows}>
                        {(row) => {
                          const p = row.original;
                          return (
                            <tr class="border-b border-rule align-top hover:bg-paper-2 max-md:grid max-md:grid-cols-[1fr_auto] max-md:gap-1 max-md:py-3">
                              <td class="px-3 py-3 max-md:col-span-2 max-md:p-0">
                                <A href={`/products/${p.sku}`} class="text-[16.5px] font-[700] underline decoration-rule underline-offset-4 hover:decoration-ink">
                                  {p.title}
                                </A>
                                <span class="block font-code text-[13px] text-ink-2">
                                  {p.sku} · {p.categoryLabel.toLowerCase()} · from {p.madeInLabel}
                                </span>
                              </td>
                              <td class="px-3 py-3 max-md:p-0">
                                <Show when={p.usCode} fallback={<span class="text-muted">–</span>}>
                                  <CodeDigits code={p.usCode!} size="sm" />
                                </Show>
                              </td>
                              <td class="px-3 py-3 max-md:hidden">
                                <Show when={p.caCode} fallback={<span class="text-muted">–</span>}>
                                  <CodeDigits code={p.caCode!} size="sm" />
                                </Show>
                              </td>
                              <td class="px-3 py-3 max-md:p-0 max-md:text-right">
                                <StandingTag standing={p.standing} label={p.standingLabel} />
                              </td>
                              <td class="px-3 py-3 font-code text-[14px] max-md:hidden">v{p.versions}</td>
                              <td class="px-3 py-3 text-[14px] text-ink-2 max-md:hidden">{p.lastDecidedAt ? dateShort(p.lastDecidedAt) : "–"}</td>
                            </tr>
                          );
                        }}
                      </For>
                    </tbody>
                  </table>
                </div>
                <Pager count={l().total} pageSize={l().pageSize} page={page()} onPage={(n) => setParams({ page: String(n) })} label="Pages of products" />
              </Show>
            )}
          </Show>
        </Show>
      </div>
    </AppPage>
  );
}
