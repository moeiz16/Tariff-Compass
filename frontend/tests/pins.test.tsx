// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@solidjs/testing-library";
import { createSignal } from "solid-js";
import { afterEach, describe, expect, it } from "vitest";
import { CodePins } from "~/components/review/CodePins";

afterEach(cleanup);

function Harness(props: { initial?: string[] }) {
  const [v, setV] = createSignal<string[]>(props.initial ?? Array(10).fill(""));
  return (
    <>
      <CodePins proposed="9617.00.10.00" value={v()} onChange={setV} />
      <output data-testid="typed">{v().join("")}</output>
    </>
  );
}

describe("correct one digit (10-cell pin input)", () => {
  it("renders ten digit cells under the proposed code, with dots between groups", () => {
    render(() => <Harness />);
    const cells = screen.getAllByRole("textbox", { name: /Digit \d+ of your code/ });
    expect(cells).toHaveLength(10);
    expect(screen.getByRole("img", { name: "Proposed code 9617.00.10.00" }).textContent).toBe("9617.00.10.00");
  });

  it("marks changed cells and strikes the proposed digits they replace", () => {
    render(() => <Harness initial={"7323930080".split("")} />);
    const cells = screen.getAllByRole("textbox", { name: /Digit \d+ of your code/ });
    const changed = cells.map((c) => c.getAttribute("data-changed"));
    expect(changed).toEqual(["true", "true", "true", "true", "true", "true", "true", "false", "true", "false"]);
    const struck = screen.getByRole("img", { name: /Proposed code/ }).querySelectorAll(".strike-bad");
    expect(Array.from(struck).map((s) => s.textContent).join("")).toBe("96170010");
  });

  it("takes a pasted code with dots and spreads it across the cells", () => {
    render(() => <Harness />);
    const control = screen.getAllByRole("textbox", { name: /Digit 1 of your code/ })[0]!.parentElement!;
    const data = { getData: () => "7323.93.00.80" };
    fireEvent.paste(control, { clipboardData: data });
    expect(screen.getByTestId("typed").textContent).toBe("7323930080");
  });
});
