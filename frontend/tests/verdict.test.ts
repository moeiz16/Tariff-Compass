import { describe, expect, it } from "vitest";
import { bottleAnswer, tumblerAnswer } from "~/lib/mock/answers";
import { depthWords, digitTreatment } from "~/lib/verdict";

describe("the confidence word at each depth", () => {
  it("falls back to the overall word when the API sends none", () => {
    expect(depthWords({ word: "strong", byDepth: [] })).toBeNull();
    expect(depthWords({ word: "broker" })).toBeNull();
    expect(digitTreatment({ leaning: false }, null)).toEqual({ heading: "hl", rest: "plain" });
    expect(digitTreatment({ leaning: true }, null)).toEqual({ heading: "dashed", rest: "plain" });
  });

  it("puts a sure heading on the highlighter and rules the unsure last digits", () => {
    const w = depthWords(bottleAnswer().verdict);
    expect(w).toEqual({ heading: "strong", full: "broker" });
    expect(digitTreatment({ leaning: true }, w)).toEqual({ heading: "hl", rest: "dashed" });
  });

  it("rules every digit when neither depth is sure, and none when both are", () => {
    expect(digitTreatment({ leaning: true }, { heading: "broker", full: "broker" })).toEqual({ heading: "dashed", rest: "dashed" });
    expect(digitTreatment({ leaning: false }, { heading: "strong", full: "strong" })).toEqual({ heading: "hl", rest: "plain" });
  });

  it("fills a missing depth from the overall word", () => {
    expect(depthWords({ word: "broker", byDepth: [{ level: "heading", levelLabel: "Heading", word: "strong", wordLabel: "Strong match" }] })).toEqual({ heading: "strong", full: "broker" });
  });

  it("keeps the overall word as the full-code word in the fixtures", () => {
    const b = bottleAnswer().verdict;
    expect(b.word).toBe(b.byDepth!.find((d) => d.level === "full_code")!.word);
    expect(tumblerAnswer().verdict.byDepth).toBeUndefined();
  });
});
