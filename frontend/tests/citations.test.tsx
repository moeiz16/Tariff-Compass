// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@solidjs/testing-library";
import { inRouter } from "./router";
import { afterEach, describe, expect, it } from "vitest";
import { CitationChip, RulingDrawer } from "~/components/answer/Citations";
import { createCitationState, moveBetweenChips } from "~/lib/citations";
import { tumblerAnswer } from "~/lib/mock/answers";

afterEach(cleanup);

function Sentence(props: { initial?: number }) {
  const answer = tumblerAnswer();
  const state = createCitationState(props.initial ?? null);
  return (
    <div>
      <p>
        Heading 9617 names vacuum vessels outright.
        <CitationChip n={1} ruling={answer.rulings[0]} state={state} />
        <CitationChip n={3} ruling={answer.rulings[2]} state={state} />
      </p>
      <RulingDrawer rulings={answer.rulings} state={state} answerId={answer.id} />
    </div>
  );
}

describe("citation state", () => {
  it("opens one ruling at a time", () => {
    const s = createCitationState();
    s.show(3);
    expect(s.open()).toBe(3);
    s.show(1);
    expect(s.isOpen(1)).toBe(true);
    expect(s.isOpen(3)).toBe(false);
    s.toggle(1);
    expect(s.open()).toBeNull();
    s.show(2);
    s.close();
    expect(s.open()).toBeNull();
  });
});

describe("the ruling drawer", () => {
  it("opens from a citation number with the holding and the fact compare", async () => {
    render(inRouter(() => <Sentence />));
    const chip = await screen.findByRole("button", { name: /Citation 1: NY N321134/ });
    expect(chip.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("dialog")).toBeNull();

    fireEvent.click(chip);
    const drawer = await screen.findByRole("dialog", { name: /NY N321134/ });
    expect(chip.getAttribute("aria-expanded")).toBe("true");
    expect(drawer.textContent).toContain("9617.00.1000");
    expect(drawer.textContent).toContain("Between the walls");
    expect(drawer.querySelector("mark")?.textContent).toBe("9617.00.1000");
  });

  it("switches to another ruling from its number", async () => {
    render(inRouter(() => <Sentence initial={1} />));
    expect(await screen.findByRole("dialog", { name: /NY N321134/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Citation 3: NY N297165/ }));
    expect(await screen.findByRole("dialog", { name: /NY N297165/ })).toBeTruthy();
  });

  it("links to the side-by-side compare for the cited answer", async () => {
    render(inRouter(() => <Sentence initial={1} />));
    const link = await screen.findByRole("link", { name: "Compare side by side" });
    expect(link.getAttribute("href")).toBe("/rulings/ny-n321134?answerId=ans-tumbler&n=1");
  });

  it("moves between numbers with [ and ]", async () => {
    render(inRouter(() => <Sentence />));
    const chips = await screen.findAllByRole("button", { name: /^Citation/ });
    const press = (key: string) => {
      const e = new KeyboardEvent("keydown", { key, cancelable: true });
      Object.defineProperty(e, "target", { value: document.body });
      return moveBetweenChips(e, document);
    };
    expect(press("]")).toBe(true);
    expect(document.activeElement).toBe(chips[0]);
    press("]");
    expect(document.activeElement).toBe(chips[1]);
    press("[");
    expect(document.activeElement).toBe(chips[0]);
    expect(press("x")).toBe(false);
  });
});
