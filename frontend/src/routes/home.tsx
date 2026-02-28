import { Title } from "@solidjs/meta";
import { A, Navigate, useNavigate } from "@solidjs/router";
import { For, Show, createResource } from "solid-js";
import { PersonMenu, ThemeButton } from "~/components/shell/QueryStrip";
import { SearchBox } from "~/components/shell/SearchBox";
import { meta } from "~/lib/endpoints";
import { whenLabel } from "~/lib/format";
import { useSession } from "~/lib/session";
import { CodeDigits } from "~/ui/Code";
import { Wordmark } from "~/ui/Compass";
import { ErrorSlip, PageLoading, SkeletonLines } from "~/ui/States";
import { VerdictTag } from "~/ui/Status";

export default function Home() {
  const { me, session, can } = useSession();
  const navigate = useNavigate();
  const [home, { refetch }] = createResource(() => (me() ? true : null), () => meta.home());
  const [counts] = createResource(() => (me() ? true : null), () => meta.counts().catch(() => null));
  const [m] = createResource(() => meta.get().catch(() => null));

  return (
    <Show when={!session.loading || session.latest} fallback={<PageLoading label="Opening Tariff Compass…" />}>
      <Show when={me()} fallback={<Navigate href="/signin?next=/home" />}>
        <Title>Front page · Tariff Compass</Title>
        <nav aria-label="Your work" class="flex items-center justify-end gap-6 px-8 pt-4 text-[17px] max-md:gap-4 max-md:px-4 max-md:text-[15.5px]">
          <Show when={can("review:read")}>
            <A href="/review" class="no-underline hover:underline">
              Review <span class="hl px-1 font-code text-[13px] font-[650]">{counts()?.review ?? ""}</span>
            </A>
          </Show>
          <Show when={can("watch:read")}>
            <A href="/watch" class="no-underline hover:underline max-sm:hidden">
              Watch <span class="hl px-1 font-code text-[13px] font-[650]">{counts()?.watch ?? ""}</span>
            </A>
          </Show>
          <Show when={can("lab:read")}>
            <A href="/lab" class="no-underline hover:underline max-sm:hidden">
              Lab
            </A>
          </Show>
          <ThemeButton />
          <PersonMenu />
        </nav>
        <main id="main" class="px-8 pb-20 pt-[clamp(28px,8vh,96px)] max-md:px-4">
          <div class="mx-auto max-w-[1060px] text-center">
            <Wordmark size="lg" />
            <p class="mt-5 font-type text-[16px] text-ink">{home()?.dateLine ?? m()?.snapshot.label ?? ""}</p>
            <Show
              when={can("classify:run")}
              fallback={
                <p class="mx-auto mt-6 max-w-[620px] text-[16.5px] text-ink-2">
                  Your role looks after people, settings and the activity record. Open them from your name at the top right, or browse{" "}
                  <A href="/products" class="underline underline-offset-4">
                    the products
                  </A>{" "}
                  and{" "}
                  <A href="/rulings" class="underline underline-offset-4">
                    the rulings
                  </A>
                  .
                </p>
              }
            >
              <div class="mx-auto mt-6 max-w-[1060px] text-left">
                <SearchBox
                  id="q-home"
                  mode="classify"
                  size="hero"
                  label="Describe a product, paste a listing, or attach a spec sheet"
                  placeholder="Describe a product, paste a listing, or attach a spec sheet…"
                  suggestions={home()?.recent.map((r) => r.queryText)}
                  origins={m()?.origins}
                  allowFiles
                  onSubmit={(text, opts) => {
                    const p = new URLSearchParams({ q: text, into: opts.into.join(","), from: opts.madeIn });
                    if (opts.evidence.length) p.set("ev", opts.evidence.map((e) => e.id).join(","));
                    navigate(`/answer?${p.toString()}`);
                  }}
                />
              </div>
            </Show>
            <p class="mt-4 flex flex-wrap justify-center gap-x-6 gap-y-1 text-[16.5px]">
              <span class="text-muted">Or search:</span>
              <A href="/rulings" class="underline decoration-rule underline-offset-[6px] hover:decoration-ink">
                Rulings
              </A>
              <A href="/tariff" class="underline decoration-rule underline-offset-[6px] hover:decoration-ink">
                Tariff text
              </A>
              <A href="/products" class="underline decoration-rule underline-offset-[6px] hover:decoration-ink">
                My products{counts()?.products !== undefined ? ` (${counts()!.products})` : ""}
              </A>
            </p>
          </div>

          <div class="mx-auto mt-14 grid max-w-[1100px] grid-cols-2 gap-x-14 gap-y-10 max-lg:grid-cols-1">
            <section aria-labelledby="recent-h">
              <div class="flex items-baseline justify-between border-b-[1.5px] border-ink pb-2">
                <h2 id="recent-h" class="ty-head">
                  Your recent classifications
                </h2>
                <A href="/products" class="text-[15px] underline underline-offset-4">
                  All products
                </A>
              </div>
              <Show when={!home.error} fallback={<div class="mt-4"><ErrorSlip error={home.error} retry={refetch} /></div>}>
                <Show when={home()} fallback={<SkeletonLines class="mt-4" lines={6} />}>
                  {(h) => (
                    <Show when={h().recent.length} fallback={<p class="py-6 text-[15.5px] text-ink-2">Nothing classified yet. Describe a product in the box above.</p>}>
                      <ul>
                        <For each={h().recent}>
                          {(r) => (
                            <li class="border-b border-rule">
                              <A href={`/answer?id=${r.id}&q=${encodeURIComponent(r.queryText)}`} class="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 py-3.5 no-underline hover:bg-paper-2">
                                <span class="min-w-0">
                                  <span class="block truncate text-[17px]">{r.queryText}</span>
                                  <span class="mt-1 flex flex-wrap items-center gap-2 text-[14px] text-muted">
                                    <VerdictTag word={r.verdict} label={r.verdictLabel} />
                                    {whenLabel(r.createdAt)} · {r.createdBy}
                                  </span>
                                </span>
                                <Show when={r.usCode}>
                                  <CodeDigits code={r.usCode!} size="sm" leaning={r.verdict === "broker"} />
                                </Show>
                              </A>
                            </li>
                          )}
                        </For>
                      </ul>
                    </Show>
                  )}
                </Show>
              </Show>
            </section>
            <Show when={can("watch:read")}>
              <section aria-labelledby="changes-h">
                <div class="flex items-baseline justify-between border-b-[1.5px] border-ink pb-2">
                  <h2 id="changes-h" class="ty-head">
                    What changed that touches your products
                  </h2>
                  <A href="/watch" class="text-[15px] underline underline-offset-4">
                    Watch
                  </A>
                </div>
                <Show when={home()} fallback={<SkeletonLines class="mt-4" lines={5} />}>
                  {(h) => (
                    <Show when={h().changes.length} fallback={<p class="py-6 text-[15.5px] text-ink-2">Nothing new touches your products since this morning's check.</p>}>
                      <ul>
                        <For each={h().changes}>
                          {(c) => (
                            <li class="border-b border-rule">
                              <A href={`/watch#${c.id}`} class="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 py-3.5 no-underline hover:bg-paper-2">
                                <span>
                                  <span class="block text-[17px]">{c.headline}</span>
                                  <span class="mt-0.5 block text-[14px] text-muted">{c.consequence}</span>
                                </span>
                                <span class="h-fit whitespace-nowrap bg-hi px-1.5 font-code text-[12.5px] font-[650] text-hi-ink">
                                  {c.affectedCount} {c.affectedCount === 1 ? "product" : "products"}
                                </span>
                              </A>
                            </li>
                          )}
                        </For>
                      </ul>
                    </Show>
                  )}
                </Show>
              </section>
            </Show>
          </div>
        </main>
      </Show>
    </Show>
  );
}
