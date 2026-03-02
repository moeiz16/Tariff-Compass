import { SegmentGroup } from "@ark-ui/solid/segment-group";
import { TreeView, createTreeCollection } from "@ark-ui/solid/tree-view";
import { useSearchParams } from "@solidjs/router";
import { For, Show, createMemo, createResource } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { LibraryHead } from "~/components/shell/Library";
import { useSigned } from "~/lib/session";
import { tariff } from "~/lib/endpoints";
import type { Country, TariffLineOut, TariffOutline } from "~/lib/types";
import { ChevronIcon } from "~/ui/Icons";
import { card, segment } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";

interface Node {
  id: string;
  line: TariffLineOut;
  children?: Node[];
}

/** Ancestors → the line → its children, as one branch of the schedule's indented outline. */
function outlineTree(o: TariffOutline): Node {
  const leaf: Node = { id: o.line.digits, line: o.line, children: o.children.length ? o.children.map((c) => ({ id: c.digits, line: c })) : undefined };
  return [...o.ancestors].reverse().reduce<Node>((child, a) => ({ id: a.digits, line: a, children: [child] }), leaf);
}

function OutlineNode(props: { node: Node; indexPath: number[]; selected: string }) {
  const label = () => (
    <span class="flex min-w-0 flex-1 items-baseline gap-3">
      <span class="w-[118px] shrink-0 font-code max-sm:w-[86px] text-[13.5px] font-[500]" classList={{ "hl font-[600]": props.node.id === props.selected }}>
        {props.node.line.code}
      </span>
      <span class="min-w-0 flex-1 text-[14.5px] leading-snug text-ink-2">{props.node.line.text}</span>
      <Show when={props.node.line.generalRate}>
        <span class="shrink-0 font-code text-[12.5px] text-muted">{props.node.line.generalRate}</span>
      </Show>
    </span>
  );
  return (
    <TreeView.NodeProvider node={props.node} indexPath={props.indexPath}>
      <Show
        when={props.node.children?.length}
        fallback={
          <TreeView.Item class="flex cursor-default items-baseline gap-2 border-b border-rule py-2.5 pl-[calc(var(--depth)*20px)] pr-4 last:border-b-0 data-[selected]:bg-hi-soft/50">
            <span class="w-4" />
            <TreeView.ItemText class="flex min-w-0 flex-1">{label()}</TreeView.ItemText>
          </TreeView.Item>
        }
      >
        <TreeView.Branch>
          <TreeView.BranchControl class="flex cursor-pointer items-baseline gap-2 border-b border-rule py-2.5 pl-[calc(var(--depth)*20px)] pr-4 hover:bg-paper-2/60">
            <TreeView.BranchIndicator class="w-4 text-muted transition-transform data-[state=closed]:-rotate-90">
              <ChevronIcon size={14} />
            </TreeView.BranchIndicator>
            <TreeView.BranchText class="flex min-w-0 flex-1">{label()}</TreeView.BranchText>
          </TreeView.BranchControl>
          <TreeView.BranchContent>
            <For each={props.node.children}>{(c, i) => <OutlineNode node={c} indexPath={[...props.indexPath, i()]} selected={props.selected} />}</For>
          </TreeView.BranchContent>
        </TreeView.Branch>
      </Show>
    </TreeView.NodeProvider>
  );
}

export default function TariffPage() {
  const signed = useSigned();
  const [params, setParams] = useSearchParams<{ q?: string; c?: string; line?: string }>();
  const country = () => (params.c === "CA" ? "CA" : "US") as Country;
  const [hits, { refetch }] = createResource(signed(() => (params.q ? { c: country(), q: params.q } : null)), (k) => tariff.search(k.c, k.q));
  const [outline] = createResource(signed(() => (params.line ? { c: country(), code: params.line } : null)), (k) => tariff.line(k.c, k.code));
  const tree = createMemo(() => {
    const o = outline();
    if (!o) return null;
    const root = { id: "root", line: o.line, children: [outlineTree(o)] } as Node;
    return createTreeCollection<Node>({ rootNode: root, nodeToValue: (n) => n.id, nodeToString: (n) => `${n.line.code} ${n.line.text}`, nodeToChildren: (n) => n.children ?? [] });
  });
  const s = segment();
  return (
    <AppPage title="Tariff text" place="library" permission="tariff:read" width="default">
      <LibraryHead active="tariff" query={params.q} placeholder="A word or a code" onSearch={(q) => setParams({ q: q || undefined, line: undefined })} />
      <SegmentGroup.Root value={country()} onValueChange={(d) => setParams({ c: d.value === "CA" ? "CA" : undefined, line: undefined })} class="mb-5 flex items-center gap-2.5">
        <SegmentGroup.Label class="text-[12.5px] font-[550] text-muted">Schedule</SegmentGroup.Label>
        <div class={s.root()}>
          <SegmentGroup.Indicator class={s.indicator()} />
          <For each={[{ v: "US", l: "United States" }, { v: "CA", l: "Canada" }]}>
            {(o) => (
              <SegmentGroup.Item value={o.v} class={s.item()}>
                <SegmentGroup.ItemText>{o.l}</SegmentGroup.ItemText>
                <SegmentGroup.ItemControl />
                <SegmentGroup.ItemHiddenInput />
              </SegmentGroup.Item>
            )}
          </For>
        </div>
      </SegmentGroup.Root>

      <Show when={tree()}>
        {(t) => (
          <section class="mb-6" aria-label={`${outline()!.line.code} in its place`}>
            <p class="mb-2 text-[12.5px] text-muted">{outline()!.editionLabel}</p>
            <TreeView.Root collection={t()} defaultExpandedValue={t().getBranchValues()} selectedValue={[outline()!.line.digits]} class={card({ class: "overflow-hidden pl-3" })} aria-label="Tariff outline">
              <TreeView.Tree>
                <For each={t().rootNode.children}>{(n, i) => <OutlineNode node={n} indexPath={[i()]} selected={outline()!.line.digits} />}</For>
              </TreeView.Tree>
            </TreeView.Root>
            <Show when={outline()!.notes.length}>
              <ul class="mt-3 space-y-1 text-[13.5px] text-muted">
                <For each={outline()!.notes}>{(n) => <li>{n}</li>}</For>
              </ul>
            </Show>
          </section>
        )}
      </Show>

      <section aria-label="Matching lines">
        <Show
          when={params.q}
          fallback={
            <div class={card()}>
              <EmptyState title="Search the schedule">Try “vacuum” or “9617”.</EmptyState>
            </div>
          }
        >
          <Show when={!hits.error} fallback={<ErrorSlip error={hits.error} retry={refetch} />}>
            <Show when={hits()} fallback={<SkeletonLines lines={6} />}>
              {(h) => (
                <Show
                  when={h().length}
                  fallback={
                    <div class={card()}>
                      <EmptyState title="No lines match" />
                    </div>
                  }
                >
                  <p class="mb-2 text-[13px] text-muted">{h().length} lines</p>
                  <ul class={card({ class: "overflow-hidden" })}>
                    <For each={h()}>
                      {(l) => (
                        <li class="border-b border-rule last:border-b-0">
                          <button
                            type="button"
                            class="flex w-full items-baseline gap-3 py-2.5 pr-5 text-left hover:bg-paper-2/60"
                            classList={{ "bg-hi-soft/40": params.line === l.code }}
                            style={{ "padding-left": `${20 + l.indent * 16}px` }}
                            onClick={() => setParams({ line: l.code })}
                          >
                            <span class="w-[118px] shrink-0 font-code max-sm:w-[86px] text-[13.5px] font-[500]">{l.code}</span>
                            <span class="min-w-0 flex-1 text-[14.5px] text-ink-2">{l.fullText}</span>
                            <span class="shrink-0 font-code text-[12.5px] text-muted">{l.generalRate}</span>
                          </button>
                        </li>
                      )}
                    </For>
                  </ul>
                </Show>
              )}
            </Show>
          </Show>
        </Show>
      </section>
    </AppPage>
  );
}
