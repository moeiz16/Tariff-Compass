/**
 * Same-origin JSON client for /api/v1 (docs/API_CONTRACT.md §1.1): sends the CSRF cookie back as
 * X-CSRFToken on unsafe methods, syncs the demo clock from every response, and turns RFC 7807 problem
 * documents into `ApiProblem` errors with a stable `code`.
 *
 * With VITE_TC_MOCK=1 the same requests are answered in the browser by fixtures that follow the contract
 * (src/lib/mock), so screens can be built and checked without the API running.
 */
import { syncFromResponse } from "./clock";

export const API_BASE = "/api/v1";
const CSRF_COOKIE = "tc_csrf";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);
export const MOCK = import.meta.env?.VITE_TC_MOCK === "1";

export interface Problem {
  type: string;
  title: string;
  status: number;
  code: string;
  detail: string;
  errors?: { field: string; message: string }[];
  requestId?: string;
  retryAfterSeconds?: number;
  triesLeft?: number;
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

type Unauthorized = (code: string) => void;
let onUnauthorized: Unauthorized | null = null;
/** The session layer registers a handler that sends the person to /signin and back afterwards. */
export function setUnauthorizedHandler(fn: Unauthorized | null): void {
  onUnauthorized = fn;
}

export function readCookie(name: string, cookie: string = typeof document === "undefined" ? "" : document.cookie) {
  const hit = cookie
    .split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${name}=`));
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : undefined;
}

async function transport(url: string, init: RequestInit): Promise<Response> {
  if (MOCK) {
    const { mockFetch } = await import("./mock/server");
    return mockFetch(url, init);
  }
  return fetch(url, init);
}

/** Make sure the CSRF cookie exists before an unsafe request (sign-in included). */
export async function ensureCsrf(): Promise<void> {
  if (!readCookie(CSRF_COOKIE) && !MOCK) await transport(`${API_BASE}/auth/csrf`, { credentials: "same-origin" });
}

export async function raw(path: string, init: RequestInit = {}, base: string = API_BASE): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (UNSAFE.has(method)) {
    await ensureCsrf();
    const token = readCookie(CSRF_COOKIE);
    if (token) headers.set("X-CSRFToken", token);
  }
  const res = await transport(`${base}${path}`, { ...init, method, headers, credentials: "same-origin" });
  syncFromResponse(res);
  if (!res.ok) {
    const type = res.headers.get("Content-Type") ?? "";
    const problem: Problem = type.includes("problem+json")
      ? ((await res.json()) as Problem)
      : { type: "about:blank", title: res.statusText, status: res.status, code: res.status === 503 ? "unavailable" : "internal_error", detail: "" };
    if (res.status === 401 && !path.startsWith("/auth/") && onUnauthorized) onUnauthorized(problem.code);
    throw new ApiProblem(problem);
  }
  return res;
}

export async function api<T>(path: string, init: RequestInit = {}, base: string = API_BASE): Promise<T> {
  const res = await raw(path, init, base);
  if (res.status === 204 || res.status === 202 && res.headers.get("Content-Length") === "0") return undefined as T;
  return (await res.json()) as T;
}

export const get = <T>(path: string) => api<T>(path);
export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T = void>(path: string) => api<T>(path, { method: "DELETE" });

/** Query string from an object, skipping empty values. */
export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") u.set(k, String(v));
  const s = u.toString();
  return s ? `?${s}` : "";
}

/** Fetch a file (binder PDF/ZIP, activity CSV) and hand it to the browser as a download. */
export async function download(path: string, fileName: string, base: string = API_BASE): Promise<void> {
  const res = await raw(path, {}, base);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
