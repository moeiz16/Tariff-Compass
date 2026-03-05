import { Tabs } from "@ark-ui/solid/tabs";
import { A, useNavigate } from "@solidjs/router";
import { For, Show, createResource } from "solid-js";
import { AppPage } from "~/components/shell/AppPage";
import { SearchBox } from "~/components/shell/SearchBox";
import { meta } from "~/lib/endpoints";
import { whenLabel } from "~/lib/format";
import { useSession } from "~/lib/session";
import { CodeDigits } from "~/ui/Code";
import { ChevronIcon } from "~/ui/Icons";
import { card, tabs, tag } from "~/ui/recipes";
import { EmptyState, ErrorSlip, SkeletonLines } from "~/ui/States";
import { VerdictTag } from "~/ui/Status";

export default function Home() {
  const { me, can } = useSession();
  const navigate = useNavigate();
  const [home, { refetch }] = createResource(() => (me() ? true : null), () => meta.home());
  const [m] = createResource(() => (me() ? true : null), () => meta.get().catch(() => null));
  const t = tabs();
  const row = "flex items-center gap-4 border-b border-rule px-5 py-3.5 no-underline last:border-b-0 hover:bg-paper-2/60 max-sm:px-4";

  return (
    <AppPage title="Home" place={can("classify:run") ? "classify" : "none"} width="narrow">
      <div class="pt-[clamp(8px,5vh,48px)] text-center">
        <h1 class="text-[clamp(28px,3.2vw,36px)] font-[600] leading-[1.15] tracking-[-0.025em]">
          {can("classify:run") ? "What are you importing?" : `Welcome, ${me()?.user.fullName.split(" ")[0] ?? ""}`}
        </h1>
        <p class="mt-2 text-[14px] text-muted">{home()?.dateLine ?? m()?.snapshot.label ?? ""}</p>
      </div>
      <Show when={can("classify:run")}>
        <div class="mt-7">
          <SearchBox
            id="q-home"
            mode="classify"
            size="hero"
            label="Describe a product, paste a listing, or attach a spec sheet"
            placeholder="Describe a product…"
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

      <Tabs.Root defaultValue="recent" class="mt-12">
        <Tabs.List class={t.list()} aria-label="Your work">
          <Tabs.Trigger value="recent" class={t.trigger()}>
            Recent
          </Tabs.Trigger>
          <Show when={can("watch:read")}>
            <Tabs.Trigger value="changes" class={t.trigger()}>
              Changes
              <Show when={home()?.changes.length}>
                <span class={t.count()}>{home()!.changes.length}</span>
              </Show>
            </Tabs.Trigger>
          </Show>
          <Tabs.Indicator class={t.indicator({ class: "w-[var(--width)] left-[var(--left)]" })} />
        </Tabs.List>
        <Tabs.Content value="recent" class="mt-4">
          <Show when={!home.error} fallback={<ErrorSlip error={home.error} retry={refetch} />}>
            <Show when={home()} fallback={<SkeletonLines lines={5} />}>
              {(h) => (
                <Show when={h().recent.length} fallback={<EmptyState title="Nothing classified yet" />}>
                  <ul class={card({ class: "overflow-hidden" })}>
                    <For each={h().recent.filter((r, i, all) => all.findIndex((x) => x.queryText === r.queryText) === i).slice(0, 6)}>
                      {(r) => (
                        <li>
                          <A href={`/answer?id=${r.id}&q=${encodeURIComponent(r.queryText)}`} class={row}>
                            <span class="min-w-0 flex-1">
                              <span class="block truncate text-[15px] font-[550]">{r.queryText}</span>
                              <span class="mt-0.5 block text-[12.5px] text-muted">
                                {whenLabel(r.createdAt)} · {r.createdBy}
                              </span>
                            </span>
                            <Show when={r.usCode}>
                              <span class="max-sm:hidden">
                                <CodeDigits code={r.usCode!} size="sm" leaning={r.verdict === "broker"} />
                              </span>
                            </Show>
                            <VerdictTag word={r.verdict} label={r.verdictLabel} />
                          </A>
                        </li>
                      )}
                    </For>
                  </ul>
                </Show>
              )}
            </Show>
          </Show>
        </Tabs.Content>
        <Tabs.Content value="changes" class="mt-4">
          <Show when={home()} fallback={<SkeletonLines lines={4} />}>
            {(h) => (
              <Show when={h().changes.length} fallback={<EmptyState title="Nothing new touches your products" />}>
                <ul class={card({ class: "overflow-hidden" })}>
                  <For each={h().changes}>
                    {(c) => (
                      <li>
                        <A href={`/watch?open=${c.id}`} class={row}>
                          <span class="min-w-0 flex-1">
                            <span class="block text-[15px] font-[550]">{c.headline}</span>
                          </span>
                          <span class={tag({ tone: "hi", class: "font-sans" })}>
                            {c.affectedCount} {c.affectedCount === 1 ? "product" : "products"}
                          </span>
                          <ChevronIcon size={15} class="-rotate-90 text-muted" />
                        </A>
                      </li>
                    )}
                  </For>
                </ul>
              </Show>
            )}
          </Show>
        </Tabs.Content>
      </Tabs.Root>
    </AppPage>
  );
}
