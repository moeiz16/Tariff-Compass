// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@solidjs/testing-library";
import { afterEach, describe, expect, it } from "vitest";
import { AnswerCard, AnswerView } from "~/components/answer/AnswerView";
import { createCitationState } from "~/lib/citations";
import { bottleAnswer, tumblerAnswer } from "~/lib/mock/answers";
import { inRouter } from "./router";

afterEach(cleanup);

const caps = { live: false, canConfirm: false, canSend: false, canFlag: false, brokerName: "Driftwood" };

describe("the answer card", () => {
  it("leads with the word, both codes and one line of why", () => {
    render(inRouter(() => <AnswerCard answer={tumblerAnswer()} state={createCitationState()} />));
    expect(screen.getByText("Strong match")).toBeTruthy();
    expect(screen.getByLabelText("9617.00.10.00")).toBeTruthy();
    expect(screen.getByLabelText("9617.00.00.00")).toBeTruthy();
    expect(screen.getByText(/heading 9617 names vacuum vessels outright/)).toBeTruthy();
    expect(screen.queryByLabelText("The confidence word at each depth")).toBeNull();
  });

  it("shows the word at each depth when they differ, with an icon for each", () => {
    render(inRouter(() => <AnswerCard answer={bottleAnswer()} state={createCitationState()} />));
    const list = screen.getByLabelText("The confidence word at each depth");
    expect(list.textContent).toContain("Heading");
    expect(list.textContent).toContain("Full code");
    expect(list.querySelectorAll("svg")).toHaveLength(2);
  });

  it("marks a sure heading and leaves the unsure last digits dashed", () => {
    render(inRouter(() => <AnswerCard answer={bottleAnswer()} state={createCitationState()} />));
    const us = screen.getByLabelText("9617.00.10.00");
    const groups = Array.from(us.querySelectorAll("[data-treatment]")).map((g) => g.getAttribute("data-treatment"));
    expect(groups).toEqual(["hl", "dashed", "dashed", "dashed"]);
  });
});

describe("the layers", () => {
  it("keep the detail folded behind five rows with a summary each", async () => {
    render(inRouter(() => <AnswerView answer={tumblerAnswer()} caps={caps} />));
    for (const name of ["Why this code", "Rulings", "Landed cost", "Facts", "Law text"]) {
      const row = screen.getByRole("button", { name: new RegExp(name) });
      expect(row.getAttribute("aria-expanded")).toBe("false");
    }
    expect(screen.getByRole("button", { name: /Rulings/ }).textContent).toMatch(/of \d+ agree/);
    expect(screen.queryByLabelText("Classification path")).toBeNull();

    const why = screen.getByRole("button", { name: /Why this code/ });
    why.focus();
    fireEvent.click(why);
    await new Promise((r) => setTimeout(r, 50));
    expect(why.getAttribute("aria-expanded")).toBe("true");
    expect(await screen.findByLabelText("Classification path")).toBeTruthy();
  });
});
