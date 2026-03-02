import { Collapsible } from "@ark-ui/solid/collapsible";
import { Splitter } from "@ark-ui/solid/splitter";
import { Tabs } from "@ark-ui/solid/tabs";
import { A, useParams, useSearchParams } from "@solidjs/router";
import { For, Match, Show, Switch, createResource } from "solid-js";
import { AppPage, PageHead } from "~/components/shell/AppPage";
import { rulings } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import { useSigned } from "~/lib/session";
import type { CompareOut, RulingDetail } from "~/lib/types";
import { ChevronIcon, ExternalIcon } from "~/ui/Icons";
import { Marked } from "~/ui/Marked";
import { button, card, tabs } from "~/ui/recipes";
import { ErrorSlip, PageLoading } from "~/ui/States";
import { MatchMark, RulingStatus } from "~/ui/Status";

function Letter(props: { ruling: RulingDetail; marked?: { start: number; end: number }[] }) {
  const paras = () => (props.ruling.paragraphs.length ? props.ruling.paragraphs : [{ start: 0, end: props.ruling.text.length }]);
  return (
    <div class="space-y-4 text-[15px] leading-[1.7] text-ink-2 max-sm:text-[14px]">
      <For each={paras()}>
        {(p) => {
          const text = props.ruling.text.slice(p.start, p.end);
          const spans = (props.marked ?? []).filter((m) => m.start < p.end && m.end > p.start).map((m) => ({ start: Math.max(0, m.start - p.start), end: Math.min(text.length, m.end - p.start) }));
          return (
            <p>
              <Marked text={text} spans={spans} />
            </p>
          );
        }}
      </For>
    </div>
  );
}

/** Your product against the ruling: the facts one by one, then both texts side by side. */
function CompareTab(props: { c: CompareOut }) {
  const r = () => props.c.ruling;
  return (
    <div class="space-y-4">
      <div class={card({ class: "overflow-hidden" })}>
        <table class="w-full border-collapse text-left max-md:block">
          <caption class="sr-only">Your product's facts against the ruling's article</caption>
          <thead class="border-b border-rule bg-paper-2/50 text-[12.5px] text-muted max-md:hidden">
            <tr>
              <th class="px-5 py-2.5 font-[600]">Fact</th>
              <th class="px-5 py-2.5 font-[600]">Yours</th>
              <th class="px-5 py-2.5 font-[600]">{r().id}</th>
              <th class="px-5 py-2.5 font-[600]">
                <span class="sr-only">Match</span>
              </th>
            </tr>
          </thead>
          <tbody class="max-md:block">
            <For each={props.c.alignment}>
              {(f) => (
                <tr class="border-b border-rule align-top text-[14.5px] last:border-b-0 max-md:block max-md:px-4 max-md:py-3">
                  <th scope="row" class="px-5 py-3 font-[550] text-muted max-md:block max-md:p-0">
                    {f.fact}
                  </th>
                  <td class="px-5 py-3 max-md:block max-md:p-0 max-md:pt-1">
                    <span class="hidden text-[12.5px] text-muted max-md:inline">Yours · </span>
                    {f.yours}
                  </td>
                  <td class="px-5 py-3 text-ink-2 max-md:block max-md:p-0 max-md:pt-1">
                    <span class="hidden text-[12.5px] text-muted max-md:inline">Ruling · </span>
                    {f.theirs}
                  </td>
                  <td class="px-5 py-3 text-right max-md:block max-md:p-0 max-md:pt-1 max-md:text-left">
                    <MatchMark match={f.match} label={f.matchLabel} />
                  </td>
                </tr>
              )}
            </For>
          </tbody>
        </table>
      </div>
      <Collapsible.Root>
        <Collapsible.Trigger class={button({ tone: "outline", size: "sm", class: "group" })}>
          Side by side
          <ChevronIcon size={13} class="transition-transform group-data-[state=open]:rotate-180" />
        </Collapsible.Trigger>
        <Collapsible.Content class="fold">
          <section class={card({ class: "mt-4 p-5 max-sm:p-4" })} aria-label="Your evidence and the ruling letter">
            <Splitter.Root
              panels={[
                { id: "yours", minSize: 25, maxSize: 75 },
                { id: "ruling", minSize: 25, maxSize: 75 },
              ]}
              defaultSize={[45, 55]}
              class="flex min-h-[380px] max-md:!flex-col"
            >
              <Splitter.Panel id="yours" class="min-w-0 overflow-auto pr-5 max-md:!w-full max-md:pr-0">
                <p class="label flex justify-between gap-2">
                  {props.c.productTitle}
                  <span class="font-[450]">{props.c.madeInLabel}</span>
                </p>
                <dl class="mt-3 space-y-4">
                  <For each={props.c.evidence}>
                    {(e) => (
                      <div>
                        <dt class="text-[12.5px] text-muted">{e.label}</dt>
                        <dd class="mt-1 text-[14.5px] leading-[1.6]">
                          <Marked text={e.text} spans={e.marked} />
                        </dd>
                      </div>
                    )}
                  </For>
                </dl>
              </Splitter.Panel>
              <Splitter.ResizeTrigger
                id="yours:ruling"
                aria-label="Resize the two panes"
                class="relative w-[14px] shrink-0 cursor-col-resize before:absolute before:inset-y-0 before:left-1/2 before:w-px before:-translate-x-1/2 before:bg-rule hover:before:bg-ink-2 data-[focus]:before:bg-ink max-md:hidden"
              />
              <Splitter.Panel id="ruling" class="min-w-0 overflow-auto pl-5 max-md:!w-full max-md:pl-0 max-md:pt-6">
                <p class="label">{r().id}</p>
                <div class="mt-3">
                  <Letter ruling={r()} marked={props.c.rulingMarked} />
                </div>
              </Splitter.Panel>
            </Splitter.Root>
          </section>
        </Collapsible.Content>
      </Collapsible.Root>
    </div>
  );
}

function RulingView(props: { r: RulingDetail; compare?: CompareOut; answerId?: string }) {
  const t = tabs();
  const related = () => props.r.related.length + props.r.alsoCitedIn.length;
  const row = "flex items-center justify-between gap-4 border-b border-rule px-5 py-3 text-[14px] last:border-b-0";
  return (
    <>
      <p class="mb-2 text-[13px]">
        <Show
          when={props.answerId}
          fallback={
            <A href="/rulings" class="text-muted no-underline hover:text-ink">
              Library
            </A>
          }
        >
          <A href={`/answer?id=${props.answerId}`} class="text-muted no-underline hover:text-ink">
            Back to the answer
          </A>
        </Show>
      </p>
      <PageHead
        title={<span class="font-code tracking-[-0.01em]">{props.r.id}</span>}
        meta={
          <>
            <RulingStatus status={props.r.status} long />
            <span aria-hidden="true">·</span>
            <span>{dateShort(props.r.issued)}</span>
            <Show when={props.compare?.citedAs}>
              <span aria-hidden="true">·</span>
              <span>Cited as {props.compare!.citedAs}</span>
            </Show>
          </>
        }
        actions={
          <a href={props.r.sourceUrl} target="_blank" rel="noreferrer" class={button({ tone: "ghost", size: "sm" })}>
            CBP CROSS <ExternalIcon size={13} />
          </a>
        }
      />
      <section class={card({ class: "p-6 max-sm:p-5" })} aria-label="Holding">
        <p class="text-[15px] font-[600]">{props.r.subject}</p>
        <p class="mt-3 border-l-2 border-hi pl-3.5 text-[15px] leading-[1.65] text-ink-2">{props.r.holding}</p>
        <p class="mt-3 text-[12.5px] text-muted">
          <span class="font-code">{props.r.codes.join(" · ")}</span>
        </p>
      </section>
      <Tabs.Root defaultValue={props.compare ? "compare" : "letter"} class="mt-8">
        <Tabs.List class={t.list()}>
          <Show when={props.compare}>
            <Tabs.Trigger value="compare" class={t.trigger()}>
              Compare
            </Tabs.Trigger>
          </Show>
          <Tabs.Trigger value="letter" class={t.trigger()}>
            Letter
          </Tabs.Trigger>
          <Show when={related()}>
            <Tabs.Trigger value="related" class={t.trigger()}>
              Related <span class={t.count()}>{related()}</span>
            </Tabs.Trigger>
          </Show>
          <Tabs.Indicator class={t.indicator({ class: "w-[var(--width)] left-[var(--left)]" })} />
        </Tabs.List>
        <Show when={props.compare}>
          <Tabs.Content value="compare" class="mt-4">
            <CompareTab c={props.compare!} />
          </Tabs.Content>
        </Show>
        <Tabs.Content value="letter" class="mt-4">
          <div class={card({ class: "p-6 max-sm:p-5" })}>
            <Letter ruling={props.r} marked={props.compare?.rulingMarked ?? []} />
          </div>
        </Tabs.Content>
        <Tabs.Content value="related" class="mt-4">
          <ul class={card({ class: "overflow-hidden" })}>
            <For each={props.r.related}>
              {(x) => (
                <li class={row}>
                  <span class="text-muted">{x.relationLabel}</span>
                  <A href={`/rulings/${x.key}`} class="font-code no-underline hover:underline">
                    {x.id}
                  </A>
                </li>
              )}
            </For>
            <For each={props.r.alsoCitedIn}>
              {(p) => (
                <li class={row}>
                  <span class="text-muted">In your binder</span>
                  <A href={`/products/${p.sku}`} class="no-underline hover:underline">
                    {p.title}
                  </A>
                </li>
              )}
            </For>
          </ul>
        </Tabs.Content>
      </Tabs.Root>
    </>
  );
}

export default function RulingPage() {
  const signed = useSigned();
  const params = useParams<{ key: string }>();
  const [search] = useSearchParams<{ answerId?: string; n?: string }>();
  const [data, { refetch }] = createResource(
    signed(() => ({ key: params.key, answerId: search.answerId, n: search.n })),
    async (k) => {
      if (!k.answerId) return { r: await rulings.get(k.key), c: undefined };
      const c = await rulings.compare(k.key, k.answerId, k.n ? Number(k.n) : undefined);
      return { r: c.ruling, c };
    },
  );
  return (
    <AppPage title={data()?.r.id ?? "Ruling"} place="library" permission="rulings:read" width="default">
      <Switch>
        <Match when={data.error}>
          <ErrorSlip error={data.error} retry={refetch} />
        </Match>
        <Match when={data()}>{(d) => <RulingView r={d().r} compare={d().c} answerId={search.answerId} />}</Match>
        <Match when={data.loading}>
          <PageLoading label="Opening the ruling…" />
        </Match>
      </Switch>
    </AppPage>
  );
}
