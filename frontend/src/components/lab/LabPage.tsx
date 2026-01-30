import { Progress } from "@ark-ui/solid/progress";
import { useNavigate } from "@solidjs/router";
import { Match, Show, Switch, createResource, createSignal } from "solid-js";
import { LabReport, RoundsStrip } from "~/components/lab/LabReport";
import { AppPage } from "~/components/shell/AppPage";
import { lab, waitForJob } from "~/lib/endpoints";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { JobOut } from "~/lib/types";
import { button } from "~/ui/recipes";
import { EmptyState, ErrorSlip, PageLoading } from "~/ui/States";
import { notify } from "~/ui/Toast";

/** The lab page for the candidate round (or a chosen round). */
export function LabPage(props: { n?: number }) {
  const { me, can } = useSession();
  const navigate = useNavigate();
  // Never ask for what the role can't see: no lab:read, no request.
  const [overview, { refetch: refetchLab }] = createResource(() => (can("lab:read") ? true : null), () => lab.get());
  const roundN = () => props.n ?? overview()?.candidate ?? overview()?.live ?? null;
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
    <AppPage title="Lab" scope="lab" permission="lab:read" placeholder="Search rounds, chapters or rulings" boxLabel="Search the lab" onSearch={(q) => navigate(`/rulings?q=${encodeURIComponent(q)}`)}>
      <Switch>
        <Match when={overview.error || round.error}>
          <div class="gm py-10">
            <div class="gl" />
            <div class="gm-body">
              <ErrorSlip error={overview.error ?? round.error} retry={() => (overview.error ? refetchLab() : refetch())} />
            </div>
          </div>
        </Match>
        <Match when={overview() && !overview()!.rounds.length}>
          <div class="gm py-10">
            <div class="gl" />
            <div class="gm-body">
              <EmptyState title="No training rounds yet">The first round is tested on the newest rulings and reported here before anyone can make it live.</EmptyState>
            </div>
          </div>
        </Match>
        <Match when={overview() && round()}>
          <RoundsStrip lab={overview()!} current={round()!.n} />
          <Show when={can("lab:run")}>
            <div class="flex flex-wrap items-center justify-end gap-3 px-8 pt-3 max-md:px-4">
              <Show when={job()}>
                {(j) => (
                  <Progress.Root value={Math.round(j().progress * 100)} class="w-[320px]">
                    <Progress.Label class="text-[14px] text-ink-2">{j().message || "Training…"}</Progress.Label>
                    <Progress.Track class="mt-1 h-2 overflow-hidden rounded-[2px] border border-ink">
                      <Progress.Range class="h-full bg-ink" />
                    </Progress.Track>
                  </Progress.Root>
                )}
              </Show>
              <button type="button" class={button({ tone: "ghost", size: "sm" })} disabled={!!job()} onClick={() => void start()}>
                Start training round {(overview()!.rounds.at(-1)?.n ?? 0) + 1}
              </button>
              <span class="text-[14px] text-muted">{overview()!.correctionsWaiting} broker corrections waiting</span>
            </div>
          </Show>
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
          <PageLoading label="Opening the lab report…" />
        </Match>
      </Switch>
    </AppPage>
  );
}

