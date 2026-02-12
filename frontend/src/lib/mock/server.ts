/**
 * In-browser stand-in for /api/v1 (VITE_TC_MOCK=1). It answers the same paths with the same shapes as
 * docs/API_CONTRACT.md, keeps a little state (who is signed in, decisions, signatures, export jobs) in
 * sessionStorage, enforces the role permissions, stamps X-Tariff-Compass-Now and returns RFC 7807 problems.
 */
import type { AnswerOut, ClassifyIn, LandedCostIn, ReviewRow, Role } from "../types";
import { SAMPLES, bikelightAnswer, bottleAnswer, tumblerAnswer, tumblerLandedCA, tumblerLandedMexico, tumblerLandedUS, tumblerLandedVietnam } from "./answers";
import { DEMO_NOW, DEMO_PEOPLE, MEMBERS, META, ROLES, ROLE_LABELS, ROLE_PERMISSIONS, meFor } from "./core";
import { SECTIONS } from "./sections";
import { AUDIT, HOME, LAB, PRODUCTS, REVIEW_ROWS, RULES, RULINGS, SETTINGS, TARIFF_LINES, WATCH, binderFor, decisionRecord, docket, productDetail, round } from "./work";

const loadedAt = Date.now();
const nowIso = () => new Date(Date.parse(DEMO_NOW) + (Date.now() - loadedAt)).toISOString();

interface State {
  role: Role | null;
  decided: Record<string, { status: string; statusLabel: string }>;
  signatures: { name: string; role: string; at: string }[];
  jobs: Record<string, { started: number; kind: string; sku: string; format: string }>;
  invitations: { id: string; email: string; role: Role }[];
}

function load(): State {
  try {
    const s = sessionStorage.getItem("tc-mock");
    if (s) return JSON.parse(s) as State;
  } catch {
    /* fall through */
  }
  return {
    role: null,
    decided: {},
    signatures: [{ name: "Maya Lindqvist", role: "compliance", at: "2026-02-19T17:48:00Z" }],
    jobs: {},
    invitations: [{ id: "inv-1", email: "ops@northbound.example", role: "importer" }],
  };
}
const state = load();
const save = () => {
  try {
    sessionStorage.setItem("tc-mock", JSON.stringify(state));
  } catch {
    /* ignore */
  }
};

function json(data: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "X-Tariff-Compass-Now": nowIso(), "X-Request-ID": "mock" },
  });
}
function problem(status: number, code: string, detail: string, errors?: { field: string; message: string }[]): Response {
  return new Response(JSON.stringify({ type: `https://tariffcompass.dev/problems/${code}`, title: code.replace(/_/g, " "), status, code, detail, errors, requestId: "mock" }), {
    status,
    headers: { "Content-Type": "application/problem+json", "X-Tariff-Compass-Now": nowIso() },
  });
}

class Fail extends Error {
  constructor(public res: Response) {
    super("fail");
  }
}
function need(permission: string) {
  if (!state.role) throw new Fail(problem(401, "not_authenticated", "Please sign in to continue."));
  if (!ROLE_PERMISSIONS[state.role].includes(permission)) throw new Fail(problem(403, "forbidden", "Your role doesn't include this."));
}

function rows(): ReviewRow[] {
  return REVIEW_ROWS.map((r) => (state.decided[r.id] ? { ...r, ...state.decided[r.id] } : r));
}

function page<T>(items: T[], p: URLSearchParams) {
  const pageNo = Math.max(1, Number(p.get("page") ?? 1));
  const size = Math.min(100, Math.max(1, Number(p.get("pageSize") ?? 25)));
  return { items: items.slice((pageNo - 1) * size, pageNo * size), page: pageNo, pageSize: size, total: items.length, totalPages: Math.max(1, Math.ceil(items.length / size)) };
}

function answerFor(text: string): AnswerOut | null {
  const t = text.toLowerCase();
  if (/bottle/.test(t)) return bottleAnswer("ans-bottle");
  if (/(tumbler|flask|vacuum|insulated|mug)/.test(t)) return tumblerAnswer("ans-tumbler");
  if (/(bike|bicycle|light|lamp|torch)/.test(t)) return bikelightAnswer("ans-bikelight");
  return null;
}

type Handler = (m: RegExpMatchArray, q: URLSearchParams, body: unknown) => Response | Promise<Response>;
const routes: [string, RegExp, Handler][] = [
  ["GET", /^\/auth\/csrf$/, () => json(null, 204)],
  ["GET", /^\/auth\/session$/, () => json({ me: state.role ? meFor(state.role) : null, clock: clock(), demoSignIn: true, demoPeople: DEMO_PEOPLE })],
  ["POST", /^\/auth\/demo$/, (_m, _q, b) => {
    const role = (b as { role: Role }).role;
    state.role = role;
    save();
    return json(meFor(role));
  }],
  ["POST", /^\/auth\/login$/, (_m, _q, b) => {
    const { email, password } = b as { email: string; password: string };
    const person = DEMO_PEOPLE.find((p) => email.toLowerCase().startsWith(p.fullName.split(" ")[0]!.toLowerCase()));
    if (!person || password.length < 12) return problem(401, "invalid_credentials", "That password didn't match. Four tries left before we pause sign-in for this email for 15 minutes.");
    state.role = person.role;
    save();
    return json(meFor(person.role));
  }],
  ["POST", /^\/auth\/logout$/, () => {
    state.role = null;
    save();
    return json(null, 204);
  }],
  ["POST", /^\/auth\/refresh$/, () => json({ expiresAt: nowIso(), absoluteExpiresAt: nowIso() })],
  ["GET", /^\/meta$/, () => json({ ...META, clock: clock() })],
  ["GET", /^\/tariff\/sections$/, () => json(SECTIONS)],
  ["GET", /^\/public\/samples$/, () => json(SAMPLES)],
  ["GET", /^\/public\/samples\/([\w-]+)$/, (m) => {
    if (m[1] === "tumbler") return json(tumblerAnswer("sample-tumbler", true));
    if (m[1] === "bike-light") return json(bikelightAnswer("sample-bike-light", true));
    if (m[1] === "bottle") return json(bottleAnswer("sample-bottle", true));
    return problem(404, "not_found", "No such sample.");
  }],
  ["POST", /^\/public\/classify$/, (_m, _q, b) => {
    const a = answerFor((b as { text: string }).text);
    return a ? json({ ...a, sample: true }) : problem(404, "not_in_demo", "The public demo only knows Northbound's sample products.");
  }],
  ["GET", /^\/home$/, () => (need("classify:read"), json(HOME))],
  ["GET", /^\/scopes\/counts$/, () => (need("classify:read"), json({ rulings: 214, products: 118, review: rows().filter((r) => r.status === "waiting").length, watch: 4 }))],
  ["POST", /^\/classify$/, (_m, _q, b) => {
    need("classify:run");
    const body = b as ClassifyIn;
    if (!body.text || body.text.trim().length < 3) return problem(422, "validation_error", "Describe the product in a few words.", [{ field: "text", message: "Describe the product in a few words." }]);
    const a = answerFor(body.text) ?? tumblerAnswer("ans-tumbler");
    return json({ ...a, query: { ...a.query, ...body } });
  }],
  ["GET", /^\/answers\/([\w-]+)$/, (m) => {
    need("classify:read");
    if (m[1]!.includes("bikelight")) return json(bikelightAnswer(m[1]));
    if (m[1]!.includes("bottle")) return json(bottleAnswer(m[1]));
    if (m[1]!.includes("tumbler")) return json(tumblerAnswer(m[1]));
    return problem(404, "not_found", "We couldn't find that answer.");
  }],
  ["POST", /^\/answers\/([\w-]+)\/facts$/, (m) => (need("classify:run"), json(m[1]!.includes("bikelight") ? bikelightAnswer(m[1]) : tumblerAnswer(m[1])))],
  ["POST", /^\/answers\/([\w-]+)\/save$/, () => (need("products:write"), json(binderFor(PRODUCTS[0]!).versions.at(-1)))],
  ["POST", /^\/answers\/([\w-]+)\/send-to-broker$/, () => (need("review:submit"), json(REVIEW_ROWS[14]))],
  ["POST", /^\/answers\/([\w-]+)\/citations\/(\d+)\/feedback$/, () => (need("review:decide"), json(null, 204))],
  ["POST", /^\/evidence$/, () => {
    need("classify:run");
    return json({ id: "ev-up", kind: "spec_sheet", kindLabel: "Spec sheet", fileName: "spec.pdf", pages: 1, extractedText: "Double wall, vacuum sealed.", photoFacts: [], certain: true, sha256: "abc1234", uploadedBy: "You", uploadedAt: nowIso() }, 201);
  }],
  ["POST", /^\/landed-cost$/, (_m, _q, b) => {
    need("classify:read");
    const body = b as LandedCostIn;
    if (body.country === "CA") return json(tumblerLandedCA());
    if (body.madeIn === "MX") return json(tumblerLandedMexico(body.usmcaAnswers ?? {}));
    if (body.madeIn === "VN") return json(tumblerLandedVietnam());
    return json(tumblerLandedUS());
  }],
  ["GET", /^\/rulings$/, (_m, q) => {
    need("rulings:read");
    const t = (q.get("q") ?? "").toLowerCase();
    const hits = RULINGS.filter((r) => !t || `${r.id} ${r.subject} ${r.code} ${r.holding}`.toLowerCase().includes(t)).map(({ text: _t, paragraphs: _p, related: _r, alsoCitedIn: _a, category: _c, codes: _cs, sourceUrl: _s, ...s }) => s);
    return json(page(hits, q));
  }],
  ["GET", /^\/rulings\/([\w-]+)\/compare$/, (m) => {
    need("rulings:read");
    const r = RULINGS.find((x) => x.key === m[1]);
    if (!r) return problem(404, "not_found", "We couldn't find that ruling.");
    const ans = tumblerAnswer();
    const cited = ans.rulings.find((c) => c.key === r.key);
    const listing = "Trailhead tumbler, 20 oz. Double-wall vacuum-insulated 18/8 stainless with a slide lid. Hot 6 hours, cold 18.";
    const spec = "Body: 18/8 SS, double wall, vacuum sealed. Lid: PP, slide closure. Capacity 591 ml.";
    const email = "Yes, the space between the walls is evacuated during manufacture.";
    const at = (s: string, p: string) => (s.indexOf(p) < 0 ? [] : [{ start: s.indexOf(p), end: s.indexOf(p) + p.length }]);
    const markIn = r.text.indexOf("vacuum insulated");
    return json({
      ruling: r,
      citedAs: cited?.n ?? null,
      productTitle: "Trailhead insulated tumbler, 20 oz · NB-KT-0412",
      madeInLabel: "Ningbo, China",
      ruleQuote: "“…will be applied only with respect to transactions involving articles identical to the sample submitted with the ruling request or to articles whose description is identical to the description set forth in the ruling letter.”",
      alignment: cited?.factCompare ?? [],
      evidence: [
        { kind: "listing", label: "Listing", text: listing, marked: at(listing, "vacuum-insulated") },
        { kind: "spec_sheet", label: "Spec sheet v3", text: spec, marked: at(spec, "vacuum sealed") },
        { kind: "supplier_email", label: "Supplier email, 14 Jan 2026", text: email, marked: at(email, "evacuated") },
      ],
      rulingMarked: markIn >= 0 ? [{ start: markIn, end: markIn + "vacuum insulated".length }] : [],
    });
  }],
  ["GET", /^\/rulings\/([\w-]+)$/, (m) => {
    need("rulings:read");
    const r = RULINGS.find((x) => x.key === m[1]);
    return r ? json(r) : problem(404, "not_found", "We couldn't find that ruling.");
  }],
  ["GET", /^\/tariff\/(US|CA)\/search$/, (m, q) => {
    need("tariff:read");
    const t = (q.get("q") ?? "").toLowerCase().replace(/\./g, "");
    return json(TARIFF_LINES.filter((l) => !t || `${l.digits} ${l.fullText}`.toLowerCase().includes(t)).map((l) => ({ ...l, country: m[1] })));
  }],
  ["GET", /^\/tariff\/(US|CA)\/lines\/([\d.]+)$/, (m) => {
    need("tariff:read");
    const digits = m[2]!.replace(/\./g, "");
    const line = TARIFF_LINES.find((l) => l.digits === digits);
    if (!line) return problem(404, "not_found", "That code isn't a line of the tariff in force.");
    const heading = TARIFF_LINES.find((l) => l.digits === digits.slice(0, 4));
    return json({
      line,
      ancestors: heading && heading !== line ? [heading] : [],
      children: TARIFF_LINES.filter((l) => l.digits.startsWith(digits) && l.digits !== digits),
      notes: digits.startsWith("9617") ? ["Section XV, Note 1(l): this section does not cover articles of Section XX."] : [],
      editionLabel: m[1] === "US" ? "HTSUS 2026 Revision 3 (in force 12–25 Feb 2026)" : "Customs Tariff T2026 (from 1 Jan 2026)",
    });
  }],
  ["GET", /^\/products$/, (_m, q) => {
    need("products:read");
    const t = (q.get("q") ?? "").toLowerCase();
    const cat = q.get("category");
    const st = q.get("standing");
    return json(page(PRODUCTS.filter((p) => (!t || `${p.sku} ${p.title} ${p.usCode}`.toLowerCase().includes(t)) && (!cat || p.category === cat) && (!st || p.standing === st)), q));
  }],
  ["GET", /^\/products\/([\w-]+)\/binder$/, (m) => {
    need("products:read");
    const p = PRODUCTS.find((x) => x.sku === m[1]);
    return p ? json(binderFor(p)) : problem(404, "not_found", "We couldn't find that product.");
  }],
  ["GET", /^\/products\/([\w-]+)$/, (m) => {
    need("products:read");
    const p = PRODUCTS.find((x) => x.sku === m[1]);
    return p ? json(productDetail(p)) : problem(404, "not_found", "We couldn't find that product.");
  }],
  ["POST", /^\/products\/([\w-]+)\/binder\/export$/, (m, _q, b) => {
    need("binder:export");
    const id = `job-${Date.now()}`;
    state.jobs[id] = { started: Date.now(), kind: "binder_export", sku: m[1]!, format: (b as { format: string }).format };
    save();
    return json({ jobId: id, statusUrl: `/api/v1/jobs/${id}`, eventsUrl: `/api/v1/jobs/${id}/events` }, 202);
  }],
  ["GET", /^\/jobs\/([\w-]+)$/, (m) => {
    const j = state.jobs[m[1]!];
    if (!j) return problem(404, "not_found", "No such job.");
    const p = Math.min(1, (Date.now() - j.started) / 2600);
    const done = p >= 1;
    const ext = j.format === "zip" ? "zip" : "pdf";
    return json({
      id: m[1],
      kind: j.kind,
      kindLabel: "Binder export",
      status: done ? "succeeded" : "running",
      statusLabel: done ? "Done" : "Working",
      progress: p,
      stage: done ? "done" : "writing",
      message: done ? "Your binder is ready." : p < 0.5 ? "Collecting every version, ruling and file…" : "Printing the record fingerprint on every page…",
      result: done ? { downloadUrl: `/api/v1/exports/${m[1]}/download`, fileName: `${j.sku}-binder.${ext}`, bytes: 184_320, pages: 9, fingerprint: "e4c1 9a07", recordFingerprint: "3f9a 71c0 e2d4" } : {},
      error: "",
      createdAt: nowIso(),
      finishedAt: done ? nowIso() : null,
    });
  }],
  ["GET", /^\/exports\/([\w-]+)\/download$/, () => new Response(new Blob(["%PDF-1.4\n% sample binder export\n"], { type: "application/pdf" }), { status: 200, headers: { "X-Tariff-Compass-Now": nowIso() } })],
  ["GET", /^\/review$/, (_m, q) => (need("review:read"), json(docket(rows(), q.get("filter") ?? "all", q.get("q") ?? "")))],
  ["GET", /^\/review\/([\w-]+)$/, (m) => {
    need("review:read");
    const r = rows().find((x) => x.id === m[1]);
    return r ? json(decisionRecord(r)) : problem(404, "not_found", "We couldn't find that review item.");
  }],
  ["POST", /^\/review\/([\w-]+)\/lesson$/, (_m, _q, b) => {
    need("review:decide");
    const body = b as { usCode?: string; reasonKind: string; reason: string };
    const yours = (body.usCode ?? "").replace(/\D/g, "").padEnd(10, " ");
    const proposed = "9617001000";
    return json({
      lesson: body.reason.length > 9 ? "“Double-wall” on its own doesn't mean vacuum. Look for “vacuum” in the spec before choosing 9617." : "Give a reason and the lesson appears here.",
      redline: Array.from({ length: 10 }, (_, i) => ({ index: i, proposed: proposed[i], yours: yours[i]!.trim(), changed: yours[i]!.trim() !== "" && yours[i] !== proposed[i] })),
    });
  }],
  ["POST", /^\/review\/([\w-]+)\/(approve|correct|ask|answer)$/, (m, _q, b) => {
    const verb = m[2]!;
    need(verb === "answer" ? "review:answer" : "review:decide");
    const r = rows().find((x) => x.id === m[1]);
    if (!r) return problem(404, "not_found", "We couldn't find that review item.");
    if (r.status !== "waiting" && r.status !== "answered") return problem(409, "already_decided", "Someone else decided this item a moment ago.");
    if (verb === "correct") {
      const body = b as { usCode?: string; reason: string };
      const errors = [];
      if (!body.reason || body.reason.trim().length < 10) errors.push({ field: "reason", message: "Give a reason for the change (at least 10 characters)." });
      if (body.usCode && body.usCode.replace(/\D/g, "").length !== 10) errors.push({ field: "usCode", message: "A code has ten digits." });
      if (errors.length) return problem(422, "validation_error", "Some fields need attention.", errors);
      if (body.usCode && !/^(7323930080|9617001000|8512102000|8513104000)$/.test(body.usCode.replace(/\D/g, ""))) {
        return problem(422, "unknown_code", "That code isn't a line of the tariff in force.", [{ field: "usCode", message: "That code isn't a line of the tariff in force." }]);
      }
    }
    const statusMap: Record<string, [string, string]> = { approve: ["approved", "Approved"], correct: ["corrected", "Corrected"], ask: ["asked", "Question asked"], answer: ["answered", "Question answered"] };
    const [status, statusLabel] = statusMap[verb]!;
    state.decided[r.id] = { status, statusLabel };
    save();
    const code = (b as { usCode?: string }).usCode;
    const toast =
      verb === "correct" ? `Corrected · ${r.sku} → ${code ? code : r.proposedUs?.code} · binder v3` : verb === "approve" ? `Approved · ${r.sku} · ${r.proposedUs?.code ?? r.proposedCa?.code} · binder v2` : verb === "ask" ? `Question sent to Northbound · ${r.sku}` : `Answer sent to Driftwood · ${r.sku}`;
    return json({ item: { ...r, status, statusLabel }, binderVersion: verb === "ask" ? null : 3, lesson: verb === "correct" ? "“Double-wall” on its own doesn't mean vacuum." : null, toast });
  }],
  ["GET", /^\/rules$/, () => (need("review:read"), json(RULES))],
  ["GET", /^\/watch$/, (_m, q) => {
    need("watch:read");
    const t = (q.get("q") ?? "").toLowerCase();
    const kind = q.get("kind");
    return json({ ...WATCH, items: WATCH.items.filter((i) => (!t || `${i.headline} ${i.body}`.toLowerCase().includes(t)) && (!kind || i.kind === kind)) });
  }],
  ["POST", /^\/watch\/scan$/, () => (need("watch:manage"), json({ jobId: "job-scan", statusUrl: "/api/v1/jobs/job-scan", eventsUrl: "" }, 202))],
  ["GET", /^\/lab$/, () => {
    need("lab:read");
    const live = state.signatures.length >= 2;
    return json(live ? { ...LAB, rounds: LAB.rounds.map((r) => (r.n === 7 ? { ...r, status: "live", statusLabel: "Live since 19 Feb" } : r.n === 6 ? { ...r, status: "retired", statusLabel: "Retired" } : r)), live: 7, candidate: null } : LAB);
  }],
  ["GET", /^\/lab\/rounds\/(\d+)$/, (m) => (need("lab:read"), json(round(Number(m[1]), state.role!, state.signatures)))],
  ["POST", /^\/lab\/rounds\/(\d+)\/sign$/, (m, _q, b) => {
    need("lab:sign");
    if (state.signatures.some((s) => s.role === state.role)) return problem(409, "same_person", "You've already signed this round.");
    const me = meFor(state.role!);
    const statement = (b as { statement: string }).statement.trim();
    if (statement.toLowerCase() !== me.user.fullName.toLowerCase()) return problem(422, "validation_error", "Type your full name to sign.", [{ field: "statement", message: `Type “${me.user.fullName}” to sign.` }]);
    state.signatures.push({ name: me.user.fullName, role: state.role!, at: nowIso() });
    save();
    return json(round(Number(m[1]), state.role!, state.signatures));
  }],
  ["POST", /^\/lab\/rounds$/, () => (need("lab:run"), problem(409, "conflict", "Round 7 is waiting for sign-off; start the next round after it is decided."))],
  ["GET", /^\/settings$/, () => (need("settings:read"), json(SETTINGS))],
  ["PATCH", /^\/settings$/, (_m, _q, b) => (need("settings:manage"), json({ ...SETTINGS, ...(b as object) }))],
  ["GET", /^\/org\/members$/, () => (need("settings:read"), json(MEMBERS))],
  ["PATCH", /^\/org\/members\/([\w-]+)$/, (m, _q, b) => {
    need("members:manage");
    const mem = MEMBERS.find((x) => x.id === m[1]);
    const role = (b as { role?: Role }).role;
    return mem ? json({ ...mem, ...(role ? { role, roleLabel: ROLE_LABELS[role] } : {}) }) : problem(404, "not_found", "No such member.");
  }],
  ["GET", /^\/org\/invitations$/, () => (need("members:manage"), json(state.invitations.map(invitationOut)))],
  ["POST", /^\/org\/invitations$/, (_m, _q, b) => {
    need("members:manage");
    const { email, role } = b as { email: string; role: Role };
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) return problem(422, "validation_error", "Some fields need attention.", [{ field: "email", message: "Enter an email address." }]);
    const inv = { id: `inv-${Date.now()}`, email, role };
    state.invitations.push(inv);
    save();
    return json({ ...invitationOut(inv), link: `${location.origin}/invite/sample-token-${inv.id}` }, 201);
  }],
  ["DELETE", /^\/org\/invitations\/([\w-]+)$/, (m) => {
    need("members:manage");
    state.invitations = state.invitations.filter((i) => i.id !== m[1]);
    save();
    return json(null, 204);
  }],
  ["GET", /^\/roles$/, () => json(ROLES)],
  ["GET", /^\/org\/brokers$/, () => (need("settings:read"), json([{ id: "eng-1", brokerOrg: "Driftwood Customs Brokers", importerOrg: "Northbound Goods Co.", countries: ["US", "CA"], countriesLabel: "US and Canadian entries", startedOn: "2025-09-10", people: MEMBERS.filter((x) => x.role === "broker") }]))],
  ["GET", /^\/audit\/verify$/, () => (need("audit:read"), json({ ok: true, events: 4200, brokenAt: null, checkedAt: nowIso(), sentence: "Chain verified 19 Feb, 10:30 · 4,200 events, none altered" }))],
  ["GET", /^\/audit\/export\.csv$/, () => {
    need("audit:read");
    const csv = ["at,actor,role,action,summary,fingerprint", ...AUDIT.map((a) => [a.at, a.actorName, a.actorRoleLabel, a.actionLabel, `"${a.summary}"`, a.fingerprint].join(","))].join("\n");
    return new Response(csv, { status: 200, headers: { "Content-Type": "text/csv", "X-Tariff-Compass-Now": nowIso() } });
  }],
  ["GET", /^\/audit$/, (_m, q) => {
    need("audit:read");
    const actor = (q.get("actor") ?? "").toLowerCase();
    return json(page(AUDIT.filter((a) => !actor || `${a.actorName} ${a.summary}`.toLowerCase().includes(actor)), q));
  }],
];

function invitationOut(i: { id: string; email: string; role: Role }) {
  return { id: i.id, email: i.email, role: i.role, roleLabel: ROLE_LABELS[i.role], expiresAt: "2026-02-24T18:30:00Z", invitedBy: "Priscilla Mensah", link: null };
}

function clock() {
  return { now: nowIso(), today: "2026-02-19", timezone: "America/Vancouver", demo: true, demoToday: "2026-02-19", demoTime: "10:30" };
}

export async function mockFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const u = new URL(url, "http://mock.local");
  const path = u.pathname.replace(/^\/api\/v1/, "");
  const method = (init.method ?? "GET").toUpperCase();
  let body: unknown = undefined;
  if (typeof init.body === "string") {
    try {
      body = JSON.parse(init.body);
    } catch {
      return problem(400, "bad_request", "That request wasn't readable.");
    }
  }
  await new Promise((r) => setTimeout(r, path.startsWith("/classify") || path.startsWith("/public/classify") ? 700 : 90));
  for (const [m, re, handler] of routes) {
    if (m !== method) continue;
    const hit = path.match(re);
    if (!hit) continue;
    try {
      return await handler(hit, u.searchParams, body);
    } catch (e) {
      if (e instanceof Fail) return e.res;
      return problem(500, "internal_error", "Something went wrong on our side.");
    }
  }
  return problem(404, "not_found", "We couldn't find that.");
}
