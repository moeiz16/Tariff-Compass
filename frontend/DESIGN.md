# Tariff Compass frontend design: "Take a bearing"

> The static prototype and its screenshots were taken with `Date` frozen at **Thu 19 Feb 2026 10:30 America/Vancouver** (1440×900 @2x light and dark, 390 px phone @3x). **Read §0 Evolution first.**

Tariff Compass answers one question an importer has to get right on every entry: **what is this product, legally?** You describe a product and get its US (HTSUS, 10-digit) and Canadian (Customs Tariff, 10-digit) codes. Each answer comes with the classification path with the interpretation rule used at each step, the customs rulings that back each sentence, and a landed-cost breakdown that names every duty. Brokers approve, correct or ask; every correction becomes an example for the next training round; every product keeps a binder that is its reasonable-care record.

- **Seed importer:** Northbound Goods Co. (Vancouver and Seattle; outdoor gear, small electronics, apparel, kitchenware; 118 products). People: **Maya Lindqvist** (compliance), **Jordan Tse** (importer, Seattle), **Priscilla Mensah** (admin).
- **Seed broker:** Driftwood Customs Brokers. **Dana Whitlock** (licensed customs broker, US entries), **Rafael Ouellet** (licensed customs broker, Canadian entries).
- **Demo moment:** Thursday 19 February 2026, 10:30 a.m. Pacific. Every displayed date is in Jan–Feb 2026 or earlier (rulings go back to 2014).
- **Stack:** SolidStart 1.5 (SolidJS) + TypeScript + Ark UI 5.40 with Park UI-style recipes + Tailwind 4.1 (§13; verified on Node 21.7.1).

> **Legal status on the demo date:** on Thursday 19 February 2026 the Supreme Court had heard *Learning Resources, Inc. v. Trump* (argued 5 Nov 2025) and had not decided it. The IEEPA duties were being collected, so the design shows them as charged with their legal status open (hatched, ⚠) and never presumes an outcome. Every duty layer carries effective dates and a source, so a change in status is a data change, not a UI change.

---

## 0. Evolution (design review)

A design review of the first version found a generic "house style" under the colours: similar font feel, the same cards, modals and panels, no established component system, and the same page skeleton (top bar + centre column + something on the right). The first version of this design had exactly that skeleton on its results page (reading column + aligned citation rail). This section records what changed. **Where it conflicts with anything below, this section wins.** Sections 5, 6, 8, 9, 10, 12 and 13 are already rewritten to match.

**Kept (the parts that were Tariff Compass's own):** the search-engine concept (front page, the box docking, scope verticals), the 97 chapters, the compass mark and its Seek / Settle / Waver states, the highlighter as the only accent, the receipt-style landed cost, Spline Sans Mono for codes, Source Serif 4 for quoted law, the palette.

**1. Component system: Ark UI + Park UI-style recipes.** Every interactive part is an **Ark UI for SolidJS** component (`@ark-ui/solid` 5.40.0, headless, from the Chakra team), styled with **Park UI-style slot recipes written in `tailwind-variants`** on our Tailwind 4.1 `@theme` tokens (Park UI itself ships Panda CSS presets; we keep its anatomy and recipe shape, not Panda). The full mapping is in §13. **Verified on Node 21.7.1:** a SolidStart 1.5.1 + Vinxi 0.5.11 (Vite 6.4.6) + Tailwind 4.1.18 + Ark UI 5.40.0 test app type-checks, builds, serves (HTTP 200) and server-renders 12 Ark components (accordion, combobox, dialog, hover-card, menu, pin-input, segment-group, splitter, tabs, toast, tooltip, tree-view). SolidStart 2.x is ruled out (it needs Node ≥ 24 and Vite 8/9). Across the portfolio this is the only Ark/Park system: Kinroot moves to shadcn/ui (React), and the others use Skeleton (Svelte), Nuxt UI (Vue), Mantine (React), Web Awesome (Lit), Angular Material and Fluent UI.

**2. Skeleton: no top bar + centre + right column anywhere.** Each page now takes its structure from the document a customs professional actually works with:

| Page | Before | After | Why (research) |
|---|---|---|---|
| Results | Answer block, reading column, **aligned citation rail on the right** | **The answer is written in the shape of a CBP ruling letter**: a full-bleed **Holding** band (codes, verdict, the holding sentence, actions), then a memo of numbered paragraphs (**¶0 In short · ¶1 Facts · ¶2 Issue · ¶3 Law and analysis · ¶4 Landed cost · ¶5 Authorities cited**) with labels and the path spine in a **left gutter**. Citations open **inline drawers** under the sentence that cites them, each with the holding and a small **your facts vs the ruling's** table. A hover peek is kept for fluency. | CBP's own rulings run Facts / Issue / Law and analysis / Holding (e.g. the 2021 revocation notices in the Customs Bulletin; the CBP rulings programme guide). Brokers read that shape every day. Legal memos lead with the bottom line. |
| Ruling | A reading page with a right margin | **Two-pane compare** (Ark Splitter): a fact-alignment table across the top (Fact · yours · match · the ruling's), then your product's evidence on the left and the ruling letter on the right, highlights in both | 19 CFR 177.9(b)(2): a classification ruling applies only to "articles identical to the sample… or to articles whose description is identical to the description set forth in the ruling letter". Comparing facts is the real task. |
| Review | A results list with the selected item expanded, plus a right summary rail | A **docket**: a full-width sortable table. The open row unfolds into a full-width **decision record** in three bands (**Facts · The code · Reason**); the code is corrected in a 10-cell **pin input** under the proposed digits, so the redline is digit-aligned | Brokers work queues as dockets and entries line by line. A pin input makes "correct one digit" literal. |
| Binder | Section-numbered document with a contents rail and a right margin | A **revision matrix**: versions as columns (v1 proposed → v4 re-approved), facts as rows (codes, standing, the deciding fact, evidence, rulings relied on, who, why, fingerprint). Unchanged cells show a **ditto mark 〃**, changed cells are marked. Evidence, entries and record sit in a three-part foot. | Reasonable care is "what did you know, when, and what did you do about it". A matrix answers that in one read. (Wikipedia's critique: merged diffs hide which edit did what; one column per decision doesn't.) |
| Lab | Report column + runs and sign-off in a right rail | A **report**: a horizontal strip of training rounds across the top (round 7 on the highlighter), numbered sections (§1 by depth, §2 the confidence word, §3 by chapter, §4 learned from brokers) and a **sign-off form** across the foot with two signature boxes; signing opens a **sheet** that drops from the query strip | A model-risk sign-off is a form with signatures, not a sidebar card. |
| Watch | News list + right rail | **Bulletin**: dated items with labels in the gutter; "what Watch checks" moved to a strip at the end | |
| Shell | App bar (brand · box · person) | **Query strip**: the mark sits in the same gutter the memo uses, the box spans the content measure, scopes are printed on the strip's lower edge with a highlighter underline | One left edge runs from the box to every paragraph number. |

No card grids anywhere: surfaces are bands (holding), tables (docket, matrix, compare), slips (receipt, drawers, toasts, sheet) and rules.

**3. Typography: the voice is now a slab serif.** Schibsted Grotesk read as "yet another grotesque" next to Hanken Grotesk, Geist and Figtree. The voice (body, headings, UI, wordmark) is now **Bitter** (variable 100–900 with italics), a screen-first slab serif, which gives the product the register of a typed ruling letter. Quoted law stays **Source Serif 4**; codes stay **Spline Sans Mono**. Gutter labels are Bitter italic with a small-caps-style bold heading (not lowercase mono, which is Nightjar's; not mono caps, which is Plotline's). Checked against Kinroot (Spectral, Hanken Grotesk, Red Hat Mono, changing), Nightjar SOC (Geist, Geist Mono), ClaimVoice (Bricolage Grotesque, Figtree), Plotline (Newsreader, IBM Plex Mono): **no project uses a slab**.

**4. Floating layers have one recipe.** Peek, menus, toasts and the sign-off sheet share a Park-style recipe: 1.5 px ink rule, radius 6 (4 for toasts), and a **hard 4 px ink offset** instead of a soft shadow. Drawers are inline, never floating. Dialogs are **sheets that drop from the query strip**, not centred modals. Toasts are small mono slips at the bottom left.

---

## 1. Research: what we looked at and what we took

Opened in this design round. Some product pages refused automated fetches (Flexport's simulator, Mobbin, Land-book, the TariffLens ruling pages, Harvey's help centre); where that happened the row says what the finding rests on.

| # | Reference | What it does | What Tariff Compass takes |
|---|---|---|---|
| 1 | Perplexity citations teardown: https://aiuxplayground.com/teardowns/perplexity/citations | Inline source chips with "+N", click-to-open popovers, a sources sidebar, a Links tab; recommends layered depth (chips for skimmers, popovers for checks, a full view for auditors); criticises three paths to the same detail and the sidebar squeezing the answer on phones. | **Three layers, one path each:** a `[n]` chip in the sentence → a peek card on hover/focus → the ruling page with highlights on Enter. On phone the peek becomes a full-width bottom sheet. Their separate "Wrong sources" signal becomes the broker's **"A ruling points elsewhere"** correction reason. We keep **numbered** chips (not publisher chips): rulings have numbers, and brokers cite by number. |
| 2 | He & Liu, *Seeing to Think? How Source Transparency Design Shapes Interactive Information Seeking* (arXiv 2601.14611, Jan 2026): https://arxiv.org/abs/2601.14611 | N=372 experiment comparing Collapsible, Hover Card, Footer and **Aligned Sidebar** source designs. Hover cards support fluent checking; only the aligned sidebar reduced information overload as citation density rose, with higher critical-thinking scores. | v1 used an aligned right rail. **Evolution:** the rail was the portfolio's shared skeleton, so citations now open **inline drawers** directly under the sentence they support. That keeps the paper's key property (claim and source read together, in line) without a right column, and adds a fact compare inside each drawer. The hover peek is kept for fluent checking. The paper's fluency-versus-reflection trade-off is the reason both exist. |
| 3 | Evatt legal research prototype: https://evatt-prototype.pages.dev/ | Three panes (history, chat, sources); numbered citation cards with an authority badge (Binding, Persuasive, Overruled) and a verification status; a tinted "Key principle" block. | Every rail note carries a **status** (In force · Modified · Revoked · Cited for contrast) and a **match** (Same heading, Same subheading, Different heading). We rejected the chat bubbles and the history sidebar: an answer is a page, not a conversation. |
| 4 | Westlaw KeyCite status flags: https://www.thomsonreuters.com/en-us/help/drafting-assistant/westcheck/keycite-status-flags | Red/yellow flags say at a glance whether authority is still good law. | The ruling **status glyph** borrows the idea and drops the colour-only coding: filled dot = in force, half dot = modified, struck circle = revoked, dashed circle = cited for contrast, always with words ("Revoked by HQ H303684, 7 Jul 2021"). |
| 5 | CoCounsel Deep Research (Thomson Reuters): https://legal.thomsonreuters.com/blog/what-is-deep-research-the-ai-research-assistant-that-thinks-like-a-legal-expert/ | Reports with a research log of what was explored and concluded, clickable citations, and KeyCite signals factored in. | The **classification path is the research log**, written as the law's own steps (section → suffix with the GRI used). The loading line names what it is reading: "Reading the heading texts and section notes, then checking 214 rulings…". |
| 6 | Harvey sources (blog): https://www.harvey.ai/en-US/blog/biglaw-bench-sources | Links point to the specific passages that support an assertion. | The **ruling page highlights the exact passages** behind the sentence you came from, with the Mark swipe in reading order. |
| 7 | Kagi lenses and Quick Answer: https://help.kagi.com/kagi/features/lenses.html, https://help.kagi.com/kagi/ai/quick-answer.html; Nieman Lab review: https://www.niemanlab.org/2025/04/testing-kagi-a-premium-search-engine-for-a-broken-internet/ | Scoped verticals (a lens narrows the corpus); an answer with copious footnotes; a "startlingly minimal" results page. | **Scopes as verticals** under the box (Answer · Rulings · Tariff text · My products · Review · Watch · Lab), each a search over its own corpus. Minimal chrome: no cards, no sidebar, rules instead of boxes. |
| 8 | Google AI Overviews citation tests (Search Engine Roundtable): https://www.seroundtable.com/google-ai-overviews-citations-cards-bottom-42177.html and hover links: https://www.seroundtable.com/google-ai-mode-hover-style-inline-links-40511.html | Google keeps testing citations on the right vs at the bottom, and hover previews on inline links. | Right-hand margin on desktop (aligned, per #2); a numbered list **after** the answer on phone. Hover preview = our peek. |
| 9 | Arc Search "Browse for Me": https://www.freethink.com/consumer-tech/arc-search-app | A page built for your question; reviewers note the sourcing is imprecise ("shows where data comes from, but not precisely"). | The answer is a built page too, but **every sentence carries its own citation**; there is no "sources" pile at the end. |
| 10 | Zonos Classify docs: https://zonos.com/docs/supply-chain/classify and confidence score: https://zonos.com/docs/supply-chain/classify/features/confidence-score | Per-level table (chapter → tariff) with WCO descriptions and friendlier display names; the confidence score is entropy-based and "85% does not mean right 85% of the time". | **No percentage anywhere in the UI.** Two words ("Strong match", "Needs a broker") on the answer, and the Lab reports what each word has meant in frequencies ("right 97 times in 100"). Heading texts are quoted in serif as law; our plain sentence carries the friendly reading. |
| 11 | TariffLens: https://tarifflens.ai/ | Each result has the code, duties incl. 301/232, the GRI applied, cited rulings, **alternatives considered and why they were ruled out**, and an exportable audit trail; the landing has no demo, only "Book Demo". | "Not 7323: excluded by Section XV, Note 1" rows inside the path. The audit trail becomes the binder. The opposite landing: **the search box is the demo**. |
| 12 | Avalara classification: https://www.avalara.com/us/en/products/intelligent-tax-classification.html | Per SKU: code, confidence and explanation; accept, adjust or escalate; bulk-accept high confidence. | Broker actions: **Approve as proposed · Save correction · Ask Northbound a question**. We do not offer bulk approval; instead **always-review rules** (lithium, steel/aluminium, over $25k) put items in the queue even when the match is strong. |
| 13 | Flexport tariff simulator: https://tariffs.flexport.com/about (403 to automated fetch; read via search summaries and the FAQ index) | Current MFN plus 301/232/safeguard surcharges with totals and dollar amounts; metal-content input for 232. | Every layer has a **rate and an amount**; the total is said in dollars, per unit, and as "+35.2%". Origin switch restacks. |
| 14 | How HTS tariff stacking works: https://tariffsapi.com/articles/how-hts-tariff-stacking-works | Explains stacking as **a receipt with line items**; each duty applies to the same customs value and they add, not compound; Chapter 99 numbers identify the action; a trade agreement reduces only the base rate. | The landed-cost copy and layout: a receipt-like ledger under one stacked bar, the line "they add up, they don't compound", and a **Source** line with the Chapter 99 number and effective date under every layer. Layers that **don't** apply are listed too, with why. |
| 15 | USITC HTS search: https://hts.usitc.gov/ | The official indented hierarchy: heading/subheading, stat suffix, article description, rates. | The **path is an indented outline**, mirroring the tariff's own indentation, not a stepper or a breadcrumb. |
| 16 | CBP CROSS: https://rulings.cbp.gov/home; a vendor's note on CROSS search: https://gingercontrol.com/es/blog/hts-classification-guide | CROSS cross-references modified, revoked and referenced rulings; a vendor reports revoked rulings appear inline with current ones with nothing to tell them apart, and that CROSS groups ten digits 4.2.4 while the HTS uses 4.2.2.2. | Status is **never optional** on a ruling. Codes always display in the HTS grouping `9617.00.10.00`; the ruling page shows CBP's own `9617.00.1000` as quoted. |
| 17 | Descartes CustomsInfo: https://www.customsinfo.com/hts-and-import-tariff-classification-software/ | Hierarchical tariff browsing, a large rulings library including Canadian rulings. | **Tariff text** is its own scope (browse the schedule as an outline); the Canadian side is first-class in every answer. |
| 18 | Wikipedia page history and RevisionSlider: https://meta.wikimedia.org/wiki/WMDE_Technical_Wishes/RevisionSlider | Revision lists with compare; a two-knob slider; criticism that combined diffs hide which edit did what. | The binder's **Every change** is one version per decision (v1 proposed → v4 re-approved), each with who, when, why and what it cited, never a merged diff. The broker's **redline** compares exactly two codes, digit by digit. |
| 19 | CBSA Memorandum D11-11-3, advance rulings for tariff classification: https://www.cbsa-asfc.gc.ca/publications/dm-md/d11/d11-11-3-eng.html | Advance rulings for Canada; apply at least 120 days before importation. | The binder's Canada panel: "Draft an advance ruling request (CBSA D11-11-3) from this binder; apply at least 120 days before the next import." *D10-14-1, named in an early brief, is not on CBSA's D10 index; the product cites D11-11-3 (advance rulings) and D10-0-1 (parts and accessories) instead.* |
| 20 | Duty facts used in the samples: US–China November 2025 changes (C.H. Robinson): https://www.chrobinson.com/en-au/resources/insights-and-advisories/client-advisories/2025q4/11-04-2025-client-advisory-us-china-tariff-reductions-regulatory-suspensions-fentanyl-controls-nov/ · de minimis suspension (KPMG on CBP's implementation): https://kpmg.com/us/en/taxnewsflash/news/2025/08/us-cbp-implements-eo-suspending-duty-free-de-minimis-treatment.html · FY2026 MPF (DSV): https://www.dsv.com/en-us/about-dsv/press/news/us/2025/09/customs-user-fees-to-be-adjusted-for-fiscal-year-2026 | Fentanyl IEEPA duty on China cut 20% → 10% from 10 Nov 2025; reciprocal 10% held for one year from 10 Nov 2025; de minimis suspended for all countries from 29 Aug 2025 (EO 14324); MPF 0.3464%, min $33.58, max $651.50 for FY2026. | The rows and dates in the tumbler sample. The product-specific rates in the prototype (7.2% base, List 4A at 7.5%, Canadian 7%) were **illustrative**. Verified against HTSUS 2026 Revision 3: 9617.00.10 is on List 4B (suspended), so the tumbler pays **no** Section 301 duty, and Canada's MFN for 9617.00.00 is 7.5%. The product shows the duty engine's figures (docs/DATA.md, verified sample stacks). |
| 21 | Galleries: Awwwards "Google Search Design Concept": https://www.awwwards.com/inspiration/google-search-design-concept · Godly (now redirects to https://recent.design) · Land-book and Mobbin (403 to automated fetch) | The Awwwards page exposes only tags (UX, navigation, design thinking); recent.design is a feed of motion and type studies; the other two refused. | Confirmed the gap rather than a pattern: award galleries have almost no **search-results** pages with citation margins. We took the classic search-engine front page (wordmark, one box, quiet links) and built the results idiom from legal research tools (#1–#6) instead of from portfolio sites. |

---

## 2. Concept: "Take a bearing"

**A search engine for customs law, with a compass in it.** In customs, a *heading* is the four-digit level of the tariff; on a compass, a heading is the direction you are going. The product plays on that one idea and nothing more: **you ask what something is, and Tariff Compass takes a bearing.** The 97 chapters are the whole horizon; the answer narrows to one chapter, one heading, and then the digits lock in. When it is sure, the needle settles. When it isn't, the needle wavers between two headings, and the product says so in words: "Needs a broker".

The answer reads like a good broker writes: exact, cited, sober. "Heading 9617 names vacuum vessels outright [1][2]." Every answer has the shape of a CBP ruling letter (facts, issue, law and analysis, holding). Every claim opens its ruling in place, every ruling has a status, and every duty has a source and a date.

Mental models by role:

- **Importer (Jordan Tse, Northbound):** "What is this product, legally, and what will it cost to land?" Wants one answer in plain words, and to know when to ask someone.
- **Compliance (Maya Lindqvist, Northbound):** "Can I show we took reasonable care?" Thinks in **binders** and in what changed overnight.
- **Broker (Dana Whitlock, Rafael Ouellet, Driftwood):** thinks in **queries and corrections**: what is waiting, why it is uncertain, what the right code is, and on what authority. Every correction should make the next answer better.
- **Lab lead (Maya, with Dana signing off):** "Is it actually getting better, on rulings it hasn't seen, and is it safe to make the new round live?"

The one rule the UI never breaks: **no code without its reason, no reason without its ruling, no duty without its source and date.**

---

## 3. Information architecture and navigation

**The search box is the navigation.** There is no sidebar, no dashboard and no app menu beyond the avatar.

- **Front page** (`/` public, `/home` signed in): the wordmark, one box, sample links. After sign-in the same page adds two columns: *Your recent classifications* (a browser-history list) and *What changed that touches your products*.
- **Results** (`/answer?q=…`): the box docks into the query strip and becomes the page's title. Under it, **scopes** as search verticals:
  - **Answer**: the classification answer for the query.
  - **Rulings** (214): rulings matching the query, each with status and holding; opens the two-pane compare against your product.
  - **Tariff text**: the schedule as an indented outline, scoped to the query.
  - **My products** (118): products and their binders.
  - **Review** (15): the broker review list. Importers see what's waiting; brokers act.
  - **Watch** (4): changes that touch your products.
  - **Lab**: training rounds, accuracy, sign-off.
- **Counts** sit beside scope names as small mono numbers; the current scope's count is on the highlighter.
- **Avatar menu** (top right): Settings, Activity, Switch organisation (brokers serve several importers), Sign out. A theme button sits beside it.
- **The box changes meaning with the scope**, like a search engine's verticals: "Describe what you're importing…" (Answer), "Search the review list: product, SKU, code or ruling" (Review), "Search changes: a code, a ruling, a duty" (Watch). The button says **Classify** on Answer and **Search** elsewhere.
- **Routes** (SolidStart file routes): `/`, `/signin`, `/home`, `/answer`, `/rulings`, `/rulings/[id]`, `/tariff`, `/products`, `/products/[sku]` (binder), `/review`, `/review/[id]`, `/watch`, `/lab`, `/lab/rounds/[n]`, `/settings/*`, `/activity`.
- **Keyboard:** `/` focuses the box anywhere; on Review `J`/`K` move, `A` approve, `C` correct, `Q` ask; on Answer `[`/`]` move between citations, `Enter` on a citation opens the ruling.
- **Phone (390 px):** the bar collapses to the mark + avatar; the box spans the width on its own row; scopes scroll horizontally; the gutter collapses into a one-line label above each memo row; drawers, the receipt and the authorities stack; the peek becomes a bottom sheet; the docket rows and the compare table stack per item.

---

## 4. Landing story, beat by beat (`/`, prototype `index.html`)

The landing **is** a search engine's front page; the demo is the box. Only two calls to action: **Classify** (the search button) and **Broker sign-in** (a text link, top right).

1. **The front page.** Quiet top links (Why now · For brokers · How we measure · **Broker sign-in**). A big wordmark, **Tariff C◎mpass**, the "o" drawn as the compass. One line under it: "Describe a product. Get its **US and Canadian tariff codes**, the **customs rulings** that back them, and **every duty** it will carry." The box (Into US + Canada · From China · **Classify**). "Try a sample:" three Northbound products.
2. **The whole tariff.** Under the box hang **the 97**: every chapter of the tariff in 21 section columns (I–XXI), mono numbers on light tiles, chapter 77 drawn dashed ("held in reserve"). It's decoration that teaches: this is everything a product could be.
3. **Narrow.** Press Classify (or a sample): the 97 dim; three candidate chapters outline and name themselves ("Plastics", "Articles of iron or steel", "Miscellaneous manufactured articles"); the caption reads "3 chapters could hold it…". Two are struck through; **96 takes the highlighter**: "…one does: Chapter 96." The compass needle in the wordmark seeks, then swings and settles (or wavers, for a needs-a-broker answer).
4. **Dock.** The box flies from the middle of the page into the top bar (FLIP), and the page becomes a results page in place.
5. **The answer.** The full-bleed **holding band** rises: US `9617.00.10.00` and Canada `9617.00.00.00`, digits locking in left to right, the heading digits on the highlighter, the heading texts quoted in serif, **Strong match** with "5 of 6 rulings reach the same heading", and the holding sentence. Below, the memo rows rise in order (¶0 In short … ¶5 Authorities cited). Each claim is briefly marked, and after a beat the first citation **opens inline** under its sentence to show where the answer comes from.
6. **The sample banner.** "This is a sample answer for a product from Northbound Goods Co. Sign in to classify your own and keep each answer in an audit binder."
7. **How it got there** (the path) and **What it costs to land** (the duty stack) follow, as on the real results page.
8. **Below the fold, like the news strip under a search box** (numbered labels in mono):
   - **01 · Why now:** "Every parcel needs a code now, and the code is on you." Three dated facts: 29 Aug 2025 de minimis ended; 19 U.S.C. 1484 reasonable care; duties stack.
   - **02 · Anatomy of an answer:** four columns keyed by real artefacts (`9617.00.10.00`, `GRI 1 → GRI 6`, `[1]–[6]`, the landed total).
   - **03 · For brokers:** a real redline (9617 → 7323) with the broker's reason.
   - **04 · How we measure:** "Accuracy is measured on rulings it hasn't seen, and shown every round."
9. **Footer:** the compliance line ("Designed to support reasonable-care record keeping under 19 U.S.C. 1484 and 19 CFR Part 163, and CBSA advance ruling requests under Memorandum D11-11-3. Not legal advice; a licensed customs broker approves every code before it's used on an entry."), the sample disclaimer, and the two CTAs again.

**Empty state** (a query the public demo doesn't know): "The public demo only knows Northbound's sample products." with **Try the tumbler** / **Sign in**. Shot: `01-landing-empty-light.png`.

Microcopy voice: exact, cited, sober; second person to importers, colleague-to-colleague to brokers. Never "AI-powered", never "magic".

---

## 5. Screens

Layout grid at 1440: `32px | gutter 280 | measure 820 (memo) or the rest of the width (tables, bands) | 32px`. The gutter holds the mark, paragraph numbers, section labels and the path spine. The box, the scopes, every paragraph and every table share one left edge. **No page has a right-hand column.**

### 5.1 Sign in (`signin.html`)
Sign-in is a search: **one question at a time in the same box**. "Your work email" → Continue → "Password for dana@driftwood.example" → Sign in; a step line underneath (1 Email · 2 Password or sign-in link · 3 Your organisation, for brokers who serve several importers). "Email me a sign-in link" as a text button. Error state in a dashed note: "That password didn't match. Four tries left before we pause sign-in for this email for 15 minutes." Shot: `07-signin-light.png`.

### 5.2 Search front page, signed in (`home.html`)
The landing's front page at a smaller wordmark, the date line ("Thursday 19 February 2026 · tariffs current as of this morning, 06:00 PT"), the box with a richer placeholder ("Describe a product, paste a listing, or drop a spec sheet…"), then two columns: **Your recent classifications** (query, code in mono, verdict tag, when, who) and **What changed that touches your products** (headline, "64 products" on the highlighter, one-line consequence). Nothing else: no KPI cards, no greeting. Shot: `06-home-light.png`.

### 5.3 Results: the answer as a ruling-shaped memo (`results.html`, also the landing's second state)
- **Query strip** (all app pages): the mark in the left gutter, the box across the content measure, the person at the right; scopes on the strip's lower edge, the current one underlined with the highlighter.
- **Holding band** (full bleed, paper-2): gutter label "Answer · Thu 19 Feb 2026 / HOLDING" with the large compass, settled on the bearing or wavering. Then the US code card, the Canada code card, and a verdict column with an ink rule on its left (verdict word with icon, one sentence, the ruling-agreement bar). The **holding sentence** follows in prose ("The tumbler is classified in subheading 9617.00.10.00, HTSUS, and tariff item 9617.00.00.00 of Canada's Customs Tariff."), then actions: **Save to the product binder** / **Send to Driftwood for review** and "Nothing is filed automatically."
- **The memo** (gutter 280 px + measure 820 px; rows separated by hairlines):
  - **¶0 In short:** the plain sentences at 19 px, each ending in citation chips. Pressing a chip opens an **inline drawer** under the paragraph: ruling number, date, status, holding with the supporting words marked, and a mini table "Fact · Yours · The ruling's · ✓ same / ≈ close / ✗ differs", with **Compare side by side**, **Read the ruling** and **This ruling doesn't apply** (the broker's "wrong source" signal). Several drawers can be open.
  - **¶1 Facts:** what the answer rests on, as a definition list; each fact says where it came from ("your description", "read from 'insulated'", "assumed", "not stated"). Read or assumed facts are marked ◇ in amber, and a confirm box asks for them ("It's vacuum-sealed" / "Only air between the walls").
  - **¶2 Issue:** the question in one italic sentence.
  - **¶3 Law and analysis:** an Ark **Accordion**, one item per step (3.1 Section XX … 3.5 Suffix .00). The **gutter carries the path**: an indented spine with nodes, level name and code, the final node on the highlighter. Each trigger shows the heading text in serif and its GRI chip. The panel holds the reasoning, the quoted text, the struck neighbours ("not 7323 … Set aside: excluded by Section XV, Note 1 [3]") and the Canada note.
  - **¶4 Landed cost:** controls (Into: US / Canada as an Ark SegmentGroup; Made in: China / Vietnam / Mexico; shipment), the stacked bar, then the **receipt** (a perforated mono slip: goods value, lettered charges with rate and amount, n/a lines struck, charges total, landed, per unit, "⚠ = legal status open") beside **lettered reasons** (a, b, c…, each with source, effective date and any legal-status flag) and "What could change this total".
  - **¶5 Authorities cited:** a two-column table of authorities: rulings with status, then the tariff texts relied on (Heading 9617, Section XV Note 1, Heading 7323, GRI 1 and 6).
- **Needs a broker** (`?q=bikelight`): both codes say "leaning" with a dashed amber underline; ¶1 shows torch mode and "sold as" as **not stated**, and its confirm box is the deciding question with "Not sure: send to Driftwood"; ¶4 shows the two possible totals.
- **Loading / error:** same memo frame with the holding row showing "Taking a bearing…" (needle seeking) and skeleton lines, or the dashed error slip ("We couldn't reach the tariff schedule just now. Your question is saved. Nothing was sent to Driftwood and nothing was filed.").
Shots: `02-results-light.png` (drawer [1] open), `02-results-full-light.png`, `02-results-analysis-light.png`, `02-results-receipt-light.png`, `02-results-peek-light.png`, `02-results-broker-light.png`, `02-results-loading-light.png`, `02-results-error-light.png`, `02-results-dark.png`.

### 5.4 Ruling: two-pane compare (`ruling.html`)
Header in the gutter grid: "‹ Back to the answer / COMPARE / cited as [1]", the title "Your tumbler against NY N321134", and the 19 CFR 177.9(b)(2) sentence quoted. Then a full-width **fact-alignment table** (Fact · your product · Match · the ruling's article), with the match column tinted. Below, an Ark **Splitter**: **Your product** on the left (listing, spec sheet, supplier email, made in, also relied on, with the supporting words marked) and **the ruling** on the right (status in the pane header, the letter in Source Serif with its supporting passages marked in reading order). The handle drags or moves with arrow keys. On phone the alignment table stacks per fact and the panes stack. Shots: `09-compare-light.png`, `09-compare-dark.png`, `11-phone-compare.png`.

### 5.5 Broker review: the docket (`review.html`)
A count line with keyboard hints, then filter chips as an Ark ToggleGroup (All · Classifier unsure · Differs from last code · Ruling changed · Always reviewed). Then a **full-width table** (TanStack Table with Ark controls): Waiting (sorted) · Product + SKU line · Into · Proposed · Why it's here (kind tag + one-line detail) · Value · With. The selected row gets a 4 px highlighter edge and **unfolds into a decision record** spanning the table:
- **Facts:** the listing and the spec sheet in serif, the deciding phrase on the highlighter ("air-insulated"), file and uploader, and one sentence on what the classifier misread.
- **The code:** the proposed digits in cells with changed ones struck in red, and **your code in a 10-cell Ark PinInput** directly beneath, changed cells on the highlighter (dots are automatic). Under them, the old heading text struck and the new one; "Also change Canada to 7323.93.00.00"; "Relied on NY N256733".
- **Reason:** an Ark RadioGroup (The product facts differ · A ruling points elsewhere · A heading was read wrongly), a required reason, and **The next training round will learn** in one sentence.
- **Footer:** Approve as proposed (A) · Ask Northbound a question (Q) · "Recorded in the binder with your name and licence" · **Save correction (C)**, which raises a toast slip "Corrected · NB-KT-0388 → 7323.93.00.80 · binder v3".
Below the table: show 9 more, this week's counts, "23 corrections waiting for round 8", and the empty-docket copy. On phone each row stacks (product, age, code, kind) and the record's three bands stack. Shots: `03-review-light.png`, `03-review-dark.png`, `11-phone-review.png`.

### 5.6 Product binder: the revision matrix (`binder.html`)
Header in the gutter grid: "Binder · NB-KT-0412 / REASONABLE-CARE RECORD", product title, opened, 4 versions, **kept until 19 Feb 2031**; at the right the approval stamp and **Download binder (PDF)** / **Everything (ZIP)**. Then the **matrix** (Ark-free, a semantic table): columns v1 Proposed (12 Jan) · v2 Question answered (14 Jan) · v3 Approved (15 Jan) · **v4 Re-approved, current** (17 Feb, header on the highlighter, ink rule down its left). Rows: US code · Canada code · Standing · Between the walls (the deciding fact: "read from 'insulated'" → "confirmed by the supplier") · Evidence · Rulings relied on · Who decided · Why · Fingerprint. Unchanged cells show **〃**; changed cells carry the soft highlighter. The foot has three parts: Evidence on file, Entries using this code (with duty on file), and Record (chain verified; draft a CBSA D11-11-3 advance ruling request). On phone the matrix scrolls sideways inside its frame. Shots: `04-binder-light.png`, `04-binder-dark.png`, `11-phone-binder.png`.

### 5.7 Tariff change watch: the bulletin (`watch.html`)
Dated items in the gutter grid ("PENDING / argued 5 Nov 2025", "16 FEB 2026"…), each with a kind tag, "N of your products" on the highlighter, a headline and a paragraph. The top item is the pending Supreme Court decision with **What we know / What we don't** and the most affected products. The others are the modified ruling with each binder's re-check, new battery-pack rulings, and the 2026 schedule in force. **What Watch checks every morning** is a strip at the end, not a rail. Shot: `08-watch-light.png`.

### 5.8 Optimisation lab: the report (`lab.html`)
*The prototype below uses illustrative figures and an imagined live round. As built, the Lab shows only measured figures, opens with what is in use (word matching until a round passes its five checks and is signed live) and offers the sign-off only for a round that passed; see §14 and `eval/RESULTS.md`.*

A **strip of training rounds** across the top (Round 4 retired · 5 not made live · 6 live since 30 Jan · **7 waiting for sign-off** on the highlighter). Then numbered report sections in the gutter grid:
- **In one sentence:** "Round 7 gets the full ten-digit code right for **71 in 100** rulings it hasn't seen, up from 58. Word matching alone gets 44.", plus the test set, data snapshot and re-run note.
- **§1 By depth:** the three-mark dot plot (word matching ring · round 6 half · round 7 filled; the gain on the highlighter) across the full measure.
- **§2 The confidence word:** two 100-dot frequency grids.
- **§3 By chapter:** a sortable table (TanStack) with an inline round-6→7 bar, the signed change and new rulings with a "moving" tag.
- **§4 Learned from brokers:** three sentences.
- **§5 Sign-off:** a form across the page: the five checks, Maya's signed box ("Signed 19 Feb, 09:48"), and Dana's empty box with **Sign and make round 7 live**. That button opens an **Ark Dialog styled as a sheet** dropping from the query strip ("Type your name to sign").
Words used: "the classifier", "word matching", "training round", "rulings it hasn't seen". Shots: `05-lab-light.png`, `05-lab-dark.png`, `05-lab-signoff-light.png`, `11-phone-lab.png`.

### 5.9 Settings and activity (`settings.html`)
Like a search engine's settings: a short left list and one long page. **Defaults for new questions** (importing into, usually made in, ports, always send to a broker), **People and roles** (importer, broker, compliance, admin, with what each can do), **Your broker**, **Records** (five-year retention; deleting hides, never destroys early), **Activity**: every sensitive action with a short fingerprint, and "Chain verified 19 Feb, 10:30". Shot: `10-settings-light.png`.

### 5.10 Phone (390 px)
- **Front page:** wordmark, the box on two rows (text, then Into · From · Classify), samples as wrapping links, the 97 as seven columns per row.
- **Results:** the holding band stacks (US, Canada, verdict, holding sentence); memo rows put their gutter label on one line above the body; the analysis spine indents by 14 px a level; drawers stack holding over the fact compare; the receipt follows its controls; the authorities run in one column.
- **Review:** each docket row stacks (product, age, code, kind) and the decision record's three bands stack, with smaller pin cells.
- **Compare:** the alignment table becomes one block per fact (yours | the ruling's, then the match), and the panes stack.
- **Lab:** the rounds strip stacks vertically; the chapter table scrolls inside its frame.
No page scrolls sideways (checked in every shot). Shots: `11-phone-landing.png`, `11-phone-results.png`, `11-phone-results-full.png`, `11-phone-results-broker.png`, `11-phone-review.png`, `11-phone-compare.png`, `11-phone-binder.png`, `11-phone-lab.png`.
---

## 6. Typefaces (Google Fonts; self-hosted via Fontsource in the build)

| Role | Face | Weights | Where |
|---|---|---|---|
| **Voice:** body, headings, UI, wordmark | **Bitter** (variable 100–900, italics 100–900), a screen-first slab serif | 400 body (16.5/1.58), 550–650 labels and buttons, 700–800 headings and the wordmark ("Tariff" at 300 italic, "Compass" at 800); italic for the Issue sentence and gutter notes | everything Tariff Compass says in its own words, like a typed ruling letter |
| **Law** | **Source Serif 4** (variable, optical size 8–60) | 400 | heading texts, ruling holdings and letters, quoted listings and spec sheets: **anything quoted from someone else** |
| **Codes** | **Spline Sans Mono** | 500 codes, 600 chips | tariff codes, ruling numbers, rates, amounts, the receipt, GRI chips, fingerprints. **Never used for labels or prose.** |

Rules: slab = our voice, transitional serif = quoted authority, mono = a value you could type into a customs form. Gutter labels are Bitter italic with a letter-spaced bold heading (FACTS, ISSUE…): not lowercase mono (Nightjar) and not mono caps (Plotline).

Portfolio check: Necessa (system sans), Plotline (Newsreader, Fraunces, IBM Plex Mono, JetBrains Mono), Kinroot (Spectral, Hanken Grotesk, Red Hat Mono; being changed), Nightjar SOC (Geist, Geist Mono), ClaimVoice (Bricolage Grotesque, Figtree), and the registry's planned faces for 6–10 (Atkinson Hyperlegible, Libre Caslon, Public Sans, Commit Mono, Archivo, DM Mono, Overpass, Big Shoulders, Mona Sans, Martian Mono). **Bitter, Source Serif 4 and Spline Sans Mono appear nowhere else, and Tariff Compass is the only slab-voiced product.** (The first version used Schibsted Grotesk; it was dropped as too neutral.)

## 7. Palette (tokens), contrast checked

Light is the default: a search engine is white paper and ink. Dark ("night reading") is a deliberate second theme for brokers on late shifts, not an inverted afterthought.

| Token | Light | Dark | Use |
|---|---|---|---|
| `paper` | `#FFFFFF` | `#131312` | page |
| `paper-2` | `#F4F4EF` | `#1C1C1A` | answer block, why-not panels, tiles |
| `paper-3` | `#EAEAE3` | `#262624` | goods value in the stack, skeletons |
| `ink` | `#111111` | `#EDEDE8` | text, rules, buttons (ink fill, paper text) |
| `ink-2` | `#3A3A36` | `#C9C9C2` | secondary text |
| `muted` | `#62625B` | `#A1A199` | captions, labels |
| `rule` | `#D9D9D0` | `#34342F` | hairlines |
| **`hi`, the highlighter** | **`#FFE14D`** | **`#E8C800`** | marks behind words, the heading digits, the current scope's count, the final path node, focus ring. **Never a button fill.** |
| `hi-soft` | `#FFF3A6` | `#4A4210` | the claim mark when its citation is focused |
| `ok` (Strong match, ✓) | `#1F7A4D` | `#6CCB97` | verdict word, approvals |
| `warn` (Needs a broker, ◇?) | `#8F5207` | `#E8B25C` | verdict word, pending, modified |
| `bad` (conflict / removed, △!) | `#B42318` | `#FF7B72` | redline strike, losses, revoked |
| duty stack | `#111111` base · `#5A5A54` trade remedy (301) · hatched ink emergency duty · `#8C8C83` fees | `#EDEDE8` · `#8E8E86` · hatched · `#727269` | segments, separated by 2 px gaps and always labelled |

Highlighter rendering is theme-aware: in light it is a marker band under the lower third of the glyphs (`--hi-band: 34%`); in dark it is a full-height mark with dark text (`--hi-band: 100%`, `--hi-ink: #131312`), because light text on yellow fails contrast.

**Contrast (WCAG 2.x, computed):**

| Pair | Light | Dark |
|---|---|---|
| ink on paper | 18.9:1 | 15.8:1 |
| ink on paper-2 | 17.1:1 | 14.5:1 |
| ink-2 on paper | 11.4:1 | 11.2:1 |
| muted on paper / paper-2 | 6.1 / 5.6:1 | 7.2 / 6.6:1 |
| ok on paper / paper-2 | 5.3 / 4.8:1 | 9.4 / 8.6:1 |
| warn on paper / paper-2 | 6.2 / 5.6:1 | 9.7 / 8.9:1 |
| bad on paper / paper-2 | 6.6 / 6.0:1 | 7.4 / 6.8:1 |
| ink on highlighter | 14.5:1 | 11.2:1 (`#131312` on `#E8C800`) |
| 301 segment `#5A5A54` vs paper | 6.9:1 | 5.6:1 |

The fee segment (`#8C8C83`, 3.4:1 on white; `#727269`, 3.3:1 on night) is never the only carrier of meaning: every segment has a labelled ledger row with a swatch. Status is never colour alone: every state has an icon shape **and** a word (✓ circle Strong match; diamond-question Needs a broker; triangle-exclamation conflict; filled / half / struck / dashed circles for ruling status).

Accent family: **yellow, hue ≈ 50°**, used only as a highlighter. The registry's other accents: Plotline orange 25° (a fill on CTAs), Kinroot oxblood 350°, Nightjar mint 170° on night, ClaimVoice orchid 330°.

---

## 8. Shape language

- **Surfaces are bands, tables and slips, never cards.** The holding band is full-bleed. Memo rows, docket rows, matrix cells and report sections are separated by hairlines and 1.5 px ink rules. Slips are the receipt (perforated top and bottom edges), inline drawers (6 px highlighter left edge, 1.5 px ink frame), toasts and the sign-off sheet.
- **One left edge.** A 280 px gutter holds the mark, paragraph numbers, section labels and the path spine; the box, every paragraph and every table start at the same x.
- **Radius:** 6 on the box, holding codes, drawers, tables' frames, the sheet; 4 on buttons, chips and toasts; 2–3 on tiles and citation chips; 0 elsewhere.
- **Floating layers (Park-style recipe):** 1.5 px ink rule plus a **hard 4 px ink offset** (`box-shadow: 4px 4px 0 ink`), no blur. Dialogs drop as sheets from the query strip; nothing floats in the middle of the screen.
- **Ink buttons, square-ish:** ink fill with paper text, or ink outline; keyboard hints as small `kbd` caps inside docket buttons.
- **Citation chips:** tiny bordered mono numbers at cap height; open = ink-filled.
- **Pin cells:** 30 × 38 px code cells; changed cells on the highlighter, struck cells with a red line.
- **Ditto marks:** unchanged matrix cells show 〃 in the law face.
- **Path:** a 2 px ink spine with elbows and 14 px open nodes in the gutter; the final node filled with the highlighter.
- **Logo:** the compass (ring, four ticks, a two-part needle with a highlighter-yellow north half) in the gutter and as the "o" of the Bitter wordmark.

## 9. Motion language: "Bearing"

Library: **WAAPI** for most motion (Solid's fine-grained updates make it trivial to start an animation on a signal change), **GSAP 3.13 + Flip** for the two layout morphs (Dock, and the chosen chapter tile flying into the path), CSS transitions for marks.

| Name | What moves | Duration / easing | Meaning | Reduced motion |
|---|---|---|---|---|
| **Seek** | the needle swings −60° ↔ 80° | 1.1 s alternate, `cubic-bezier(.5,0,.5,1)` | "taking a bearing" (loading) | static needle; the line "Taking a bearing…" stays |
| **Narrow** | the 97 dim; candidates outline and name themselves; losers strike; the winner takes the highlighter | 300 ms steps at 0 / 700 / 1350 ms | the whole tariff narrows to one chapter | final state drawn at once |
| **Settle** | needle swings past the bearing and back in shrinking arcs (+38°, −18°, +8°, −3°) | 1300 ms, `cubic-bezier(.25,.6,.3,1)` | Strong match: the answer is still | needle drawn at its bearing |
| **Waver** | needle rocks between two bearings | 1.6 s ease-in-out, three loops then stops | Needs a broker: torn between two headings | needle drawn at the leaning bearing; the dashed underline carries the meaning |
| **Dock** | the box flies from mid-page into the top bar (FLIP) | 460 ms, `cubic-bezier(.2,.8,.2,1)` | the question becomes the page's title | instant swap |
| **Lock** | each code digit drops from −0.5 em with a slight overshoot | 300 ms each, 50 ms stagger, `cubic-bezier(.34,1.4,.64,1)` | a combination lock: the code is set | code appears whole |
| **Mark** | the highlighter sweeps left→right behind words (`background-size`) | 380 ms (claims), 420–520 ms (holdings, ruling passages), `cubic-bezier(.3,0,.2,1)` | "this is the passage that supports it" | marks drawn static |
| **Stack** | duty segments grow from the left one after another; amounts already final | 260 ms each, 140 ms stagger | each charge adds to the same value | bar drawn whole |
| **Redline** | removed digits get a red strike drawn left→right, then new digits are marked | 260 ms strike, 45 ms stagger; marks start at 380 ms | the broker's correction, digit by digit | static strike and mark |
| **Rise** | the holding band and memo rows fade up 8 px in order | 360 ms, 120 ms stagger | reading order | none |
| **Drawer** | an inline citation drawer slides down 6 px and fades in under its paragraph; the chip turns ink | 280 ms, `cubic-bezier(.2,.8,.2,1)` | "here is the authority for this sentence" | appears in place |
| **Unfold** | the docket row's decision record opens to full height; pin cells drop in with Lock's overshoot | 300 ms; cells 45 ms stagger | the broker opens a file | opens in place |
| **Sheet** | the sign-off sheet drops from the query strip | 260 ms | a formal step, below the search, never a pop-up in the middle | appears in place |
| **Slip** | a toast slides up at the bottom left and leaves after 3.2 s | 240 ms in | something was recorded | appears and leaves without motion |

Everything animates `transform`, `opacity` or `background-size` only. `prefers-reduced-motion` and the prototype's `?still` collapse every motion to its final frame; no meaning is carried by motion alone.

---

## 10. Signature interactions

1. **The answer is a ruling.** Facts → Issue → Law and analysis → Holding, the shape brokers read daily. Facts that were *read* or *assumed* are marked ◇ and confirmable in one click; confirming re-runs the answer and is recorded.
2. **Citations open where you read.** A chip opens an inline drawer under its sentence with the holding, the supporting words marked and **your facts against the ruling's** (✓ same · ≈ close · ✗ differs). From there, **Compare side by side** opens the two-pane compare (Splitter) with the fact-alignment table, and **This ruling doesn't apply** files a per-citation correction.
3. **Why not its neighbour.** Each Law-and-analysis step is an accordion item whose gutter carries the path; opening it shows the rule, the quoted text and the struck alternatives with one reason each.
4. **Correct one digit.** In the docket, the broker types the right code into a 10-cell pin input under the proposed digits; changed digits mark themselves, a reason is required, and the record says what the next training round will learn.
5. **Read the record across.** The binder's revision matrix shows every decision as a column; ditto marks make change visible at a glance.
6. **Restack the receipt.** Switching country or origin reprints the receipt line by line; Mexico asks the three USMCA questions first.

## 11. Data visualisation approach

Monochrome first; the highlighter is the only colour that means "look here". Every chart has text values beside it and a table view.

1. **The 97 (landing):** a section-column grid of chapter tiles. A teaching device and the stage for Narrow; on phone it wraps into seven columns per row.
2. **Ruling agreement (answer block):** a segmented bar, one segment per cited ruling: solid = same heading, dashed = cited for contrast, then "5 of 6" in mono. Status counts are words.
3. **Duty stack:** one horizontal bar from $0: goods value as a dashed light block, then each charge as a segment (base solid ink, 301 dark grey, emergency duties **hatched** because their legal status is open, fees light grey), 2 px gaps, scale labels at $0 / goods value / end. The ledger below carries swatch, name, plain reason, source and date, rate and amount; the total is said three ways (dollars, per unit, %).
4. **Accuracy by depth (Lab):** a dot plot on a 0–100 track, four rows, three marks distinguished by **shape** (ring, half, filled) and labelled values; the gain is the highlighter band. No bars-from-zero for comparisons of the same quantity; no dual axes.
5. **Calibration (Lab):** frequency grids of 100 dots ("right 97 times in 100"), with misses as red rings.
6. **By chapter (Lab):** a table with an inline mini bar (round 6 tick → round 7 end; gain on the highlighter, loss as a red outline), signed change with ▲/▼, and a "moving" tag for drift.
7. **Code redline:** digits as the visual unit.

Libraries: none needed; hand-built SVG/CSS from data in Solid components. If scales are needed, `d3-scale` only.

---

## 12. How this differs

| Dimension | Necessa | Plotline | Kinroot | Nightjar SOC | ClaimVoice | **Tariff Compass** |
|---|---|---|---|---|---|---|
| Metaphor | Clinical worklist | Field atlas, surveyor's ledger | Investigation board, red string | Night watch, baton, regulator clocks | "On the line": a call with two voices | **A search engine whose answers are written like customs rulings**; the compass takes a bearing |
| Component system | own Tailwind components | own components | shadcn/ui (React, moving to) | Skeleton (Svelte) | Nuxt UI (Vue) | **Ark UI (Solid) + Park UI-style tailwind-variants recipes** |
| App shell / nav | Left sidebar with org card | Masthead mono caps tabs over a full-bleed map | Ink icon spine + graph board + dossier drawer | ⌘K tiled console + clock bar | Floating pill dock | **Query strip**: mark in a 280 px gutter, the box, scopes printed on the strip's edge; no sidebar, dock, rail, palette or drawer |
| Page skeleton | sidebar + content + cards | map + floating ledger + inspector | canvas + right drawer | tiles | split transcript ↔ claim file | **Gutter + measure**: full-bleed holding band, then numbered memo rows; the docket, matrix and compare are full-width tables; **no right column on any page** |
| Landing archetype | Headline left, card right | Scroll story under a huge serif date | Type into the client pin | Console replay of a night | Mirrored waveform you play | **A search engine's front page** with the 97 chapters; Classify narrows them and the page turns into the ruling-shaped answer in place |
| Primary data idiom | Cards | Map + ledger | Graph canvas | Logs and tiles | Waveform + transcript | **Memo paragraphs with inline citation drawers, a receipt, a docket table, a revision matrix with ditto marks** |
| Type | System sans | Newsreader / Fraunces + IBM Plex Mono | Spectral + Hanken Grotesk + Red Hat Mono | Geist + Geist Mono | Bricolage Grotesque + Figtree | **Bitter (slab voice) + Source Serif 4 (quoted law) + Spline Sans Mono (codes)** |
| Palette / theme | Grey + indigo | Map paper + slate + orange | Bond grey + oxblood | Night + mint, dark-first | Porcelain + aubergine + orchid | **Pure white + true ink + highlighter yellow as a mark only**; warm-black night reading |
| Floating layers | soft shadow cards and modals | paper sheets | drawer | palette and tiles | sheets in pills | **Hard 4 px ink offset slips; dialogs as sheets dropping from the query strip; drawers inline** |
| Motion | 150 ms fades | Self-drawing outlines, fly-to | Unfold, string pull | Ticks, baton, hold | Breathe, settle, pluck, hush | **Bearing**: seek, narrow, settle/waver, dock, lock, mark, stack, redline, drawer, unfold, sheet, slip |
| Signature interactions | Live check progress | Time ruler scrub | Pull the thread | Replay, hold to authorise | Take over, hush | **Answer as a ruling · citations open in place with a fact compare · two-pane compare · correct one digit · read the record across · restack the receipt** |
| CTA wording | Explore the demo / Create an account | Open the Northbank atlas | Trace a client | Take the watch | Play the call | **Classify / Broker sign-in** |

**Comparison verdict (from `shots/99-side-by-side.png`, re-shot after the evolution):** Tariff Compass is not a sibling. The landing is still the only centred, white, single-box page in the set. The app screens no longer share the portfolio skeleton:
- The results page opens on a full-bleed grey holding band with two large mono codes, then left-gutter memo rows.
- The review screen is a full-width docket table with an unfolded three-band record and yellow pin cells.
- No right column appears anywhere.

The slab voice separates it from every grotesque- or serif-voiced sibling at a glance. Remaining risk: the white, rule-based look depends on the highlighter, the mono codes and the gutter discipline. The implementation must keep the gutter alignment and must not add cards.

### Changes from the §Harmon hypothesis
1. **Renamed** to Tariff Compass, and the metaphor sharpened into "take a bearing": a heading in customs and a heading on a compass. The compass becomes the logo, the "o" of the wordmark, the loading state (**Seek**) and the confidence signal (**Settle** vs **Waver**).
2. **The answer block spans the page.** The original had the citation rail beside everything; that left a dead margin next to the codes. Now codes, verdict and a ruling-agreement bar form a full-width headline, and the reading column with **aligned margin notes** starts below (He & Liu 2026).
3. **The 97** replaces the funnel band: chapters hang under the box in their 21 section columns, so Narrow teaches the tariff's shape. The chosen tile flies into the path (Flip).
4. **Needs a broker** got its own design: dashed underline instead of the highlighter, "leaning" labels, "Also possible", the duty at stake, and **the fact that decides it**. No percentages anywhere (Zonos's own docs say their score isn't a probability).
5. **Landed cost** became a receipt: a monochrome stack with **hatched emergency duties** (legally open on the demo date), every row with source and effective date, the rows that don't apply, origin restack and the USMCA questions; plus a margin note with "what could change this total".
6. **Broker review** is a results list whose selected result expands in place, with a digit **Redline**, a required reason, always-review rules and "what the next round will learn".
7. **Binder** is a section-numbered memorandum with a version history and a record fingerprint; **Watch** is a news vertical with "What we know / What we don't"; **Lab** reports in frequencies with two sign-offs.
8. **Sign-in is a search**: one question at a time in the same box.
9. Palette and tokens kept, with two corrections: a theme-aware highlighter (full-height mark with dark text in dark mode, for contrast) and a duty-stack ramp that passes 3:1 for the 301 segment.

---

## 13. Implementation notes (SolidStart + Ark UI + Tailwind 4.1)

**Pins, verified on Node 21.7.1:** a test app type-checks (`tsc --noEmit`), builds (`vinxi build`), serves (`node .output/server/index.mjs`, HTTP 200) and server-renders 12 Ark components.

| Package | Version | Note |
|---|---|---|
| `@solidjs/start` | **1.5.1** | 2.x needs Node ≥ 24 and Vite 8/9: do not use |
| `@solidjs/router` | **0.15.4** | 1.x pairs with Start 2 |
| `solid-js` | 1.9.19 | |
| `vinxi` | 0.5.11 | resolves Vite 6.4.6 |
| `@ark-ui/solid` | **5.40.0** | peer `solid-js >= 1.6`; per-component imports (`@ark-ui/solid/accordion`) |
| `tailwind-variants` | 4.0.2 | Park UI-style slot recipes |
| `@tanstack/solid-table` | 8.21.3 | docket, chapter table |
| `tailwindcss` / `@tailwindcss/vite` | 4.1.18 | peer Vite ^5.2 \|\| ^6 \|\| ^7 |
| `@fontsource-variable/bitter`, `/source-serif-4`, `/spline-sans-mono` | 5.3.0 / 5.3.1 / 5.3.0 | self-hosted, works offline |
| `gsap` | 3.13.0 | only Dock and the chapter-tile morph (Flip), lazy-loaded |

Expected `npm` warnings on Node 21 (harmless, the build passes): EBADENGINE for vite 6.4.6, nitropack 2.13.6, rollup-plugin-visualizer 7.1.3, and vite 8.3.8 (pulled only by `@tanstack/directive-functions-plugin` inside Start; unused by the build). Config: `app.config.ts` = `defineConfig({ vite: { plugins: [tailwindcss()] } })`. Portal-based parts use `Portal` from `solid-js/web`.

**Component map: every interactive part is an Ark UI component styled by a recipe in `src/ui/recipes/*.ts`:**

| Need | Ark UI component | Where | Recipe notes |
|---|---|---|---|
| The search box with suggestions (products, rulings, chapters as you type) | **Combobox** | query strip, front page | box recipe: 1.5 px ink, radius 6; listbox as a slip with hard offset; highlighter on the matched text via **Highlight** |
| Into / From pickers in the box | **Select** | box | compact `pick` recipe |
| Scopes (Answer · Rulings · …) | **Tabs** (as links, `activationMode="manual"`) | query strip | underline indicator in the highlighter |
| Classification path | **Accordion** (`multiple`, `collapsible`) | ¶3 | item = gutter spine + trigger + panel |
| Inline citation drawer | **Collapsible** (one per chip) | ¶0, ¶3 | inline, highlighter left edge, never portalled |
| Citation peek on hover/focus | **HoverCard** | all chips | slip with hard offset; phone: **Dialog** as a bottom sheet |
| GRI chip explanations, keyboard hints | **Tooltip** | path, docket | ink fill, paper text |
| Facts confirmation, deciding question | **RadioGroup** / buttons | ¶1 | |
| Country and origin switches | **SegmentGroup** | ¶4 | ink segmented recipe |
| USMCA questions | **Checkbox** ×3 | ¶4 | |
| Copy codes | **Clipboard** | holding band | |
| Money and percentages | **Format.Number** | receipt, docket | `currency`, `percent` |
| Docket and chapter tables | **TanStack Table** + Ark **Checkbox** (row select), **Menu** (column/sort menu), **Pagination** | review, lab | table recipe: ink header rule, hairline rows, sticky header |
| Docket filters | **ToggleGroup** | review | chip recipe |
| Code correction | **PinInput** (`count=10`, numeric, `otp=false`) | decision record | cells with dots between groups; changed cells marked |
| Correction reason | **RadioGroup** + **Field**/**Textarea** (required) | decision record | |
| Two-pane compare | **Splitter** | ruling | drag and arrow-key resize; 25–75 % bounds |
| Tariff text scope (browse the schedule) | **TreeView** | Tariff text | indented outline with the same spine as ¶3 |
| Account menu, row actions | **Menu** | strip, docket | slip with hard offset |
| Sign-off confirmation, delete/export confirmations | **Dialog** | lab, binder | **sheet** recipe: drops from the query strip, not centred |
| Saved / corrected / exported notices | **Toast** (`createToaster`, `placement: "bottom-start"`) | everywhere | mono slip |
| Spec sheet / photo upload in the box | **FileUpload** | front page, answer | drop zone inside the box |
| Date range on Watch and Activity | **DatePicker** | watch, settings | |
| Long panes on phone | **ScrollArea** | compare, matrix | |
| Theme toggle, settings toggles | **Switch** | strip, settings | |
| Training rounds strip | **Steps** (read-only) | lab | candidate step on the highlighter |

**`@theme` tokens (`src/styles/app.css`):**

```css
@import "tailwindcss";
@import "@fontsource-variable/bitter";
@import "@fontsource-variable/source-serif-4";
@import "@fontsource-variable/spline-sans-mono";
@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));
@theme {
  --font-voice: "Bitter Variable", ui-serif, Georgia, serif;
  --font-law: "Source Serif 4 Variable", ui-serif, Georgia, serif;
  --font-code: "Spline Sans Mono Variable", ui-monospace, monospace;
  --color-paper: #FFFFFF;  --color-paper-2: #F4F4EF; --color-paper-3: #EAEAE3;
  --color-ink: #111111;    --color-ink-2: #3A3A36;   --color-muted: #62625B;
  --color-rule: #D9D9D0;   --color-hi: #FFE14D;      --color-hi-soft: #FFF3A6;
  --color-ok: #1F7A4D;     --color-warn: #8F5207;    --color-bad: #B42318;
  --color-seg-301: #5A5A54; --color-seg-fee: #8C8C83;
  --radius-box: 6px; --radius-btn: 4px; --radius-chip: 3px;
  --shadow-hard: 4px 4px 0 var(--color-ink);
  --spacing-gutter: 280px; --spacing-measure: 820px;
  --ease-dock: cubic-bezier(.2,.8,.2,1); --ease-mark: cubic-bezier(.3,0,.2,1); --ease-lock: cubic-bezier(.34,1.4,.64,1);
}
[data-theme=dark] {
  --color-paper: #131312; --color-paper-2: #1C1C1A; --color-paper-3: #262624;
  --color-ink: #EDEDE8; --color-ink-2: #C9C9C2; --color-muted: #A1A199; --color-rule: #34342F;
  --color-hi: #E8C800; --color-hi-soft: #4A4210; --color-ok: #6CCB97; --color-warn: #E8B25C; --color-bad: #FF7B72;
  --color-seg-301: #8E8E86; --color-seg-fee: #727269;
}
```

**Recipe example** (Park-style slots in tailwind-variants; Ark exposes `data-scope`/`data-part`/`data-state`, so recipes style states without extra JS):

```ts
export const drawer = tv({ slots: {
  root: "my-3 rounded-r-[--radius-box] border-[1.5px] border-ink border-l-[6px] border-l-hi bg-paper data-[state=open]:animate-[drawer_280ms_var(--ease-dock)]",
  head: "flex flex-wrap items-baseline gap-2.5 border-b border-rule px-3.5 py-2.5",
  body: "grid grid-cols-[1.2fr_1fr] max-md:grid-cols-1",
}});
export const floating = tv({ base: "rounded-[--radius-box] border-[1.5px] border-ink bg-paper shadow-[--shadow-hard]" }); // HoverCard, Menu, Combobox list, Toast
```

**Solid components** (prototype equivalents in `tc.js` / `tc.css`): `QueryStrip`, `Scopes`, `FrontPage`, `Wordmark`, `CompassMark` (`bearing`, `state: still|seek|settle|waver`), `The97`; answer: `HoldingBand`, `CodeCard`, `CodeDigits` (`unsettled`, `lock`), `Verdict`, `RulingAgreementBar`, `Memo`, `MemoRow` (gutter label + body), `InShort`, `FactsList` (source per fact, confirm box), `IssueLine`, `AnalysisAccordion` (gutter spine), `NotNeighbour`, `CitationChip`, `CitationDrawer` (with `FactCompareMini`), `CitationPeek`, `Receipt`, `ReceiptReasons`, `StackBar`, `UsmcaQuestions`, `CostRange`, `AuthoritiesCited`; ruling: `CompareHeader`, `FactAlignment`, `ComparePanes`; review: `Docket`, `DocketRow`, `DecisionRecord`, `CodePins`, `ReasonPicker`, `WhatItWillLearn`; binder: `BinderHeader`, `RevisionMatrix`, `BinderFoot`; watch: `Bulletin`, `KnowsPair`, `AffectedTable`; lab: `RoundsStrip`, `ReportSection`, `DepthPlot`, `FrequencyGrid`, `ChapterTable`, `SignOffForm`, `SignSheet`; platform: `SignInBox` (stepped), `Settings`, `ActivityLog`, `EmptyState`, `ErrorSlip`, `Skeleton`.

**Data contracts the UI needs from the API:** an answer carries `us{code,text}`, `ca{code,text}`, `verdict{word,sentence}`, `alt?`, `holdingSentence`, `facts[{label,value,source: stated|read|assumed|unknown,decides?}]`, `issue`, `reason[{text,cites[]}]`, `path[{level,code,text,gri,why,cites[],notNeighbours[{code,text,reason,cite?}],countryNote?}]`, `rulings[{n,id,date,status{kind,text,byId?,date?},holding,markedSpans[],match[],factCompare[{fact,yours,theirs,match}]}]`, `tariffAuthorities[{ref,quote}]`; landed cost carries `value`, `currency`, `layers[{kind,name,rate,amount,plain,source,chapter99?,effectiveFrom,effectiveTo?,legalStatus?}]`, `notApplied[{name,why}]`. **Every duty row carries an effective date and a source; the UI refuses to render a row without them.**

**Motion:** `useMotion()` reads `prefers-reduced-motion` (via `@solid-primitives/media`) and the user setting; WAAPI for Lock, Rise, Stack, Redline, Mark, Drawer, Unfold, Sheet, Slip and the needle; GSAP Flip only for Dock and the chapter-tile morph.

**Copy guard:** the forbidden-word scan from STANDARDS §4, plus `DSPy`, `GEPA`, `TF-IDF`, `score`, `model`. Use "the classifier", "word matching", "training round", "rulings it hasn't seen".

**Dates:** every displayed date comes from the clock helper (`TARIFF_COMPASS_DEMO_TODAY`, default 2026-02-19); "tariffs as of" uses the data snapshot date.

## 14. As built

The web app follows sections 0–13. Where the build had to choose, this section records the choice.

**Routes** (`src/routes`): `/` front page (the 97, Narrow, Dock into the sample answer), `/signin` (stepped: email → password → organisation, plus the sample organisation's four people), `/home`, `/answer?q=…|id=…`, `/rulings`, `/rulings/[key]` (the letter; with `?answerId=` the two-pane compare), `/tariff`, `/products`, `/products/[sku]` (binder), `/review` (`/review/[id]` opens the docket at that row), `/watch`, `/lab`, `/lab/rounds/[n]`, `/settings`, `/activity`, and a not-found page. The app renders in the browser (`ssr: false`): every screen depends on the signed-in session and the server's demo clock.

**Ark UI parts in use:** Accordion (law and analysis), Collapsible (inline citation drawers, never portalled), HoverCard (citation peek), Tooltip (GRI explanations), Combobox (the box, with past questions), Select (Into, From, roles), FileUpload (spec sheet or photo in the box), Tabs (scopes as links), SegmentGroup (Into / Made in, schedule), Popover (the shipment), Checkbox (USMCA questions, "also change Canada"), RadioGroup (correction reason), PinInput (the 10-digit correction), ToggleGroup (docket, rulings, products and watch filters), Splitter (compare), Dialog (every sheet: send for review, ask the importer, invite, remove, sign-off), Menu (the person), Toast (slips at bottom left), Clipboard (copy a code), Pagination, Progress (binder export, watch check, training round), Steps (the rounds strip), Switch (settings, rules) and TreeView (the tariff outline). Tables (docket, products, chapters) use TanStack Table. Recipes live in `src/ui/recipes.ts`.

**Motion:** Narrow, Settle, Waver and Seek are CSS keyframes on the compass; Lock, Rise and Drawer are WAAPI or CSS animations; GSAP Flip is loaded only for Dock. `prefers-reduced-motion` collapses all of it to the final frame.

**Data rules kept in the UI:** a duty line without a source or an effective date is not rendered (and the page says one was left out); no percentage appears for confidence; ruling numbers come only from the API; dates come from the server's `X-Tariff-Compass-Now`, never the browser clock; RFC 7807 problems are shown in plain words with the request reference.

**Mock mode:** `npm run dev:mock` (or `VITE_TC_MOCK=1`) answers the same `/api/v1` paths in the browser from fixtures that follow the contract (`src/lib/mock`). The fixtures use the verified sample values: the tumbler's US stack is 7.2% + 10% + 10% = $3,400.00 plus MPF $43.30 and HMF $15.63 = $3,458.93 (no Section 301 line: 9617.00.10 is on List 4B, which is suspended), Canada's MFN is 7.5%, and the rulings cited are NY N321134, HQ H303684 and NY N297165.

**Lab governance as built:** a training round is "in use" only after it passes all five checks and two different people sign it. The Lab opens with an **In use** band (`LabOut.inUse`: word matching, or the signed round) above the rounds strip; every other round is a challenger, measured against what is in use (a loss is outlined in red, a gain sits on the highlighter), and the sign-off button appears only when the API says the viewer can sign.

**Role gating as built:** every page waits for the session and asks only for what the role may see, so no screen sends a request its role would be refused; the receipt prints `effectiveRate` as "Duties alone · +27.2% of value" (duties over the customs value, fees and taxes excluded).
