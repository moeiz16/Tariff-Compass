import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { createSolidTable, flexRender, getCoreRowModel, type ColumnDef } from "@tanstack/solid-table";
import { A, useSearchParams } from "@solidjs/router";
import { For, Show, createResource } from "solid-js";
import { AppPage, PageHead, PageSearch } from "~/components/shell/AppPage";
import { useSigned } from "~/lib/session";
import { products } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import type { ProductSummary } from "~/lib/types";
import { CodeDigits } from "~/ui/Code";
import { Pager } from "~/ui/Pager";
import { card, chip } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { StandingTag } from "~/ui/Standing";

const STANDINGS = [
  { value: "", label: "All" },
  { value: "approved", label: "Approved" },
  { value: "in_review", label: "With broker" },
  { value: "needs_recheck", label: "Re-check" },
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
    { id: "standing", header: "Standing" },
    { id: "last", header: "Decided" },
  ];
  const table = createSolidTable({
    get data() {
      return list()?.items ?? [];
    },
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
  return (
    <AppPage title="Products" place="products" permission="products:read" width="wide">
      <PageHead
        title="Products"
        meta={<Show when={list()}>{(l) => <span aria-live="polite">{l().total} with a binder</span>}</Show>}
        actions={<PageSearch label="Search your products" placeholder="Name, SKU or code" value={params.q} onSearch={(q) => setParams({ q: q || undefined, page: undefined })} />}
      />
      <ToggleGroup.Root value={[params.standing ?? ""]} onValueChange={(d) => setParams({ standing: d.value[0] || undefined, page: undefined })} class="mb-4 flex flex-wrap gap-2" aria-label="Filter by standing">
        <For each={STANDINGS}>
          {(s) => (
            <ToggleGroup.Item value={s.value} class={chip()}>
              {s.label}
            </ToggleGroup.Item>
          )}
        </For>
      </ToggleGroup.Root>
      <Show when={!list.error} fallback={<ErrorSlip error={list.error} retry={refetch} />}>
        <Show when={list()} fallback={<SkeletonLines lines={10} />}>
          {(l) => (
            <Show
              when={l().items.length}
              fallback={
                <div class={card()}>
                  <EmptyState title="No products match" />
                </div>
              }
            >
              <div class={card({ class: "overflow-hidden" })}>
                <table class="w-full border-collapse text-left">
                  <caption class="sr-only">Your products and their current codes</caption>
                  <thead class="max-md:hidden">
                    <For each={table.getHeaderGroups()}>
                      {(hg) => (
                        <tr class="border-b border-rule bg-paper-2/50 text-[12.5px] text-muted">
                          <For each={hg.headers}>
                            {(h) => (
                              <th scope="col" class="px-5 py-2.5 font-[600]" classList={{ "text-right": h.id === "last" }}>
                                {flexRender(h.column.columnDef.header, h.getContext())}
                              </th>
                            )}
                          </For>
                        </tr>
                      )}
                    </For>
                  </thead>
                  <tbody>
                    <For each={table.getRowModel().rows}>
                      {(row) => {
                        const p = row.original;
                        return (
                          <tr class="relative border-b border-rule align-middle last:border-b-0 hover:bg-paper-2/60 max-md:grid max-md:grid-cols-[1fr_auto] max-md:gap-1.5 max-md:px-4 max-md:py-3">
                            <td class="px-5 py-3.5 max-md:col-span-2 max-md:p-0">
                              <A href={`/products/${p.sku}`} class="text-[14.5px] font-[600] no-underline after:absolute after:inset-0">
                                {p.title}
                              </A>
                              <span class="block font-code text-[12px] text-muted">{p.sku}</span>
                            </td>
                            <td class="px-5 py-3.5 max-md:p-0">
                              <Show when={p.usCode} fallback={<span class="text-muted">–</span>}>
                                <CodeDigits code={p.usCode!} size="sm" />
                              </Show>
                            </td>
                            <td class="px-5 py-3.5 max-md:p-0 max-md:text-right">
                              <StandingTag standing={p.standing} label={p.standingLabel} />
                            </td>
                            <td class="px-5 py-3.5 text-right text-[13px] text-muted max-md:hidden">{p.lastDecidedAt ? dateShort(p.lastDecidedAt) : "–"}</td>
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
    </AppPage>
  );
}
