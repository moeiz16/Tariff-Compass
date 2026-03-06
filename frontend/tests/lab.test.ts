// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { checkValue } from "~/components/lab/LabReport";

describe("release checks read as frequencies", () => {
  it("says a share as so many in 100 against what it needs", () => {
    expect(checkValue("0.2481", "0.3609")).toBe("25 in 100 · needs 36");
  });
  it("says a drop as points against its limit", () => {
    expect(checkValue("-0.1739", "-0.03")).toBe("-17 points · limit -3");
  });
  it("leaves anything that isn't a share as it is", () => {
    expect(checkValue("12", "10")).toBe("12 (10)");
  });
});
