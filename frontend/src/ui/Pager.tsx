/** Page through a list (Ark Pagination). */
import { Pagination } from "@ark-ui/solid/pagination";
import { For, Show } from "solid-js";

export function Pager(props: { count: number; pageSize: number; page: number; onPage: (p: number) => void; label: string }) {
  const cell = "grid h-9 min-w-9 place-items-center rounded-[var(--radius-btn)] border border-rule bg-card px-2 font-code text-[13px] data-[selected]:border-ink data-[selected]:bg-ink data-[selected]:text-card hover:border-rule-2 disabled:opacity-40";
  return (
    <Show when={props.count > props.pageSize}>
      <Pagination.Root count={props.count} pageSize={props.pageSize} page={props.page} onPageChange={(d) => props.onPage(d.page)} siblingCount={1} class="mt-6 flex flex-wrap items-center gap-1.5" aria-label={props.label}>
        <Pagination.PrevTrigger class={`${cell} font-sans text-[14px]`}>Previous</Pagination.PrevTrigger>
        <Pagination.Context>
          {(api) => (
            <For each={api().pages}>
              {(pg, i) =>
                pg.type === "page" ? (
                  <Pagination.Item {...pg} class={cell}>
                    {pg.value}
                  </Pagination.Item>
                ) : (
                  <Pagination.Ellipsis index={i()} class="px-1 text-muted">
                    …
                  </Pagination.Ellipsis>
                )
              }
            </For>
          )}
        </Pagination.Context>
        <Pagination.NextTrigger class={`${cell} font-sans text-[14px]`}>Next</Pagination.NextTrigger>
      </Pagination.Root>
    </Show>
  );
}
