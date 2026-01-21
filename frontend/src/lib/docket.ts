/**
 * The broker docket's rules, kept apart from the screen so they can be tested: which key does what, and what a
 * correction must contain before it is sent (a ten-digit code that differs, a reason kind and a reason).
 */
import { digitsOf, groupCode } from "./format";
import type { ReasonKind } from "./types";

export type DocketAction = "next" | "prev" | "approve" | "correct" | "ask" | "close" | null;

export function docketKeyAction(e: Pick<KeyboardEvent, "key" | "metaKey" | "ctrlKey" | "altKey">, ctx: { typing: boolean; canDecide: boolean; open: boolean }): DocketAction {
  if (e.metaKey || e.ctrlKey || e.altKey) return null;
  if (e.key === "Escape") return ctx.open ? "close" : null;
  if (ctx.typing) return null;
  switch (e.key.toLowerCase()) {
    case "j":
      return "next";
    case "k":
      return "prev";
    case "a":
      return ctx.canDecide && ctx.open ? "approve" : null;
    case "c":
      return ctx.canDecide && ctx.open ? "correct" : null;
    case "q":
      return ctx.canDecide && ctx.open ? "ask" : null;
    default:
      return null;
  }
}

/** Is the keyboard focus somewhere the person is typing? Then single-letter keys belong to the field. */
export function isTyping(el: Element | null): boolean {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (el as HTMLElement).isContentEditable === true;
}

export interface CorrectionDraft {
  proposed: string; // the proposed code ("9617.00.10.00")
  pins: string[]; // ten cells, "" where empty
  reasonKind: ReasonKind | null;
  reason: string;
  alsoChangeCa: boolean;
  rulingRelied?: string | null;
}

export interface CorrectionCheck {
  ok: boolean;
  errors: Partial<Record<"code" | "reasonKind" | "reason", string>>;
  usCode?: string;
  caCode?: string;
}

/** Canada's tariff item for a US code: the first eight digits, suffix 00. Offered, never sent unless ticked. */
export function canadaFor(code: string): string {
  const d = digitsOf(code);
  return d.length >= 8 ? groupCode(`${d.slice(0, 8)}00`) : "";
}

export function checkCorrection(d: CorrectionDraft): CorrectionCheck {
  const errors: CorrectionCheck["errors"] = {};
  const typed = d.pins.map((c) => c.trim()).join("");
  if (typed.length !== 10 || !/^\d{10}$/.test(typed)) errors.code = "Type all ten digits of your code.";
  else if (typed === digitsOf(d.proposed)) errors.code = "Your code is the same as the proposed one. Approve it instead.";
  if (!d.reasonKind) errors.reasonKind = "Choose what kind of correction this is.";
  if (d.reason.trim().length < 10) errors.reason = "Give a reason for the change (at least 10 characters).";
  const ok = Object.keys(errors).length === 0;
  return ok ? { ok, errors, usCode: groupCode(typed), caCode: d.alsoChangeCa ? canadaFor(typed) : undefined } : { ok, errors };
}
