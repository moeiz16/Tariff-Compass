import { Splitter } from "@ark-ui/solid/splitter";
import { A, useNavigate, useParams, useSearchParams } from "@solidjs/router";
import { For, Match, Show, Switch, createResource } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { rulings } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import type { CompareOut, RulingDetail } from "~/lib/types";
import { Marked } from "~/ui/Marked";
import { PageLoading, ErrorSlip } from "~/ui/States";
import { MatchMark, RulingStatus } from "~/ui/Status";

function Letter(props: { ruling: RulingDetail; marked?: { start: number; end: number }[] }) {
  const paras = () => (props.ruling.paragraphs.length ? props.ruling.paragraphs : [{ start: 0, end: props.ruling.text.length }]);
  return (
    <div class="space-y-4 font-law text-[17.5px] leading-[1.65]">
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

function Compare(props: { c: CompareOut; answerId: string }) {
  const r = () => props.c.ruling;
  return (
    <>
      <section class="gm py-8">
        <div class="gl">
          <A href={`/answer?id=${props.answerId}`} class="text-[14px] underline underline-offset-4">
            ‹ Back to the answer
          </A>
          <b>Compare</b>
          <Show when={props.c.citedAs}>
            <span>cited as [{props.c.citedAs}]</span>
          </Show>
        </div>
        <div class="gm-body">
          <h1 class="text-[clamp(28px,3.4vw,40px)] font-[800] leading-[1.1] tracking-[-0.02em]">
            Your product against {r().id}
          </h1>
          <blockquote class="mt-4 border-l-[3px] border-ink pl-4">
            <p class="font-law text-[17px] leading-[1.55]">{props.c.ruleQuote}</p>
            <p class="mt-1 text-[14px] text-muted">19 CFR 177.9(b)(2): a classification ruling applies only to articles identical to the ones it describes.</p>
          </blockquote>
        </div>
      </section>
      <section class="px-8 max-md:px-4" aria-labelledby="align-h">
        <h2 id="align-h" class="sr-only">
          The facts, side by side
        </h2>
        <div class="overflow-hidden rounded-[var(--radius-box)] border-[1.5px] border-ink">
          <table class="w-full border-collapse text-left max-md:block">
            <thead class="bg-paper-2 text-[14px] text-ink-2 max-md:hidden">
              <tr class="border-b-[1.5px] border-ink">
                <th class="px-4 py-3 font-[650]">Fact</th>
                <th class="px-4 py-3 font-[650]">{props.c.productTitle}</th>
                <th class="px-4 py-3 text-center font-[650]">Match</th>
                <th class="px-4 py-3 font-[650]">The article in {r().id}</th>
              </tr>
            </thead>
            <tbody class="max-md:block">
              <For each={props.c.alignment}>
                {(f) => (
                  <tr class="border-b border-rule align-top last:border-b-0 max-md:block max-md:px-4 max-md:py-3">
                    <th scope="row" class="px-4 py-3 text-[16px] font-[650] max-md:block max-md:p-0">{f.fact}</th>
                    <td class="px-4 py-3 text-[16px] max-md:block max-md:p-0 max-md:pt-1">
                      <span class="hidden text-[13px] text-muted max-md:inline">Yours: </span>
                      {f.yours}
                    </td>
                    <td class="bg-paper-2 px-4 py-3 text-center max-md:inline-block max-md:bg-transparent max-md:p-0 max-md:pt-1">
                      <MatchMark match={f.match} label={f.matchLabel} />
                    </td>
                    <td class="px-4 py-3 font-law text-[16.5px] max-md:block max-md:p-0 max-md:pt-1">
                      <span class="hidden font-voice text-[13px] text-muted max-md:inline">The ruling's: </span>
                      {f.theirs}
                    </td>
                  </tr>
                )}
              </For>
            </tbody>
          </table>
        </div>
      </section>
      <section class="px-8 py-8 max-md:px-4" aria-label="Your evidence and the ruling letter">
        <Splitter.Root
          panels={[
            { id: "yours", minSize: 25, maxSize: 75 },
            { id: "ruling", minSize: 25, maxSize: 75 },
          ]}
          defaultSize={[50, 50]}
          class="flex min-h-[420px] max-md:!flex-col"
        >
          <Splitter.Panel id="yours" class="min-w-0 overflow-auto pr-6 max-md:!w-full max-md:pr-0">
            <h3 class="flex flex-wrap items-baseline justify-between gap-2 border-b-[1.5px] border-ink pb-2 text-[14px] font-[750] uppercase tracking-[0.08em]">
              Your product
              <span class="font-code text-[13px] normal-case tracking-normal text-ink-2">{props.c.madeInLabel}</span>
            </h3>
            <dl class="mt-3">
              <For each={props.c.evidence}>
                {(e) => (
                  <div class="grid grid-cols-[130px_minmax(0,1fr)] gap-x-4 border-b border-rule py-3 max-sm:grid-cols-1">
                    <dt class="text-[15px] text-muted">{e.label}</dt>
                    <dd class="font-law text-[16.5px] leading-[1.55]">
                      “<Marked text={e.text} spans={e.marked} />”
                    </dd>
                  </div>
                )}
              </For>
            </dl>
          </Splitter.Panel>
          <Splitter.ResizeTrigger
            id="yours:ruling"
            aria-label="Resize the two panes"
            class="relative w-[14px] shrink-0 cursor-col-resize before:absolute before:inset-y-0 before:left-1/2 before:w-[1.5px] before:-translate-x-1/2 before:bg-rule hover:before:bg-ink data-[focus]:before:bg-ink max-md:hidden"
          />
          <Splitter.Panel id="ruling" class="min-w-0 overflow-auto pl-6 max-md:!w-full max-md:pl-0 max-md:pt-8">
            <h3 class="flex flex-wrap items-baseline justify-between gap-2 border-b-[1.5px] border-ink pb-2 text-[14px] font-[750] uppercase tracking-[0.08em]">
              {r().id} · {dateShort(r().issued)}
              <span class="normal-case tracking-normal">
                <RulingStatus status={r().status} />
              </span>
            </h3>
            <div class="mt-3">
              <Letter ruling={r()} marked={props.c.rulingMarked} />
            </div>
          </Splitter.Panel>
        </Splitter.Root>
      </section>
    </>
  );
}

function Reader(props: { r: RulingDetail }) {
  return (
    <section class="gm py-8">
      <div class="gl">
        <A href="/rulings" class="text-[14px] underline underline-offset-4">
          ‹ Rulings
        </A>
        <b>Ruling</b>
        <span>{props.r.category}</span>
      </div>
      <div class="gm-body">
        <p class="flex flex-wrap items-baseline gap-3">
          <span class="font-code text-[15px] font-[650]">{props.r.id}</span>
          <span class="text-[14.5px] text-muted">{dateShort(props.r.issued)}</span>
          <RulingStatus status={props.r.status} long />
        </p>
        <h1 class="mt-2 text-[clamp(26px,3vw,36px)] font-[800] leading-[1.15] tracking-[-0.015em]">{props.r.subject}</h1>
        <p class="mt-3 text-[15.5px] text-ink-2">
          Codes in the letter: <span class="font-code">{props.r.codes.join(" · ")}</span> (CBP prints <span class="font-code">{props.r.codeAsQuoted}</span>)
        </p>
        <div class="mt-6 border-t-[1.5px] border-ink pt-5">
          <Letter ruling={props.r} marked={[]} />
        </div>
        <Show when={props.r.related.length}>
          <h2 class="mt-8 text-[15px] font-[750]">Related rulings</h2>
          <ul class="mt-2">
            <For each={props.r.related}>
              {(x) => (
                <li class="border-b border-rule py-2 text-[15.5px]">
                  {x.relationLabel}{" "}
                  <A href={`/rulings/${x.key}`} class="font-code underline underline-offset-4">
                    {x.id}
                  </A>
                </li>
              )}
            </For>
          </ul>
        </Show>
        <Show when={props.r.alsoCitedIn.length}>
          <h2 class="mt-8 text-[15px] font-[750]">Relied on in your binders</h2>
          <ul class="mt-2">
            <For each={props.r.alsoCitedIn}>
              {(p) => (
                <li class="border-b border-rule py-2 text-[15.5px]">
                  <A href={`/products/${p.sku}`} class="underline underline-offset-4">
                    {p.title}
                  </A>{" "}
                  <span class="font-code text-[13px] text-muted">{p.sku}</span>
                </li>
              )}
            </For>
          </ul>
        </Show>
        <p class="mt-8 text-[14.5px]">
          <a href={props.r.sourceUrl} target="_blank" rel="noreferrer" class="underline underline-offset-4">
            The ruling on CBP CROSS
          </a>
        </p>
      </div>
    </section>
  );
}

export default function RulingPage() {
  const params = useParams<{ key: string }>();
  const [search] = useSearchParams<{ answerId?: string; n?: string }>();
  const navigate = useNavigate();
  const [data, { refetch }] = createResource(
    () => ({ key: params.key, answerId: search.answerId, n: search.n }),
    async (k) =>
      k.answerId ? { kind: "compare" as const, c: await rulings.compare(k.key, k.answerId, k.n ? Number(k.n) : undefined) } : { kind: "reader" as const, r: await rulings.get(k.key) },
  );
  const title = () => {
    const d = data();
    return d ? (d.kind === "compare" ? `Compare with ${d.c.ruling.id}` : d.r.id) : "Ruling";
  };
  return (
    <AppPage title={title()} scope="rulings" permission="rulings:read" placeholder="Search rulings: a product, a code, a ruling number" boxLabel="Search the customs rulings" onSearch={(q) => navigate(`/rulings?q=${encodeURIComponent(q)}`)}>
      <Switch>
        <Match when={data.error}>
          <div class="gm py-10">
            <div class="gl" />
            <div class="gm-body">
              <ErrorSlip error={data.error} retry={refetch} />
            </div>
          </div>
        </Match>
        <Match when={data()}>
          {(d) => (
            <Show when={d().kind === "compare"} fallback={<Reader r={(d() as { r: RulingDetail }).r} />}>
              <Compare c={(d() as { c: CompareOut }).c} answerId={search.answerId!} />
            </Show>
          )}
        </Match>
        <Match when={data.loading}>
          <PageLoading label="Opening the ruling…" />
        </Match>
      </Switch>
    </AppPage>
  );
}
