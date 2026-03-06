import { Accordion } from "@ark-ui/solid/accordion";
import { Menu } from "@ark-ui/solid/menu";
import { Progress } from "@ark-ui/solid/progress";
import { Tabs } from "@ark-ui/solid/tabs";
import { A, useParams } from "@solidjs/router";
import { For, Match, Show, Switch, createResource, createSignal, type JSX } from "solid-js";
import { Portal } from "solid-js/web";
import { AppPage, PageHead } from "~/components/shell/AppPage";
import { download } from "~/lib/api";
import { products, waitForJob } from "~/lib/endpoints";
import { dateShort, dateTime, money } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession, useSigned } from "~/lib/session";
import type { BinderOut, BinderRow, BinderVersion, ExportResult, JobOut } from "~/lib/types";
import { CodeDigits } from "~/ui/Code";
import { ChevronIcon, InfoIcon, OkIcon } from "~/ui/Icons";
import { Tip } from "~/ui/Tip";
import { button, card, floating, tabs } from "~/ui/recipes";
import { StandingTag } from "~/ui/Standing";
import { EmptyState, ErrorSlip, PageLoading } from "~/ui/States";
import { notify } from "~/ui/Toast";

/** The retention sentence without a repeated "Kept until <date>:" lead (the date is shown beside it). */
function retention(note: string): string {
  const s = note.replace(/^Kept until [^:]+:\s*/i, "");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const FIELDS: { key: BinderRow; label: string; show: (v: BinderVersion) => JSX.Element }[] = [
  { key: "usCode", label: "US code", show: (v) => <span class="font-code">{v.usCode ?? "–"}</span> },
  { key: "caCode", label: "Canada code", show: (v) => <span class="font-code">{v.caCode ?? "–"}</span> },
  { key: "standing", label: "Standing", show: (v) => v.standingLabel },
  { key: "decidingFact", label: "Deciding fact", show: (v) => (v.decidingFact ? `${v.decidingFact.value} (${v.decidingFact.sourceNote})` : "–") },
  { key: "evidence", label: "Evidence", show: (v) => v.evidence.join(" · ") || "–" },
  {
    key: "rulingsRelied",
    label: "Rulings",
    show: (v) => (
      <span class="flex flex-wrap gap-1.5">
        <For each={v.rulingsRelied} fallback="–">
          {(r) => (
            <A href={`/rulings/${r.key}`} class="rounded-full bg-paper-2 px-2 py-0.5 font-code text-[12px] text-ink-2 no-underline hover:text-ink" title={r.statusLabel}>
              {r.id}
            </A>
          )}
        </For>
      </span>
    ),
  },
];

/** History: one entry per decision, newest first. Opening one shows only what changed from the version before. */
export function History(props: { binder: BinderOut }) {
  const versions = () => [...props.binder.versions].sort((a, b) => b.n - a.n);
  const before = (v: BinderVersion) => props.binder.versions.find((x) => x.n === v.n - 1) ?? null;
  return (
    <Accordion.Root multiple collapsible defaultValue={[`v${versions()[0]?.n}`]} class={card({ class: "overflow-hidden" })}>
      <For each={versions()}>
        {(v) => {
          const prev = before(v);
          const changed = () => FIELDS.filter((f) => !prev || v.changed.includes(f.key));
          return (
            <Accordion.Item value={`v${v.n}`} class="border-b border-rule last:border-b-0">
              <Accordion.ItemTrigger class="flex w-full items-start gap-4 px-5 py-4 text-left hover:bg-paper-2/60 max-sm:px-4">
                <span
                  class="mt-0.5 grid h-7 min-w-7 place-items-center rounded-full px-1.5 font-code text-[12px] font-[600]"
                  classList={{ "bg-ink text-card": v.current, "bg-paper-2 text-ink-2": !v.current }}
                >
                  v{v.n}
                </span>
                <span class="min-w-0 flex-1">
                  <span class="flex flex-wrap items-baseline gap-x-2.5">
                    <span class="text-[14.5px] font-[600]">{v.kindLabel}</span>
                    <span class="text-[12.5px] text-muted">
                      {dateTime(v.at)}
                      {v.decidedBy ? ` · ${v.decidedBy.fullName}` : ""}
                    </span>
                  </span>
                  <span class="mt-0.5 block text-[14px] text-ink-2">{v.why}</span>
                </span>
                <Accordion.ItemIndicator class="mt-1 text-muted transition-transform duration-200 data-[state=open]:rotate-180">
                  <ChevronIcon size={15} />
                </Accordion.ItemIndicator>
              </Accordion.ItemTrigger>
              <Accordion.ItemContent class="fold">
                <dl class="space-y-2 px-5 pb-5 pl-[68px] text-[13.5px] max-sm:pl-4">
                  <For each={changed()} fallback={<p class="text-muted">Nothing changed but the decision.</p>}>
                    {(f) => (
                      <div class="grid grid-cols-[120px_minmax(0,1fr)] gap-x-4 max-sm:grid-cols-1">
                        <dt class="text-muted">{f.label}</dt>
                        <dd class="flex flex-wrap items-center gap-x-2 gap-y-1">
                          <Show when={prev}>
                            {(p) => (
                              <>
                                <span class="text-muted line-through decoration-rule-2">{f.show(p())}</span>
                                <span class="text-muted" aria-label="changed to">
                                  →
                                </span>
                              </>
                            )}
                          </Show>
                          <span class="rounded-[4px] bg-hi-soft px-1">{f.show(v)}</span>
                        </dd>
                      </div>
                    )}
                  </For>
                </dl>
              </Accordion.ItemContent>
            </Accordion.Item>
          );
        }}
      </For>
    </Accordion.Root>
  );
}

function ExportMenu(props: { sku: string }) {
  const [job, setJob] = createSignal<JobOut | null>(null);
  const [error, setError] = createSignal("");
  const run = async (format: "pdf" | "zip") => {
    setError("");
    try {
      const accepted = await products.exportBinder(props.sku, format);
      const done = await waitForJob(accepted.jobId, setJob);
      if (done.status === "failed") throw new Error(done.error || "The export didn't finish.");
      const result = done.result as unknown as ExportResult;
      notify(`Exported · ${result.fileName}`, `Fingerprint ${result.fingerprint} on every page.`);
      await download(result.downloadUrl.replace(/^\/api\/v1/, ""), result.fileName);
      setJob(null);
    } catch (e) {
      setJob(null);
      setError(e instanceof Error && !("problem" in e) ? e.message : plainProblem(e).message);
    }
  };
  const item = "cursor-pointer rounded-[6px] px-2.5 py-2 text-[14px] data-[highlighted]:bg-paper-2";
  return (
    <div class="flex flex-col items-end gap-2">
      <Menu.Root positioning={{ placement: "bottom-end", gutter: 6 }} onSelect={(d) => void run(d.value as "pdf" | "zip")}>
        <Menu.Trigger class={button({ tone: "outline", size: "sm" })} disabled={!!job()}>
          Export
          <ChevronIcon size={13} />
        </Menu.Trigger>
        <Portal>
          <Menu.Positioner class="z-50">
            <Menu.Content class={floating({ class: "min-w-[200px] p-1.5" })}>
              <Menu.Item value="pdf" class={item}>
                Binder (PDF)
              </Menu.Item>
              <Menu.Item value="zip" class={item}>
                Everything (ZIP)
              </Menu.Item>
            </Menu.Content>
          </Menu.Positioner>
        </Portal>
      </Menu.Root>
      <Show when={job()}>
        {(j) => (
          <Progress.Root value={Math.round(j().progress * 100)} class="w-[220px]" aria-label="Binder export">
            <Progress.Label class="text-[12.5px] text-muted">{j().message || j().statusLabel}</Progress.Label>
            <Progress.Track class="mt-1 h-1.5 overflow-hidden rounded-full bg-paper-3">
              <Progress.Range class="h-full rounded-full bg-ink transition-[width]" />
            </Progress.Track>
          </Progress.Root>
        )}
      </Show>
      <Show when={error()}>
        <p role="alert" class="text-[13px] font-[600] text-bad">
          {error()}
        </p>
      </Show>
    </div>
  );
}

export default function BinderPage() {
  const signed = useSigned();
  const params = useParams<{ sku: string }>();
  const { can } = useSession();
  const [binder, { refetch }] = createResource(signed(() => params.sku), (sku) => products.binder(sku));
  const t = tabs();
  const row = "flex items-center justify-between gap-4 border-b border-rule px-5 py-3 text-[14px] last:border-b-0 max-sm:px-4";
  return (
    <AppPage title={binder()?.product.title ?? "Binder"} place="products" permission="products:read" width="narrow">
      <Switch>
        <Match when={binder.error}>
          <ErrorSlip error={binder.error} retry={refetch} />
        </Match>
        <Match when={binder()}>
          {(b) => {
            const current = () => b().versions.find((v) => v.current) ?? b().versions[b().versions.length - 1];
            return (
              <>
                <p class="mb-2 text-[13px]">
                  <A href="/products" class="text-muted no-underline hover:text-ink">
                    Products
                  </A>
                </p>
                <PageHead
                  title={b().product.title}
                  meta={
                    <>
                      <span class="font-code">{b().product.sku}</span>
                      <span aria-hidden="true">·</span>
                      <span>{b().product.categoryLabel}</span>
                      <span aria-hidden="true">·</span>
                      <span>Made in {b().product.madeInLabel}</span>
                    </>
                  }
                  actions={<Show when={can("binder:export")}>{<ExportMenu sku={b().product.sku} />}</Show>}
                />
                <section class={card({ class: "p-6 max-sm:p-5" })} aria-label="Current code">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <StandingTag standing={b().product.standing} label={b().product.standingLabel} />
                    <Show when={b().approval}>
                      {(a) => (
                        <span class="inline-flex items-center gap-1.5 text-[13px] text-muted">
                          v{a().version} · {dateShort(a().at)} · {a().by.fullName}
                        </span>
                      )}
                    </Show>
                  </div>
                  <div class="mt-5 grid grid-cols-2 gap-6 max-sm:grid-cols-1">
                    <div>
                      <p class="text-[13px] font-[550] text-muted">United States</p>
                      <p class="mt-1.5">{current()?.usCode ? <CodeDigits code={current()!.usCode!} size="lg" /> : "–"}</p>
                    </div>
                    <div>
                      <p class="text-[13px] font-[550] text-muted">Canada</p>
                      <p class="mt-1.5">{current()?.caCode ? <CodeDigits code={current()!.caCode!} size="lg" /> : "–"}</p>
                    </div>
                  </div>
                </section>

                <Tabs.Root defaultValue="history" class="mt-8">
                  <Tabs.List class={t.list()}>
                    <Tabs.Trigger value="history" class={t.trigger()}>
                      History <span class={t.count()}>{b().versions.length}</span>
                    </Tabs.Trigger>
                    <Tabs.Trigger value="evidence" class={t.trigger()}>
                      Evidence <span class={t.count()}>{b().evidence.length}</span>
                    </Tabs.Trigger>
                    <Tabs.Trigger value="entries" class={t.trigger()}>
                      Entries <span class={t.count()}>{b().entries.length}</span>
                    </Tabs.Trigger>
                    <Tabs.Trigger value="record" class={t.trigger()}>
                      Record
                    </Tabs.Trigger>
                    <Tabs.Indicator class={t.indicator({ class: "w-[var(--width)] left-[var(--left)]" })} />
                  </Tabs.List>
                  <Tabs.Content value="history" class="mt-4">
                    <History binder={b()} />
                  </Tabs.Content>
                  <Tabs.Content value="evidence" class="mt-4">
                    <Show when={b().evidence.length} fallback={<div class={card()}><EmptyState title="Only the listing so far" /></div>}>
                      <ul class={card({ class: "overflow-hidden" })}>
                        <For each={b().evidence}>
                          {(e) => (
                            <li class={row}>
                              <span class="min-w-0">
                                <span class="block truncate font-code text-[13px]">{e.fileName}</span>
                                <span class="text-[12.5px] text-muted">{e.kindLabel}</span>
                              </span>
                              <span class="shrink-0 text-[12.5px] text-muted">
                                {e.uploadedBy}, {dateShort(e.uploadedAt)}
                              </span>
                            </li>
                          )}
                        </For>
                      </ul>
                    </Show>
                  </Tabs.Content>
                  <Tabs.Content value="entries" class="mt-4">
                    <Show when={b().entries.length} fallback={<div class={card()}><EmptyState title="No entries yet" /></div>}>
                      <ul class={card({ class: "overflow-hidden" })}>
                        <For each={b().entries}>
                          {(e) => (
                            <li class={row}>
                              <span>
                                <span class="block font-code text-[13px]">{e.entryNumber}</span>
                                <span class="text-[12.5px] text-muted">
                                  {e.country} · {dateShort(e.enteredOn)} · <span class="font-code">{e.code}</span>
                                </span>
                              </span>
                              <span class="text-right">
                                <span class="block font-code text-[13.5px]">{money(e.dutyPaid)}</span>
                                <span class="text-[11.5px] text-muted">duty paid</span>
                              </span>
                            </li>
                          )}
                        </For>
                      </ul>
                    </Show>
                  </Tabs.Content>
                  <Tabs.Content value="record" class="mt-4">
                    <dl class={card({ class: "divide-y divide-rule" })}>
                      <div class={row}>
                        <dt class="text-muted">Chain</dt>
                        <dd class="flex items-center gap-1.5" classList={{ "text-ok": b().record.chainVerified, "text-bad": !b().record.chainVerified }}>
                          <OkIcon size={14} />
                          {b().record.chainVerified ? "Verified" : "Check failed"} · {dateTime(b().record.checkedAt)}
                        </dd>
                      </div>
                      <div class={row}>
                        <dt class="text-muted">Recorded actions</dt>
                        <dd title={`Fingerprint ${b().record.fingerprint}`}>{b().record.events}</dd>
                      </div>
                      <div class={row}>
                        <dt class="text-muted">Opened</dt>
                        <dd>{dateShort(b().openedOn)}</dd>
                      </div>
                      <div class={row}>
                        <dt class="text-muted">Kept until</dt>
                        <dd class="flex items-center gap-1.5">
                          {dateShort(b().keptUntil)}
                          <Tip label={retention(b().retentionNote)}>
                            <InfoIcon size={13} class="text-muted" />
                          </Tip>
                        </dd>
                      </div>
                      <Show when={b().advanceRuling}>
                        <div class={row}>
                          <dt class="text-muted">Canada advance ruling</dt>
                          <dd class="flex items-center gap-1.5">
                            Ready to draft
                            <Tip label={b().advanceRuling!}>
                              <InfoIcon size={13} class="text-muted" />
                            </Tip>
                          </dd>
                        </div>
                      </Show>
                    </dl>
                  </Tabs.Content>
                </Tabs.Root>
              </>
            );
          }}
        </Match>
        <Match when={binder.loading}>
          <PageLoading label="Opening the binder…" />
        </Match>
      </Switch>
    </AppPage>
  );
}
