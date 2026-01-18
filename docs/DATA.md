# Data

Everything Tariff Compass knows comes from public sources, plus a clearly labelled sample company. Downloads live
in the git-ignored `data/` folder (`make fetch-data`); small samples are committed under
`backend/tariffcompass/search/fixtures/` so tests, CI and the offline demo work without a download.

## Sources

| Source | What we use | Access | Licence / terms | Snapshot |
|---|---|---|---|---|
| **CBP CROSS rulings** (NY and HQ ruling letters) | ruling number, date, tariff numbers, the letter text | Public mirror of CROSS on Hugging Face (`orlandowhite/hts-cross-rulings`, ~290 MB JSON), stream-parsed by `scripts/fetch_data.py` | The letters are works of the US government (public domain, 17 U.S.C. 105). The mirror states no licence; we keep only CBP's own content and drop the mirror's generated summaries | 18,136 rulings issued 21 Jan 2014 – 1 Aug 2025 (3,442 HQ) |
| **USITC Harmonized Tariff Schedule** | headings, subheadings, indent, article descriptions, units, column 1 General / Special rates, Chapter 99 | REST JSON export, chapter by chapter (`/reststop/exportList`); revision list (`/reststop/releaseList`); archived revisions as PDF (`/reststop/file?release=…`) | US government work, public domain | Demo edition: **2026 HTSUS Revision 3**, in force 12–25 Feb 2026 |
| **CBSA Customs Tariff T2026** | tariff item, statistical suffix, description, unit, MFN rate, preferential treatments (MXT, CEUT, CPTPT …) | Chapter HTML pages of the departmental consolidation effective 1 Jan 2026 | Federal law, reproduced under the Reproduction of Federal Law Order; not an official version | **T2026**, effective 1 Jan 2026 (the edition in force on 19 Feb 2026) |
| **Duty layers** | rate, scope, stacking and exclusion rules, Chapter 99 numbers, effective dates, legal status, sources | Hand-curated from primary sources into `backend/tariffcompass/duties/data/layers.json` (33 layers) | Federal Register, executive orders, USTR notices, CBP CSMS messages (public domain); Canada Gazette and CBSA customs notices (Reproduction of Federal Law Order) | As of **Thu 19 Feb 2026** |
| **CBSA memoranda** | citations in copy and binders | cbsa-asfc.gc.ca | Government of Canada | D11-11-3, D10-0-1, D10-14-64, D11-6-6, D17-1-21 |

### Why a mirror for the rulings

CROSS (rulings.cbp.gov) has no bulk export, and its search API refuses scripted clients ("Security parameters are
missing from this request context."). We did not try to get around that. The closest working path is a public
mirror that carries CBP's own fields: ruling number, date, tariff number and the full letter. The fetcher keeps
exactly those fields and links every ruling back to `https://rulings.cbp.gov/ruling/<number>` for the official
text.

### Label quality, and how training uses it

The mirror's tariff numbers are mostly right but not always. Measured over the 18,136 rulings kept:

- 12,689 (70.0%) state a classification holding in the letter ("The applicable subheading … will be …"); the
  rest are HQ decisions phrased differently, country-of-origin or marking rulings, or rulings that decline to rule.
- Where a holding is stated, the mirror's number agrees with it 97.0% at ten digits, 97.6% at six and 97.9% at the
  heading.
- Some entries carry the wrong collection or number (e.g. the 2021 revocation listed as "NY N319947" is HQ H303684
  by its own letterhead).

So the training and test sets use **labels re-derived from the letter's own holding**, keep only rulings where the
holding and the stated number agree at the heading, and take the ruling number from the letterhead when it
disagrees with the mirror. Rulings without a holding stay searchable (they are real evidence) but never become
labelled examples. The classification core records the exact counts per round in its report.

### Splits by date (no leakage across time)

Rulings are split by issue date: the newest rulings are the test set ("rulings it hasn't seen"), the slice before
them validates, everything older trains. The Lab and `eval/RESULTS.md` state the test window and its size. Broker
corrections join training only, never the test set. Every training round records a SHA-256 over the ids and texts
it used.

### The tariff editions on the demo date

USITC serves JSON only for the current revision; archived revisions (including 2026 Revision 3) are published as
PDF. The fetcher stores the current JSON with its release name (`data/hts/release.json`). The demo pins the
**2026 Revision 3** reading: the lines the seed and the duty engine rely on are checked against the Revision 3
chapter PDFs, and the duty layers were read from the Revision 3 Chapter 99. Canada's T2026 consolidation is the one
in force from 1 Jan 2026.

## Duty layers as of Thursday 19 February 2026

`duties/data/layers.json` holds every layer with its authority, Chapter 99 numbers, rate, scope, stacking rule,
`effectiveFrom`/`effectiveTo`, legal status and sources. Highlights:

| Layer | Rate | From | Status on 19 Feb 2026 |
|---|---|---|---|
| IEEPA duty on China linked to synthetic opioids (9903.01.24) | 10% (was 20%) | 10 Nov 2025 | Collected; legality pending at the Supreme Court |
| IEEPA reciprocal: China (9903.01.25) | 10% (34% suspended for one year from 10 Nov 2025) | 10 Nov 2025 | Collected; pending |
| IEEPA reciprocal: Vietnam (9903.02.69) | 20% | 7 Aug 2025 | Collected; pending |
| IEEPA reciprocal: EU (9903.02.19 / .20) | up to 15% all-in | 7 Aug 2025 | Collected; pending |
| IEEPA duties on Mexico (9903.01.01) / Canada (9903.01.10) | 25% / 35%, USMCA goods exempt | 2025 | Collected; pending |
| Section 301 China, Lists 1–3 / 4A | 25% / 7.5% | 2018–2019 | In force (4B suspended) |
| Section 301 four-year review: lithium-ion non-EV batteries (9903.91.06) | 25% | 1 Jan 2026 | In force |
| Section 232 steel / aluminium (derivatives on metal content) | 50% (UK 25%) | 4 Jun 2025 | In force |
| De minimis | suspended for all countries | 29 Aug 2025 (EO 14324) | In force |
| Merchandise Processing Fee FY2026 | 0.3464%, min $33.58, max $651.50 | 1 Oct 2025 | In force |
| Harbor Maintenance Fee (ocean) | 0.125% | n/a | In force |
| Canada: MFN / MXT / CEUT / CPTPT (T2026) | per tariff item | 1 Jan 2026 | In force (Vietnam lost GPT on 1 Jan 2025) |
| Canada: China Surtax Order (SOR/2024-187) | 100% EVs; 25% listed steel and aluminium | Oct 2024 | In force; does not cover 7323, 7615, 9617 or 8507 |
| Canada: Steel Derivative Goods Surtax Order (SOR/2025-267) | 25% | 26 Dec 2025 | In force; covers e.g. 7326, not 7323 |
| Canada: GST on imports | 5% of value plus duties | n/a | In force |

**Legal status is data.** The IEEPA case (*Learning Resources, Inc. v. Trump*, consolidated with *Trump v. V.O.S.
Selections*) was argued on 5 November 2025 and undecided on the demo date. Every IEEPA layer carries that status
and the product shows those duties as charged with their status open. The product never states an outcome; any
change in status is a change to `layers.json` with its own source and date.

### Verified sample stacks (US, ocean, 19 Feb 2026)

| Product | Line | Layers | Duty rate before fees |
|---|---|---|---|
| 20 oz vacuum tumbler, China, $12,500 | 9617.00.10.00 | 7.2% MFN + 0% (List 4B, suspended) + 10% opioid-linked IEEPA + 10% reciprocal | 27.2% → $3,400.00; with MPF $43.30 and HMF $15.63: **$3,458.93** |
| Bicycle headlight, China | 8512.10.20.00 | Free MFN + 7.5% (List 4A) + 10% + 10% | 27.5% |
| Knitted cotton pullover, Vietnam | 6110.20.20 | 16.5% MFN + 20% reciprocal | 36.5% |

The design prototype used illustrative rates for the tumbler (List 4A at 7.5%); the verified line is on List 4B,
so the product shows the engine's figures above. The eval's hand-checked landed-cost set (20 products) is built on
the same layer file.

## Seed plan: the sample organisations

All seeded records are dated by the demo clock (`TARIFF_COMPASS_DEMO_TODAY`, default Thu 19 Feb 2026), relative
to "today", in January and February 2026 or earlier. Every ruling number shown anywhere is a **real** CBP ruling
from the corpus; the seed never invents a ruling. The seed is idempotent and labelled as sample data.

### Organisations and people

| Organisation | Kind | People (role) |
|---|---|---|
| **Northbound Goods Co.** (Vancouver, BC and Seattle, WA) | importer | Maya Lindqvist (compliance), Jordan Tse (importer, Seattle), Priscilla Mensah (admin) |
| **Driftwood Customs Brokers** | broker firm, engaged by Northbound for US and Canadian entries | Dana Whitlock (licensed customs broker, US entries), Rafael Ouellet (licensed customs broker, Canadian entries) |

Emails use `@northbound.example` and `@driftwood.example`. Demo sign-in by role: importer → Jordan, broker → Dana,
compliance → Maya, admin → Priscilla. Dana and Rafael act inside Northbound through the engagement (broker
memberships).

### About 120 products

| Category | Examples (heading) | Made in |
|---|---|---|
| Kitchenware | vacuum tumblers and bottles (9617), stainless cookware (7323), aluminium cookware (7615), plastic food storage (3924), knives (8211) | China, Vietnam, Germany, Italy |
| Small electronics | bicycle lights (8512), torches and headlamps (8513), power banks (8507), Bluetooth speakers (8518), USB chargers (8504) | China, Vietnam, Mexico |
| Apparel | knitted pullovers (6110), base layers (6109), fleece and rain jackets (6101/6201/6210), socks (6115), gloves (6116) | Vietnam, China, Portugal |
| Outdoor gear | tents and tarps (6306), sleeping bags (9404), lanterns (9405), camp stoves (7321), tent stakes (7326), trekking poles (6602) | China, Vietnam, Mexico |
| Bags | backpacks and duffels (4202) | Vietnam, China |

SKUs follow `NB-<category>-<nnnn>` (e.g. `NB-KT-0412`, the 20 oz tumbler). Each product has a listing text, a
typical shipment (value, quantity, transport) and current codes. A handful carry evidence files (a spec sheet PDF,
a photo, a supplier email) generated by the seed and stored under `data/uploads/`.

### Binder histories

- **NB-KT-0412, 20 oz vacuum tumbler (China):** opened 12 Jan 2026. v1 proposed 9617.00.10.00 (between the walls:
  read from "insulated") → v2 question answered by the supplier ("vacuum-sealed") on 14 Jan → v3 approved by Dana
  Whitlock on 15 Jan → v4 re-approved on 17 Feb after the 2026 Revision 3 re-check (no line changed). Relies on
  NY N321134 and HQ H303684; NY N297165 cited for contrast.
- About 30 other binders with one to three versions (proposed → approved, or corrected with a reason), including
  two where a broker correction changed the heading.
- Entries using each code (entry number, date, duty paid) for the hero products; retention runs five years from the
  latest entry.

### Driftwood's review queue (about 15 items, waiting 0–6 days)

| Kind | Examples |
|---|---|
| Classifier unsure | a bicycle light that may also work as a hand torch (8512 vs 8513); a camp lantern with a power-bank port |
| Differs from the last code | a double-wall tumbler that is *not* vacuum-sealed (9617 proposed, 7323 likely) |
| A ruling changed | a product whose binder relied on a ruling later revoked in the corpus (the 2021 revocation family) |
| Always-review rules | power banks (lithium cells), steel and aluminium cookware (232 content), any entry over $25,000 |
| Into Canada | items where the Canadian tariff item splits differently from the US line |

Plus this week's history (about 31 approved, 9 corrected, 4 questions) and 23 corrections waiting for the next
training round, each with the broker's one-sentence lesson.

### Watch items (all real, dated on or before 19 Feb 2026)

1. **Pending:** the Supreme Court IEEPA case (argued 5 Nov 2025), with what we know and what we don't, and the
   products whose landed cost includes IEEPA layers.
2. **12 Feb 2026:** 2026 HTSUS Revision 3 in force: none of Northbound's lines renumbered or split.
3. **1 Jan 2026:** Section 301 increase on lithium-ion non-EV batteries to 25% (9903.91.06): power banks affected.
4. **26 Dec 2025:** Canada's Steel Derivative Goods Surtax Order (SOR/2025-267): steel tent stakes into Canada
   affected.
5. **10 Nov 2025:** the opioid-linked IEEPA duty on China cut from 20% to 10% (EO 14357).

### Lab rounds

Training rounds 4–7 come from real `make optimize` runs (offline simulator unless a key is set), loaded by the
seed with dates assigned by the demo clock: round 4 retired, round 5 not made live, round 6 live since 30 Jan,
round 7 trained on 19 Feb and waiting for its second signature (Maya signed at 09:48). The seed never invents
accuracy figures; it loads the reports the runs produced, labelled with the LM that produced them.

## Sizes on disk

| Item | Size |
|---|---|
| Rulings download (deleted after parsing) | ~290 MB |
| `data/rulings/rulings.jsonl` | ~100 MB |
| `data/hts/hts_current.jsonl`, `data/ca/customs_tariff_t2026.jsonl` | a few MB each |
| Committed fixtures (`search/fixtures`) | ~1.6 MB rulings sample (616 rulings, letters trimmed) + tariff samples |
