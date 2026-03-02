import { Accordion } from "@ark-ui/solid/accordion";
import { Popover } from "@ark-ui/solid/popover";
import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { Progress } from "@ark-ui/solid/progress";
import { A, useSearchParams } from "@solidjs/router";
import { For, Show, createResource, createSignal } from "solid-js";
import { Portal } from "solid-js/web";
import { AppPage, PageHead, PageSearch } from "~/components/shell/AppPage";
import { waitForJob, watch } from "~/lib/endpoints";
import { money, timeOfDay, whenLabel } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession, useSigned } from "~/lib/session";
import type { JobOut, WatchItemOut } from "~/lib/types";
import { ChevronIcon, InfoIcon } from "~/ui/Icons";
import { button, card, chip, floating, tag } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { KindTag } from "~/ui/Status";
import { notify } from "~/ui/Toast";

const GROUPS: Record<string, string[]> = {
  "": [],
  duties: ["legal_pending", "duty_layer"],
  rulings: ["ruling_modified", "ruling_revoked", "new_rulings"],
  tariff: ["schedule_revision"],
};
const GROUP_LABELS: [string, string][] = [
  ["", "All"],
  ["duties", "Duties"],
  ["rulings", "Rulings"],
  ["tariff", "Tariff text"],
];

function kindTone(kind: string): { tone: "warn" | "ink" | "bad" | "muted"; icon?: "warn" | "modified" | "revoked" | "ask" } {
  if (kind === "legal_pending") return { tone: "warn", icon: "warn" };
  if (kind === "ruling_modified") return { tone: "ink", icon: "modified" };
  if (kind === "ruling_revoked") return { tone: "bad", icon: "revoked" };
  return { tone: "ink" };
}

/** "12 FEB 2026" → "12 Feb 2026" */
function calmDate(label: string): string {
  return label.replace(/\b([A-Z])([A-Z]{2,})\b/g, (_, a: string, b: string) => a + b.toLowerCase());
}

function Item(props: { item: WatchItemOut }) {
  const [all, setAll] = createSignal<WatchItemOut | null>(null);
  const [loading, setLoading] = createSignal(false);
  const item = () => all() ?? props.item;
  const t = () => kindTone(item().kind);
  const showAll = async () => {
    setLoading(true);
    try {
      setAll(await watch.get(item().id));
    } catch (e) {
      notify("Couldn't open the full list", plainProblem(e).message, "error");
    } finally {
      setLoading(false);
    }
  };
  return (
    <Accordion.Item value={item().id} id={item().id} class="border-b border-rule last:border-b-0">
      <Accordion.ItemTrigger class="flex w-full items-start gap-4 px-5 py-4 text-left hover:bg-paper-2/60 max-sm:px-4">
        <span class="min-w-0 flex-1">
          <span class="flex flex-wrap items-center gap-2">
            <KindTag tone={t().tone} icon={t().icon}>
              {item().kindLabel}
            </KindTag>
            <Show when={!/^pending$/i.test(item().dateLabel)}>
              <span class="text-[12.5px] text-muted">{calmDate(item().dateLabel)}</span>
            </Show>
          </span>
          <span class="mt-1.5 block text-[15px] font-[600] leading-snug">{item().headline}</span>
        </span>
        <span class={tag({ tone: "hi", class: "mt-0.5 font-sans" })}>
          {item().affectedCount} {item().affectedCount === 1 ? "product" : "products"}
        </span>
        <Accordion.ItemIndicator class="mt-1 text-muted transition-transform duration-200 data-[state=open]:rotate-180">
          <ChevronIcon size={15} />
        </Accordion.ItemIndicator>
      </Accordion.ItemTrigger>
      <Accordion.ItemContent class="fold">
        <div class="space-y-5 px-5 pb-6 max-sm:px-4">
          <p class="max-w-[720px] text-[14.5px] leading-[1.6] text-ink-2">{item().body}</p>
          <Show when={item().knows.length || item().unknowns.length}>
            <div class="grid grid-cols-2 gap-4 max-md:grid-cols-1">
              <div class="rounded-[8px] bg-paper-2 px-4 py-3">
                <p class="text-[12.5px] font-[600] text-muted">Known</p>
                <ul class="mt-1.5 space-y-1 text-[14px]">
                  <For each={item().knows}>{(k) => <li>{k}</li>}</For>
                </ul>
              </div>
              <div class="rounded-[8px] bg-paper-2 px-4 py-3">
                <p class="text-[12.5px] font-[600] text-muted">Open</p>
                <ul class="mt-1.5 space-y-1 text-[14px]">
                  <For each={item().unknowns}>{(k) => <li>{k}</li>}</For>
                </ul>
              </div>
            </div>
          </Show>
          <Show when={item().affected.length}>
            <table class="w-full border-collapse text-left">
              <caption class="sr-only">Products affected</caption>
              <thead>
                <tr class="border-b border-rule text-[12.5px] text-muted">
                  <th class="py-2 pr-3 font-[600]">Product</th>
                  <th class="py-2 pr-3 font-[600] max-md:hidden">Duty</th>
                  <th class="py-2 text-right font-[600]">Re-check</th>
                </tr>
              </thead>
              <tbody>
                <For each={item().affected}>
                  {(a) => (
                    <tr class="border-b border-rule align-top text-[14px] last:border-b-0">
                      <td class="py-2.5 pr-3">
                        <A href={`/products/${a.sku}`} class="no-underline hover:underline">
                          {a.title}
                        </A>
                      </td>
                      <td class="py-2.5 pr-3 text-ink-2 max-md:hidden">
                        <Show when={a.dutyBefore && a.dutyAfter} fallback={<span class="text-muted">{a.effect}</span>}>
                          <span class="font-code text-[13px]" title={a.effect}>
                            {money(a.dutyBefore!)} → {money(a.dutyAfter!)}
                          </span>
                        </Show>
                      </td>
                      <td class="py-2.5 text-right text-[13px] text-muted">{a.recheckLabel}</td>
                    </tr>
                  )}
                </For>
              </tbody>
            </table>
          </Show>
          <div class="flex flex-wrap items-center gap-3">
            <Show when={!all() && item().affectedCount > item().affected.length}>
              <button type="button" class={button({ tone: "outline", size: "sm" })} disabled={loading()} onClick={() => void showAll()}>
                All {item().affectedCount}
              </button>
            </Show>
            <a href={item().sourceUrl} target="_blank" rel="noreferrer" class="text-[13px] text-muted underline decoration-rule-2 underline-offset-4 hover:text-ink">
              {item().sourceLabel}
            </a>
          </div>
        </div>
      </Accordion.ItemContent>
    </Accordion.Item>
  );
}

export default function WatchPage() {
  const signed = useSigned();
  const { can } = useSession();
  const [params, setParams] = useSearchParams<{ q?: string; group?: string; open?: string }>();
  const [data, { refetch }] = createResource(signed(() => ({ q: params.q ?? "" })), (k) => watch.list(k));
  const [job, setJob] = createSignal<JobOut | null>(null);
  const items = () => {
    const kinds = GROUPS[params.group ?? ""] ?? [];
    return (data()?.items ?? []).filter((i) => !kinds.length || kinds.includes(i.kind));
  };
  const count = (g: string) => (data()?.items ?? []).filter((i) => !GROUPS[g]!.length || GROUPS[g]!.includes(i.kind)).length;
  const scan = async () => {
    try {
      const accepted = await watch.scan();
      const done = await waitForJob(accepted.jobId, setJob);
      setJob(null);
      notify(done.status === "succeeded" ? "Checked every binder" : "The check didn't finish", done.message);
      void refetch();
    } catch (e) {
      setJob(null);
      notify("The check didn't start", plainProblem(e).message, "error");
    }
  };
  return (
    <AppPage title="Watch" place="watch" permission="watch:read" width="default">
      <PageHead
        title="Watch"
        meta={
          <Show when={data()}>
            {(d) => (
              <>
                <span>Checked {whenLabel(d().lastCheckedAt).startsWith("Today") ? `today, ${timeOfDay(d().lastCheckedAt)}` : whenLabel(d().lastCheckedAt)}</span>
                <Popover.Root positioning={{ placement: "bottom-start", gutter: 6 }}>
                  <Popover.Trigger class="grid h-6 w-6 place-items-center rounded-full text-muted hover:bg-paper-2 hover:text-ink" aria-label="What Watch checks">
                    <InfoIcon size={14} />
                  </Popover.Trigger>
                  <Portal>
                    <Popover.Positioner class="z-50">
                      <Popover.Content class={floating({ class: "w-[min(360px,90vw)] p-4 text-[13.5px]" })}>
                        <Popover.Title class="font-[600]">Every morning</Popover.Title>
                        <ul class="mt-2 list-disc space-y-1 pl-4 text-ink-2">
                          <For each={d().checks}>{(c) => <li>{c}</li>}</For>
                        </ul>
                      </Popover.Content>
                    </Popover.Positioner>
                  </Portal>
                </Popover.Root>
              </>
            )}
          </Show>
        }
        actions={
          <>
            <PageSearch label="Search changes" placeholder="A code, a ruling, a duty" value={params.q} onSearch={(q) => setParams({ q: q || undefined })} class="w-[260px] max-sm:w-full" />
            <Show when={can("watch:manage")}>
              <button type="button" class={button({ tone: "outline", size: "md" })} disabled={!!job()} onClick={() => void scan()}>
                Check now
              </button>
            </Show>
          </>
        }
      />
      <ToggleGroup.Root value={[params.group ?? ""]} onValueChange={(d) => setParams({ group: d.value[0] || undefined })} class="mb-4 flex flex-wrap gap-2" aria-label="Filter changes">
        <For each={GROUP_LABELS}>
          {([v, l]) => (
            <ToggleGroup.Item value={v} class={chip()}>
              {l} <span class="text-[11.5px] opacity-70">{data() ? count(v) : ""}</span>
            </ToggleGroup.Item>
          )}
        </For>
      </ToggleGroup.Root>
      <Show when={job()}>
        {(j) => (
          <Progress.Root value={Math.round(j().progress * 100)} class="mb-4 max-w-[420px]">
            <Progress.Label class="text-[13px] text-muted">{j().message || "Checking…"}</Progress.Label>
            <Progress.Track class="mt-1 h-1.5 overflow-hidden rounded-full bg-paper-3">
              <Progress.Range class="h-full rounded-full bg-ink" />
            </Progress.Track>
          </Progress.Root>
        )}
      </Show>
      <Show when={!data.error} fallback={<ErrorSlip error={data.error} retry={refetch} />}>
        <Show when={data()} fallback={<SkeletonLines lines={8} />}>
          <Show
            when={items().length}
            fallback={
              <div class={card()}>
                <EmptyState title="Nothing here">{data()!.quietMessage}</EmptyState>
              </div>
            }
          >
            <Accordion.Root multiple collapsible defaultValue={params.open ? [params.open] : []} class={card({ class: "overflow-hidden" })}>
              <For each={items()}>{(i) => <Item item={i} />}</For>
            </Accordion.Root>
          </Show>
        </Show>
      </Show>
    </AppPage>
  );
}
