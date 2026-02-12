/**
 * Mock answers and landed costs. Figures follow the verified sample stacks in docs/DATA.md: the tumbler
 * (9617.00.10.00, China, $12,500 by ocean) pays 7.2% + 10% + 10% = 27.2% ($3,400.00), plus MPF $43.30 and
 * HMF $15.63: $3,458.93. 9617.00.10 is on Section 301 List 4B (suspended), so there is no Section 301 line.
 */
import type { AnswerOut, CitedRulingOut, CodeOut, LandedCostOut, LayerLineOut, Money } from "../types";
import { RAW_RULINGS } from "./data-rulings";

const usd = (amount: string): Money => ({ amount, currency: "USD" });
const cad = (amount: string): Money => ({ amount, currency: "CAD" });

export function rulingKey(id: string): string {
  return id.toLowerCase().replace(/\s+/g, "-");
}
function cbpUrl(id: string): string {
  return `https://rulings.cbp.gov/ruling/${id.split(" ").pop()}`;
}
function raw(id: string) {
  const r = RAW_RULINGS.find((x) => x.id === id);
  if (!r) throw new Error(`mock ruling ${id} missing`);
  return r;
}
function spanOf(text: string, phrase: string) {
  const start = text.indexOf(phrase);
  return start < 0 ? [] : [{ start, end: start + phrase.length }];
}

const VACUUM = "Vacuum flasks and other vacuum vessels, complete; parts thereof other than glass inners";

export const TUMBLER_US: CodeOut = {
  country: "US",
  countryLabel: "United States",
  code: "9617.00.10.00",
  digits: "9617001000",
  headingDigits: "9617",
  text: "Vacuum flasks and other vacuum vessels, complete; having a capacity not exceeding 1 litre",
  headingText: VACUUM,
  leaning: false,
};
export const TUMBLER_CA: CodeOut = {
  country: "CA",
  countryLabel: "Canada",
  code: "9617.00.00.00",
  digits: "9617000000",
  headingDigits: "9617",
  text: VACUUM,
  headingText: VACUUM,
  leaning: false,
};

function cited(n: number, id: string, opts: Partial<CitedRulingOut> & { phrase?: string }): CitedRulingOut {
  const r = raw(id);
  const holding = opts.holding ?? r.holding;
  return {
    n,
    id,
    key: rulingKey(id),
    date: r.issued,
    subject: r.subject,
    status: opts.status ?? { kind: "in_force", kindLabel: "In force", text: "In force" },
    holding,
    markedSpans: opts.phrase ? spanOf(holding, opts.phrase) : [],
    match: opts.match ?? ["same_heading", "same_subheading"],
    matchLabels: opts.matchLabels ?? ["Same heading", "Same subheading"],
    factCompare: opts.factCompare ?? [],
    supports: opts.supports ?? [0],
    url: cbpUrl(id),
  };
}

/* ---------------- landed cost ---------------- */

const IEEPA_OPEN = "Pending at the Supreme Court (argued 5 Nov 2025)";

function line(p: Partial<LayerLineOut> & Pick<LayerLineOut, "letter" | "layerId" | "kind" | "kindLabel" | "name" | "rate" | "amount" | "plain" | "source" | "effectiveFrom">): LayerLineOut {
  return { sourceUrl: "https://hts.usitc.gov/", chapter99: null, effectiveTo: null, legalStatus: null, legalStatusOpen: false, ...p };
}

export function tumblerLandedUS(): LandedCostOut {
  return {
    country: "US",
    countryLabel: "United States",
    code: "9617.00.10.00",
    madeIn: "CN",
    madeInLabel: "China",
    value: usd("12500.00"),
    quantity: 2000,
    transport: "ocean",
    transportLabel: "Ocean freight",
    lines: [
      line({ letter: "a", layerId: "US-MFN", kind: "base", kindLabel: "Normal duty", name: "Base duty", rate: "7.2%", amount: usd("900.00"), plain: "The everyday rate for this code. Every origin pays it unless a trade agreement removes it.", source: "HTSUS 2026 Revision 3, 9617.00.10", effectiveFrom: "2026-01-01" }),
      line({ letter: "b", layerId: "US-IEEPA-CN-FENTANYL", kind: "emergency", kindLabel: "Emergency duty", name: "Emergency duty, China (synthetic-opioid order)", rate: "10%", amount: usd("1250.00"), plain: "Added by executive order in 2025; cut from 20% to 10% on 10 Nov 2025.", source: "EO 14357 · 90 FR 50725", sourceUrl: "https://www.federalregister.gov/documents/2025/11/07/2025-19825/modifying-duties-addressing-the-synthetic-opioid-supply-chain-in-the-peoples-republic-of-china", chapter99: "9903.01.24", effectiveFrom: "2025-11-10", legalStatus: IEEPA_OPEN, legalStatusOpen: true }),
      line({ letter: "c", layerId: "US-IEEPA-RECIP-CN", kind: "emergency", kindLabel: "Emergency duty", name: "Emergency duty, China (reciprocal)", rate: "10%", amount: usd("1250.00"), plain: "Held at 10% for one year from 10 Nov 2025 under the November 2025 arrangement.", source: "EO 14358 · 90 FR 50729", sourceUrl: "https://www.federalregister.gov/documents/2025/11/07/2025-19826/modifying-reciprocal-tariff-rates-consistent-with-the-economic-and-trade-arrangement-between-the", chapter99: "9903.01.25", effectiveFrom: "2025-11-10", effectiveTo: "2026-11-10", legalStatus: IEEPA_OPEN, legalStatusOpen: true }),
      line({ letter: "d", layerId: "US-MPF", kind: "fee", kindLabel: "Fee", name: "Merchandise processing fee", rate: "0.3464% (min $33.58, max $651.50)", amount: usd("43.30"), plain: "CBP's fee on a formal entry, at the fiscal-year 2026 rate.", source: "19 U.S.C. 58c · CBP Dec. 25-10, 90 FR 34665", sourceUrl: "https://www.federalregister.gov/documents/2025/07/23/2025-13869/customs-user-fees-to-be-adjusted-for-inflation-in-fiscal-year-2026-cbp-dec-25-10", effectiveFrom: "2025-10-01" }),
      line({ letter: "e", layerId: "US-HMF", kind: "fee", kindLabel: "Fee", name: "Harbour maintenance fee", rate: "0.125%", amount: usd("15.63"), plain: "Charged because the goods arrive by sea.", source: "19 CFR 24.24", sourceUrl: "https://www.ecfr.gov/current/title-19/chapter-I/part-24/section-24.24", effectiveFrom: "1998-07-01" }),
    ],
    notApplied: [
      { name: "Section 301, China", why: "9617.00.10 is on List 4B, which is suspended, so no Section 301 duty is collected." },
      { name: "Section 232, steel and aluminium", why: "Heading 9617 is not on the steel or aluminium derivatives lists." },
      { name: "Low-value parcel exemption", why: "Duty-free de minimis ended for every country on 29 Aug 2025 (EO 14324)." },
    ],
    chargesTotal: usd("3458.93"),
    landedTotal: usd("15958.93"),
    perUnit: usd("7.98"),
    effectiveRate: "+27.2%",
    questions: [],
    whatCouldChange: [
      { label: "If the pending emergency duties end", landedTotal: usd("13458.93"), chargesTotal: usd("958.93") },
      { label: "If made in Vietnam", landedTotal: usd("15958.93"), chargesTotal: usd("3458.93") },
    ],
    tariffsAsOf: "2026-02-19",
    snapshotLabel: "HTSUS 2026 Revision 3 · duty layers as of 19 Feb 2026",
  };
}

export function tumblerLandedCA(): LandedCostOut {
  return {
    country: "CA",
    countryLabel: "Canada",
    code: "9617.00.00.00",
    madeIn: "CN",
    madeInLabel: "China",
    value: cad("12500.00"),
    quantity: 2000,
    transport: "ocean",
    transportLabel: "Ocean freight",
    lines: [
      line({ letter: "a", layerId: "CA-MFN-T2026", kind: "base", kindLabel: "Normal duty", name: "Most-favoured-nation duty", rate: "7.5%", amount: cad("937.50"), plain: "Canada's general rate for tariff item 9617.00.00.", source: "Customs Tariff T2026, 9617.00.00", sourceUrl: "https://www.cbsa-asfc.gc.ca/trade-commerce/tariff-tarif/2026/html/00/ch96-eng.html", effectiveFrom: "2026-01-01" }),
      line({ letter: "b", layerId: "CA-GST", kind: "tax", kindLabel: "Tax", name: "GST on imported goods", rate: "5% of value plus duty", amount: cad("671.88"), plain: "Charged on the value for duty plus the duty itself.", source: "Excise Tax Act s. 212 · CBSA Memorandum D13-2-5", sourceUrl: "https://www.cbsa-asfc.gc.ca/publications/dm-md/d13/d13-2-5-eng.html", effectiveFrom: "2008-01-01" }),
    ],
    notApplied: [
      { name: "China surtax (2024)", why: "Applies to electric vehicles, steel and aluminium; a vacuum vessel isn't covered." },
      { name: "Steel derivative goods surtax", why: "Tariff item 9617.00.00 is not on the derivative goods list." },
      { name: "Courier low-value relief", why: "The shipment is well over CAD 20." },
    ],
    chargesTotal: cad("1609.38"),
    landedTotal: cad("14109.38"),
    perUnit: cad("7.05"),
    effectiveRate: "+7.5%",
    questions: [],
    whatCouldChange: [],
    tariffsAsOf: "2026-02-19",
    snapshotLabel: "Customs Tariff T2026 · duty layers as of 19 Feb 2026",
  };
}

/** Mexico origin into the US: the three USMCA questions come first; "yes" to all three waives the duties. */
export function tumblerLandedMexico(answers: Record<string, boolean>): LandedCostOut {
  const qualifies = ["tariff_shift", "regional_value", "certification"].every((k) => answers[k] === true);
  const base = tumblerLandedUS();
  const questions = [
    { key: "tariff_shift", question: "Do the non-Mexican materials change tariff heading in Mexico (the product-specific rule)?", answer: answers.tariff_shift ?? null },
    { key: "regional_value", question: "Is the regional value content at least the level the rule asks for?", answer: answers.regional_value ?? null },
    { key: "certification", question: "Will you hold a certification of origin when you claim the preference?", answer: answers.certification ?? null },
  ];
  if (qualifies) {
    return {
      ...base,
      madeIn: "MX",
      madeInLabel: "Mexico",
      lines: [base.lines[4]!].map((l) => ({ ...l, letter: "a" })),
      notApplied: [
        { name: "Base duty", why: "Waived: the goods qualify under USMCA (General Note 11)." },
        { name: "Emergency duty, Mexico", why: "Not charged on USMCA-qualifying goods (9903.01.04)." },
        { name: "Merchandise processing fee", why: "Originating goods of Mexico are exempt under USMCA." },
      ],
      chargesTotal: usd("15.63"),
      landedTotal: usd("12515.63"),
      perUnit: usd("6.26"),
      effectiveRate: "+0.1%",
      questions,
      whatCouldChange: [{ label: "If made in Mexico without a USMCA claim", landedTotal: usd("16483.93"), chargesTotal: usd("3983.93") }],
    };
  }
  return {
    ...base,
    madeIn: "MX",
    madeInLabel: "Mexico",
    lines: [
      base.lines[0]!,
      line({ letter: "b", layerId: "US-IEEPA-MX", kind: "emergency", kindLabel: "Emergency duty", name: "Emergency duty, Mexico (non-USMCA goods)", rate: "25%", amount: usd("3125.00"), plain: "Charged on goods from Mexico that don't qualify under USMCA.", source: "EO 14194 · 90 FR 9117, as amended", chapter99: "9903.01.01", effectiveFrom: "2025-03-04", legalStatus: IEEPA_OPEN, legalStatusOpen: true }),
      { ...base.lines[3]!, letter: "c" },
      { ...base.lines[4]!, letter: "d" },
    ],
    chargesTotal: usd("3983.93"),
    landedTotal: usd("16483.93"),
    perUnit: usd("8.24"),
    effectiveRate: "+32.2%",
    questions,
    whatCouldChange: [{ label: "If made in Mexico and it qualifies under USMCA", landedTotal: usd("12515.63"), chargesTotal: usd("15.63") }],
  };
}

export function tumblerLandedVietnam(): LandedCostOut {
  const base = tumblerLandedUS();
  return {
    ...base,
    madeIn: "VN",
    madeInLabel: "Vietnam",
    lines: [
      base.lines[0]!,
      line({ letter: "b", layerId: "US-IEEPA-RECIP-VN", kind: "emergency", kindLabel: "Emergency duty", name: "Emergency duty, Vietnam (reciprocal)", rate: "20%", amount: usd("2500.00"), plain: "The country rate for Vietnam under the reciprocal-tariff order.", source: "EO 14326 · 90 FR 37963", chapter99: "9903.02.69", effectiveFrom: "2025-08-07", legalStatus: IEEPA_OPEN, legalStatusOpen: true }),
      { ...base.lines[3]!, letter: "c" },
      { ...base.lines[4]!, letter: "d" },
    ],
    whatCouldChange: [{ label: "If the pending emergency duties end", landedTotal: usd("13458.93"), chargesTotal: usd("958.93") }],
  };
}

/* ---------------- answers ---------------- */

const TUMBLER_TEXT = "Stainless insulated tumbler, 20 oz, double wall, slide lid. Keeps drinks hot 6 hours, cold 18.";

export function tumblerAnswer(id = "ans-tumbler", sample = false): AnswerOut {
  const reason = [
    { text: "The space between the two steel walls is a vacuum, so this is a vacuum vessel, and heading 9617 names vacuum vessels outright.", cites: [1, 2], marked: [] },
    { text: "Steel kitchenware (7323) is the obvious second guess, but HQ H303684 puts insulated stainless containers in 9617.", cites: [2, 3], marked: [] },
    { text: "At 20 oz it sits under the one-litre line that splits the US subheadings.", cites: [1], marked: [] },
    { text: "If the walls were not vacuum-sealed, it would be steel tableware instead.", cites: [3], marked: [] },
  ];
  return {
    id,
    query: { text: TUMBLER_TEXT, madeIn: "CN", into: ["US", "CA"], evidenceIds: [], confirmedFacts: [], shipment: { value: usd("12500.00"), quantity: 2000, transport: "ocean" } },
    madeInLabel: "China",
    createdAt: "2026-02-19T18:21:00Z",
    createdBy: sample ? null : "Jordan Tse",
    tariffsAsOf: "2026-02-19",
    snapshotLabel: "HTSUS 2026 Revision 3 · Customs Tariff T2026",
    sample,
    us: TUMBLER_US,
    ca: TUMBLER_CA,
    verdict: {
      word: "strong",
      wordLabel: "Strong match",
      sentence: "Both countries agree down to the heading. Two of the three rulings cited reach the same heading; the third is there to show where the line is.",
      agreeing: 2,
      cited: 3,
      inForce: 3,
      agreementBar: [
        { n: 1, kind: "same" },
        { n: 2, kind: "same" },
        { n: 3, kind: "contrast" },
      ],
    },
    alternative: null,
    decidingQuestion: null,
    holdingSentence: "The tumbler is classified in subheading 9617.00.10.00, HTSUS, and tariff item 9617.00.00.00 of Canada's Customs Tariff.",
    issue: "Is a double-wall stainless tumbler a vacuum vessel of heading 9617, or a household article of steel of heading 7323?",
    facts: [
      { key: "body", label: "Body", value: "Stainless steel, double wall", source: "stated", sourceLabel: "Stated", sourceNote: "your description", decides: false },
      { key: "between_walls", label: "Between the walls", value: "A vacuum", source: "read", sourceLabel: "Read from the text", sourceNote: "read from 'insulated'", decides: true },
      { key: "capacity", label: "Capacity", value: "20 oz (591 ml)", source: "stated", sourceLabel: "Stated", sourceNote: "your description", decides: false },
      { key: "lid", label: "Lid", value: "Plastic slide lid", source: "stated", sourceLabel: "Stated", sourceNote: "your description", decides: false },
      { key: "case", label: "Case", value: "None", source: "assumed", sourceLabel: "Assumed", sourceNote: "nothing mentions one", decides: false },
    ],
    reason,
    path: [
      { level: "section", levelLabel: "Section", code: "XX", text: "Miscellaneous manufactured articles", gri: "GRI 1", griLabel: "Classify by the terms of the headings and the section and chapter notes.", why: "Not Section XV, base metals, even though the body is steel: vacuum vessels are named in Section XX.", cites: [], notNeighbours: [] },
      { level: "chapter", levelLabel: "Chapter", code: "96", text: "Miscellaneous manufactured articles", gri: "GRI 1", griLabel: "Classify by the terms of the headings and the section and chapter notes.", why: "Chapter 96 holds heading 9617, vacuum flasks and other vacuum vessels.", cites: [], notNeighbours: [] },
      {
        level: "heading", levelLabel: "Heading", code: "9617", text: VACUUM, gri: "GRI 1", griLabel: "Classify by the terms of the headings and the section and chapter notes.",
        why: "The heading text names the article. A tumbler with a sealed vacuum between its walls is a vacuum vessel, and the lid makes it complete.",
        cites: [1, 2],
        notNeighbours: [
          { code: "7323", text: "Table, kitchen or other household articles of iron or steel", reason: "Set aside: HQ H303684 puts insulated stainless containers in 9617", cite: 2 },
          { code: "3924", text: "Tableware and kitchenware, of plastics", reason: "Set aside: only the lid is plastic; the vessel is steel", cite: null },
        ],
      },
      { level: "subheading", levelLabel: "Subheading", code: "9617.00.10", text: "Vessels: having a capacity not exceeding 1 litre", gri: "GRI 6", griLabel: "Subheadings are compared only with subheadings at the same level.", why: "At 591 ml it is under the one-litre line.", cites: [1], notNeighbours: [{ code: "9617.00.30", text: "Having a capacity exceeding 1 litre but not exceeding 2 litres", reason: "Set aside: capacity is under one litre", cite: null }] },
      { level: "suffix", levelLabel: "Statistical suffix", code: "9617.00.10.00", text: "No further split for this line", gri: "GRI 6", griLabel: "Subheadings are compared only with subheadings at the same level.", why: "The line has a single statistical suffix.", cites: [], notNeighbours: [], countryNote: "Canada: 9617.00.00 is one tariff item for every capacity, suffix 00." },
    ],
    rulings: [
      cited(1, "NY N321134", {
        phrase: "9617.00.1000",
        supports: [0, 2],
        factCompare: [
          { fact: "Body", yours: "Stainless steel, double wall", theirs: "Stainless steel, double-walled", match: "same", matchLabel: "Same" },
          { fact: "Between the walls", yours: "Read from 'insulated'", theirs: "Vacuum insulated (laboratory)", match: "close", matchLabel: "Close" },
          { fact: "Capacity", yours: "20 oz (591 ml)", theirs: "17 oz", match: "same", matchLabel: "Same" },
          { fact: "Case", yours: "None", theirs: "No protective outer casing", match: "same", matchLabel: "Same" },
        ],
      }),
      cited(2, "HQ H303684", {
        phrase: "classified in heading 9617",
        supports: [0, 1],
        factCompare: [
          { fact: "Body", yours: "Stainless steel, double wall", theirs: "Insulated stainless steel containers", match: "same", matchLabel: "Same" },
          { fact: "Between the walls", yours: "Read from 'insulated'", theirs: "A vacuum", match: "close", matchLabel: "Close" },
        ],
      }),
      cited(3, "NY N297165", {
        status: { kind: "contrast", kindLabel: "Cited for contrast", text: "Cited for contrast: decided before the 2021 move to 9617" },
        match: ["different_heading"],
        matchLabels: ["Different heading"],
        phrase: "7323.93.0080",
        supports: [1, 3],
        factCompare: [
          { fact: "Body", yours: "Stainless steel, double wall", theirs: "Insulated stainless steel", match: "same", matchLabel: "Same" },
          { fact: "Heading reached", yours: "9617", theirs: "7323", match: "differs", matchLabel: "Differs" },
        ],
      }),
    ],
    tariffAuthorities: [
      { ref: "Heading 9617, HTSUS", quote: VACUUM },
      { ref: "Heading 7323, HTSUS", quote: "Table, kitchen or other household articles and parts thereof, of iron or steel" },
      { ref: "GRI 1", quote: "Classification shall be determined according to the terms of the headings and any relative section or chapter notes." },
      { ref: "GRI 6", quote: "Classification in the subheadings of a heading shall be determined according to the terms of those subheadings and any related subheading notes." },
    ],
    landed: [tumblerLandedUS(), tumblerLandedCA()],
    productId: "p-NB-KT-0412",
    reviewItemId: null,
    provenance: { classifierRound: 6, firstStageVersion: "first-stage", searchVersion: "search", lmLabel: "offline simulator" },
    timings: { totalMs: 212 },
  };
}

const LIGHT_HEADING = "Electrical lighting or signalling equipment of a kind used for cycles or motor vehicles";
const TORCH_HEADING = "Portable electric lamps designed to function by their own source of energy";

export function bikelightAnswer(id = "ans-bikelight", sample = false): AnswerOut {
  const us: CodeOut = { country: "US", countryLabel: "United States", code: "8512.10.20.00", digits: "8512102000", headingDigits: "8512", text: "Lighting equipment of a kind used on bicycles", headingText: LIGHT_HEADING, leaning: true };
  const ca: CodeOut = { country: "CA", countryLabel: "Canada", code: "8512.10.00.00", digits: "8512100000", headingDigits: "8512", text: "Lighting or visual signalling equipment of a kind used on bicycles", headingText: LIGHT_HEADING, leaning: true };
  const alt: CodeOut = { country: "US", countryLabel: "United States", code: "8513.10.40.00", digits: "8513104000", headingDigits: "8513", text: "Portable electric lamps: other", headingText: TORCH_HEADING, leaning: true };
  const base = tumblerAnswer(id, sample);
  return {
    ...base,
    id,
    query: { text: "Bluetooth bike light, 800 lumen, USB-C rechargeable, handlebar mount, with a torch mode.", madeIn: "CN", into: ["US", "CA"], evidenceIds: [], confirmedFacts: [], shipment: { value: usd("14100.00"), quantity: 1500, transport: "ocean" } },
    us,
    ca,
    verdict: {
      word: "broker",
      wordLabel: "Needs a broker",
      sentence: "It leans to bicycle lighting, but a light that also works in the hand can be a portable lamp. One fact decides it.",
      byDepth: [
        { level: "heading", levelLabel: "Heading", word: "broker", wordLabel: "Needs a broker" },
        { level: "full_code", levelLabel: "Full code", word: "broker", wordLabel: "Needs a broker" },
      ],
      agreeing: 1,
      cited: 3,
      inForce: 3,
      agreementBar: [
        { n: 1, kind: "same" },
        { n: 2, kind: "differs" },
        { n: 3, kind: "differs" },
      ],
    },
    alternative: { code: alt, condition: "if it is sold and used as a hand torch", dutyAtStake: "about $520 more on this shipment" },
    decidingQuestion: {
      factKey: "torch_mode",
      question: "Is it sold to be used off the bike, as a hand torch?",
      options: [
        { key: "bike_only", label: "No, it's sold as a bike light", leadsTo: "8512.10.20.00" },
        { key: "also_torch", label: "Yes, it's also sold as a torch", leadsTo: "8513.10.40.00" },
      ],
      notSureLabel: "Not sure: send to Driftwood",
    },
    holdingSentence: "The bike light leans to subheading 8512.10.20.00, HTSUS, and tariff item 8512.10.00.00 of Canada's Customs Tariff, subject to how it is sold.",
    issue: "Is a rechargeable bike light with a torch mode lighting equipment for cycles (8512) or a portable lamp with its own power source (8513)?",
    facts: [
      { key: "power", label: "Power", value: "Built-in rechargeable battery", source: "stated", sourceLabel: "Stated", sourceNote: "your description", decides: false },
      { key: "mount", label: "Mount", value: "Handlebar mount included", source: "stated", sourceLabel: "Stated", sourceNote: "your description", decides: false },
      { key: "torch_mode", label: "Used off the bike", value: "Not stated", source: "unknown", sourceLabel: "Not stated", sourceNote: "'torch mode' is mentioned, not how it is sold", decides: true },
      { key: "sold_as", label: "Sold as", value: "Not stated", source: "unknown", sourceLabel: "Not stated", sourceNote: "no listing category given", decides: false },
    ],
    reason: [
      { text: "A light made to mount on a bicycle is lighting equipment of a kind used for cycles.", cites: [1], marked: [] },
      { text: "Lights with their own battery that are used in the hand are portable lamps of 8513.", cites: [2, 3], marked: [] },
      { text: "The description mentions a torch mode but not how it is sold, and that decides the heading.", cites: [2], marked: [] },
    ],
    path: [
      { level: "section", levelLabel: "Section", code: "XVI", text: "Machinery and electrical equipment", gri: "GRI 1", griLabel: "Classify by the terms of the headings and the section and chapter notes.", why: "An electric light is electrical equipment.", cites: [], notNeighbours: [] },
      { level: "chapter", levelLabel: "Chapter", code: "85", text: "Electrical machinery and equipment", gri: "GRI 1", griLabel: "Classify by the terms of the headings and the section and chapter notes.", why: "Chapter 85 holds both candidate headings.", cites: [], notNeighbours: [] },
      { level: "heading", levelLabel: "Heading", code: "8512", text: LIGHT_HEADING, gri: "GRI 3(a)", griLabel: "The most specific description wins.", why: "Bicycle lighting is the more specific description, if the light is sold for the bike.", cites: [1], notNeighbours: [{ code: "8513", text: TORCH_HEADING, reason: "Possible: if it is sold and used as a hand torch", cite: 3 }] },
      { level: "subheading", levelLabel: "Subheading", code: "8512.10", text: "Lighting or visual signalling equipment of a kind used on bicycles", gri: "GRI 6", griLabel: "Subheadings are compared only with subheadings at the same level.", why: "The bicycle subheading.", cites: [], notNeighbours: [] },
      { level: "suffix", levelLabel: "Statistical suffix", code: "8512.10.20.00", text: "Lighting equipment", gri: "GRI 6", griLabel: "Subheadings are compared only with subheadings at the same level.", why: "Lighting, not signalling.", cites: [], notNeighbours: [], countryNote: "Canada: tariff item 8512.10.00, suffix 00." },
    ],
    rulings: [
      cited(1, "NY N317188", { match: ["same_heading"], matchLabels: ["Same heading"], phrase: "8512.20.2040", factCompare: [{ fact: "Mounted on a vehicle", yours: "Handlebar mount", theirs: "Mounted on a vehicle", match: "close", matchLabel: "Close" }] }),
      cited(2, "NY N350173", { match: ["different_heading"], matchLabels: ["Different heading"], phrase: "8513.10.4000", supports: [1, 2], factCompare: [{ fact: "Own power source", yours: "Rechargeable battery", theirs: "Battery operated", match: "same", matchLabel: "Same" }, { fact: "Used in the hand", yours: "Not stated", theirs: "Clip-on, portable", match: "differs", matchLabel: "Differs" }] }),
      cited(3, "NY N333144", { match: ["different_heading"], matchLabels: ["Different heading"], phrase: "8513.10.4000", supports: [1], factCompare: [{ fact: "Own power source", yours: "Rechargeable battery", theirs: "Battery operated", match: "same", matchLabel: "Same" }] }),
    ],
    tariffAuthorities: [
      { ref: "Heading 8512, HTSUS", quote: LIGHT_HEADING },
      { ref: "Heading 8513, HTSUS", quote: TORCH_HEADING },
      { ref: "GRI 3(a)", quote: "The heading which provides the most specific description shall be preferred to headings providing a more general description." },
    ],
    landed: [],
    productId: "p-NB-EL-0217",
    reviewItemId: "rv-02",
  };
}

/**
 * Sure at the heading, unsure at the full code: a vacuum bottle whose capacity isn't stated. Heading 9617 is settled
 * by "vacuum"; the US statistical line splits at one and two litres, so the last digits need a broker.
 */
export function bottleAnswer(id = "ans-bottle", sample = false): AnswerOut {
  const base = tumblerAnswer(id, sample);
  const over: CodeOut = { ...TUMBLER_US, code: "9617.00.30.00", digits: "9617003000", text: "Having a capacity exceeding 1 litre but not exceeding 2 litres", leaning: true };
  return {
    ...base,
    query: { ...base.query, text: "Insulated stainless steel bottle, vacuum double wall, screw cap, carry loop." },
    us: { ...TUMBLER_US, leaning: true },
    ca: TUMBLER_CA,
    verdict: {
      ...base.verdict,
      word: "broker",
      wordLabel: "Needs a broker",
      sentence: "The heading is settled: a vacuum between the walls makes it a vacuum vessel. The capacity isn't stated, and the US line splits at one litre.",
      byDepth: [
        { level: "heading", levelLabel: "Heading", word: "strong", wordLabel: "Strong match" },
        { level: "full_code", levelLabel: "Full code", word: "broker", wordLabel: "Needs a broker" },
      ],
    },
    alternative: { code: over, condition: "if it holds more than one litre", dutyAtStake: "0.3 points of duty on the goods value" },
    decidingQuestion: {
      factKey: "capacity",
      question: "Does the bottle hold one litre or less?",
      options: [
        { key: "up_to_1l", label: "One litre or less", leadsTo: "9617.00.10.00" },
        { key: "over_1l", label: "More than one litre, up to two", leadsTo: "9617.00.30.00" },
      ],
      notSureLabel: "Not sure: send to Driftwood",
    },
    holdingSentence: "The bottle is classified in heading 9617, HTSUS, and tariff item 9617.00.00.00 of Canada's Customs Tariff; the US statistical line waits on its capacity.",
    facts: base.facts.map((f) =>
      f.key === "capacity"
        ? { ...f, value: "Not stated", source: "unknown", sourceLabel: "Not stated", sourceNote: "the listing gives no capacity", decides: true }
        : f.key === "between_walls"
          ? { ...f, source: "stated", sourceLabel: "Stated", sourceNote: "your description: 'vacuum double wall'", decides: false }
          : f,
    ),
  };
}

export const SAMPLES = [
  { key: "tumbler", title: "stainless insulated tumbler, 20 oz", madeIn: "CN", query: TUMBLER_TEXT },
  { key: "bottle", title: "insulated bottle, capacity not stated", madeIn: "CN", query: "Insulated stainless steel bottle, vacuum double wall, screw cap, carry loop." },
  { key: "bike-light", title: "Bluetooth bike light, USB-C", madeIn: "CN", query: "Bluetooth bike light, 800 lumen, USB-C rechargeable, handlebar mount, with a torch mode." },
];
