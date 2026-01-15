import { afterEach, describe, expect, it } from "vitest";
import { dateLine, daysSince, now, reset, syncFromHeader, today } from "~/lib/clock";

describe("demo clock", () => {
  afterEach(() => reset());

  it("follows the server's X-Tariff-Compass-Now, not the browser clock", () => {
    const browser = Date.parse("2026-01-03T00:00:00Z");
    expect(syncFromHeader("2026-02-19T18:30:00+00:00", browser)).toBe(true);
    expect(now(browser).toISOString()).toBe("2026-02-19T18:30:00.000Z");
    expect(now(browser + 60_000).toISOString()).toBe("2026-02-19T18:31:00.000Z");
  });

  it("formats the date line and today in Vancouver", () => {
    const d = new Date("2026-02-19T18:30:00Z");
    expect(dateLine(d)).toBe("Thursday 19 February 2026");
    expect(today(new Date("2026-02-20T05:00:00Z"))).toBe("2026-02-19");
  });

  it("counts whole days waiting", () => {
    expect(daysSince("2026-02-16T17:00:00Z", new Date("2026-02-19T18:30:00Z"))).toBe(3);
  });

  it("ignores a missing or broken header", () => {
    expect(syncFromHeader(null)).toBe(false);
    expect(syncFromHeader("not a date")).toBe(false);
  });
});
