/** The Library's head: one title, the Rulings / Tariff text switch, and the search for the current one. */
import { SegmentGroup } from "@ark-ui/solid/segment-group";
import { useNavigate } from "@solidjs/router";
import { For, Show } from "solid-js";
import { useSession } from "~/lib/session";
import { segment } from "~/ui/recipes";
import { PageHead, PageSearch } from "./AppPage";

export function LibraryHead(props: { active: "rulings" | "tariff"; query?: string; placeholder: string; onSearch: (q: string) => void }) {
  const navigate = useNavigate();
  const { can } = useSession();
  const s = segment();
  const items = () => [
    ...(can("rulings:read") ? [{ v: "rulings", l: "Rulings", href: "/rulings" }] : []),
    ...(can("tariff:read") ? [{ v: "tariff", l: "Tariff text", href: "/tariff" }] : []),
  ];
  return (
    <>
      <PageHead title="Library" actions={<PageSearch label={props.active === "rulings" ? "Search the rulings" : "Search the tariff"} placeholder={props.placeholder} value={props.query} onSearch={props.onSearch} />} />
      <Show when={items().length > 1}>
        <SegmentGroup.Root value={props.active} onValueChange={(d) => d.value && d.value !== props.active && navigate(items().find((i) => i.v === d.value)!.href)} class="mb-5" aria-label="Library">
          <div class={s.root()}>
            <SegmentGroup.Indicator class={s.indicator()} />
            <For each={items()}>
              {(o) => (
                <SegmentGroup.Item value={o.v} class={`${s.item()} px-4 py-1.5`}>
                  <SegmentGroup.ItemText>{o.l}</SegmentGroup.ItemText>
                  <SegmentGroup.ItemControl />
                  <SegmentGroup.ItemHiddenInput />
                </SegmentGroup.Item>
              )}
            </For>
          </div>
        </SegmentGroup.Root>
      </Show>
    </>
  );
}
