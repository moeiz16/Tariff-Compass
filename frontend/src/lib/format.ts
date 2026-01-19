/**
 * Formatting for everything a customs form would carry: tariff codes in the official grouping, money as decimal
 * strings, dates in the organisation's zone (America/Vancouver for the sample) and marked text spans.
 */
import type { Money, Span } from "./types";
import { DEFAULT_ZONE, now } from "./clock";

/* ---------------- tariff codes ---------------- */

/** Bare digits of a code typed with or without dots ("9617.00.10.00" → "9617001000"). */
export function digitsOf(code: string): string {
  return code.replace(/\D/g, "");
}

/** Group digits the way the HTSUS and Canada's Customs Tariff print them: 4.2.2.2 ("9617.00.10.00"). */
export function groupCode(code: string): string {
  const d = digitsOf(code);
  const parts = [d.slice(0, 4), d.slice(4, 6), d.slice(6, 8), d.slice(8, 10)].filter(Boolean);
  return parts.join(".");
}

export interface CodeSegment {
  text: string;
  heading: boolean;
}

/** Split a code into its groups, flagging the four heading digits that are drawn on the highlighter. */
export function codeSegments(code: string): CodeSegment[] {
  const grouped = groupCode(code);
  return grouped.split(".").map((text, i) => ({ text, heading: i === 0 }));
}

/** A ten-digit code is complete when it has exactly ten digits. */
export function isFullCode(code: string): boolean {
  return digitsOf(code).length === 10;
}

export interface RedlineDigit {
  index: number;
  proposed: string;
  yours: string;
  changed: boolean;
}

/** Digit-by-digit comparison of two ten-digit codes; blanks in `yours` count as unchanged until typed. */
export function redline(proposed: string, yours: string[] | string): RedlineDigit[] {
  const p = digitsOf(proposed).padEnd(10, " ").slice(0, 10);
  const y = Array.isArray(yours) ? yours : digitsOf(yours).padEnd(10, " ").split("");
  return Array.from({ length: 10 }, (_, index) => {
    const a = p[index] ?? " ";
    const b = (y[index] ?? "").trim();
    return { index, proposed: a.trim(), yours: b, changed: b !== "" && b !== a };
  });
}

/* ---------------- money ---------------- */

const moneyFormatters = new Map<string, Intl.NumberFormat>();
function moneyFormatter(currency: string, cents: boolean): Intl.NumberFormat {
  const key = `${currency}:${cents}`;
  let f = moneyFormatters.get(key);
  if (!f) {
    f = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: cents ? 2 : 0,
      maximumFractionDigits: cents ? 2 : 0,
    });
    moneyFormatters.set(key, f);
  }
  return f;
}

/** "$3,458.93" (USD) or "CA$1,012.50" (CAD). Amounts arrive as decimal strings and are never added as floats. */
export function money(m: Money | null | undefined, opts: { cents?: boolean } = {}): string {
  if (!m) return "–";
  const n = Number(m.amount);
  if (!Number.isFinite(n)) return "–";
  return moneyFormatter(m.currency, opts.cents ?? true).format(n);
}

/** Adds decimal strings exactly, in cents. */
export function addMoney(...items: Money[]): Money {
  const currency = items[0]?.currency ?? "USD";
  const cents = items.reduce((acc, m) => acc + toCents(m.amount), 0n);
  return { amount: fromCents(cents), currency };
}

export function subtractMoney(a: Money, b: Money): Money {
  return { amount: fromCents(toCents(a.amount) - toCents(b.amount)), currency: a.currency };
}

function toCents(amount: string): bigint {
  const neg = amount.trim().startsWith("-");
  const [whole = "0", frac = ""] = amount.replace("-", "").trim().split(".");
  const v = BigInt(whole || "0") * 100n + BigInt((frac + "00").slice(0, 2));
  return neg ? -v : v;
}
function fromCents(c: bigint): string {
  const neg = c < 0n;
  const abs = neg ? -c : c;
  const s = `${abs / 100n}.${(abs % 100n).toString().padStart(2, "0")}`;
  return neg ? `-${s}` : s;
}

/* ---------------- dates ---------------- */

const dtf = (opts: Intl.DateTimeFormatOptions, zone = DEFAULT_ZONE) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: zone, ...opts });

function asDate(v: string | Date): Date {
  if (v instanceof Date) return v;
  // A calendar date ("2026-02-19") is a date, not midnight UTC: anchor it at noon so no zone moves it a day.
  return /^\d{4}-\d{2}-\d{2}$/.test(v) ? new Date(`${v}T12:00:00Z`) : new Date(v);
}

/** "19 Feb 2026" */
export function dateShort(v: string | Date | null | undefined, zone = DEFAULT_ZONE): string {
  if (!v) return "–";
  return dtf({ day: "numeric", month: "short", year: "numeric" }, zone).format(asDate(v));
}

/** "Thu 19 Feb 2026" */
export function dateWithDay(v: string | Date, zone = DEFAULT_ZONE): string {
  return dtf({ weekday: "short", day: "numeric", month: "short", year: "numeric" }, zone).format(asDate(v)).replace(",", "");
}

/** "17 Feb" */
export function dayMonth(v: string | Date, zone = DEFAULT_ZONE): string {
  return dtf({ day: "numeric", month: "short" }, zone).format(asDate(v));
}

/** "10:21" (24-hour, the organisation's zone) */
export function timeOfDay(v: string | Date, zone = DEFAULT_ZONE): string {
  return dtf({ hour: "2-digit", minute: "2-digit", hour12: false }, zone).format(asDate(v));
}

/** "17 Feb 2026, 10:12" */
export function dateTime(v: string | Date | null | undefined, zone = DEFAULT_ZONE): string {
  if (!v) return "–";
  return `${dateShort(v, zone)}, ${timeOfDay(v, zone)}`;
}

function zoneDay(v: Date, zone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit" }).format(v);
}

/** "Today, 10:21", "Yesterday", "17 Feb" or "17 Feb 2025": relative to the demo clock, never the browser's. */
export function whenLabel(v: string | Date, at: Date = now(), zone = DEFAULT_ZONE): string {
  const d = asDate(v);
  const today = zoneDay(at, zone);
  const day = zoneDay(d, zone);
  if (day === today) return `Today, ${timeOfDay(d, zone)}`;
  const yesterday = zoneDay(new Date(at.getTime() - 86_400_000), zone);
  if (day === yesterday) return "Yesterday";
  return day.slice(0, 4) === today.slice(0, 4) ? dayMonth(d, zone) : dateShort(d, zone);
}

/** "3 days", "1 day", "today" */
export function waitingFor(iso: string, at: Date = now()): string {
  const days = Math.max(0, Math.floor((at.getTime() - Date.parse(iso)) / 86_400_000));
  if (days === 0) return "today";
  return days === 1 ? "1 day" : `${days} days`;
}

/* ---------------- text ---------------- */

export interface TextPiece {
  text: string;
  marked: boolean;
}

/** Split plain text into marked and unmarked pieces by character offsets (untrusted text never becomes HTML). */
export function markSpans(text: string, spans: Span[] = []): TextPiece[] {
  const clean = [...spans]
    .map((s) => ({ start: Math.max(0, Math.min(text.length, s.start)), end: Math.max(0, Math.min(text.length, s.end)) }))
    .filter((s) => s.end > s.start)
    .sort((a, b) => a.start - b.start);
  const out: TextPiece[] = [];
  let at = 0;
  for (const s of clean) {
    if (s.start < at) continue;
    if (s.start > at) out.push({ text: text.slice(at, s.start), marked: false });
    out.push({ text: text.slice(s.start, s.end), marked: true });
    at = s.end;
  }
  if (at < text.length) out.push({ text: text.slice(at), marked: false });
  return out.length ? out : [{ text, marked: false }];
}

/** Initials for the avatar ("Maya Lindqvist" → "ML"). */
export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

/** "5 of 6" style counting words for small numbers in prose. */
const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
export function countWord(n: number): string {
  return WORDS[n] ?? String(n);
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n.toLocaleString("en-US")} ${n === 1 ? one : many}`;
}
