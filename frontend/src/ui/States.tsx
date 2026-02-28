/** Empty, loading and error states. Errors are RFC 7807 problems said in plain words. */
import { For, Show, type JSX } from "solid-js";
import { plainProblem } from "~/lib/problem";
import { CompassMark } from "./Compass";
import { WarnIcon } from "./Icons";
import { button } from "./recipes";

export function ErrorSlip(props: { error: unknown; retry?: () => void; children?: JSX.Element }) {
  const p = () => plainProblem(props.error);
  return (
    <div role="alert" class="rounded-[var(--radius-box)] border border-rule bg-card px-5 py-4">
      <p class="flex items-start gap-2.5 text-[15px] font-[600]">
        <WarnIcon size={18} class="mt-0.5 shrink-0 text-warn" />
        <span>{p().message}</span>
      </p>
      {props.children}
      <div class="mt-3 flex flex-wrap items-center gap-3 text-[12.5px] text-muted">
        <Show when={props.retry}>
          <button type="button" class={button({ tone: "outline", size: "sm" })} onClick={() => props.retry?.()}>
            Try again
          </button>
        </Show>
        <Show when={p().requestId}>
          <span>
            Reference <span class="font-code">{p().requestId}</span>
          </span>
        </Show>
      </div>
    </div>
  );
}

export function EmptyState(props: { title: string; children?: JSX.Element; action?: JSX.Element }) {
  return (
    <div class="px-4 py-14 text-center">
      <CompassMark size={32} class="mx-auto text-muted" />
      <p class="mt-3 text-[16px] font-[600]">{props.title}</p>
      <Show when={props.children}>
        <div class="mx-auto mt-1 max-w-[440px] text-[14px] text-muted">{props.children}</div>
      </Show>
      <Show when={props.action}>
        <div class="mt-4 flex justify-center gap-2">{props.action}</div>
      </Show>
    </div>
  );
}

export function Bearing(props: { label?: string }) {
  return (
    <p role="status" class="flex items-center gap-2.5 text-[14.5px] text-muted">
      <CompassMark size={22} state="seek" class="text-ink" />
      <span>{props.label ?? "Reading the tariff…"}</span>
    </p>
  );
}

export function SkeletonLines(props: { lines?: number; class?: string }) {
  return (
    <div class={`space-y-3 ${props.class ?? ""}`} aria-hidden="true">
      <For each={Array.from({ length: props.lines ?? 4 }, (_, i) => i)}>
        {(i) => <div class="skeleton h-3.5" style={{ width: `${92 - ((i * 17) % 40)}%` }} />}
      </For>
    </div>
  );
}

/** Loading frame for any page: the needle seeks and skeleton lines hold the layout. */
export function PageLoading(props: { label?: string }) {
  return (
    <div class="mx-auto max-w-[960px] space-y-6 px-6 py-12 max-sm:px-4">
      <Bearing label={props.label} />
      <SkeletonLines lines={5} />
    </div>
  );
}
