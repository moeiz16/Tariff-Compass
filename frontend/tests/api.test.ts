import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiProblem, qs, readCookie, setUnauthorizedHandler } from "~/lib/api";
import { now, reset } from "~/lib/clock";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setUnauthorizedHandler(null);
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

  it("echoes the CSRF cookie on unsafe methods only", async () => {
    vi.stubGlobal("document", { cookie: "tc_csrf=tok123" });
    const calls: { url: string; headers: Headers; method?: string }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init: RequestInit) => {
        calls.push({ url, headers: new Headers(init.headers), method: init.method });
        return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
      }),
    );
    await api("/home");
    await api("/review/rv-01/approve", { method: "POST", body: "{}" });
    expect(calls[0]!.headers.get("X-CSRFToken")).toBeNull();
    expect(calls[1]!.headers.get("X-CSRFToken")).toBe("tok123");
    expect(calls[1]!.headers.get("Content-Type")).toBe("application/json");
  });

  it("sends the person to sign in when the session ends, but not for sign-in itself", async () => {
    const seen: string[] = [];
    setUnauthorizedHandler((c) => seen.push(c));
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ type: "x", title: "t", status: 401, code: "session_expired", detail: "" }), { status: 401, headers: { "Content-Type": "application/problem+json" } })),
    );
    await api("/home").catch(() => undefined);
    await api("/auth/session").catch(() => undefined);
    expect(seen).toEqual(["session_expired"]);
  });

  it("builds query strings without empty values", () => {
    expect(qs({ q: "tumbler", page: 2, status: "", x: undefined })).toBe("?q=tumbler&page=2");
    expect(qs({})).toBe("");
  });
});
