import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiProblem, readCookie } from "~/lib/api";
import { now, reset } from "~/lib/clock";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    reset();
  });

  it("reads the CSRF cookie", () => {
    expect(readCookie("tc_csrf", "a=1; tc_csrf=abc%3D; b=2")).toBe("abc=");
  });

  it("turns problem documents into ApiProblem and syncs the clock", async () => {
    const body = { type: "x", title: "Not found", status: 404, code: "not_found", detail: "Nope" };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(body), {
          status: 404,
          headers: { "Content-Type": "application/problem+json", "X-Tariff-Compass-Now": "2026-02-19T18:30:00Z" },
        }),
      ),
    );
    const err = await api("/rulings/none").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiProblem);
    expect((err as ApiProblem).code).toBe("not_found");
    expect(now().toISOString().slice(0, 10)).toBe("2026-02-19");
  });
});
