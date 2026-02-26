/**
 * The answer, written in the shape of a CBP ruling letter: the holding band, then ¶0 In short · ¶1 Facts ·
 * ¶2 Issue · ¶3 Law and analysis · ¶4 Landed cost · ¶5 Authorities cited.
 */
import { onCleanup, onMount, untrack, type JSX } from "solid-js";
import { createCitationState, moveBetweenChips } from "~/lib/citations";
import { rise } from "~/lib/motion";
import type { AnswerOut } from "~/lib/types";
import { CompassMark } from "~/ui/Compass";
import { ErrorSlip, SkeletonLines } from "~/ui/States";
import { HoldingBand } from "./HoldingBand";
import { LandedCost } from "./Landed";
import { Analysis, Authorities, Facts, InShort, Issue } from "./Sections";

export interface MemoCapabilities {
  live: boolean; // signed in: landed cost restacks through the API
  canConfirm: boolean;
  canSend: boolean;
  canFlag: boolean;
  brokerName: string;
}

export function AnswerMemo(props: {
  answer: AnswerOut;
  caps: MemoCapabilities;
  actions?: JSX.Element;
  banner?: JSX.Element;
  openCites?: number[];
  onAnswer?: (a: AnswerOut) => void;
  onSend?: () => void;
}) {
  const state = createCitationState(untrack(() => props.openCites) ?? []);
  let root!: HTMLDivElement;
  onMount(() => {
    rise(root);
    const onKey = (e: KeyboardEvent) => moveBetweenChips(e, root);
    window.addEventListener("keydown", onKey);
    onCleanup(() => window.removeEventListener("keydown", onKey));
  });
  return (
    <div ref={root}>
      <HoldingBand answer={props.answer} actions={props.actions} lock />
      {props.banner}
      <InShort answer={props.answer} state={state} canFlag={props.caps.canFlag} />
      <Facts
        answer={props.answer}
        canConfirm={props.caps.canConfirm}
        canSend={props.caps.canSend}
        brokerName={props.caps.brokerName}
        onAnswer={(a) => props.onAnswer?.(a)}
        onSend={() => props.onSend?.()}
      />
      <Issue answer={props.answer} />
      <Analysis answer={props.answer} state={state} canFlag={props.caps.canFlag} />
      <LandedCost answer={props.answer} live={props.caps.live} />
      <Authorities answer={props.answer} />
      <p class="gm py-6 text-[13.5px] text-muted">
        <span />
        <span class="gm-body">
          {props.answer.snapshotLabel}. Nothing is filed automatically; a licensed customs broker approves every code before it is used on an entry.
        </span>
      </p>
    </div>
  );
}

/** Same frame while the classifier works: the needle seeks and the memo rows wait. */
export function AnswerLoading(props: { label?: string }) {
  return (
    <div aria-busy="true">
      <section class="border-b border-rule bg-paper-2">
        <div class="gm py-9">
          <div class="gl">
            <span>Answer</span>
            <b>Holding</b>
            <span class="gl-extra mt-5 block text-ink">
              <CompassMark size={92} state="seek" />
            </span>
          </div>
          <div class="gm-wide">
            <p role="status" class="ty-title">
              {props.label ?? "Taking a bearing…"}
            </p>
            <p class="mt-1 text-[15px] text-muted">Reading the heading texts and section notes, then checking the rulings that match.</p>
            <div class="mt-6 grid max-w-[900px] grid-cols-2 gap-10 max-md:grid-cols-1">
              <SkeletonLines lines={3} />
              <SkeletonLines lines={3} />
            </div>
          </div>
        </div>
      </section>
      {["¶ 0", "¶ 1", "¶ 2"].map((n) => (
        <section class="gm border-b border-rule py-9">
          <div class="gl">{n}</div>
          <div class="gm-body">
            <SkeletonLines lines={3} />
          </div>
        </section>
      ))}
    </div>
  );
}

export function AnswerError(props: { error: unknown; retry: () => void; brokerName?: string }) {
  return (
    <section class="border-b border-rule bg-paper-2">
      <div class="gm py-9">
        <div class="gl">
          <span>Answer</span>
          <b>Holding</b>
          <span class="gl-extra mt-5 block text-muted">
            <CompassMark size={92} />
          </span>
        </div>
        <div class="gm-body">
          <ErrorSlip error={props.error} retry={props.retry}>
            <p class="ml-7 mt-1 text-[15px] text-ink-2">
              Your question is saved. Nothing was sent to {props.brokerName ?? "your broker"} and nothing was filed.
            </p>
          </ErrorSlip>
        </div>
      </div>
    </section>
  );
}
