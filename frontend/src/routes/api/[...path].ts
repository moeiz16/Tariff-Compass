import type { APIEvent } from "@solidjs/start/server";

/**
 * Same-origin proxy: /api/** on :3050 → the API on :8050 (API_ORIGIN). Streams bodies both ways, so SSE
 * job events and file downloads pass through unbuffered; cookies and the CSRF header travel unchanged.
 */
const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8050";
const HOP = ["connection", "keep-alive", "transfer-encoding", "upgrade", "host", "content-length"];

async function forward({ request }: APIEvent): Promise<Response> {
  const url = new URL(request.url);
  const target = `${API_ORIGIN}${url.pathname}${url.search}`;
  const headers = new Headers(request.headers);
  for (const h of HOP) headers.delete(h);
  headers.set("X-Forwarded-Host", url.host);
  const hasBody = !["GET", "HEAD"].includes(request.method);
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      redirect: "manual",
      // @ts-expect-error Node's fetch needs duplex for streamed request bodies
      duplex: hasBody ? "half" : undefined,
    });
    const out = new Headers(upstream.headers);
    for (const h of HOP) out.delete(h);
    out.delete("content-encoding");
    return new Response(upstream.body, { status: upstream.status, headers: out });
  } catch {
    const problem = {
      type: "https://tariffcompass.dev/problems/unavailable",
      title: "A service we depend on is unavailable",
      status: 503,
      code: "unavailable",
      detail: "We couldn't reach the tariff service just now.",
    };
    return new Response(JSON.stringify(problem), {
      status: 503,
      headers: { "Content-Type": "application/problem+json", "Retry-After": "5" },
    });
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
