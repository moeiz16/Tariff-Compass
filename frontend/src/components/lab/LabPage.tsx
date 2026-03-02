import { Progress } from "@ark-ui/solid/progress";
import { Match, Show, Switch, createResource, createSignal } from "solid-js";
import { LabReport, RoundsStrip } from "~/components/lab/LabReport";
import { AppPage, PageHead } from "~/components/shell/AppPage";
import { lab, waitForJob } from "~/lib/endpoints";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { JobOut } from "~/lib/types";
import { button, card } from "~/ui/recipes";
import { Tip } from "~/ui/Tip";
import { InfoIcon } from "~/ui/Icons";
import { EmptyState, ErrorSlip, PageLoading } from "~/ui/States";
import { notify } from "~/ui/Toast";

/** The lab page for the candidate round (or a chosen round). */
export function LabPage(props: { n?: number }) {
  const { me, can } = useSession();
  // Never ask for what the role can't see: no lab:read, no request.
  const [overview, { refetch: refetchLab }] = createResource(() => (can("lab:read") ? true : null), () => lab.get());
  // Show the chosen round, else the challenger waiting for sign-off, else the round in use, else the latest round.
  const roundN = () =>
    can("lab:read") ? (props.n ?? overview()?.candidate ?? overview()?.live ?? overview()?.rounds.at(-1)?.n ?? null) : null;
  const [round, { mutate, refetch }] = createResource(roundN, (n) => lab.round(n));
  const [job, setJob] = createSignal<JobOut | null>(null);

  const start = async () => {
    try {
      const accepted = await lab.start("");
      const done = await waitForJob(accepted.jobId, setJob);
      setJob(null);
      notify(done.status === "succeeded" ? "Training round finished" : "The training round didn't finish", done.message);
      void refetchLab();
    } catch (e) {
      setJob(null);
      notify("The round didn't start", plainProblem(e).message, "error");
    }
  };

  return (
    <AppPage title="Lab" place="lab" permission="lab:read" width="default">
      <PageHead
        title="Lab"
        meta={<Show when={overview()}>{(o) => <span>{o().correctionsWaiting} broker corrections waiting</span>}</Show>}
        actions={
          <Show when={can("lab:run") && overview()}>
            <button type="button" class={button({ tone: "outline", size: "md" })} disabled={!!job()} onClick={() => void start()}>
              Start round {(overview()!.rounds.at(-1)?.n ?? 0) + 1}
            </button>
          </Show>
        }
      />
      <Show when={job()}>
        {(j) => (
          <Progress.Root value={Math.round(j().progress * 100)} class="mb-4 max-w-[360px]">
            <Progress.Label class="text-[13px] text-muted">{j().message || "Training…"}</Progress.Label>
            <Progress.Track class="mt-1 h-1.5 overflow-hidden rounded-full bg-paper-3">
              <Progress.Range class="h-full rounded-full bg-ink" />
            </Progress.Track>
          </Progress.Root>
        )}
      </Show>
      <Switch>
        <Match when={overview.error || round.error}>
          <ErrorSlip error={overview.error ?? round.error} retry={() => (overview.error ? refetchLab() : refetch())} />
        </Match>
        <Match when={overview() && !overview()!.rounds.length}>
          <div class={card()}>
            <EmptyState title="No training rounds yet" />
          </div>
        </Match>
        <Match when={overview() && round()}>
          <Show when={overview()!.inUse}>
            {(u) => (
              <section class={card({ class: "mb-8 p-6 max-sm:p-5" })} aria-labelledby="inuse-h">
                <p id="inuse-h" class="label flex items-center gap-1.5">
                  In use
                  <Tip label={u().sentence}>
                    <InfoIcon size={13} />
                  </Tip>
                </p>
                <div class="mt-2 flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
                  <p class="text-[24px] font-[600] tracking-[-0.02em]">{u().label}</p>
                  <dl class="flex gap-10">
                    <div>
                      <dt class="text-[12.5px] text-muted">Heading</dt>
                      <dd class="font-code text-[28px] font-[500] leading-none tracking-[-0.02em]">
                        {Math.round(u().heading)}
                        <span class="text-[13px] text-muted"> in 100</span>
                      </dd>
                    </div>
                    <div>
                      <dt class="text-[12.5px] text-muted">Full code</dt>
                      <dd class="font-code text-[28px] font-[500] leading-none tracking-[-0.02em]">
                        {Math.round(u().fullCode)}
                        <span class="text-[13px] text-muted"> in 100</span>
                      </dd>
                    </div>
                  </dl>
                </div>
              </section>
            )}
          </Show>
          <RoundsStrip lab={overview()!} current={round()!.n} />
          <LabReport
            lab={overview()!}
            round={round()!}
            me={me()?.user.fullName ?? ""}
            onSigned={(r) => {
              mutate(r);
              void refetchLab();
            }}
          />
        </Match>
        <Match when={true}>
          <PageLoading label="Opening the lab…" />
        </Match>
      </Switch>
    </AppPage>
  );
}
