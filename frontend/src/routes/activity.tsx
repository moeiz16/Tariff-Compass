import { useSearchParams } from "@solidjs/router";
import { useSession } from "~/lib/session";
import { For, Show, createResource, createSignal } from "solid-js";
import { AppPage, PageHead, PageSearch } from "~/components/shell/AppPage";
import { download } from "~/lib/api";
import { audit } from "~/lib/endpoints";
import { dateTime } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { today } from "~/lib/clock";
import type { ChainOut } from "~/lib/types";
import { FailIcon, OkIcon } from "~/ui/Icons";
import { Pager } from "~/ui/Pager";
import { button, card, tag } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { notify } from "~/ui/Toast";

export default function ActivityPage() {
  const [params, setParams] = useSearchParams<{ actor?: string; page?: string }>();
  const page = () => Number(params.page ?? 1);
  const { can } = useSession();
  const [rows, { refetch }] = createResource(() => (can("audit:read") ? { actor: params.actor ?? "", page: page() } : null), (k) => audit.list({ ...k, pageSize: 25 }));
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
    <AppPage title="Activity" place="none" permission="audit:read" width="wide">
      <PageHead
        title="Activity"
        meta={
          <Show when={chain()} fallback={<span>Every sensitive action, chained</span>}>
            {(c) => (
              <span role="status" class={tag({ tone: c().ok ? "ok" : "bad" })}>
                {c().ok ? <OkIcon size={13} /> : <FailIcon size={13} />}
                {c().ok ? "Chain verified" : `Altered at #${c().brokenAt ?? "?"}`}
              </span>
            )}
          </Show>
        }
        actions={
          <>
            <PageSearch label="Search the activity" placeholder="A person, a product, a code" value={params.actor} onSearch={(q) => setParams({ actor: q || undefined, page: undefined })} class="w-[260px] max-sm:w-full" />
            <button type="button" class={button({ tone: "outline", size: "md" })} disabled={checking()} onClick={() => void verify()} title="Each entry carries a fingerprint of the one before it">
              {checking() ? "Checking…" : "Verify the chain"}
            </button>
            <button type="button" class={button({ tone: "ghost", size: "md" })} onClick={() => void exportCsv()}>
              CSV
            </button>
          </>
        }
      />
      <Show when={!rows.error} fallback={<ErrorSlip error={rows.error} retry={refetch} />}>
        <Show when={rows()} fallback={<SkeletonLines lines={10} />}>
          {(r) => (
            <Show
              when={r().items.length}
              fallback={
                <div class={card()}>
                  <EmptyState title="Nothing matches" />
                </div>
              }
            >
              <div class={card({ class: "overflow-x-auto" })}>
                <table class="w-full min-w-[760px] border-collapse text-left">
                  <caption class="sr-only">{r().total} entries, newest first</caption>
                  <thead>
                    <tr class="border-b border-rule bg-paper-2/50 text-[12.5px] text-muted">
                      <th class="px-5 py-2.5 font-[600]">When</th>
                      <th class="px-5 py-2.5 font-[600]">Who</th>
                      <th class="px-5 py-2.5 font-[600]">What</th>
                      <th class="px-5 py-2.5 text-right font-[600]">Fingerprint</th>
                    </tr>
                  </thead>
                  <tbody>
                    <For each={r().items}>
                      {(a) => (
                        <tr class="border-b border-rule align-top text-[14px] last:border-b-0">
                          <td class="whitespace-nowrap px-5 py-3 text-muted">{dateTime(a.at)}</td>
                          <td class="px-5 py-3">
                            {a.actorName}
                            <span class="block text-[12.5px] text-muted">{a.actorRoleLabel}</span>
                          </td>
                          <td class="px-5 py-3">
                            <span class="font-[600]">{a.actionLabel}</span>
                            <span class="block text-[13px] text-ink-2">{a.summary}</span>
                          </td>
                          <td class="px-5 py-3 text-right font-code text-[12px] text-muted">{a.fingerprint}</td>
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
    </AppPage>
  );
}
