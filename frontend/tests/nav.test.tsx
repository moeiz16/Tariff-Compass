// @vitest-environment jsdom
import { cleanup, render, screen } from "@solidjs/testing-library";
import { createResource, untrack } from "solid-js";
import { inRouter } from "./router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";
import { Nav } from "~/components/shell/TopBar";
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
      <Nav active="classify" />
    </SessionContext.Provider>
  );
}

describe("the top bar follows the role", () => {
  it("hides the Lab from importers", async () => {
    render(inRouter(() => <As role="importer" />));
    const names = (await screen.findAllByRole("link")).map((t) => t.textContent?.replace(/\d+/g, "").trim());
    expect(names).toEqual(["Classify", "Review", "Products", "Library", "Watch"]);
  });

  it("shows the Lab to a broker, marks the current place and counts what waits for review", async () => {
    render(inRouter(() => <As role="broker" />));
    expect(await screen.findByRole("link", { name: /Lab/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Classify/ }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByText("15")).toBeTruthy();
  });
});
