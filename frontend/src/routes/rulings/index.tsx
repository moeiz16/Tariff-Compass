import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { A, useSearchParams } from "@solidjs/router";
import { For, Show, createResource } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { useSigned } from "~/lib/session";
import { rulings } from "~/lib/endpoints";
import { dateShort, plural } from "~/lib/format";
import { Marked } from "~/ui/Marked";
import { Pager } from "~/ui/Pager";
import { chip } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { RulingStatus } from "~/ui/Status";

const STATUS = [
  { value: "", label: "Every status" },
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
    <AppPage title="Rulings" scope="rulings" permission="rulings:read" query={params.q} placeholder="Search rulings: a product, a code, a ruling number" boxLabel="Search the customs rulings" onSearch={(q) => setParams({ q, page: undefined })}>
      <div class="gm py-8">
        <div class="gl">
          <span>Search</span>
          <b>Rulings</b>
          <span class="gl-extra block">real CBP rulings, each with its status</span>
        </div>
        <div class="gm-body">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-[15.5px] text-ink-2" aria-live="polite">
              <Show when={res()} fallback="Searching the rulings…">
                {(r) => (
                  <>
                    {plural(r().total, "ruling")}
                    {params.q ? <> for “{params.q}”</> : null} · {params.q ? "most relevant first" : "newest first"}
                  </>
                )}
              </Show>
            </p>
            <ToggleGroup.Root
              value={[params.status ?? ""]}
              onValueChange={(d) => setParams({ status: d.value[0] || undefined, page: undefined })}
              class="flex flex-wrap gap-1.5"
              aria-label="Filter by status"
            >
              <For each={STATUS}>
                {(s) => (
                  <ToggleGroup.Item value={s.value} class={chip()}>
                    {s.label}
                  </ToggleGroup.Item>
                )}
              </For>
            </ToggleGroup.Root>
          </div>
          <Show when={!res.error} fallback={<div class="mt-6"><ErrorSlip error={res.error} retry={refetch} /></div>}>
            <Show when={res()} fallback={<SkeletonLines class="mt-6" lines={8} />}>
              {(r) => (
                <Show when={r().items.length} fallback={<div class="mt-6"><EmptyState title="No rulings match that">Try a product word (“tumbler”), a heading (“9617”) or a ruling number (“N321134”).</EmptyState></div>}>
                  <ol class="mt-4 border-t-[1.5px] border-ink">
                    <For each={r().items}>
                      {(h) => (
                        <li class="border-b border-rule py-4">
                          <p class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                            <A href={`/rulings/${h.key}`} class="font-code text-[17px] font-[650] underline decoration-rule underline-offset-4 hover:decoration-ink">
                              {h.id}
                            </A>
                            <span class="text-[14px] text-muted">{dateShort(h.issued)}</span>
                            <RulingStatus status={h.status} />
                            <span class="font-code text-[13.5px] text-ink-2">{h.code}</span>
                          </p>
                          <p class="mt-1 text-[16.5px] font-[650]">{h.subject}</p>
                          <p class="mt-1 font-law text-[16px] leading-[1.5] text-ink-2">
                            <Marked text={h.snippet || h.holding} spans={h.snippetMarks} />
                          </p>
                          <Show when={h.status.kind !== "in_force" && h.status.text}>
                            <p class="mt-1 text-[14px] font-[600] text-warn">{h.status.text}</p>
                          </Show>
                        </li>
                      )}
                    </For>
                  </ol>
                  <Pager count={r().total} pageSize={r().pageSize} page={page()} onPage={(p) => setParams({ page: String(p) })} label="Pages of rulings" />
                </Show>
              )}
            </Show>
          </Show>
        </div>
      </div>
    </AppPage>
  );
}
