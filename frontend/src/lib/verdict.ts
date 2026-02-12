/**
 * The confidence word at each depth. A code can be sure at the heading and still need a broker for the last digits:
 * the heading digits then sit on the highlighter and the rest carry the dashed amber rule.
 */
import type { CodeOut, Verdict, VerdictOut } from "./types";

export interface DepthWords {
  heading: Verdict;
  full: Verdict;
}

/** Words by depth from the API, or null when it sends none (then the overall word and `leaning` rule as before). */
export function depthWords(v: Pick<VerdictOut, "word" | "byDepth">): DepthWords | null {
  const list = v.byDepth ?? [];
  if (!list.length) return null;
  const at = (level: "heading" | "full_code") => list.find((d) => d.level === level)?.word ?? v.word;
  return { heading: at("heading"), full: at("full_code") };
}

export type DigitTreatment = "hl" | "dashed" | "plain";

/** How to draw the heading digits and the remaining digits of a code. */
export function digitTreatment(code: Pick<CodeOut, "leaning">, words: DepthWords | null): { heading: DigitTreatment; rest: DigitTreatment } {
  if (!words) return { heading: code.leaning ? "dashed" : "hl", rest: "plain" };
  return { heading: words.heading === "strong" ? "hl" : "dashed", rest: words.full === "strong" ? "plain" : "dashed" };
}
