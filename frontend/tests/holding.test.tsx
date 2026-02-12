// @vitest-environment jsdom
import { cleanup, render, screen } from "@solidjs/testing-library";
import { afterEach, describe, expect, it } from "vitest";
import { HoldingBand } from "~/components/answer/HoldingBand";
import { bottleAnswer, tumblerAnswer } from "~/lib/mock/answers";

afterEach(cleanup);

describe("the holding band", () => {
  it("shows only the overall word when there is no word by depth", () => {
    render(() => <HoldingBand answer={tumblerAnswer()} />);
    expect(screen.getByText("Strong match")).toBeTruthy();
    expect(screen.queryByLabelText("The confidence word at each depth")).toBeNull();
  });

  it("shows the confidence word at each depth, with an icon and a word for each", () => {
    const a = tumblerAnswer();
    a.verdict = {
      ...a.verdict,
      word: "broker",
      wordLabel: "Needs a broker",
      byDepth: [
        { level: "heading", levelLabel: "Heading", word: "strong", wordLabel: "Strong match" },
        { level: "full_code", levelLabel: "Full code", word: "broker", wordLabel: "Needs a broker" },
      ],
    };
    render(() => <HoldingBand answer={a} />);
    const list = screen.getByLabelText("The confidence word at each depth");
    expect(list.textContent).toContain("Heading ·Strong match");
    expect(list.textContent).toContain("Full code ·Needs a broker");
    expect(list.querySelectorAll("svg")).toHaveLength(2);
  });

  it("draws a sure heading on the highlighter and the unsure last digits with the dashed amber rule", () => {
    render(() => <HoldingBand answer={bottleAnswer()} />);
    const us = screen.getByLabelText("9617.00.10.00");
    const groups = Array.from(us.querySelectorAll("[data-treatment]")).map((g) => g.getAttribute("data-treatment"));
    expect(groups).toEqual(["hl", "dashed", "dashed", "dashed"]);
    expect(us.querySelector("[data-treatment=hl]")?.classList.contains("hl")).toBe(true);
    expect(screen.getAllByText("heading sure, last digits leaning").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("The confidence word at each depth").textContent).toContain("Heading ·Strong match");
  });
});
