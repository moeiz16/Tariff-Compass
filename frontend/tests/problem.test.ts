import { describe, expect, it } from "vitest";
import { ApiProblem } from "~/lib/api";
import { plainMessage, plainProblem } from "~/lib/problem";

describe("RFC 7807 problems in plain words", () => {
  it("keeps the API's own sentence and the field errors", () => {
    const err = new ApiProblem({
      type: "x",
      title: "Some fields need attention",
      status: 422,
      code: "validation_error",
      detail: "One or more fields are invalid.",
      errors: [{ field: "reason", message: "Give a reason for the change." }],
      requestId: "r-1",
    });
    const p = plainProblem(err);
    expect(p.message).toBe("One or more fields are invalid.");
    expect(p.fields).toEqual({ reason: "Give a reason for the change." });
    expect(p.requestId).toBe("r-1");
  });

  it("falls back to a sentence per code when the detail is empty", () => {
    const p = plainProblem(new ApiProblem({ type: "x", title: "t", status: 409, code: "already_decided", detail: "" }));
    expect(p.message).toMatch(/Someone else decided/);
    expect(plainMessage("unavailable")).toMatch(/Nothing was sent/);
  });

  it("treats anything else as the network being unreachable", () => {
    expect(plainProblem(new TypeError("Failed to fetch")).code).toBe("network");
  });

  it("never shows technical words", () => {
    const codes = ["bad_request", "forbidden", "csrf_failed", "rate_limited", "internal_error", "unavailable", "unknown_code", "gates_failed"];
    for (const c of codes) expect(plainMessage(c)).not.toMatch(/\b(LLM|model|cache|latency|fallback|pipeline|token|SQL)\b/i);
  });
});
