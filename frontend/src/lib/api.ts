/**
 * Same-origin JSON client for /api/v1 (docs/API_CONTRACT.md §1.1): sends the CSRF cookie back as
 * X-CSRFToken on unsafe methods, syncs the demo clock from every response, and turns RFC 7807 problem
 * documents into `ApiProblem` errors with a stable `code`.
 */
import { syncFromResponse } from "./clock";

export const API_BASE = "/api/v1";
const CSRF_COOKIE = "tc_csrf";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export interface Problem {
  type: string;
  title: string;
  status: number;
  code: string;
  detail: string;
  errors?: { field: string; message: string }[];
  requestId?: string;
}

export class ApiProblem extends Error {
  constructor(public readonly problem: Problem) {
    super(problem.detail || problem.title);
  }
  get code(): string {
    return this.problem.code;
  }
  get status(): number {
    return this.problem.status;
  }
}

export function readCookie(name: string, cookie: string = typeof document === "undefined" ? "" : document.cookie) {
  const hit = cookie.split(";").map((c) => c.trim()).find((c) => c.startsWith(`${name}=`));
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : undefined;
}

export async function api<T>(path: string, init: RequestInit = {}, base: string = API_BASE): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (UNSAFE.has(method)) {
    const token = readCookie(CSRF_COOKIE);
    if (token) headers.set("X-CSRFToken", token);
  }
  const res = await fetch(`${base}${path}`, { ...init, method, headers, credentials: "same-origin" });
  syncFromResponse(res);
  if (res.status === 204) return undefined as T;
  const type = res.headers.get("Content-Type") ?? "";
  if (!res.ok) {
    if (type.includes("problem+json")) throw new ApiProblem((await res.json()) as Problem);
    throw new ApiProblem({ type: "about:blank", title: res.statusText, status: res.status, code: "internal_error", detail: "" });
  }
  return (await res.json()) as T;
}
