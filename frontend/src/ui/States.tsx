/** Empty, loading and error states in the product's voice. Errors are RFC 7807 problems said in plain words. */
import { For, Show, type JSX } from "solid-js";
import { plainProblem } from "~/lib/problem";
import { CompassMark } from "./Compass";
import { WarnIcon } from "./Icons";
import { button } from "./recipes";

export function ErrorSlip(props: { error: unknown; retry?: () => void; children?: JSX.Element }) {
  const p = () => plainProblem(props.error);
  return (
    <div role="alert" class="rounded-[var(--radius-box)] border-[1.5px] border-dashed border-ink bg-paper-2 px-5 py-4">
      <p class="flex items-start gap-2.5 text-[16px] font-[600]">
        <WarnIcon size={18} class="mt-0.5 shrink-0 text-warn" />
        <span>{p().message}</span>
      </p>
      {props.children}
      <div class="mt-3 flex flex-wrap items-center gap-3 text-[13px] text-muted">
        <Show when={props.retry}>
          <button type="button" class={button({ tone: "ghost", size: "sm" })} onClick={() => props.retry?.()}>
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
    <div class="border-y border-rule py-10 text-center">
      <CompassMark size={36} class="mx-auto text-muted" />
      <p class="mt-3 text-[18px] font-[700]">{props.title}</p>
      <Show when={props.children}>
        <div class="mx-auto mt-1.5 max-w-[520px] text-[15px] text-ink-2">{props.children}</div>
      </Show>
      <Show when={props.action}>
        <div class="mt-4 flex justify-center gap-2">{props.action}</div>
      </Show>
    </div>
  );
}

export function Bearing(props: { label?: string }) {
  return (
    <p role="status" class="flex items-center gap-3 text-[16px] text-ink-2">
      <CompassMark size={26} state="seek" />
      <span>{props.label ?? "Taking a bearing…"}</span>
    </p>
  );
}

export function SkeletonLines(props: { lines?: number; class?: string }) {
  return (
    <div class={`space-y-3 ${props.class ?? ""}`} aria-hidden="true">
      <For each={Array.from({ length: props.lines ?? 4 }, (_, i) => i)}>
        {(i) => <div class="skeleton h-4" style={{ width: `${92 - ((i * 17) % 40)}%` }} />}
      </For>
    </div>
  );
}

/** Loading frame for any page: the needle seeks and skeleton lines hold the layout. */
export function PageLoading(props: { label?: string }) {
  return (
    <div class="gm py-10">
      <div class="gl" />
      <div class="gm-body space-y-6">
        <Bearing label={props.label} />
        <SkeletonLines lines={5} />
      </div>
    </div>
  );
}
