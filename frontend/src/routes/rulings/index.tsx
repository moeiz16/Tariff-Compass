import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { A, useSearchParams } from "@solidjs/router";
import { For, Show, createResource } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { LibraryHead } from "~/components/shell/Library";
import { useSigned } from "~/lib/session";
import { rulings } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import { Pager } from "~/ui/Pager";
import { card, chip } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { RulingStatus } from "~/ui/Status";

const STATUS = [
  { value: "", label: "All" },
  { value: "in_force", label: "In force" },
  { value: "modified", label: "Modified" },
  { value: "revoked", label: "Revoked" },
];

export default function RulingsPage() {
  const signed = useSigned();
  const [params, setParams] = useSearchParams<{ q?: string; status?: string; sort?: string; page?: string }>();
  const page = () => Number(params.page ?? 1);
  const [res, { refetch }] = createResource(
    signed(() => ({ q: params.q ?? "", status: params.status ?? "", sort: params.sort ?? (params.q ? "relevance" : "newest"), page: page() })),
    (k) => rulings.search({ ...k, pageSize: 20 }),
  );
  return (
    <AppPage title="Rulings" place="library" permission="rulings:read" width="default">
      <LibraryHead active="rulings" query={params.q} placeholder="Product, code or ruling number" onSearch={(q) => setParams({ q: q || undefined, page: undefined })} />
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <ToggleGroup.Root value={[params.status ?? ""]} onValueChange={(d) => setParams({ status: d.value[0] || undefined, page: undefined })} class="flex flex-wrap gap-2" aria-label="Filter by status">
          <For each={STATUS}>
            {(s) => (
              <ToggleGroup.Item value={s.value} class={chip()}>
                {s.label}
              </ToggleGroup.Item>
            )}
          </For>
        </ToggleGroup.Root>
        <p class="text-[13px] text-muted" aria-live="polite">
          <Show when={res()}>{(r) => <>{r().total.toLocaleString("en-US")} {params.q ? "matches" : "rulings, newest first"}</>}</Show>
        </p>
      </div>
      <Show when={!res.error} fallback={<ErrorSlip error={res.error} retry={refetch} />}>
        <Show when={res()} fallback={<SkeletonLines lines={8} />}>
          {(r) => (
            <Show
              when={r().items.length}
              fallback={
                <div class={card()}>
                  <EmptyState title="No rulings match">Try “tumbler”, “9617” or “N321134”.</EmptyState>
                </div>
              }
            >
              <ol class={card({ class: "overflow-hidden" })}>
                <For each={r().items}>
                  {(h) => (
                    <li class="relative border-b border-rule px-5 py-4 last:border-b-0 hover:bg-paper-2/60 max-sm:px-4">
                      <p class="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <A href={`/rulings/${h.key}`} class="font-code text-[14.5px] font-[600] no-underline after:absolute after:inset-0">
                          {h.id}
                        </A>
                        <RulingStatus status={h.status} />
                        <span class="ml-auto text-[12.5px] text-muted">{dateShort(h.issued)}</span>
                      </p>
                      <p class="mt-1 line-clamp-1 text-[14.5px] text-ink-2">{h.subject}</p>
                    </li>
                  )}
                </For>
              </ol>
              <Pager count={r().total} pageSize={r().pageSize} page={page()} onPage={(p) => setParams({ page: String(p) })} label="Pages of rulings" />
            </Show>
          )}
        </Show>
      </Show>
    </AppPage>
  );
}
