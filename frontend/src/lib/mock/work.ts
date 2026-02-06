/** Mock working data: products and binders, the broker docket, watch, the lab, home and the activity record. */
import type {
  AuditRow,
  BinderOut,
  CodeOut,
  DecisionRecord,
  DocketOut,
  HomeOut,
  LabOut,
  Money,
  OrgSettingsOut,
  ProductDetail,
  ProductSummary,
  ReviewRow,
  RoundOut,
  RuleOut,
  RulingDetail,
  RulingSummary,
  Standing,
  TariffLineOut,
  WatchOut,
} from "../types";
import { rulingKey } from "./answers";
import { RAW_RULINGS } from "./data-rulings";

const usd = (amount: string): Money => ({ amount, currency: "USD" });
const DAY = 86_400_000;
const NOW = Date.parse("2026-02-19T18:30:00Z");
const ago = (days: number, hours = 0) => new Date(NOW - days * DAY - hours * 3_600_000).toISOString();

function group(d: string) {
  return [d.slice(0, 4), d.slice(4, 6), d.slice(6, 8), d.slice(8, 10)].filter(Boolean).join(".");
}

/* ---------------- products ---------------- */

const TEMPLATES: [string, string, string, string, string, string, string][] = [
  // prefix, category, label, title, madeIn, us digits, ca digits
  ["KT", "kitchen", "Kitchenware", "Trailhead insulated tumbler, 20 oz", "CN", "9617001000", "9617000000"],
  ["KT", "kitchen", "Kitchenware", "Ridgeline double-wall camp mug, 350 ml", "CN", "9617001000", "9617000000"],
  ["KT", "kitchen", "Kitchenware", "Trail food jar, 500 ml, with folding spoon", "CN", "9617001000", "9617000000"],
  ["KT", "kitchen", "Kitchenware", "Stainless camp pot, 1.2 litre", "CN", "7323930080", "7323930000"],
  ["KT", "kitchen", "Kitchenware", "Stacking food storage set, plastic", "VN", "3924104000", "3924100000"],
  ["EL", "electronics", "Small electronics", "Bluetooth bike light, 800 lumen, USB-C", "CN", "8512102000", "8512100000"],
  ["EL", "electronics", "Small electronics", "LED camp lantern with power-bank port", "CN", "8513104000", "8513100000"],
  ["EL", "electronics", "Small electronics", "Power bank, 10,000 mAh", "CN", "8507600020", "8507600000"],
  ["EL", "electronics", "Small electronics", "Clip-on reading light", "MX", "8513104000", "8513100000"],
  ["AP", "apparel", "Apparel", "Merino base layer crew, men's", "VN", "6109901065", "6109900000"],
  ["AP", "apparel", "Apparel", "Knitted pullover, men's", "VN", "6110303053", "6110300000"],
  ["OD", "outdoor", "Outdoor gear", "Daypack, 22 litre", "VN", "4202923120", "4202920000"],
  ["OD", "outdoor", "Outdoor gear", "Hydration backpack, 12 litre", "CN", "4202923120", "4202920000"],
  ["BG", "bags", "Bags", "Waist bag, recycled nylon", "VN", "4202923131", "4202920000"],
];
const ORIGIN: Record<string, string> = { CN: "China", VN: "Vietnam", MX: "Mexico" };
const STANDING: [Standing, string][] = [
  ["approved", "Approved"],
  ["approved", "Approved"],
  ["approved", "Approved"],
  ["in_review", "With the broker"],
  ["needs_recheck", "Needs a re-check"],
  ["proposed", "Proposed"],
];

export const PRODUCTS: ProductSummary[] = Array.from({ length: 118 }, (_, i) => {
  const t = TEMPLATES[i % TEMPLATES.length]!;
  const [prefix, category, categoryLabel, title, madeIn, us, ca] = t;
  const sku = i === 0 ? "NB-KT-0412" : i === 1 ? "NB-KT-0388" : `NB-${prefix}-${String(200 + i * 7).padStart(4, "0")}`;
  const [standing, standingLabel] = i < 3 ? STANDING[i === 1 ? 3 : 0]! : STANDING[i % STANDING.length]!;
  const round = Math.floor(i / TEMPLATES.length);
  return {
    id: `p-${sku}`,
    sku,
    title: round === 0 ? title : `${title} (${["colourway B", "colourway C", "2025 run", "gift set", "bulk pack", "spring line", "trail edition", "travel size"][round - 1] ?? "variant"})`,
    category,
    categoryLabel,
    madeIn,
    madeInLabel: ORIGIN[madeIn]!,
    usCode: group(us),
    caCode: group(ca),
    standing,
    standingLabel,
    versions: 1 + (i % 4),
    lastDecidedAt: standing === "proposed" ? null : ago(2 + (i % 40), i % 9),
    inReview: standing === "in_review",
  };
});

export function productDetail(p: ProductSummary): ProductDetail {
  return {
    ...p,
    listingText: `${p.title}. Made in ${p.madeInLabel}.`,
    unitValue: usd("6.25"),
    evidence: [],
    latestAnswerId: p.sku === "NB-KT-0412" ? "ans-tumbler" : null,
  };
}

/* ---------------- binder (NB-KT-0412) ---------------- */

const dana = { id: "u-dana", fullName: "Dana Whitlock", role: "broker", roleLabel: "Licensed customs broker", licence: "Sample licence US-0001" };
const rafael = { id: "u-rafael", fullName: "Rafael Ouellet", role: "broker", roleLabel: "Licensed customs broker", licence: "Sample licence CA-0001" };
const jordan = { id: "u-jordan", fullName: "Jordan Tse", role: "importer", roleLabel: "Importer", licence: "" };
const relied = [
  { id: "NY N321134", key: "ny-n321134", statusLabel: "In force" },
  { id: "HQ H303684", key: "hq-h303684", statusLabel: "In force" },
];

export function binderFor(p: ProductSummary): BinderOut {
  const hero = p.sku === "NB-KT-0412";
  const versions: BinderOut["versions"] = hero
    ? [
        { n: 1, kind: "proposed", kindLabel: "Proposed", at: "2026-01-12T19:31:00Z", usCode: "9617.00.10.00", caCode: "9617.00.00.00", standing: "proposed", standingLabel: "Strong match · the classifier, round 6", decidingFact: { label: "Between the walls", value: "A vacuum", sourceNote: "read from 'insulated'" }, evidence: ["Listing text"], rulingsRelied: [...relied, { id: "NY N297165", key: "ny-n297165", statusLabel: "Cited for contrast" }], decidedBy: jordan, why: "First answer, from the listing.", fingerprint: "c1d0 8e42", current: false, changed: [] },
        { n: 2, kind: "question_answered", kindLabel: "Question answered", at: "2026-01-14T17:05:00Z", usCode: "9617.00.10.00", caCode: "9617.00.00.00", standing: "in_review", standingLabel: "Waiting on a fact", decidingFact: { label: "Between the walls", value: "A vacuum", sourceNote: "confirmed by the supplier" }, evidence: ["Listing text", "Supplier email, 14 Jan", "Trailhead_spec_v3.pdf"], rulingsRelied: [...relied, { id: "NY N297165", key: "ny-n297165", statusLabel: "Cited for contrast" }], decidedBy: { id: "u-maya", fullName: "Maya Lindqvist", role: "compliance", roleLabel: "Compliance lead", licence: "" }, why: "“Is the space between the walls vacuum-sealed?” “Yes.”", fingerprint: "7d3a 01bf", current: false, changed: ["standing", "decidingFact", "evidence", "decidedBy", "why"] },
        { n: 3, kind: "approved", kindLabel: "Approved", at: "2026-01-16T00:40:00Z", usCode: "9617.00.10.00", caCode: "9617.00.00.00", standing: "approved", standingLabel: "Approved by a licensed broker", decidingFact: { label: "Between the walls", value: "A vacuum", sourceNote: "confirmed by the supplier" }, evidence: ["Listing text", "Supplier email, 14 Jan", "Trailhead_spec_v3.pdf"], rulingsRelied: relied, decidedBy: dana, why: "Spec sheet v3 confirms the vacuum; heading 9617 names the article.", fingerprint: "2b6e 94c7", current: false, changed: ["standing", "rulingsRelied", "decidedBy", "why"] },
        { n: 4, kind: "re_approved", kindLabel: "Re-approved", at: "2026-02-17T18:12:00Z", usCode: "9617.00.10.00", caCode: "9617.00.00.00", standing: "approved", standingLabel: "Re-approved after the 2026 Revision 3 re-check", decidingFact: { label: "Between the walls", value: "A vacuum", sourceNote: "confirmed by the supplier" }, evidence: ["Listing text", "Supplier email, 14 Jan", "Trailhead_spec_v3.pdf"], rulingsRelied: relied, decidedBy: dana, why: "HTSUS 2026 Revision 3 came into force on 12 Feb; line 9617.00.10.00 is unchanged, so the code stands.", fingerprint: "3f9a 71c0", current: true, changed: ["standing", "why"] },
      ]
    : [
        { n: 1, kind: "proposed", kindLabel: "Proposed", at: ago(30), usCode: p.usCode, caCode: p.caCode, standing: "proposed", standingLabel: "Proposed", decidingFact: null, evidence: ["Listing text"], rulingsRelied: [], decidedBy: jordan, why: "First answer, from the listing.", fingerprint: "a10b 22c3", current: p.standing === "proposed", changed: [] },
        ...(p.standing === "proposed"
          ? []
          : [{ n: 2, kind: "approved", kindLabel: "Approved", at: ago(20), usCode: p.usCode, caCode: p.caCode, standing: p.standing, standingLabel: p.standingLabel, decidingFact: null, evidence: ["Listing text"], rulingsRelied: [], decidedBy: p.madeIn === "CA" ? rafael : dana, why: "The heading names the article.", fingerprint: "b20c 33d4", current: true, changed: ["standing", "decidedBy", "why"] as BinderOut["versions"][number]["changed"] }]),
      ];
  return {
    product: p,
    openedOn: hero ? "2026-01-12" : ago(30).slice(0, 10),
    keptUntil: hero ? "2032-02-10" : "2031-01-20",
    retentionNote: "Kept five years after the latest US entry (19 CFR 163.4) and six years after the latest Canadian import (CBSA D17-1-21), whichever is later.",
    versions,
    approval: hero
      ? { by: dana, at: "2026-02-17T18:12:00Z", version: 4, sentence: "Approved by Dana Whitlock, licensed customs broker, Driftwood · 17 Feb 2026, 10:12 PT · version 4" }
      : null,
    evidence: hero
      ? [
          { id: "ev-1", kind: "spec_sheet", kindLabel: "Spec sheet", fileName: "Trailhead_spec_v3.pdf", pages: 2, extractedText: "Body: 18/8 stainless steel, double wall, vacuum sealed. Lid: polypropylene, slide closure. Capacity 591 ml.", photoFacts: [], certain: true, sha256: "9a1c0e4", uploadedBy: "Jordan Tse", uploadedAt: "2026-01-14T17:00:00Z" },
          { id: "ev-2", kind: "supplier_email", kindLabel: "Supplier email", fileName: "supplier-email-2026-01-14.eml", pages: null, extractedText: "Yes, the space between the walls is evacuated during manufacture.", photoFacts: [], certain: true, sha256: "41bd772", uploadedBy: "Maya Lindqvist", uploadedAt: "2026-01-14T17:02:00Z" },
        ]
      : [],
    entries: hero
      ? [
          { entryNumber: "NBX-0118842-6", country: "US", enteredOn: "2026-02-09", code: "9617.00.10.00", dutyPaid: usd("3400.00") },
          { entryNumber: "NBX-0117301-2", country: "US", enteredOn: "2026-01-22", code: "9617.00.10.00", dutyPaid: usd("2720.00") },
          { entryNumber: "26-0044817", country: "CA", enteredOn: "2026-01-29", code: "9617.00.00.00", dutyPaid: { amount: "937.50", currency: "CAD" } },
        ]
      : [],
    record: { chainVerified: true, checkedAt: "2026-02-19T18:30:00Z", events: hero ? 11 : 3, fingerprint: hero ? "3f9a 71c0 e2d4" : "b20c 33d4 9e01" },
    advanceRuling: "Draft a CBSA advance ruling request (Memorandum D11-11-3) from this binder; apply at least 120 days before the next import.",
  };
}

/* ---------------- review docket ---------------- */

function code(country: "US" | "CA", digits: string, text: string, leaning = false): CodeOut {
  return { country, countryLabel: country === "US" ? "United States" : "Canada", code: group(digits), digits, headingDigits: digits.slice(0, 4), text, headingText: text, leaning };
}

const KIND_LABELS: Record<ReviewRow["kind"], string> = {
  unsure: "Classifier unsure",
  differs: "Differs from last code",
  ruling_changed: "Ruling changed",
  always_review: "Always reviewed",
  requested: "Sent for review",
};

const ROWS: [string, string, string, ReviewRow["kind"], string, string, number, ReviewRow["into"]][] = [
  ["NB-KT-0388", "Ridgeline double-wall camp mug, 350 ml", "9617001000", "differs", "Proposed 9617; the last approved mug of this type went to 7323 (NY N297165); HQ H303684 moved vacuum vessels to 9617", "7440.00", 1, "US"],
  ["NB-EL-0217", "Bluetooth bike light, 800 lumen, USB-C", "8512102000", "unsure", "Northbound answered: sold in the cycling range", "14100.00", 2, "US"],
  ["NB-OD-0734", "Collapsible LED lantern", "8513104000", "ruling_changed", "Relied on NY N284187, revoked by HQ H289250", "5180.00", 3, "US"],
  ["NB-EL-0241", "Power bank, 10,000 mAh", "8507600020", "always_review", "Rule: anything with lithium cells", "26800.00", 3, "both"],
  ["NB-EL-0249", "LED camp lantern with power-bank port", "8513104000", "unsure", "Lantern or power bank: which gives the essential character?", "9300.00", 2, "US"],
  ["NB-KT-0311", "Stainless camp pot, 1.2 litre", "7323930080", "always_review", "Rule: steel or aluminium content", "4120.00", 1, "US"],
  ["NB-AP-0272", "Knitted pullover, men's", "6110303053", "differs", "Canada splits this item differently from the US line", "8800.00", 4, "CA"],
  ["NB-OD-0283", "Daypack, 22 litre", "4202923120", "requested", "Jordan asked: is the hip-belt pocket a separate article?", "6100.00", 0, "US"],
  ["NB-AP-0265", "Merino base layer crew, men's", "6109901065", "unsure", "Knit or woven panels at the shoulder?", "3900.00", 5, "US"],
  ["NB-KT-0325", "Stacking food storage set, plastic", "3924104000", "differs", "Proposed 3924; last year's set went to 3924.10.40 too, but with a steel lid", "2400.00", 2, "CA"],
  ["NB-EL-0255", "Clip-on reading light", "8513104000", "always_review", "Rule: made in Mexico, USMCA claim", "1800.00", 1, "US"],
  ["NB-OD-0297", "Hydration backpack, 12 litre", "4202923120", "unsure", "Bag or drinking system?", "5400.00", 6, "US"],
  ["NB-BG-0304", "Waist bag, recycled nylon", "4202923131", "ruling_changed", "A ruling relied on was modified", "2200.00", 2, "US"],
  ["NB-EL-0262", "Power bank, 10,000 mAh (gift set)", "8507600020", "always_review", "Rule: entries over $25,000", "31200.00", 0, "US"],
  ["NB-KT-0339", "Trailhead insulated tumbler, 20 oz (bulk pack)", "9617001000", "requested", "Maya asked for a second look before the March order", "11900.00", 1, "both"],
];

export const REVIEW_ROWS: ReviewRow[] = ROWS.map(([sku, title, us, kind, detail, value, days, into], i) => ({
  id: `rv-${String(i + 1).padStart(2, "0")}`,
  productId: `p-${sku}`,
  sku,
  productTitle: title,
  waitingSince: ago(days, 3 + i),
  waitingLabel: days === 0 ? "today" : days === 1 ? "1 day" : `${days} days`,
  into,
  intoLabel: into === "both" ? "US + Canada" : into,
  proposedUs: into === "CA" ? null : code("US", us, title, kind === "unsure"),
  proposedCa: into === "US" ? null : code("CA", us.slice(0, 8) + "00", title, kind === "unsure"),
  kind,
  kindLabel: KIND_LABELS[kind],
  detail,
  value: usd(value),
  withName: into === "CA" ? "Rafael O." : "Dana W.",
  status: "waiting",
  statusLabel: "Waiting",
}));

export function docket(rows: ReviewRow[], filter: string, q: string): DocketOut {
  const match = (r: ReviewRow) =>
    filter === "all" ||
    (filter === "unsure" && r.kind === "unsure") ||
    (filter === "differs" && r.kind === "differs") ||
    (filter === "ruling_changed" && r.kind === "ruling_changed") ||
    (filter === "always" && r.kind === "always_review") ||
    (filter === "ca" && r.into !== "US");
  const ql = q.trim().toLowerCase();
  const waiting = rows.filter((r) => r.status === "waiting" || r.status === "answered");
  const items = waiting.filter(match).filter((r) => !ql || `${r.sku} ${r.productTitle} ${r.proposedUs?.code ?? ""} ${r.detail}`.toLowerCase().includes(ql));
  const count = (f: (r: ReviewRow) => boolean) => waiting.filter(f).length;
  return {
    counts: {
      all: waiting.length,
      unsure: count((r) => r.kind === "unsure"),
      differs: count((r) => r.kind === "differs"),
      rulingChanged: count((r) => r.kind === "ruling_changed"),
      always: count((r) => r.kind === "always_review"),
      ca: count((r) => r.into !== "US"),
    },
    oldestLabel: "oldest 6 days",
    items: items.sort((a, b) => a.waitingSince.localeCompare(b.waitingSince)),
    total: items.length,
    week: { approved: 31, corrected: 9, questions: 4 },
    nextRound: { round: 8, correctionsWaiting: 23 },
    emptyMessage: "Nothing waiting for Driftwood. Northbound's next shipment books on Monday.",
  };
}

export function decisionRecord(row: ReviewRow): DecisionRecord {
  const mug = row.sku === "NB-KT-0388";
  const listing = mug ? "Double-wall 18/8 stainless camp mug with a sip lid. Keeps coffee hot on the trail." : `${row.productTitle}. ${row.detail}.`;
  const spec = mug ? "Double-wall construction, air-insulated. Not vacuum-sealed. Capacity 350 ml." : "No spec sheet on file.";
  const phrase = "air-insulated";
  return {
    row,
    listing,
    specSheet: spec,
    specSheetFile: mug ? "Ridgeline_spec_v2.pdf, page 1" : null,
    uploadedBy: mug ? "Jordan Tse" : null,
    uploadedAt: mug ? "2026-02-17T21:00:00Z" : null,
    decidingPhrases: mug ? [{ source: "spec_sheet", span: { start: spec.indexOf(phrase), end: spec.indexOf(phrase) + phrase.length } }] : [],
    misread: mug ? "The classifier read “double-wall” as vacuum-insulated. The listing never says vacuum." : null,
    previousUs: mug ? "7323.93.00.80" : null,
    rulingsRelied: mug ? [{ id: "NY N321985", key: "ny-n321985", statusLabel: "In force" }] : [],
    rulingChange: row.kind === "ruling_changed" ? { kind: "revoked", kindLabel: "Revoked", text: "NY N284187 was revoked by HQ H289250, 7 Oct 2021", byId: "HQ H289250", date: "2021-10-07" } : null,
    rule: row.kind === "always_review" ? row.detail.replace("Rule: ", "") : null,
    answerId: mug ? "ans-tumbler" : "ans-bikelight",
    questions:
      row.sku === "NB-EL-0217"
        ? [{ id: "q-1", askedBy: "Dana Whitlock", askedAt: ago(2), text: "Is the light sold to be used off the bike, as a hand torch?", options: ["Sold as a bike light", "Also sold as a torch"], answer: "Sold as a bike light, in the cycling range", answeredBy: "Jordan Tse", answeredAt: ago(1) }]
        : [],
  };
}

/* ---------------- rulings ---------------- */

const STATUS_OVERRIDE: Record<string, RulingSummary["status"]> = {
  "NY N297165": { kind: "contrast", kindLabel: "Cited for contrast", text: "Decided before the 2021 move of insulated stainless containers to 9617" },
};

export const RULINGS: RulingDetail[] = RAW_RULINGS.map((r) => {
  const text = r.text;
  const hold = text.indexOf(r.holding.slice(0, 40));
  const paragraphs: { start: number; end: number }[] = [];
  let at = 0;
  for (const part of text.split(/\n\n/)) {
    paragraphs.push({ start: at, end: at + part.length });
    at += part.length + 2;
  }
  return {
    id: r.id,
    key: rulingKey(r.id),
    issued: r.issued,
    subject: r.subject,
    code: group(r.code.padEnd(10, "0")),
    codeAsQuoted: `${r.code.slice(0, 4)}.${r.code.slice(4, 6)}.${r.code.slice(6, 10)}`,
    heading: r.code.slice(0, 4),
    status: STATUS_OVERRIDE[r.id] ?? { kind: "in_force", kindLabel: "In force", text: "In force" },
    holding: r.holding,
    snippet: r.facts.slice(0, 220),
    snippetMarks: [],
    category: "Classification",
    codes: [group(r.code.padEnd(10, "0"))],
    text,
    paragraphs,
    related: [],
    alsoCitedIn: r.code.startsWith("9617") ? [{ productId: "p-NB-KT-0412", sku: "NB-KT-0412", title: "Trailhead insulated tumbler, 20 oz" }] : [],
    sourceUrl: `https://rulings.cbp.gov/ruling/${r.id.split(" ").pop()}`,
    ...(hold >= 0 ? {} : {}),
  };
});

/* ---------------- tariff text ---------------- */

export const TARIFF_LINES: TariffLineOut[] = [
  { country: "US", code: "9617", digits: "9617", level: "heading", levelLabel: "Heading", indent: 0, text: "Vacuum flasks and other vacuum vessels, complete; parts thereof other than glass inners", fullText: "Vacuum flasks and other vacuum vessels, complete; parts thereof other than glass inners", unit: "", generalRate: "", special: "", hasChildren: true },
  { country: "US", code: "9617.00.10.00", digits: "9617001000", level: "suffix", levelLabel: "Statistical suffix", indent: 2, text: "Having a capacity not exceeding 1 liter", fullText: "Vacuum vessels: Having a capacity not exceeding 1 liter", unit: "No.", generalRate: "7.2%", special: "Free (A+, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG)", hasChildren: false },
  { country: "US", code: "9617.00.30.00", digits: "9617003000", level: "suffix", levelLabel: "Statistical suffix", indent: 2, text: "Having a capacity exceeding 1 liter but not exceeding 2 liters", fullText: "Vacuum vessels: Having a capacity exceeding 1 liter but not exceeding 2 liters", unit: "No.", generalRate: "6.9%", special: "Free (A+, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG)", hasChildren: false },
  { country: "US", code: "9617.00.40.00", digits: "9617004000", level: "suffix", levelLabel: "Statistical suffix", indent: 2, text: "Having a capacity exceeding 2 liters", fullText: "Vacuum vessels: Having a capacity exceeding 2 liters", unit: "No.", generalRate: "6.9%", special: "Free (A+, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG)", hasChildren: false },
  { country: "US", code: "7323", digits: "7323", level: "heading", levelLabel: "Heading", indent: 0, text: "Table, kitchen or other household articles and parts thereof, of iron or steel", fullText: "Table, kitchen or other household articles and parts thereof, of iron or steel", unit: "", generalRate: "", special: "", hasChildren: true },
  { country: "US", code: "7323.93.00.80", digits: "7323930080", level: "suffix", levelLabel: "Statistical suffix", indent: 3, text: "Other", fullText: "Other, of stainless steel: Other", unit: "No.", generalRate: "2%", special: "Free (A+, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG)", hasChildren: false },
  { country: "US", code: "8512.10.20.00", digits: "8512102000", level: "suffix", levelLabel: "Statistical suffix", indent: 2, text: "Lighting equipment", fullText: "Lighting or visual signaling equipment of a kind used on bicycles: Lighting equipment", unit: "No.", generalRate: "Free", special: "", hasChildren: false },
  { country: "US", code: "8513.10.40.00", digits: "8513104000", level: "suffix", levelLabel: "Statistical suffix", indent: 2, text: "Other", fullText: "Portable electric lamps: Lamps: Other", unit: "No.", generalRate: "3.5%", special: "Free (A, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG)", hasChildren: false },
];

/* ---------------- watch ---------------- */

export const WATCH: WatchOut = {
  lastCheckedAt: "2026-02-19T14:00:00Z",
  checks: [
    "The duty layers in force for every origin you import from, with their legal status.",
    "New, modified and revoked rulings that touch a heading in your binders.",
    "The HTSUS revision and Canada's Customs Tariff in force, line by line against your codes.",
    "Federal Register and Canada Gazette notices that name a Chapter 99 number or surtax order you rely on.",
  ],
  quietMessage: "Nothing new touches your products since the last check.",
  items: [
    {
      id: "w-scotus",
      date: null,
      dateLabel: "PENDING",
      dateNote: "argued 5 Nov 2025",
      kind: "legal_pending",
      kindLabel: "Pending decision",
      headline: "The Supreme Court is deciding whether the emergency duties can stand",
      body: "The challenge to tariffs imposed under the International Emergency Economic Powers Act was argued on 5 November 2025. Until the Court rules and CBP says how to apply it, these duties are still collected, and your estimates include them.",
      knows: [
        "64 products carry one or more emergency duty lines (China, Vietnam, Mexico).",
        "Section 301 and Section 232 duties are separate and not part of this case.",
        "Every estimate shows what the total would be if these duties end.",
      ],
      unknowns: ["When the Court will rule, or what it will decide.", "Whether duties already paid would be refunded, and how.", "What might replace them."],
      affectedCount: 64,
      affected: [
        { productId: "p-NB-KT-0412", sku: "NB-KT-0412", title: "Trailhead insulated tumbler, 20 oz", effect: "Charges would fall from $3,458.93 to $958.93 on a $12,500 shipment if these duties end", recheck: "unchanged", recheckLabel: "Unchanged", dutyBefore: usd("3458.93"), dutyAfter: usd("958.93") },
        { productId: "p-NB-AP-0272", sku: "NB-AP-0272", title: "Knitted pullover, men's", effect: "The 20% Vietnam line would come off", recheck: "unchanged", recheckLabel: "Unchanged", dutyBefore: null, dutyAfter: null },
      ],
      sourceLabel: "Learning Resources, Inc. v. Trump (No. 24-1287)",
      sourceUrl: "https://www.supremecourt.gov/",
    },
    {
      id: "w-rev3",
      date: "2026-02-12",
      dateLabel: "12 FEB 2026",
      dateNote: null,
      kind: "schedule_revision",
      kindLabel: "Tariff revision",
      headline: "HTSUS 2026 Revision 3 is in force",
      body: "None of Northbound's lines were renumbered or split. Binders that rely on a line were re-checked and re-approved where a broker had already approved them.",
      knows: [],
      unknowns: [],
      affectedCount: 0,
      affected: [],
      sourceLabel: "USITC HTS release list",
      sourceUrl: "https://hts.usitc.gov/",
    },
    {
      id: "w-batteries",
      date: "2026-01-01",
      dateLabel: "1 JAN 2026",
      dateNote: null,
      kind: "duty_layer",
      kindLabel: "Duty change",
      headline: "Section 301 on lithium-ion batteries (non-EV) rose to 25%",
      body: "The four-year review moved non-EV lithium-ion batteries, power banks included, from List 4A at 7.5% to 25% under 9903.91.06.",
      knows: [],
      unknowns: [],
      affectedCount: 3,
      affected: [
        { productId: "p-NB-EL-0241", sku: "NB-EL-0241", title: "Power bank, 10,000 mAh", effect: "Section 301 on this line went from 7.5% to 25%", recheck: "needs_review", recheckLabel: "Needs review", dutyBefore: null, dutyAfter: null },
      ],
      sourceLabel: "USTR notice of modification, 18 Sep 2024",
      sourceUrl: "https://www.federalregister.gov/documents/2024/09/18/2024-21217/notice-of-modification-chinas-acts-policies-and-practices-related-to-technology-transfer",
    },
    {
      id: "w-steel-ca",
      date: "2025-12-26",
      dateLabel: "26 DEC 2025",
      dateNote: null,
      kind: "duty_layer",
      kindLabel: "Duty change",
      headline: "Canada's steel derivative goods surtax took effect",
      body: "A 25% surtax on listed steel derivative goods. Steel tent stakes into Canada are on the list; the binder for that product is flagged for a re-check.",
      knows: [],
      unknowns: [],
      affectedCount: 1,
      affected: [],
      sourceLabel: "Steel Derivative Goods Surtax Order, SOR/2025-267",
      sourceUrl: "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2025-267/FullText.html",
    },
  ],
};

/* ---------------- lab ---------------- */

export const LAB: LabOut = {
  inUse: { kind: "round", round: 6, label: "Round 6", fullCode: 58, heading: 84, sentence: "In use: round 6, signed by the compliance lead and a licensed broker after it passed its five checks." },
  rounds: [
    { n: 4, status: "retired", statusLabel: "Retired", trainedOn: "2025-12-08", note: "full code 51 in 100" },
    { n: 5, status: "not_made_live", statusLabel: "Not made live", trainedOn: "2026-01-08", note: "worse on knitted apparel, so round 4 stayed" },
    { n: 6, status: "live", statusLabel: "Live since 30 Jan", trainedOn: "2026-01-29", note: "full code 58 in 100" },
    { n: 7, status: "waiting_signoff", statusLabel: "Waiting for sign-off", trainedOn: "2026-02-19", note: "full code 71 in 100 · 46 broker corrections" },
  ],
  live: 6,
  candidate: 7,
  correctionsWaiting: 23,
};

export function round(n: number, viewerRole: string, signed: { name: string; role: string; at: string }[]): RoundOut {
  const sigs = signed.map((s) => ({ name: s.name, role: s.role, roleLabel: s.role === "broker" ? "Licensed customs broker" : "Compliance lead", signedAt: s.at, statement: s.name }));
  const canSign = (viewerRole === "broker" || viewerRole === "compliance") && !sigs.some((s) => s.role === viewerRole) && n === 7 && sigs.length < 2;
  return {
    n,
    status: sigs.length >= 2 ? "live" : n === 7 ? "waiting_signoff" : n === 6 ? "live" : "retired",
    statusLabel: sigs.length >= 2 ? "Live" : n === 7 ? "Waiting for sign-off" : "Live since 30 Jan",
    trainedOn: n === 7 ? "2026-02-19" : "2026-01-29",
    testCount: 1240,
    testFrom: "2025-07-01",
    testTo: "2026-01-31",
    snapshot: "a41c 09e7",
    rerunNote: "The same rulings, seed and budget gave the same numbers on two re-runs.",
    lede: `Round ${n} gets the full ten-digit code right for 71 in 100 rulings it hasn't seen, up from 58. Word matching alone gets 44.`,
    byDepth: [
      { level: "chapter", levelLabel: "Chapter", wordMatching: 88, live: 93, candidate: 96, unoptimised: 91 },
      { level: "heading", levelLabel: "Heading", wordMatching: 74, live: 84, candidate: 90, unoptimised: 81 },
      { level: "subheading", levelLabel: "Subheading", wordMatching: 61, live: 73, candidate: 82, unoptimised: 70 },
      { level: "full_code", levelLabel: "Full code", wordMatching: 44, live: 58, candidate: 71, unoptimised: 55 },
    ],
    confidence: {
      strong: { said: 812, right: 788, per100: 97, sentence: "When it said Strong match (812 times): right 97 times in 100." },
      broker: { said: 428, right: 150, per100: 35, sentence: "When it said Needs a broker (428 times): its first guess was wrong 35 times in 100." },
    },
    byChapter: [
      { chapter: "96", title: "Miscellaneous manufactured articles", tested: 62, before: 74, after: 87, change: 13, changeLabel: "▲ 13", newRulings: 9, moving: false },
      { chapter: "73", title: "Articles of iron or steel", tested: 148, before: 61, after: 72, change: 11, changeLabel: "▲ 11", newRulings: 31, moving: true },
      { chapter: "85", title: "Electrical equipment", tested: 212, before: 55, after: 66, change: 11, changeLabel: "▲ 11", newRulings: 44, moving: true },
      { chapter: "61", title: "Apparel, knitted", tested: 190, before: 52, after: 63, change: 11, changeLabel: "▲ 11", newRulings: 12, moving: false },
      { chapter: "42", title: "Leather goods and travel bags", tested: 132, before: 64, after: 70, change: 6, changeLabel: "▲ 6", newRulings: 8, moving: false },
      { chapter: "39", title: "Plastics", tested: 96, before: 58, after: 56, change: -2, changeLabel: "▼ 2", newRulings: 6, moving: false },
    ],
    learned: [
      "“Double-wall” on its own doesn't mean vacuum: look for “vacuum-sealed” or “only air between the walls” before choosing 9617.",
      "A light sold in the cycling range with a mount goes to 8512 even when it has a torch mode.",
      "Canada splits knitted pullovers by fibre one level earlier than the US; check the Canadian item separately.",
    ],
    drift: { newRulings: 212, mostMoved: "85", psi: 0.14, sentence: "212 new rulings since round 6; chapter 85 moved most. The shift is small enough that round 7's numbers still hold." },
    checks: [
      { key: "full_code", label: "Full-code accuracy at least the live round's", passed: true, value: "71", threshold: "≥ 58" },
      { key: "heading", label: "Heading accuracy at least the live round's", passed: true, value: "90", threshold: "≥ 84" },
      { key: "no_chapter_worse", label: "No chapter Northbound imports worse by more than 3 points", passed: true, value: "worst ▼ 2 (39)", threshold: "≤ 3" },
      { key: "strong_right", label: "“Strong match” right at least 90 times in 100", passed: true, value: "97", threshold: "≥ 90" },
      { key: "citations", label: "Cited rulings share the heading at least 95 times in 100", passed: true, value: "98", threshold: "≥ 95" },
    ],
    signOff: {
      required: 2,
      signatures: sigs,
      canSign,
      willPromote: canSign && sigs.length === 1,
      note: "Round 6 stays one step away. Answers already approved keep their codes; nothing is re-filed.",
    },
    runBy: "offline simulator",
  };
}

/* ---------------- home, rules, settings, audit ---------------- */

export const HOME: HomeOut = {
  dateLine: "Thursday 19 February 2026 · tariffs current as of this morning, 06:00 PT",
  recent: [
    { id: "ans-tumbler", queryText: "Stainless insulated tumbler, 20 oz, double wall, slide lid", usCode: "9617.00.10.00", verdict: "strong", verdictLabel: "Strong match", createdAt: "2026-02-19T18:21:00Z", createdBy: "Jordan Tse" },
    { id: "ans-bikelight", queryText: "Bluetooth bike light, 800 lumen, USB-C", usCode: "8512.10.20.00", verdict: "broker", verdictLabel: "Needs a broker", createdAt: "2026-02-18T20:02:00Z", createdBy: "Jordan Tse" },
    { id: "ans-tumbler", queryText: "Ridgeline double-wall camp mug, 350 ml", usCode: "9617.00.10.00", verdict: "strong", verdictLabel: "Strong match", createdAt: "2026-02-17T19:40:00Z", createdBy: "Jordan Tse" },
  ],
  changes: [
    { id: "w-scotus", headline: "Supreme Court decision on the emergency duties is pending", affectedCount: 64, consequence: "Argued 5 Nov 2025 · your estimates show both outcomes" },
    { id: "w-rev3", headline: "HTSUS 2026 Revision 3 in force", affectedCount: 0, consequence: "12 Feb 2026 · none of your lines were renumbered" },
    { id: "w-batteries", headline: "Section 301 on lithium-ion batteries rose to 25%", affectedCount: 3, consequence: "1 Jan 2026 · power banks re-checked" },
  ],
};

export const RULES: RuleOut[] = [
  { id: "r-1", kind: "keyword", kindLabel: "Keyword", value: "lithium", label: "Anything with lithium cells", active: true, createdBy: "Maya Lindqvist", createdAt: "2025-10-02T17:00:00Z", matches: 9 },
  { id: "r-2", kind: "material", kindLabel: "Material", value: "steel,aluminium", label: "Steel or aluminium content", active: true, createdBy: "Maya Lindqvist", createdAt: "2025-10-02T17:00:00Z", matches: 14 },
  { id: "r-3", kind: "value_over", kindLabel: "Value over", value: "25000", label: "Entries over $25,000", active: true, createdBy: "Dana Whitlock", createdAt: "2025-11-12T17:00:00Z", matches: 4 },
  { id: "r-4", kind: "origin", kindLabel: "Origin", value: "MX", label: "Made in Mexico, USMCA claim", active: true, createdBy: "Dana Whitlock", createdAt: "2025-12-01T17:00:00Z", matches: 6 },
];

export const SETTINGS: OrgSettingsOut = {
  into: ["US", "CA"],
  madeIn: "CN",
  ports: ["Seattle (3001), ocean", "Blaine (3004), truck", "Vancouver (809), ocean"],
  alwaysSendToBroker: false,
  retentionYears: 5,
  deletingNote: "Deleting hides a record; it is kept until its retention date.",
  brokerName: "Driftwood Customs Brokers",
};

const ACTIONS: [string, string, string, string, string][] = [
  ["auth.login", "Signed in", "Maya Lindqvist", "compliance", "Signed in"],
  ["lab.round_signed", "Signed a training round", "Maya Lindqvist", "compliance", "Signed round 7 (first signature)"],
  ["answer.created", "Classified a product", "Jordan Tse", "importer", "Stainless insulated tumbler, 20 oz → 9617.00.10.00"],
  ["review.corrected", "Corrected a code", "Dana Whitlock", "broker", "NB-KT-0377 → 7323.93.00.80 · binder v3"],
  ["binder.exported", "Exported a binder", "Maya Lindqvist", "compliance", "NB-KT-0412 binder (PDF)"],
  ["review.approved", "Approved a code", "Dana Whitlock", "broker", "NB-KT-0412 re-approved · binder v4"],
  ["watch.scanned", "Checked for changes", "Maya Lindqvist", "compliance", "Re-checked 118 binders against Revision 3"],
  ["answer.sent_to_broker", "Sent to the broker", "Jordan Tse", "importer", "NB-EL-0217 sent to Driftwood"],
  ["review.asked", "Asked the importer", "Dana Whitlock", "broker", "NB-EL-0217: sold as a torch?"],
  ["review.answered", "Answered the broker", "Jordan Tse", "importer", "NB-EL-0217: sold as a bike light"],
  ["member.invited", "Invited someone", "Priscilla Mensah", "admin", "Invited ops@northbound.example as importer"],
  ["settings.changed", "Changed settings", "Priscilla Mensah", "admin", "Added Blaine (3004) to ports"],
  ["rule.created", "Added an always-review rule", "Dana Whitlock", "broker", "Made in Mexico, USMCA claim"],
];

export const AUDIT: AuditRow[] = Array.from({ length: 42 }, (_, i) => {
  const [action, actionLabel, actorName, actorRole, summary] = ACTIONS[i % ACTIONS.length]!;
  const roleLabel = { compliance: "Compliance lead", importer: "Importer", broker: "Licensed customs broker", admin: "Administrator" }[actorRole]!;
  return {
    id: 4200 - i,
    at: ago(Math.floor(i / 3), (i * 5) % 24),
    actorName,
    actorRole,
    actorRoleLabel: roleLabel,
    action,
    actionLabel,
    summary,
    targetType: action.split(".")[0]!,
    targetId: `t-${i}`,
    targetLabel: summary.split(" ")[0]!,
    fingerprint: `${(0x3f9a + i * 977).toString(16).slice(-4)} ${(0x71c0 + i * 331).toString(16).slice(-4)}`,
  };
});
