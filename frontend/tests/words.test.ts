import { describe, expect, it } from "vitest";
import { plain, withoutBrokerClause } from "~/lib/words";

describe("plain words on screen", () => {
  it("names the confidence word and the baseline in customer words", () => {
    expect(plain("Strong match")).toBe("Confident");
    expect(plain("falls short of a Strong match")).toBe("falls short of a confident match");
    expect(plain("Full-code accuracy at least as good as word matching (in use)")).toBe("Full-code accuracy at least as good as the current method (in use)");
    expect(plain("Word matching alone gets 36.")).toBe("Current method alone gets 36.");
  });
  it("drops the broker clause the badge already says", () => {
    expect(withoutBrokerClause("No heading has enough support; a broker should confirm the code.")).toBe("No heading has enough support.");
    expect(withoutBrokerClause("The description states the fact; a broker should confirm it before the code is used.")).toBe("The description states the fact.");
  });
});
