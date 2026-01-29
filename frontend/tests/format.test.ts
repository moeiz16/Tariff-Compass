import { describe, expect, it } from "vitest";
import {
  addMoney,
  codeSegments,
  countWord,
  dateShort,
  dateTime,
  digitsOf,
  groupCode,
  initials,
  isFullCode,
  markSpans,
  money,
  redline,
  subtractMoney,
  waitingFor,
  whenLabel,
} from "~/lib/format";

const AT = new Date("2026-02-19T18:30:00Z"); // Thu 19 Feb 2026, 10:30 Pacific

describe("tariff codes", () => {
  it("groups ten digits 4.2.2.2 whatever the input looks like", () => {
    expect(groupCode("9617001000")).toBe("9617.00.10.00");
    expect(groupCode("9617.00.1000")).toBe("9617.00.10.00"); // CBP's own grouping
    expect(groupCode("9617.00.10")).toBe("9617.00.10");
    expect(groupCode("96")).toBe("96");
    expect(digitsOf(" 7323.93.00.80 ")).toBe("7323930080");
  });

  it("flags only the four heading digits for the highlighter", () => {
    expect(codeSegments("9617.00.10.00")).toEqual([
      { text: "9617", heading: true },
      { text: "00", heading: false },
      { text: "10", heading: false },
      { text: "00", heading: false },
    ]);
  });

  it("knows a full code has exactly ten digits", () => {
    expect(isFullCode("9617.00.10.00")).toBe(true);
    expect(isFullCode("9617.00.10")).toBe(false);
  });

  it("redlines digit by digit and ignores cells not yet typed", () => {
    const cells = redline("9617.00.10.00", ["7", "3", "2", "3", "", "", "", "", "", ""]);
    expect(cells.filter((c) => c.changed).map((c) => c.index)).toEqual([0, 1, 2, 3]);
    expect(cells[4]).toEqual({ index: 4, proposed: "0", yours: "", changed: false });
    const full = redline("9617001000", "7323930080");
    expect(full.filter((c) => c.changed).map((c) => c.index)).toEqual([0, 1, 2, 3, 4, 5, 6, 8]);
  });
});

describe("money", () => {
  it("formats decimal strings without float drift", () => {
    expect(money({ amount: "3458.93", currency: "USD" })).toBe("$3,458.93");
    expect(money({ amount: "1275.00", currency: "CAD" })).toBe("CA$1,275.00");
    expect(money({ amount: "7440.00", currency: "USD" }, { cents: false })).toBe("$7,440");
    expect(money(null)).toBe("–");
  });

  it("adds and subtracts exactly, in cents", () => {
    const parts = ["900.00", "1250.00", "1250.00", "43.30", "15.63"].map((amount) => ({ amount, currency: "USD" as const }));
    expect(addMoney(...parts)).toEqual({ amount: "3458.93", currency: "USD" });
    expect(subtractMoney({ amount: "3458.93", currency: "USD" }, { amount: "2500.00", currency: "USD" }).amount).toBe("958.93");
    expect(addMoney({ amount: "0.10", currency: "USD" }, { amount: "0.20", currency: "USD" }).amount).toBe("0.30");
    expect(subtractMoney({ amount: "1.00", currency: "USD" }, { amount: "2.50", currency: "USD" }).amount).toBe("-1.50");
  });
});

describe("dates in the organisation's zone", () => {
  it("never moves a calendar date across the date line", () => {
    expect(dateShort("2026-02-19")).toBe("19 Feb 2026");
    expect(dateShort("2025-11-05")).toBe("5 Nov 2025");
  });

  it("shows timestamps in Vancouver time", () => {
    expect(dateTime("2026-02-17T18:12:00Z")).toBe("17 Feb 2026, 10:12");
  });

  it("says today, yesterday or the date relative to the demo clock, not the browser", () => {
    expect(whenLabel("2026-02-19T18:21:00Z", AT)).toBe("Today, 10:21");
    expect(whenLabel("2026-02-18T20:02:00Z", AT)).toBe("Yesterday");
    expect(whenLabel("2026-02-12T20:00:00Z", AT)).toBe("12 Feb");
    expect(whenLabel("2025-12-08T20:00:00Z", AT)).toBe("8 Dec 2025");
  });

  it("counts how long an item has waited", () => {
    expect(waitingFor("2026-02-16T17:00:00Z", AT)).toBe("3 days");
    expect(waitingFor("2026-02-18T17:00:00Z", AT)).toBe("1 day");
    expect(waitingFor("2026-02-19T17:00:00Z", AT)).toBe("today");
  });
});

describe("marked text", () => {
  it("splits plain text by character offsets and never produces HTML", () => {
    const text = "with a vacuum between the walls and a lid";
    const pieces = markSpans(text, [{ start: 7, end: 31 }]);
    expect(pieces).toEqual([
      { text: "with a ", marked: false },
      { text: "vacuum between the walls", marked: true },
      { text: " and a lid", marked: false },
    ]);
    expect(markSpans("<b>x</b>", [])).toEqual([{ text: "<b>x</b>", marked: false }]);
  });

  it("clamps spans that run past the text and skips overlaps", () => {
    expect(markSpans("abcdef", [{ start: 4, end: 99 }, { start: 5, end: 6 }])).toEqual([
      { text: "abcd", marked: false },
      { text: "ef", marked: true },
    ]);
  });

  it("makes initials and number words", () => {
    expect(initials("Maya Lindqvist")).toBe("ML");
    expect(countWord(5)).toBe("five");
    expect(countWord(12)).toBe("12");
  });
});
