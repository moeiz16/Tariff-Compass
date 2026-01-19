/**
 * RFC 7807 problems in plain words. The API's `detail` is already written for people; when it is missing we fall
 * back to a sentence per `code`. Field errors are kept so forms can show them beside the field.
 */
import { ApiProblem } from "./api";

const PLAIN: Record<string, string> = {
  bad_request: "Something in that request wasn't readable. Please try again.",
  not_authenticated: "Please sign in to continue.",
  session_expired: "Your session ended. Sign in again and you'll come back here.",
  invalid_credentials: "That email and password didn't match.",
  forbidden: "Your role doesn't include this. Ask an administrator if you need it.",
  csrf_failed: "This page was open too long to send that safely. Reload and try again.",
  no_active_org: "Choose an organisation to work in first.",
  not_found: "We couldn't find that. It may have been removed, or it belongs to another organisation.",
  not_in_demo: "The public demo only knows Northbound's sample products.",
  already_decided: "Someone else decided this item a moment ago. Here is the current state.",
  stale_version: "This changed while you were looking at it. Reload to see the latest version.",
  needs_second_signature: "A round goes live only with a second signature from someone else.",
  same_person: "You've already signed this round. The second signature has to come from someone else.",
  gates_failed: "One of the five checks didn't pass, so this round can't go live yet.",
  expired: "This invitation has expired. Ask for a new one.",
  payload_too_large: "That file is too large. Files can be up to 10 MB.",
  unsupported_media_type: "We accept PDF spec sheets and JPEG, PNG or WebP photos.",
  validation_error: "Some fields need attention.",
  weak_password: "Choose a longer password that isn't common or close to your email.",
  unknown_code: "That code isn't a line of the tariff in force.",
  sign_in_paused: "Too many tries. Sign-in for this email is paused for 15 minutes.",
  rate_limited: "That was a lot of requests in a minute. Please wait a moment and try again.",
  internal_error: "Something went wrong on our side. It has been logged; please try again.",
  unavailable: "We couldn't reach the tariff service just now. Nothing was sent and nothing was filed.",
  conflict: "Something else is already running. Try again when it finishes.",
  last_admin: "Every organisation needs at least one administrator.",
  network: "We couldn't reach Tariff Compass. Check your connection and try again.",
};

export interface PlainProblem {
  code: string;
  title: string;
  message: string;
  fields: Record<string, string>;
  status: number;
  requestId?: string;
}

export function plainProblem(err: unknown): PlainProblem {
  if (err instanceof ApiProblem) {
    const p = err.problem;
    const fields: Record<string, string> = {};
    for (const e of p.errors ?? []) fields[e.field] = e.message;
    return {
      code: p.code,
      title: p.title,
      message: p.detail || PLAIN[p.code] || PLAIN.internal_error!,
      fields,
      status: p.status,
      requestId: p.requestId,
    };
  }
  return { code: "network", title: "Not reachable", message: PLAIN.network!, fields: {}, status: 0 };
}

export function plainMessage(code: string): string {
  return PLAIN[code] ?? PLAIN.internal_error!;
}
