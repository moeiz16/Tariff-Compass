// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@solidjs/testing-library";
import { afterEach, describe, expect, it } from "vitest";
import { Receipt } from "~/components/answer/Landed";
import { tumblerLandedUS } from "~/lib/mock/answers";

afterEach(cleanup);

describe("the landed-cost receipt", () => {
  it("lists every charge with its rate and amount, flags open legal status and folds what doesn't apply", async () => {
    render(() => <Receipt cost={tumblerLandedUS()} />);
    const slip = screen.getByRole("group", { name: /Landed cost receipt/ });
    const text = slip.textContent ?? "";
    expect(text).toContain("Goods, customs value$12,500.00");
    expect(text).toContain("$900.00");
    expect(screen.getAllByLabelText("legal status open")).toHaveLength(2);
    expect(slip.querySelectorAll(".line-through")).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: /3 don't apply/ }));
    await Promise.resolve();
    expect(slip.querySelectorAll(".line-through")).toHaveLength(3);
    expect(slip.textContent).toContain("Section 301, China");
  });

  it("leaves out a line that has no source or date", () => {
    const cost = tumblerLandedUS();
    cost.lines = cost.lines.map((l) => (l.letter === "e" ? { ...l, source: "" } : l));
    render(() => <Receipt cost={cost} />);
    expect(screen.getByRole("group", { name: /Landed cost receipt/ }).textContent).not.toContain("Harbour maintenance fee");
  });
});
