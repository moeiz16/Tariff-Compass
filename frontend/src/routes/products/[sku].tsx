import { Progress } from "@ark-ui/solid/progress";
import { A, useNavigate, useParams } from "@solidjs/router";
import { For, Match, Show, Switch, createResource, createSignal, type JSX } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { download } from "~/lib/api";
import { products, waitForJob } from "~/lib/endpoints";
import { dateShort, dateTime, money } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { BinderOut, BinderRow, BinderVersion, ExportResult, JobOut } from "~/lib/types";
import { OkIcon } from "~/ui/Icons";
import { button } from "~/ui/recipes";
import { ErrorSlip, PageLoading } from "~/ui/States";
import { notify } from "~/ui/Toast";

interface MatrixRow {
  key: BinderRow | "fingerprint";
  label: string;
  cell: (v: BinderVersion) => JSX.Element;
}

/** The retention sentence without a repeated "Kept until <date>:" lead (the date is already shown above it). */
function retention(note: string): string {
  const s = note.replace(/^Kept until [^:]+:\s*/i, "");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function ditto(v: BinderVersion, key: MatrixRow["key"]): boolean {
  return v.n > 1 && key !== "fingerprint" && !v.changed.includes(key as BinderRow);
}

export function RevisionMatrix(props: { binder: BinderOut }) {
  const versions = () => props.binder.versions;
  const factLabel = () => versions().find((v) => v.decidingFact)?.decidingFact?.label ?? "The deciding fact";
  const rows: MatrixRow[] = [
    { key: "usCode", label: "US code", cell: (v) => <span class="font-code text-[16px]">{v.usCode ?? "–"}</span> },
    { key: "caCode", label: "Canada code", cell: (v) => <span class="font-code text-[16px]">{v.caCode ?? "–"}</span> },
    { key: "standing", label: "Standing", cell: (v) => <span>{v.standingLabel}</span> },
    {
      key: "decidingFact",
      label: "",
      cell: (v) => (
        <Show when={v.decidingFact} fallback={<span class="text-muted">–</span>}>
          {(f) => (
            <span>
              <b class="font-[650]">{f().value}</b>, <span classList={{ "text-warn": /read|assumed/.test(f().sourceNote) }}>{f().sourceNote}</span>
            </span>
          )}
        </Show>
      ),
    },
    { key: "evidence", label: "Evidence", cell: (v) => <span>{v.evidence.join(" · ") || "–"}</span> },
    {
      key: "rulingsRelied",
      label: "Rulings relied on",
      cell: (v) => (
        <span class="flex flex-wrap gap-x-2 gap-y-1">
          <For each={v.rulingsRelied} fallback={<span class="text-muted">–</span>}>
            {(r) => (
              <A href={`/rulings/${r.key}`} class="font-code text-[14px] underline decoration-rule underline-offset-4 hover:decoration-ink" title={r.statusLabel}>
                {r.id}
              </A>
            )}
          </For>
        </span>
      ),
    },
    { key: "decidedBy", label: "Who decided", cell: (v) => <span>{v.decidedBy ? `${v.decidedBy.fullName}, ${v.decidedBy.roleLabel.toLowerCase()}` : "–"}</span> },
    { key: "why", label: "Why", cell: (v) => <span>{v.why}</span> },
    { key: "fingerprint", label: "Fingerprint", cell: (v) => <span class="font-code text-[13.5px] text-ink-2">{v.fingerprint}</span> },
  ];
  return (
    <div class="overflow-x-auto rounded-[var(--radius-box)] border-[1.5px] border-ink" role="region" aria-label="Revision matrix: every decision as a column" tabIndex={0}>
      <table class="w-full min-w-[920px] border-collapse text-left">
        <caption class="sr-only">Versions as columns, facts as rows. A ditto mark means unchanged from the version before.</caption>
        <thead>
          <tr class="border-b-[1.5px] border-ink">
            <th scope="col" class="w-[210px] bg-paper-2 px-4 py-3 text-[15px] font-[700] leading-snug">Read across: what changed, when, and why</th>
            <For each={versions()}>
              {(v) => (
                <th scope="col" class="px-4 py-3 align-top" classList={{ "bg-hi text-hi-ink border-l-[2px] border-ink": v.current, "bg-paper-2": !v.current }}>
                  <span class="flex items-center gap-2 text-[16px] font-[700]">
                    <span class="rounded-[3px] border-[1.5px] border-current px-1 font-code text-[12px]">v{v.n}</span>
                    {v.kindLabel}
                    {v.current ? ", current" : ""}
                  </span>
                  <span class="mt-1 block text-[13.5px] font-[400]" classList={{ "text-muted": !v.current }}>
                    {dateTime(v.at)}
                  </span>
                </th>
              )}
            </For>
          </tr>
        </thead>
        <tbody>
          <For each={rows}>
            {(row) => (
              <tr class="border-b border-rule align-top last:border-b-0">
                <th scope="row" class="bg-paper px-4 py-3 text-[15px] font-[650]">
                  {row.key === "decidingFact" ? factLabel() : row.label}
                </th>
                <For each={versions()}>
                  {(v) => {
                    const same = ditto(v, row.key);
                    const changed = v.n > 1 && v.changed.includes(row.key as BinderRow);
                    return (
                      <td class="px-4 py-3 text-[15.5px] leading-[1.5]" classList={{ "bg-hi-soft": changed, "border-l-[2px] border-ink": v.current }}>
                        <Show when={!same} fallback={<span class="ditto" title="Unchanged" aria-label="Unchanged">〃</span>}>
                          {row.cell(v)}
                        </Show>
                      </td>
                    );
                  }}
                </For>
              </tr>
            )}
          </For>
        </tbody>
      </table>
    </div>
  );
}

function ExportButtons(props: { sku: string }) {
  const [job, setJob] = createSignal<JobOut | null>(null);
  const [error, setError] = createSignal("");
  const run = async (format: "pdf" | "zip") => {
    setError("");
    try {
      const accepted = await products.exportBinder(props.sku, format);
      const done = await waitForJob(accepted.jobId, setJob);
      if (done.status === "failed") throw new Error(done.error || "The export didn't finish.");
      const result = done.result as unknown as ExportResult;
      notify(`Exported · ${result.fileName}`, `Fingerprint ${result.fingerprint} printed on every page.`);
      await download(result.downloadUrl.replace(/^\/api\/v1/, ""), result.fileName);
      setJob(null);
    } catch (e) {
      setJob(null);
      setError(e instanceof Error && !("problem" in e) ? e.message : plainProblem(e).message);
    }
  };
  return (
    <div class="flex flex-col items-end gap-2 max-lg:items-start">
      <div class="flex flex-wrap gap-2">
        <button type="button" class={button({ size: "md" })} disabled={!!job()} onClick={() => void run("pdf")}>
          Download binder (PDF)
        </button>
        <button type="button" class={button({ tone: "ghost", size: "md" })} disabled={!!job()} onClick={() => void run("zip")}>
          Everything (ZIP)
        </button>
      </div>
      <Show when={job()}>
        {(j) => (
          <Progress.Root value={Math.round(j().progress * 100)} class="w-[300px]" aria-label="Binder export">
            <Progress.Label class="text-[13.5px] text-ink-2">{j().message || j().statusLabel}</Progress.Label>
            <Progress.Track class="mt-1 h-2 overflow-hidden rounded-[2px] border border-ink bg-paper">
              <Progress.Range class="h-full bg-ink transition-[width]" />
            </Progress.Track>
          </Progress.Root>
        )}
      </Show>
      <Show when={error()}>
        <p role="alert" class="text-[14px] font-[600] text-bad">
          {error()}
        </p>
      </Show>
    </div>
  );
}

export default function BinderPage() {
  const params = useParams<{ sku: string }>();
  const navigate = useNavigate();
  const { can } = useSession();
  const [binder, { refetch }] = createResource(() => params.sku, (sku) => products.binder(sku));
  return (
    <AppPage
      title={binder()?.product.title ?? "Binder"}
      scope="products"
      permission="products:read"
      query={binder()?.product.title}
      placeholder="Search your products: name, SKU or code"
      boxLabel="Search your products"
      onSearch={(q) => navigate(`/products?q=${encodeURIComponent(q)}`)}
    >
      <Switch>
        <Match when={binder.error}>
          <div class="gm py-10">
            <div class="gl" />
            <div class="gm-body">
              <ErrorSlip error={binder.error} retry={refetch} />
            </div>
          </div>
        </Match>
        <Match when={binder()}>
          {(b) => (
            <>
              <section class="gm py-8">
                <div class="gl self-end">
                  <span>Binder · {b().product.sku}</span>
                  <b>Reasonable-care record</b>
                </div>
                <div class="gm-wide flex flex-wrap items-end justify-between gap-6">
                  <div class="min-w-0 max-w-[760px] flex-1">
                    <p class="text-[15px] text-ink-2">
                      <A href="/products" class="underline decoration-rule underline-offset-4">
                        My products
                      </A>{" "}
                      › {b().product.categoryLabel} › made in {b().product.madeInLabel}
                    </p>
                    <h1 class="mt-1 text-[clamp(30px,3.6vw,46px)] font-[800] leading-[1.05] tracking-[-0.025em]">{b().product.title}</h1>
                    <p class="mt-2 flex flex-wrap gap-x-5 text-[16px] text-ink-2">
                      <span>Opened {dateShort(b().openedOn)}</span>
                      <span>{b().versions.length} versions</span>
                      <span>
                        Kept until <b class="text-ink">{dateShort(b().keptUntil)}</b>
                      </span>
                    </p>
                    <p class="mt-1 text-[14px] text-muted">{retention(b().retentionNote)}</p>
                  </div>
                  <div class="flex flex-col items-end gap-3 max-lg:items-start">
                    <Show when={b().approval}>
                      {(a) => (
                        <p class="inline-flex items-center gap-2 rounded-[var(--radius-btn)] border-[1.5px] border-ok px-3 py-1.5 text-[15px] font-[650] text-ok">
                          <OkIcon size={16} /> Approved · version {a().version} · {dateShort(a().at)}
                        </p>
                      )}
                    </Show>
                    <Show when={can("binder:export")}>
                      <ExportButtons sku={b().product.sku} />
                    </Show>
                  </div>
                </div>
              </section>
              <section class="px-8 max-md:px-4">
                <RevisionMatrix binder={b()} />
                <Show when={b().approval}>
                  <p class="mt-2 text-[14px] text-muted">{b().approval!.sentence}</p>
                </Show>
              </section>
              <section class="mx-8 mb-12 mt-8 grid grid-cols-3 border-t-[1.5px] border-ink max-lg:grid-cols-1 max-md:mx-4" aria-label="Evidence, entries and record">
                <div class="py-5 pr-6 max-lg:pr-0">
                  <h2 class="text-[13px] font-[750] uppercase tracking-[0.08em] text-ink-2">Evidence on file</h2>
                  <ul class="mt-2">
                    <For each={b().evidence} fallback={<li class="text-[15px] text-muted">Only the listing text so far.</li>}>
                      {(e) => (
                        <li class="border-b border-rule py-2 text-[15px]">
                          <span class="font-code text-[13.5px]">{e.fileName}</span>
                          <span class="block text-[13.5px] text-muted">
                            {e.kindLabel} · {e.uploadedBy}, {dateShort(e.uploadedAt)}
                          </span>
                        </li>
                      )}
                    </For>
                  </ul>
                </div>
                <div class="border-l border-rule px-6 py-5 max-lg:border-l-0 max-lg:border-t max-lg:px-0">
                  <h2 class="text-[13px] font-[750] uppercase tracking-[0.08em] text-ink-2">Entries using this code</h2>
                  <ul class="mt-2">
                    <For each={b().entries} fallback={<li class="text-[15px] text-muted">No entries yet.</li>}>
                      {(e) => (
                        <li class="flex justify-between gap-3 border-b border-rule py-2 text-[15px]">
                          <span>
                            <span class="font-code text-[13.5px]">{e.entryNumber}</span>
                            <span class="block text-[13.5px] text-muted">
                              {e.country} · {dateShort(e.enteredOn)} · <span class="font-code">{e.code}</span>
                            </span>
                          </span>
                          <span class="font-code text-[14px]">{money(e.dutyPaid)}</span>
                        </li>
                      )}
                    </For>
                  </ul>
                </div>
                <div class="border-l border-rule py-5 pl-6 max-lg:border-l-0 max-lg:border-t max-lg:pl-0">
                  <h2 class="text-[13px] font-[750] uppercase tracking-[0.08em] text-ink-2">Record</h2>
                  <p class="mt-2 flex items-center gap-2 text-[15.5px]" classList={{ "text-ok": b().record.chainVerified, "text-bad": !b().record.chainVerified }}>
                    <OkIcon size={16} />
                    {b().record.chainVerified ? "Chain verified" : "Chain check failed"} {dateTime(b().record.checkedAt)}
                  </p>
                  <p class="mt-1 text-[14.5px] text-ink-2">
                    {b().record.events} recorded events · fingerprint <span class="font-code">{b().record.fingerprint}</span>
                  </p>
                  <Show when={b().advanceRuling}>
                    <p class="mt-3 text-[15px] leading-[1.5]">{b().advanceRuling}</p>
                  </Show>
                </div>
              </section>
            </>
          )}
        </Match>
        <Match when={binder.loading}>
          <PageLoading label="Opening the binder…" />
        </Match>
      </Switch>
    </AppPage>
  );
}
