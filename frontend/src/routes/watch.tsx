import { ToggleGroup } from "@ark-ui/solid/toggle-group";
import { Progress } from "@ark-ui/solid/progress";
import { A, useSearchParams } from "@solidjs/router";
import { For, Show, createResource, createSignal } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { waitForJob, watch } from "~/lib/endpoints";
import { money, timeOfDay, whenLabel } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession, useSigned } from "~/lib/session";
import type { JobOut, WatchItemOut } from "~/lib/types";
import { button, chip } from "~/ui/recipes";
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
  ["", "Everything"],
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

function Bulletin(props: { item: WatchItemOut }) {
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
    <article id={item().id} class="gm ty-ruled py-9 max-md:py-7" aria-labelledby={`${item().id}-h`}>
      <p class="pt-1 font-type text-[15px] font-[700] leading-snug max-[960px]:mb-2">
        {item().dateLabel}
        <Show when={item().dateNote}>
          <span class="block font-sans text-[13.5px] font-[400] text-ink-2">{item().dateNote}</span>
        </Show>
      </p>
      <div class="gm-body">
        <p class="flex flex-wrap items-center gap-2.5">
          <KindTag tone={t().tone} icon={t().icon}>
            {item().kindLabel}
          </KindTag>
          <span class="bg-hi px-1.5 font-code text-[13px] font-[650] text-hi-ink">
            {item().affectedCount} of your products
          </span>
        </p>
        <h2 id={`${item().id}-h`} class="ty-title mt-3 text-[clamp(20px,2.1vw,26px)]">
          {item().headline}
        </h2>
        <p class="mt-2 text-[17px] leading-[1.6] text-ink-2">{item().body}</p>
        <Show when={item().knows.length || item().unknowns.length}>
          <div class="mt-5 grid grid-cols-2 rounded-[var(--radius-box)] border border-rule max-md:grid-cols-1">
            <div class="px-5 py-4">
              <h3 class="ty-head">What we know</h3>
              <ul class="mt-2 list-disc space-y-1 pl-5 text-[16px]">
                <For each={item().knows}>{(k) => <li>{k}</li>}</For>
              </ul>
            </div>
            <div class="border-l border-rule px-5 py-4 max-md:border-l-0 max-md:border-t">
              <h3 class="ty-head">What we don't</h3>
              <ul class="mt-2 list-disc space-y-1 pl-5 text-[16px]">
                <For each={item().unknowns}>{(k) => <li>{k}</li>}</For>
              </ul>
            </div>
          </div>
        </Show>
        <Show when={item().affected.length}>
          <table class="mt-5 w-full border-collapse text-left">
            <caption class="sr-only">Products affected</caption>
            <thead>
              <tr class="border-b-[1.5px] border-ink text-[14px] text-ink-2">
                <th class="py-2 pr-3 font-[650]">Most affected</th>
                <th class="py-2 pr-3 font-[650] max-md:hidden">What changes</th>
                <th class="py-2 text-right font-[650]">Re-check</th>
              </tr>
            </thead>
            <tbody>
              <For each={item().affected}>
                {(a) => (
                  <tr class="border-b border-rule align-top">
                    <td class="py-2.5 pr-3 text-[15.5px]">
                      <A href={`/products/${a.sku}`} class="underline decoration-rule underline-offset-4 hover:decoration-ink">
                        {a.title}
                      </A>
                      <span class="block font-code text-[12.5px] text-muted">{a.sku}</span>
                    </td>
                    <td class="py-2.5 pr-3 text-[15px] text-ink-2 max-md:hidden">
                      {a.effect}
                      <Show when={a.dutyBefore && a.dutyAfter}>
                        <span class="block font-code text-[13px]">
                          {money(a.dutyBefore!)} → {money(a.dutyAfter!)}
                        </span>
                      </Show>
                    </td>
                    <td class="py-2.5 text-right text-[14.5px]">{a.recheckLabel}</td>
                  </tr>
                )}
              </For>
            </tbody>
          </table>
        </Show>
        <div class="mt-4 flex flex-wrap items-center gap-3">
          <Show when={!all() && item().affectedCount > item().affected.length}>
            <button type="button" class={button({ tone: "ghost", size: "sm" })} disabled={loading()} onClick={() => void showAll()}>
              See all {item().affectedCount}
            </button>
          </Show>
          <a href={item().sourceUrl} target="_blank" rel="noreferrer" class="text-[14.5px] underline decoration-rule underline-offset-4 hover:decoration-ink">
            Source: {item().sourceLabel}
          </a>
        </div>
      </div>
    </article>
  );
}

export default function WatchPage() {
  const signed = useSigned();
  const { can } = useSession();
  const [params, setParams] = useSearchParams<{ q?: string; group?: string }>();
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
    <AppPage title="Watch" scope="watch" permission="watch:read" query={params.q} placeholder="Search changes: a code, a ruling, a duty" boxLabel="Search changes" onSearch={(q) => setParams({ q: q || undefined })}>
      <div class="gm pt-6">
        <div class="gl">
          <span>Watch</span>
          <h1 class="not-italic">
            <b>Bulletin</b>
          </h1>
        </div>
        <div class="gm-body">
          <p class="text-[15.5px] text-ink-2">
            <Show when={data()} fallback="Opening the bulletin…">
              {(d) => (
                <>
                  {d().items.length} changes touch your products · newest first · checked {whenLabel(d().lastCheckedAt).startsWith("Today") ? `this morning at ${timeOfDay(d().lastCheckedAt)} PT` : whenLabel(d().lastCheckedAt)}
                </>
              )}
            </Show>
          </p>
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <ToggleGroup.Root value={[params.group ?? ""]} onValueChange={(d) => setParams({ group: d.value[0] || undefined })} class="flex flex-wrap gap-2" aria-label="Filter changes">
              <For each={GROUP_LABELS}>
                {([v, l]) => (
                  <ToggleGroup.Item value={v} class={chip()}>
                    {l} <span class="font-code text-[11.5px] font-[600] text-muted">{data() ? count(v) : ""}</span>
                  </ToggleGroup.Item>
                )}
              </For>
            </ToggleGroup.Root>
            <Show when={can("watch:manage")}>
              <button type="button" class={button({ tone: "ghost", size: "sm", class: "ml-auto" })} disabled={!!job()} onClick={() => void scan()}>
                Check every binder now
              </button>
            </Show>
          </div>
          <Show when={job()}>
            {(j) => (
              <Progress.Root value={Math.round(j().progress * 100)} class="mt-3 max-w-[420px]">
                <Progress.Label class="text-[14px] text-ink-2">{j().message || "Checking…"}</Progress.Label>
                <Progress.Track class="mt-1 h-2 overflow-hidden rounded-[2px] border border-ink">
                  <Progress.Range class="h-full bg-ink" />
                </Progress.Track>
              </Progress.Root>
            )}
          </Show>
        </div>
      </div>
      <Show when={!data.error} fallback={<div class="gm py-8"><span /><div class="gm-body"><ErrorSlip error={data.error} retry={refetch} /></div></div>}>
        <Show when={data()} fallback={<div class="gm py-8"><span /><SkeletonLines class="gm-body" lines={8} /></div>}>
          <Show when={items().length} fallback={<div class="gm py-8"><span /><div class="gm-body"><EmptyState title="Nothing here">{data()!.quietMessage}</EmptyState></div></div>}>
            <For each={items()}>{(i) => <Bulletin item={i} />}</For>
          </Show>
          <section class="mx-8 mb-12 mt-2 border-t-[1.5px] border-ink pt-5 max-md:mx-4" aria-labelledby="checks-h">
            <h2 id="checks-h" class="ty-head">
              What Watch checks every morning
            </h2>
            <ul class="mt-3 grid grid-cols-4 gap-6 text-[15px] text-ink-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
              <For each={data()!.checks}>{(c) => <li class="border-t border-rule pt-2">{c}</li>}</For>
            </ul>
          </section>
        </Show>
      </Show>
    </AppPage>
  );
}
