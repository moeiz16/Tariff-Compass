import { describe, expect, it } from "vitest";
import { addMoney, subtractMoney } from "~/lib/format";
import { hasOpenLegalStatus, renderableLines, stackSegments } from "~/lib/landed";
import { tumblerLandedCA, tumblerLandedMexico, tumblerLandedUS } from "~/lib/mock/answers";

describe("landed cost", () => {
  it("refuses to render a duty line without a source or an effective date", () => {
    const cost = tumblerLandedUS();
    const broken = [...cost.lines, { ...cost.lines[0]!, letter: "x", source: "" }, { ...cost.lines[0]!, letter: "y", effectiveFrom: "" }];
    const { shown, refused } = renderableLines(broken);
    expect(shown.map((l) => l.letter)).toEqual(["a", "b", "c", "d", "e"]);
    expect(refused.map((l) => l.letter)).toEqual(["x", "y"]);
  });

  it("stacks the goods value and each charge on the same base (they add, they don't compound)", () => {
    const cost = tumblerLandedUS();
    const segs = stackSegments(cost);
    expect(segs[0]!.kind).toBe("value");
    expect(segs.reduce((s, x) => s + x.share, 0)).toBeCloseTo(1, 10);
    expect(addMoney(...cost.lines.map((l) => l.amount)).amount).toBe(cost.chargesTotal.amount);
    expect(addMoney(cost.value, cost.chargesTotal).amount).toBe(cost.landedTotal.amount);
  });

  it("matches the verified tumbler stack: 27.2%, $3,458.93 with fees, no Section 301 line", () => {
    const cost = tumblerLandedUS();
    expect(cost.chargesTotal.amount).toBe("3458.93");
    expect(cost.lines.some((l) => /301/.test(l.name))).toBe(false);
    expect(cost.notApplied.some((n) => /301/.test(n.name) && /List 4B/.test(n.why))).toBe(true);
    const emergency = cost.lines.filter((l) => l.kind === "emergency");
    expect(emergency.every((l) => l.legalStatusOpen && /Supreme Court/.test(l.legalStatus ?? ""))).toBe(true);
    const ifTheyEnd = subtractMoney(cost.chargesTotal, addMoney(...emergency.map((l) => l.amount)));
    expect(ifTheyEnd.amount).toBe("958.93");
    expect(cost.whatCouldChange[0]!.chargesTotal.amount).toBe(ifTheyEnd.amount);
    expect(hasOpenLegalStatus(cost)).toBe(true);
  });

  it("uses Canada's 7.5% MFN for the tumbler", () => {
    const ca = tumblerLandedCA();
    expect(ca.lines[0]!.rate).toBe("7.5%");
    expect(ca.lines.map((l) => l.amount.amount)).toEqual(["937.50", "671.88"]);
    expect(addMoney(...ca.lines.map((l) => l.amount))).toEqual(ca.chargesTotal);
    expect(hasOpenLegalStatus(ca)).toBe(false);
  });

  it("asks the three USMCA questions for Mexico and waives the duties only on three yeses", () => {
    expect(tumblerLandedMexico({}).questions).toHaveLength(3);
    expect(tumblerLandedMexico({ tariff_shift: true, regional_value: true }).chargesTotal.amount).toBe("3983.93");
    expect(tumblerLandedMexico({ tariff_shift: true, regional_value: true, certification: true }).chargesTotal.amount).toBe("15.63");
  });
});
