import { A, useSearchParams } from "@solidjs/router";
import { Match, Show, Switch, createResource, createSignal } from "solid-js";
import { AnswerError, AnswerLoading, AnswerMemo } from "~/components/answer/AnswerMemo";
import { AppPage } from "~/components/shell/AppPage";
import { answers, meta } from "~/lib/endpoints";
import { answerCache, useBrokerName } from "~/lib/org";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { AnswerOut, Country } from "~/lib/types";
import { button } from "~/ui/recipes";
import { Sheet } from "~/ui/Sheet";
import { EmptyState } from "~/ui/States";
import { notify } from "~/ui/Toast";

export default function AnswerPage() {
  const [params, setParams] = useSearchParams<{ id?: string; q?: string; into?: string; from?: string; ev?: string; cite?: string }>();
  const { can } = useSession();
  const broker = useBrokerName();
  const [override, setOverride] = createSignal<AnswerOut | null>(null);

  const [answer, { refetch }] = createResource(
    () => ({ id: params.id, q: params.q, into: params.into, from: params.from, ev: params.ev }),
    async (k) => {
      setOverride(null);
      if (k.id) return answerCache.get(k.id) ?? (await answers.get(k.id));
      if (!k.q && !k.ev) return null;
      if (!can("classify:run")) return null; // the role reads answers but doesn't classify: no request

      const a = await answers.classify({
        text: k.q ?? "",
        madeIn: k.from ?? "CN",
        into: (k.into?.split(",") ?? ["US", "CA"]) as Country[],
        evidenceIds: k.ev ? k.ev.split(",") : [],
        confirmedFacts: [],
      });
      answerCache.put(a);
      setParams({ id: a.id, q: k.q, into: undefined, from: undefined, ev: undefined }, { replace: true });
      return a;
    },
  );
  const [recent] = createResource(() => meta.home().catch(() => null));

  const current = () => override() ?? answer.latest ?? null;
  const [sending, setSending] = createSignal(false);
  const [note, setNote] = createSignal("");
  const [busy, setBusy] = createSignal(false);
  const [sheetError, setSheetError] = createSignal("");

  const save = async () => {
    const a = current();
    if (!a) return;
    setBusy(true);
    try {
      const v = await answers.save(a.id, a.productId ?? undefined);
      notify(`Saved · binder v${v.n}`, `${v.usCode ?? ""} recorded with the rulings it relies on.`);
    } catch (e) {
      notify("Not saved", plainProblem(e).message, "error");
    } finally {
      setBusy(false);
    }
  };
  const send = async () => {
    const a = current();
    if (!a) return;
    setBusy(true);
    setSheetError("");
    try {
      const row = await answers.sendToBroker(a.id, note());
      setSending(false);
      notify(`Sent to ${broker()} · ${row.sku}`, "It is in the review docket. Nothing was filed.");
    } catch (e) {
      setSheetError(plainProblem(e).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppPage title={params.q ? params.q.slice(0, 60) : "Answer"} scope="answer" query={params.q ?? current()?.query.text}>
      <Switch>
        <Match when={answer.loading && !current()}>
          <AnswerLoading />
        </Match>
        <Match when={answer.error}>
          <AnswerError error={answer.error} retry={() => void refetch()} brokerName={broker()} />
        </Match>
        <Match when={current()} keyed>
          {(a) => (
            <AnswerMemo
              answer={a}
              openCites={params.cite ? params.cite.split(",").map(Number) : undefined}
              caps={{ live: true, canConfirm: can("classify:run"), canSend: can("review:submit"), canFlag: can("review:decide"), brokerName: broker() }}
              onAnswer={(next) => {
                answerCache.put(next);
                setOverride(next);
                notify("Answer re-run with your fact", "The question and your answer are recorded in the binder.");
              }}
              onSend={() => setSending(true)}
              actions={
                <>
                  <Show when={can("products:write")}>
                    <button type="button" class={button({ size: "lg" })} disabled={busy()} onClick={() => void save()}>
                      Save to the product binder
                    </button>
                  </Show>
                  <Show when={can("review:submit")}>
                    <button type="button" class={button({ tone: "ghost", size: "lg" })} onClick={() => setSending(true)}>
                      Send to {broker()} for review
                    </button>
                  </Show>
                  <Show when={can("review:decide") && a.reviewItemId}>
                    <A href={`/review?open=${a.reviewItemId}`} class={button({ size: "lg" })}>
                      Open it in the review docket
                    </A>
                  </Show>
                  <p class="text-[14.5px] text-muted">Nothing is filed automatically. A licensed broker approves every code.</p>
                </>
              }
            />
          )}
        </Match>
        <Match when={!answer.loading}>
          <div class="gm py-12">
            <div class="gl">
              <b>Answer</b>
            </div>
            <div class="gm-body">
              <EmptyState
                title={params.q && !can("classify:run") ? "Your role reads answers but doesn't classify" : "Ask about a product"}
                action={
                  <Show when={recent()?.recent.length}>
                    <A href={`/answer?id=${recent()!.recent[0]!.id}`} class={button({ tone: "ghost", size: "sm" })}>
                      Open your latest answer
                    </A>
                  </Show>
                }
              >
                Describe it in the box above, paste a listing, or attach a spec sheet or photo. You get its US and Canadian codes, the rulings that back them and
                every duty it will carry.
              </EmptyState>
            </div>
          </div>
        </Match>
      </Switch>
      <Sheet
        open={sending()}
        onOpenChange={setSending}
        title={`Send to ${broker()} for review`}
        description="A licensed broker reviews the code before it is used on an entry. Add anything they should know."
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <label for="send-note" class="text-[13px] font-[650] text-ink-2">
            Note for the broker (optional)
          </label>
          <textarea
            id="send-note"
            value={note()}
            onInput={(e) => setNote(e.currentTarget.value)}
            class="mt-1 min-h-[96px] w-full rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper px-3 py-2 text-[15.5px] text-ink"
            placeholder="The March order books on Monday."
          />
          <Show when={sheetError()}>
            <p role="alert" class="mt-2 text-[14px] font-[600] text-bad">
              {sheetError()}
            </p>
          </Show>
          <div class="mt-4 flex gap-2">
            <button type="submit" class={button()} disabled={busy()}>
              Send for review
            </button>
            <button type="button" class={button({ tone: "ghost" })} onClick={() => setSending(false)}>
              Not yet
            </button>
          </div>
        </form>
      </Sheet>
    </AppPage>
  );
}
