// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@solidjs/testing-library";
import { inRouter } from "./router";
import { afterEach, describe, expect, it } from "vitest";
import { CitationChip, CitationDrawer } from "~/components/answer/Citations";
import { createCitationState, moveBetweenChips } from "~/lib/citations";
import { tumblerAnswer } from "~/lib/mock/answers";

afterEach(cleanup);

function Paragraph(props: { initial?: number[] }) {
  const answer = tumblerAnswer();
  const state = createCitationState(props.initial);
  return (
    <div>
      <p>
        Heading 9617 names vacuum vessels outright.
        <CitationChip n={1} ruling={answer.rulings[0]} state={state} anchor="p0" />
        <CitationChip n={3} ruling={answer.rulings[2]} state={state} anchor="p0" />
      </p>
      <CitationDrawer ruling={answer.rulings[0]!} state={state} anchor="p0" answerId={answer.id} />
      <CitationDrawer ruling={answer.rulings[2]!} state={state} anchor="p0" answerId={answer.id} />
    </div>
  );
}

describe("citation state", () => {
  it("keeps several drawers open at once, in citation order", () => {
    const s = createCitationState();
    s.toggle(3);
    s.toggle(1);
    expect(s.open()).toEqual([1, 3]);
    s.toggle(3);
    expect(s.open()).toEqual([1]);
    s.show(1);
    expect(s.open()).toEqual([1]);
    s.closeAll();
    expect(s.open()).toEqual([]);
  });
});

describe("inline citation drawers", () => {
  it("open under the sentence when the chip is pressed, and close again", async () => {
    render(inRouter(() => <Paragraph />));
    const chip = await screen.findByRole("button", { name: /Citation 1: NY N321134/ });
    expect(chip.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("region", { name: /Citation 1/ })).toBeNull();

    fireEvent.click(chip);
    const drawer = await screen.findByRole("region", { name: "Citation 1, NY N321134" });
    expect(chip.getAttribute("aria-expanded")).toBe("true");
    expect(drawer.textContent).toContain("9617.00.1000");
    expect(drawer.textContent).toContain("Between the walls");
    expect(drawer.querySelector("mark")?.textContent).toBe("9617.00.1000");

    fireEvent.click(screen.getByRole("button", { name: /Citation 3: NY N297165/ }));
    expect(await screen.findByRole("region", { name: "Citation 3, NY N297165" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Citation 1, NY N321134" })).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "Close" })[0]!);
    await Promise.resolve();
    expect(chip.getAttribute("aria-expanded")).toBe("false");
  });

  it("links to the side-by-side compare for the cited answer", async () => {
    render(inRouter(() => <Paragraph initial={[1]} />));
    const link = await screen.findByRole("link", { name: "Compare side by side" });
    expect(link.getAttribute("href")).toBe("/rulings/ny-n321134?answerId=ans-tumbler&n=1");
  });

  it("moves between chips with [ and ]", async () => {
    render(inRouter(() => <Paragraph />));
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
