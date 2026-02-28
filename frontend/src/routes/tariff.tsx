import { SegmentGroup } from "@ark-ui/solid/segment-group";
import { TreeView, createTreeCollection } from "@ark-ui/solid/tree-view";
import { useSearchParams } from "@solidjs/router";
import { For, Show, createMemo, createResource } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { useSigned } from "~/lib/session";
import { tariff } from "~/lib/endpoints";
import type { Country, TariffLineOut, TariffOutline } from "~/lib/types";
import { ChevronIcon } from "~/ui/Icons";
import { segment } from "~/ui/recipes";
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
      <span class="w-[118px] shrink-0 font-code text-[14.5px] font-[600]" classList={{ hl: props.node.id === props.selected }}>
        {props.node.line.code}
      </span>
      <span class="min-w-0 flex-1 font-law text-[16.5px] leading-snug">{props.node.line.text}</span>
      <Show when={props.node.line.generalRate}>
        <span class="shrink-0 font-code text-[13.5px] text-ink-2">{props.node.line.generalRate}</span>
      </Show>
    </span>
  );
  return (
    <TreeView.NodeProvider node={props.node} indexPath={props.indexPath}>
      <Show
        when={props.node.children?.length}
        fallback={
          <TreeView.Item class="flex cursor-default items-baseline gap-2 border-b border-rule py-2 pl-[calc(var(--depth)*22px)] data-[selected]:bg-paper-2">
            <span class="w-4" />
            <TreeView.ItemText class="flex min-w-0 flex-1">{label()}</TreeView.ItemText>
          </TreeView.Item>
        }
      >
        <TreeView.Branch>
          <TreeView.BranchControl class="flex cursor-pointer items-baseline gap-2 border-b border-rule py-2 pl-[calc(var(--depth)*22px)] hover:bg-paper-2">
            <TreeView.BranchIndicator class="w-4 transition-transform data-[state=closed]:-rotate-90">
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
    <AppPage title="Tariff text" scope="tariff" permission="tariff:read" query={params.q} placeholder="Search the tariff: a word or a code" boxLabel="Search the tariff schedule" onSearch={(q) => setParams({ q: q || undefined, line: undefined })}>
      <div class="gm py-8">
        <div class="gl">
          <span>Search</span>
          <h1 class="not-italic">
            <b>Tariff text</b>
          </h1>
          <span class="gl-extra block">the schedule as its own indented outline</span>
        </div>
        <div class="gm-body">
          <SegmentGroup.Root value={country()} onValueChange={(d) => setParams({ c: d.value === "CA" ? "CA" : undefined, line: undefined })} class="flex items-center gap-3">
            <SegmentGroup.Label class="text-[13px] font-[700] text-ink-2">Schedule</SegmentGroup.Label>
            <div class={s.root()}>
              <SegmentGroup.Indicator class={s.indicator()} />
              <For each={[{ v: "US", l: "HTSUS" }, { v: "CA", l: "Canada's Customs Tariff" }]}>
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
              <section class="mt-6" aria-labelledby="outline-h">
                <h2 id="outline-h" class="ty-head">
                  {outline()!.line.code} in its place
                </h2>
                <p class="text-[14px] text-muted">{outline()!.editionLabel}</p>
                <TreeView.Root collection={t()} defaultExpandedValue={t().getBranchValues()} selectedValue={[outline()!.line.digits]} class="mt-3 border-t-[1.5px] border-ink" aria-label="Tariff outline">
                  <TreeView.Tree>
                    <For each={t().rootNode.children}>{(n, i) => <OutlineNode node={n} indexPath={[i()]} selected={outline()!.line.digits} />}</For>
                  </TreeView.Tree>
                </TreeView.Root>
                <Show when={outline()!.notes.length}>
                  <ul class="mt-3 space-y-1 text-[15px] text-ink-2">
                    <For each={outline()!.notes}>{(n) => <li class="font-law">{n}</li>}</For>
                  </ul>
                </Show>
              </section>
            )}
          </Show>

          <section class="mt-8" aria-label="Matching lines">
            <Show when={params.q} fallback={<EmptyState title="Search the schedule">Type a word (“vacuum”) or a code (“9617”) in the box. Results are the schedule's own lines, with their rates.</EmptyState>}>
              <Show when={!hits.error} fallback={<ErrorSlip error={hits.error} retry={refetch} />}>
                <Show when={hits()} fallback={<SkeletonLines lines={6} />}>
                  {(h) => (
                    <Show when={h().length} fallback={<EmptyState title="No lines match that">Try a broader word, or the first four digits of a code.</EmptyState>}>
                      <h2 class="ty-sub border-b-[1.5px] border-ink pb-2">
                        {h().length} lines for “{params.q}”
                      </h2>
                      <ul>
                        <For each={h()}>
                          {(l) => (
                            <li class="border-b border-rule">
                              <button type="button" class="flex w-full items-baseline gap-3 py-2.5 text-left hover:bg-paper-2" style={{ "padding-left": `${l.indent * 16}px` }} onClick={() => setParams({ line: l.code })}>
                                <span class="w-[118px] shrink-0 font-code text-[14.5px] font-[600]">{l.code}</span>
                                <span class="min-w-0 flex-1 font-law text-[16.5px]">{l.fullText}</span>
                                <span class="shrink-0 font-code text-[13.5px] text-ink-2">{l.generalRate}</span>
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
        </div>
      </div>
    </AppPage>
  );
}
