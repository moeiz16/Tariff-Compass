/** Status is never colour alone: every state is an icon shape plus a word. */
import { Match, Switch, type JSX } from "solid-js";
import type { MatchWord, RulingStatusOut, Verdict } from "~/lib/types";
import { tag } from "./recipes";
import { ApproxIcon, AskIcon, CloseIcon, ContrastIcon, InForceIcon, ModifiedIcon, OkIcon, RevokedIcon, SameIcon, WarnIcon } from "./Icons";

export function RulingStatusGlyph(props: { kind: RulingStatusOut["kind"]; size?: number }) {
  const s = () => props.size ?? 11;
  return (
    <Switch fallback={<InForceIcon size={s()} />}>
      <Match when={props.kind === "modified"}>
        <ModifiedIcon size={s()} class="text-warn" />
      </Match>
      <Match when={props.kind === "revoked"}>
        <RevokedIcon size={s()} class="text-bad" />
      </Match>
      <Match when={props.kind === "contrast"}>
        <ContrastIcon size={s()} />
      </Match>
    </Switch>
  );
}

export function RulingStatus(props: { status: RulingStatusOut; long?: boolean; class?: string }) {
  return (
    <span class={`inline-flex items-center gap-1.5 whitespace-nowrap text-[13px] font-[550] text-ink-2 ${props.class ?? ""}`}>
      <RulingStatusGlyph kind={props.status.kind} />
      <span>{props.long ? props.status.text || props.status.kindLabel : props.status.kindLabel}</span>
    </span>
  );
}

export function VerdictTag(props: { word: Verdict; label: string; size?: "sm" | "lg" }) {
  return (
    <span class={tag({ tone: props.word === "strong" ? "ok" : "warn", class: props.size === "lg" ? "text-[13.5px] px-3 py-1" : "" })}>
      {props.word === "strong" ? <OkIcon size={14} /> : <AskIcon size={14} />}
      {props.label}
    </span>
  );
}

export function KindTag(props: { tone: "ok" | "warn" | "bad" | "ink" | "muted"; icon?: "ok" | "ask" | "warn" | "modified" | "revoked"; children: JSX.Element }) {
  return (
    <span class={tag({ tone: props.tone })}>
      <Switch>
        <Match when={props.icon === "ok"}>
          <OkIcon size={14} />
        </Match>
        <Match when={props.icon === "ask"}>
          <AskIcon size={14} />
        </Match>
        <Match when={props.icon === "warn"}>
          <WarnIcon size={14} />
        </Match>
        <Match when={props.icon === "modified"}>
          <ModifiedIcon size={12} />
        </Match>
        <Match when={props.icon === "revoked"}>
          <RevokedIcon size={12} />
        </Match>
      </Switch>
      {props.children}
    </span>
  );
}

/** ✓ same · ≈ close · ✗ differs */
export function MatchMark(props: { match: MatchWord; label: string }) {
  return (
    <span
      class="inline-flex items-center gap-1 whitespace-nowrap text-[13px] font-[600]"
      classList={{ "text-ok": props.match === "same", "text-warn": props.match === "close", "text-bad": props.match === "differs" }}
    >
      <Switch>
        <Match when={props.match === "same"}>
          <SameIcon size={12} />
        </Match>
        <Match when={props.match === "close"}>
          <ApproxIcon size={12} />
        </Match>
        <Match when={props.match === "differs"}>
          <CloseIcon size={12} />
        </Match>
      </Switch>
      {props.label.toLowerCase()}
    </span>
  );
}
