import { useSearchParams } from "@solidjs/router";
import { For, Show, createResource, createSignal } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { download } from "~/lib/api";
import { audit } from "~/lib/endpoints";
import { dateTime, plural } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { today } from "~/lib/clock";
import type { ChainOut } from "~/lib/types";
import { FailIcon, OkIcon } from "~/ui/Icons";
import { Pager } from "~/ui/Pager";
import { button } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { notify } from "~/ui/Toast";

export default function ActivityPage() {
  const [params, setParams] = useSearchParams<{ actor?: string; page?: string }>();
  const page = () => Number(params.page ?? 1);
  const [rows, { refetch }] = createResource(() => ({ actor: params.actor ?? "", page: page() }), (k) => audit.list({ ...k, pageSize: 25 }));
  const [chain, setChain] = createSignal<ChainOut | null>(null);
  const [checking, setChecking] = createSignal(false);
  const verify = async () => {
    setChecking(true);
    try {
      setChain(await audit.verify());
    } catch (e) {
      notify("The check didn't run", plainProblem(e).message, "error");
    } finally {
      setChecking(false);
    }
  };
  const exportCsv = async () => {
    try {
      await download(audit.csvPath({ actor: params.actor }), `activity-${today()}.csv`);
    } catch (e) {
      notify("Not exported", plainProblem(e).message, "error");
    }
  };
  return (
    <AppPage title="Activity record" scope="none" permission="audit:read" query={params.actor} placeholder="Search activity: a person, a product, a code" boxLabel="Search the activity record" onSearch={(q) => setParams({ actor: q || undefined, page: undefined })}>
      <div class="gm py-8">
        <div class="gl">
          <span>Settings</span>
          <b>Activity record</b>
          <span class="gl-extra block">every sensitive action, chained</span>
        </div>
        <div class="gm-wide max-w-[1160px]">
          <div class="flex flex-wrap items-center gap-3">
            <button type="button" class={button({ size: "md" })} disabled={checking()} onClick={() => void verify()}>
              {checking() ? "Checking the chain…" : "Verify the chain"}
            </button>
            <button type="button" class={button({ tone: "ghost", size: "md" })} onClick={() => void exportCsv()}>
              Export as CSV
            </button>
            <Show when={chain()}>
              {(c) => (
                <p role="status" class="inline-flex items-center gap-2 text-[15.5px] font-[650]" classList={{ "text-ok": c().ok, "text-bad": !c().ok }}>
                  {c().ok ? <OkIcon size={16} /> : <FailIcon size={16} />}
                  {c().sentence}
                  <Show when={!c().ok && c().brokenAt}> (first altered entry: #{c().brokenAt})</Show>
                </p>
              )}
            </Show>
          </div>
          <p class="mt-3 text-[15px] text-ink-2">
            Each entry carries a fingerprint of the one before it, so changing or deleting an old entry breaks the chain from that point on.
          </p>
          <Show when={!rows.error} fallback={<div class="mt-6"><ErrorSlip error={rows.error} retry={refetch} /></div>}>
            <Show when={rows()} fallback={<SkeletonLines class="mt-6" lines={10} />}>
              {(r) => (
                <Show when={r().items.length} fallback={<div class="mt-6"><EmptyState title="Nothing recorded that matches">Clear the search to see every entry.</EmptyState></div>}>
                  <p class="mt-6 text-[14.5px] text-muted">{plural(r().total, "entry", "entries")}, newest first</p>
                  <div class="mt-2 overflow-x-auto">
                    <table class="w-full min-w-[760px] border-collapse text-left">
                      <thead>
                        <tr class="border-b-[1.5px] border-ink text-[14px] text-ink-2">
                          <th class="py-2 pr-3 font-[650]">When</th>
                          <th class="py-2 pr-3 font-[650]">Who</th>
                          <th class="py-2 pr-3 font-[650]">What</th>
                          <th class="py-2 font-[650]">Fingerprint</th>
                        </tr>
                      </thead>
                      <tbody>
                        <For each={r().items}>
                          {(a) => (
                            <tr class="border-b border-rule align-top">
                              <td class="whitespace-nowrap py-2.5 pr-3 text-[14.5px]">{dateTime(a.at)}</td>
                              <td class="py-2.5 pr-3 text-[15px]">
                                {a.actorName}
                                <span class="block text-[13px] text-muted">{a.actorRoleLabel}</span>
                              </td>
                              <td class="py-2.5 pr-3 text-[15px]">
                                <b class="font-[650]">{a.actionLabel}</b>
                                <span class="block text-ink-2">{a.summary}</span>
                              </td>
                              <td class="py-2.5 font-code text-[13px] text-ink-2">{a.fingerprint}</td>
                            </tr>
                          )}
                        </For>
                      </tbody>
                    </table>
                  </div>
                  <Pager count={r().total} pageSize={r().pageSize} page={page()} onPage={(n) => setParams({ page: String(n) })} label="Pages of the activity record" />
                </Show>
              )}
            </Show>
          </Show>
        </div>
      </div>
    </AppPage>
  );
}
