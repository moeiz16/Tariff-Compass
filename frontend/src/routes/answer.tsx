import { A, useNavigate, useSearchParams } from "@solidjs/router";
import { Match, Show, Switch, createResource, createSignal } from "solid-js";
import { AnswerError, AnswerLoading, AnswerView } from "~/components/answer/AnswerView";
import { AppPage, PageHead } from "~/components/shell/AppPage";
import { SearchBox } from "~/components/shell/SearchBox";
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
  const { can, me } = useSession();
  const navigate = useNavigate();
  const [asking, setAsking] = createSignal(false);
  const broker = useBrokerName();
  const [override, setOverride] = createSignal<AnswerOut | null>(null);

  const [answer, { refetch }] = createResource(
    // Wait for the session, so the role check below sees the signed-in person.
    () => (me() ? { id: params.id, q: params.q, into: params.into, from: params.from, ev: params.ev } : null),
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

  const question = () => current()?.query.text ?? params.q ?? "";
  const intoLabel = (into: string[]) => (into.length > 1 ? "US + Canada" : into[0] === "CA" ? "Canada" : "US");
  const box = (
    <SearchBox
      id="q"
      mode="classify"
      size="compact"
      label="Describe what you're importing"
      placeholder="Describe what you're importing…"
      value={params.q ?? current()?.query.text}
      madeIn={current()?.query.madeIn}
      into={current()?.query.into}
      suggestions={recent()?.recent.map((r) => r.queryText)}
      allowFiles={can("classify:run")}
      onSubmit={(text, opts) => {
        if (!can("classify:run")) return;
        setAsking(false);
        const p = new URLSearchParams({ q: text, into: opts.into.join(","), from: opts.madeIn });
        if (opts.evidence.length) p.set("ev", opts.evidence.map((e) => e.id).join(","));
        navigate(`/answer?${p.toString()}`);
      }}
    />
  );

  return (
    <AppPage title={params.q ? params.q.slice(0, 60) : "Answer"} place="classify" width="narrow">
      <Show when={question()} fallback={<PageHead title="What are you importing?" />}>
        <PageHead
          title={<span class="line-clamp-2 text-[22px] max-sm:text-[19px]">{question()}</span>}
          meta={
            <Show when={current()}>
              {(a) => (
                <>
                  <span>Into {intoLabel(a().query.into)}</span>
                  <span aria-hidden="true">·</span>
                  <span>From {a().madeInLabel}</span>
                </>
              )}
            </Show>
          }
          actions={
            <Show when={can("classify:run")}>
              <button type="button" class={button({ tone: "outline", size: "sm" })} aria-expanded={asking()} onClick={() => setAsking((v) => !v)}>
                {asking() ? "Close" : "New question"}
              </button>
            </Show>
          }
        />
      </Show>
      <Show when={asking() || (!question() && can("classify:run"))}>
        <div class="anim-rise mb-5">{box}</div>
      </Show>
      <Switch>
        <Match when={answer.loading && !current()}>
          <AnswerLoading />
        </Match>
        <Match when={answer.error}>
          <AnswerError error={answer.error} retry={() => void refetch()} brokerName={broker()} />
        </Match>
        <Match when={current()} keyed>
          {(a) => (
            <AnswerView
              answer={a}
              openCite={params.cite ? Number(params.cite.split(",")[0]) : undefined}
              caps={{ live: true, canConfirm: can("classify:run"), canSend: can("review:submit"), canFlag: can("review:decide"), brokerName: broker() }}
              onAnswer={(next) => {
                const before = a.us?.code ?? a.ca?.code;
                const after = next.us?.code ?? next.ca?.code;
                answerCache.put(next);
                setOverride(next);
                if (after && after !== before) notify(`Changed to ${after}`, "Your answer is recorded.");
                else notify("Recorded", `The code stays ${after ?? ""}. ${broker()} can confirm it.`, "info");
              }}
              onSend={() => setSending(true)}
              actions={
                (can("products:write") || can("review:submit") || (can("review:decide") && !!a.reviewItemId)) && (
                <>
                  <Show when={can("products:write")}>
                    <button type="button" class={button({ size: "md" })} disabled={busy()} onClick={() => void save()}>
                      Save to binder
                    </button>
                  </Show>
                  <Show when={can("review:submit")}>
                    <button type="button" class={button({ tone: "outline", size: "md" })} onClick={() => setSending(true)}>
                      Send to {broker()}
                    </button>
                  </Show>
                  <Show when={can("review:decide") && a.reviewItemId}>
                    <A href={`/review?open=${a.reviewItemId}`} class={button({ size: "md" })}>
                      Open in Review
                    </A>
                  </Show>
                </>
                )
              }
            />
          )}
        </Match>
        <Match when={!answer.loading && !can("classify:run")}>
          <EmptyState
            title="Your role reads answers"
            action={
              <Show when={recent()?.recent.length}>
                <A href={`/answer?id=${recent()!.recent[0]!.id}`} class={button({ tone: "outline", size: "sm" })}>
                  Open the latest answer
                </A>
              </Show>
            }
          />
        </Match>
      </Switch>
      <Sheet
        open={sending()}
        onOpenChange={setSending}
        title={`Send to ${broker()} for review`}
        description="A licensed broker checks the code before it is used on an entry."
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <label for="send-note" class="text-[13px] font-[600] text-ink-2">
            Note (optional)
          </label>
          <textarea
            id="send-note"
            value={note()}
            onInput={(e) => setNote(e.currentTarget.value)}
            class="mt-1 min-h-[96px] w-full rounded-[var(--radius-btn)] border border-rule-2 bg-card px-3 py-2 text-[15px] text-ink outline-none focus:border-ink"
            placeholder="The March order books on Monday."
          />
          <Show when={sheetError()}>
            <p role="alert" class="mt-2 text-[14px] font-[600] text-bad">
              {sheetError()}
            </p>
          </Show>
          <div class="mt-4 flex justify-end gap-2">
            <button type="submit" class={button()} disabled={busy()}>
              Send for review
            </button>
            <button type="button" class={button({ tone: "ghost" })} onClick={() => setSending(false)}>
              Cancel
            </button>
          </div>
        </form>
      </Sheet>
    </AppPage>
  );
}
