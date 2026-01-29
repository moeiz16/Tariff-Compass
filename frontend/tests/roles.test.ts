import { describe, expect, it } from "vitest";
import { ROLE_PERMISSIONS } from "~/lib/mock/core";
import { SCOPE_PERMISSION, allows } from "~/lib/roles";

const scopesFor = (role: keyof typeof ROLE_PERMISSIONS) => Object.entries(SCOPE_PERMISSION).filter(([, p]) => allows(ROLE_PERMISSIONS[role], p)).map(([s]) => s);

describe("role gating (mirrors platform/roles.py)", () => {
  it("shows each role the scopes its job needs", () => {
    expect(scopesFor("importer")).toEqual(["answer", "rulings", "tariff", "products", "review", "watch"]);
    expect(scopesFor("broker")).toEqual(["answer", "rulings", "tariff", "products", "review", "watch", "lab"]);
    expect(scopesFor("compliance")).toContain("lab");
    expect(scopesFor("admin")).toContain("lab");
  });

  it("keeps decisions with brokers and sign-off with brokers and compliance", () => {
    expect(allows(ROLE_PERMISSIONS.broker, "review:decide")).toBe(true);
    for (const r of ["importer", "compliance", "admin"] as const) expect(allows(ROLE_PERMISSIONS[r], "review:decide")).toBe(false);
    expect(allows(ROLE_PERMISSIONS.compliance, "lab:sign")).toBe(true);
    expect(allows(ROLE_PERMISSIONS.importer, "lab:sign")).toBe(false);
  });

  it("lets only admins manage people, and keeps admins from classifying", () => {
    expect(allows(ROLE_PERMISSIONS.admin, "members:manage")).toBe(true);
    expect(allows(ROLE_PERMISSIONS.compliance, "members:manage")).toBe(false);
    expect(allows(ROLE_PERMISSIONS.admin, "classify:run")).toBe(false);
    expect(allows(undefined, "classify:read")).toBe(false);
  });
});
