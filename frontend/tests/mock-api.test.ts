import { beforeEach, describe, expect, it, vi } from "vitest";

// The mock API keeps its state in sessionStorage; give each test a fresh one.
beforeEach(() => {
  const store = new Map<string, string>();
  vi.stubGlobal("sessionStorage", { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v), removeItem: (k: string) => void store.delete(k) });
  vi.stubGlobal("location", { origin: "http://127.0.0.1:3050" });
  vi.resetModules();
});

async function server() {
  return (await import("~/lib/mock/server")).mockFetch;
}
const json = (body: unknown, method = "POST") => ({ method, body: JSON.stringify(body) });

describe("the in-browser API follows the contract", () => {
  it("stamps the demo clock on every response, problems included", async () => {
    const f = await server();
    const ok = await f("/api/v1/auth/session");
    expect(ok.headers.get("X-Tariff-Compass-Now")).toMatch(/^2026-02-19T18:3/);
    const bad = await f("/api/v1/review");
    expect(bad.status).toBe(401);
    expect(bad.headers.get("Content-Type")).toBe("application/problem+json");
    expect(bad.headers.get("X-Tariff-Compass-Now")).toMatch(/^2026-02-19/);
  });

  it("refuses what a role can't do", async () => {
    const f = await server();
    await f("/api/v1/auth/demo", json({ role: "importer" }));
    const r = await f("/api/v1/review/rv-01/approve", json({ note: "" }));
    expect(r.status).toBe(403);
    expect((await r.json()).code).toBe("forbidden");
  });

  it("lets a broker correct with a reason, and reports a second decision as a conflict", async () => {
    const f = await server();
    await f("/api/v1/auth/demo", json({ role: "broker" }));
    const short = await f("/api/v1/review/rv-01/correct", json({ usCode: "7323.93.00.80", reasonKind: "facts_differ", reason: "short" }));
    expect(short.status).toBe(422);
    const ok = await f("/api/v1/review/rv-01/correct", json({ usCode: "7323.93.00.80", reasonKind: "facts_differ", reason: "Spec sheet says air-insulated, not vacuum-sealed." }));
    expect(ok.status).toBe(200);
    expect((await ok.json()).toast).toMatch(/Corrected · NB-KT-0388 → 7323.93.00.80/);
    const again = await f("/api/v1/review/rv-01/approve", json({ note: "" }));
    expect(again.status).toBe(409);
  });

  it("answers only the sample products on the public front page", async () => {
    const f = await server();
    expect((await f("/api/v1/public/classify", json({ text: "stainless insulated tumbler" }))).status).toBe(200);
    const miss = await f("/api/v1/public/classify", json({ text: "a wooden chair" }));
    expect(miss.status).toBe(404);
    expect((await miss.json()).code).toBe("not_in_demo");
  });

  it("only cites real rulings for the tumbler", async () => {
    const f = await server();
    const a = await (await f("/api/v1/public/samples/tumbler")).json();
    expect(a.rulings.map((r: { id: string }) => r.id)).toEqual(["NY N321134", "HQ H303684", "NY N297165"]);
    expect(JSON.stringify(a)).not.toMatch(/N338211|H337010|D10-14-1/);
  });

  it("needs the signer's own name and a second person to make a round live", async () => {
    const f = await server();
    await f("/api/v1/auth/demo", json({ role: "compliance" }));
    expect((await f("/api/v1/lab/rounds/7/sign", json({ statement: "Maya Lindqvist" }))).status).toBe(409);
    await f("/api/v1/auth/demo", json({ role: "broker" }));
    expect((await f("/api/v1/lab/rounds/7/sign", json({ statement: "Someone Else" }))).status).toBe(422);
    const r = await (await f("/api/v1/lab/rounds/7/sign", json({ statement: "Dana Whitlock" }))).json();
    expect(r.status).toBe("live");
  });
});
