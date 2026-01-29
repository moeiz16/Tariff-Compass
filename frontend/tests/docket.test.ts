import { describe, expect, it } from "vitest";
import { canadaFor, checkCorrection, docketKeyAction, isTyping } from "~/lib/docket";

const key = (k: string, mods: Partial<KeyboardEvent> = {}) => ({ key: k, metaKey: false, ctrlKey: false, altKey: false, ...mods });
const broker = { typing: false, canDecide: true, open: true };

describe("docket keys", () => {
  it("moves with J and K for everyone", () => {
    expect(docketKeyAction(key("j"), { ...broker, canDecide: false, open: false })).toBe("next");
    expect(docketKeyAction(key("K"), broker)).toBe("prev");
  });

  it("decides with A, C and Q only for a broker with a row open", () => {
    expect(docketKeyAction(key("a"), broker)).toBe("approve");
    expect(docketKeyAction(key("c"), broker)).toBe("correct");
    expect(docketKeyAction(key("q"), broker)).toBe("ask");
    expect(docketKeyAction(key("a"), { ...broker, canDecide: false })).toBeNull();
    expect(docketKeyAction(key("a"), { ...broker, open: false })).toBeNull();
  });

  it("leaves letters alone while the person is typing, and ignores shortcuts with modifiers", () => {
    expect(docketKeyAction(key("a"), { ...broker, typing: true })).toBeNull();
    expect(docketKeyAction(key("j"), { ...broker, typing: true })).toBeNull();
    expect(docketKeyAction(key("c", { metaKey: true }), broker)).toBeNull();
  });

  it("closes the open record with Escape, even from a field", () => {
    expect(docketKeyAction(key("Escape"), { ...broker, typing: true })).toBe("close");
    expect(docketKeyAction(key("Escape"), { ...broker, open: false })).toBeNull();
  });

  it("recognises fields as typing", () => {
    expect(isTyping({ tagName: "INPUT" } as Element)).toBe(true);
    expect(isTyping({ tagName: "TEXTAREA" } as Element)).toBe(true);
    expect(isTyping({ tagName: "TR", isContentEditable: false } as unknown as Element)).toBe(false);
    expect(isTyping(null)).toBe(false);
  });
});

describe("a correction", () => {
  const base = { proposed: "9617.00.10.00", pins: "7323930080".split(""), reasonKind: "facts_differ" as const, reason: "Spec sheet says air-insulated, not vacuum-sealed.", alsoChangeCa: false };

  it("is sent with the code in the official grouping", () => {
    const c = checkCorrection(base);
    expect(c.ok).toBe(true);
    expect(c.usCode).toBe("7323.93.00.80");
    expect(c.caCode).toBeUndefined();
  });

  it("offers Canada's tariff item when asked", () => {
    expect(checkCorrection({ ...base, alsoChangeCa: true }).caCode).toBe("7323.93.00.00");
    expect(canadaFor("7323930080")).toBe("7323.93.00.00");
    expect(canadaFor("7323")).toBe("");
  });

  it("needs all ten digits", () => {
    const c = checkCorrection({ ...base, pins: ["7", "3", "2", "3", "", "", "", "", "", ""] });
    expect(c.ok).toBe(false);
    expect(c.errors.code).toMatch(/ten digits/);
  });

  it("refuses a code identical to the proposal", () => {
    expect(checkCorrection({ ...base, pins: "9617001000".split("") }).errors.code).toMatch(/Approve/);
  });

  it("needs a reason kind and a reason of at least ten characters", () => {
    const c = checkCorrection({ ...base, reasonKind: null, reason: "too short" });
    expect(c.errors.reasonKind).toBeTruthy();
    expect(c.errors.reason).toMatch(/at least 10/);
  });
});
