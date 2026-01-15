/**
 * The demo clock on the client. The API stamps every response with `X-Tariff-Compass-Now`
 * (TARIFF_COMPASS_DEMO_TODAY, default 2026-02-19); we keep the offset from the browser clock and use it for
 * every "today", "3 days ago" and date line. The browser clock is never trusted for business time.
 */

export const NOW_HEADER = "X-Tariff-Compass-Now";
export const DEFAULT_ZONE = "America/Vancouver";

let offsetMs = 0;
let synced = false;

export function syncFromHeader(value: string | null | undefined, browserNow: number = Date.now()): boolean {
  if (!value) return false;
  const server = Date.parse(value);
  if (Number.isNaN(server)) return false;
  offsetMs = server - browserNow;
  synced = true;
  return true;
}

export function syncFromResponse(res: Response): boolean {
  return syncFromHeader(res.headers.get(NOW_HEADER));
}

export function now(browserNow: number = Date.now()): Date {
  return new Date(browserNow + offsetMs);
}

export function isSynced(): boolean {
  return synced;
}

export function reset(): void {
  offsetMs = 0;
  synced = false;
}

/** "Thursday 19 February 2026" in the organisation's zone. */
export function dateLine(d: Date = now(), timeZone: string = DEFAULT_ZONE): string {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone,
  }).format(d);
}

/** ISO date (YYYY-MM-DD) of "today" in the zone. */
export function today(d: Date = now(), timeZone: string = DEFAULT_ZONE): string {
  const parts = new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit", timeZone })
    .formatToParts(d)
    .reduce<Record<string, string>>((acc, p) => ({ ...acc, [p.type]: p.value }), {});
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/** Whole days between an ISO timestamp and the demo "now" ("waiting 3 days"). */
export function daysSince(iso: string, at: Date = now()): number {
  return Math.max(0, Math.floor((at.getTime() - Date.parse(iso)) / 86_400_000));
}
