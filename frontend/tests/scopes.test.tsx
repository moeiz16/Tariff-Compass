// @vitest-environment jsdom
import { cleanup, render, screen } from "@solidjs/testing-library";
import { createResource, untrack } from "solid-js";
import { inRouter } from "./router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Scopes } from "~/components/shell/QueryStrip";
import { meFor } from "~/lib/mock/core";
import { SessionContext, type SessionCtx } from "~/lib/session";
import type { Role } from "~/lib/types";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify({ rulings: 214, products: 118, review: 15, watch: 4 }), { status: 200, headers: { "Content-Type": "application/json" } })),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function As(props: { role: Role }) {
  const me = meFor(untrack(() => props.role));
  const [session] = createResource(async () => ({ me, clock: { now: "", today: "", timezone: "", demo: true }, demoSignIn: true, demoPeople: [] }));
  const ctx: SessionCtx = {
    session,
    me: () => me,
    role: () => props.role,
    can: (p) => me.membership!.permissions.includes(p),
    reload: async () => undefined,
    signOut: async () => undefined,
  };
  return (
    <SessionContext.Provider value={ctx}>
      <Scopes active="answer" />
    </SessionContext.Provider>
  );
}

describe("scopes follow the role", () => {
  it("hides the Lab from importers and never asks for it", async () => {
    render(inRouter(() => <As role="importer" />));
    const names = (await screen.findAllByRole("tab")).map((t) => t.textContent?.replace(/\d+/g, "").trim());
    expect(names).toEqual(["Answer", "Rulings", "Tariff text", "My products", "Review", "Watch"]);
  });

  it("shows the Lab to a broker, and marks the current scope", async () => {
    render(inRouter(() => <As role="broker" />));
    expect(await screen.findByRole("tab", { name: /Lab/ })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /Answer/ }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByText("15")).toBeTruthy();
  });
});
