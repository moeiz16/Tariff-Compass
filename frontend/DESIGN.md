# Tariff Compass frontend design, v3: "The answer first"

> v3 replaces the typewriter design (Courier Prime capitals, "RE:" captions, typed `====` rules, pages shaped like CBP ruling letters). Earlier versions are in the git history. Screens are taken with the demo clock at **Thu 19 Feb 2026 10:30 America/Vancouver**.

Tariff Compass answers one question an importer has to get right on every entry: **what is this product, legally?** You describe a product and get its US (HTSUS) and Canadian (Customs Tariff) ten-digit codes, the customs rulings behind them, every duty it will carry, and a licensed broker's sign-off. Every product keeps a binder, its reasonable-care record.

- **Seed importer:** Northbound Goods Co. (Maya Lindqvist, compliance · Jordan Tse, importer · Priscilla Mensah, admin). **Seed broker:** Driftwood Customs Brokers (Dana Whitlock, US · Rafael Ouellet, Canada).
- **Demo moment:** Thursday 19 February 2026, 10:30 a.m. Pacific. *Learning Resources v. Trump* was argued and not yet decided, so IEEPA duties show as charged with their legal status open. The UI never presumes an outcome.
- **Stack:** SolidStart 1.5 + Ark UI 5.40 (re-themed recipes in `tailwind-variants`) + Tailwind 4.1.

---

## 1. Why v3 (analysis of v2)

The owner's verdict on v2: "funky", dense, and a first-time viewer thinks "what is this?". Looking at the v2 shots side by side with Vortex AI v2 and Necessa's landing, the causes are concrete:

| v2 trait | What it did to a first-time viewer |
|---|---|
| Courier Prime capitals with underlines and colons ("HOLDING:", "FACTS:"), "RE:" captions, `====` rules | Read as a costume, not a product. Every heading shouted at the same volume, so nothing led. |
| The answer as a ruling letter: holding band, then ¶0–¶5 all open at once | About 40 lines of text before the first scroll. The code competed with a paragraph number, a gutter label, a law quote, a verdict essay, an agreement bar and a holding sentence. |
| A 280 px gutter of margin notes on every page | Half of the first glance was spent on labels about the content, not the content. |
| The front page's 97-chapter grid and four story sections | Decoration that had to be read to be understood. |
| Same facts said twice (code in the band, again in the holding sentence, again in the path) | Doubt: "is this a different code?" |
| Hard 4 px offset shadows, ink frames, perforated receipt | Loud surfaces around quiet information. |

What the calm references do instead (Vortex v2 shots, Necessa's landing): one title, one primary object, a short line of context, then a list you can open. Everything else waits.

**What we keep, because it is Tariff Compass's own:** the compass mark (it still settles for a strong match and wavers when a broker is needed); the yellow highlighter, now restrained to one job; the code as the hero; Ark UI; the search box as the way in; "no code without its reason, no reason without its ruling, no duty without its source and date". **Every feature and data flow stays.**

## 2. Rules for every screen

1. **One title per screen.** Sentence case, no capitals, no underline, no colon. No stacked headings: a section inside a page is a 13 px label or a tab, never a second heading.
2. **Layers, not pages of text.** Layer 1 answers "what is it?" in one glance. Layer 2 is a list of rows or tabs, each with a 1–3 word label and a one-value summary. Layer 3 opens in place (an accordion row) or in a drawer. Layer 4 is a full page (a ruling, a binder).
3. **Labels are 1–3 words.** Sentences live in hover cards, drawers and detail views. No explanatory paragraphs on the surface.
4. **Say each fact once.** If the code is in the answer card, the path doesn't repeat it as a heading; the path names its levels.
5. **Status is never colour alone:** a dot or icon plus a word.
6. **Calm surfaces:** white cards on a warm off-white page, 1 px hairlines, a soft shadow only on floating layers, 10 px radius. No ink frames, no offset shadows, no rules made of characters.

## 3. Concept

**"The answer first."** Tariff Compass is a quiet classification desk. You ask, and the first thing you see is the answer: two ten-digit codes, one word for how sure it is, and one line of why. The reasoning, the rulings, the duties and the law are there, folded, one click away. Brokers see a queue and decide in a drawer. Compliance sees a binder that opens on the current code with its history behind it.

The compass stays as the mark and the loading state: the needle seeks while it reads, settles on a strong match, wavers when a broker is needed.

## 4. Information architecture

**Shell:** one 60 px top bar on a white surface with a hairline. Left: the compass and "Tariff Compass". Centre: six links, each 1 word: **Classify · Review · Products · Library · Watch · Lab** (role-gated; Review shows its waiting count as a small badge). Right: theme switch and the person (Ark Menu: Settings, Activity, Switch organisation, Sign out). On phones the links move into a menu button. No sidebar, no second row.

**Library** groups the two research scopes, Rulings and Tariff text, as a segmented switch on one page header. The old "scope" tabs are gone from the shell.

| Route | Title | Layer 1 (first glance) | Layer 2 (rows / tabs) | Layer 3+ (opens) |
|---|---|---|---|---|
| `/` public | "The right tariff code, with the rulings behind it." | the box, three sample chips, and the tumbler's answer card below as a live preview | three feature tiles, 3 words + one line each | the sample's layers open like the real answer |
| `/signin` | "Sign in" | one field at a time (email → password → organisation) | "Try as" demo people | — |
| `/home` | "What are you importing?" | the box | tabs: **Recent · Changes** (5 rows each) | the answer, the Watch item |
| `/answer` | the question (one line, truncates) | **answer card**: verdict badge, US and Canada codes, one-line reason, actions. Needs a broker adds the one question that decides it | accordion rows with a summary value: **Why this code · Rulings · Landed cost · Facts · Law text** | path steps open in place; a ruling opens in the **ruling drawer** (holding, your facts vs the ruling's, compare, flag) |
| `/library` → `/rulings` | "Library" | search box + Rulings / Tariff text switch + filter chips | result rows: number, status, one-line subject | `/rulings/[key]` |
| `/rulings/[key]` | the ruling number | status, date, subject, the holding quoted with marked words | tabs: **Holding · Letter · Compare** (Compare when opened from an answer: fact table, then side by side in a Splitter) | — |
| `/tariff` | "Library" (Tariff text selected) | the outline (Ark TreeView) | a line's text and rates open in place | — |
| `/products` | "Products" | search + standing filter + table: product, US code, standing, updated | — | the binder |
| `/products/[sku]` | the product name | standing badge, current US and Canada codes, "Approved · v4 · 17 Feb", export menu | tabs: **History · Evidence · Entries · Record** | each history version opens to show only what changed |
| `/review` | "Review" | filter chips + queue table: product, proposed code, reason badge, waiting | — | **decision drawer**: facts (listing and spec quoted, deciding words marked), your code (10-cell pin input), reason, what the next round learns; Approve · Ask · Save correction; J/K/A/C/Q |
| `/watch` | "Watch" | list: date, kind badge, headline, "64 products" | each item opens: what we know / don't, affected products | — |
| `/lab` | "Lab" | **In use** card: the round in use and three accuracy numbers | tabs: **Accuracy · Confidence · Chapters · Rounds** + the sign-off card when a round is waiting | `/lab/rounds/[n]` |
| `/settings` | "Settings" | vertical tabs: **Defaults · People · Broker · Records** | one panel at a time | invite / remove sheets |
| `/activity` | "Activity" | chain-verified badge + the event table | a row's fingerprint on hover | — |

## 5. Screens in detail

### 5.1 The answer (`/answer`, and the landing's preview)
- **Question line** (the page title): the question in one line at 22 px, with "Into US + Canada · From China" as small chips; **Edit** reveals the box in place. A new question is asked from the box, which also sits in the Classify page when there is no answer.
- **Answer card** (white, radius 12, 28 px padding):
  - Row 1: the verdict badge (● Strong match in green, ◇ Needs a broker in amber; hover lists the word at each depth and the verdict sentence) and the compass (24 px, settles or wavers). Right: the date.
  - Row 2: two code columns, "United States" and "Canada", each a label (13 px) and the code in Reddit Mono 36 px. The four heading digits are ink on a soft highlighter band; the rest are ink-2. A leaning code drops the highlighter and gets a dashed amber underline. A copy button appears on hover/focus.
  - Row 3: the one-line reason (strong: the first reason sentence with its citation numbers; needs a broker: the verdict sentence), 17 px.
  - Needs a broker only: **"Also possible"** one line, and the **deciding question** as a soft amber panel with its answer buttons and "Not sure: send to Driftwood".
  - Row 4: actions. **Save to binder** (ink), **Send to Driftwood** (outline), or for a broker **Open in Review**.
- **Layers** (Ark Accordion, multiple, all closed on arrival; each row: label, summary on the right, chevron):
  - **Why this code** · "5 steps": the remaining reason sentences, then the path as a vertical list (level label, code, the heading text on one line, GRI badge with its rule on hover). A step opens to its reasoning, the neighbours set aside (struck code + one reason) and the Canada note.
  - **Rulings** · "2 of 3 agree": one row per cited ruling (number, ruling id, status, subject). A row opens the **ruling drawer**.
  - **Landed cost** · "$3,458.93 · US": Into and Made in switches, the shipment ("2,000 units · $6.25 · ocean", Change), one stacked bar, then the charge lines (name, rate, amount). A line's source, Chapter 99 number, effective date and legal status sit behind an info hover. Total, landed and per unit as three figures. Charges that don't apply sit behind "3 don't apply". USMCA questions appear only for Mexico. "What could change" is one muted line.
  - **Facts** · "1 assumed": label, value, a source badge (Stated · Read · Assumed · Not stated). The deciding fact carries a "Decides it" badge.
  - **Law text** · "4 texts": the tariff texts and rules relied on, quoted.
- **Ruling drawer** (Ark Dialog as a right-hand panel, 520 px; full-screen sheet on phones): ruling number, date, status; the holding with the supporting words on the highlighter; "Your facts vs the ruling's" as a compact table; **Compare side by side**, **Read the ruling**, **Doesn't apply** (broker only, asks for a reason).
- **Loading:** the card frame with the compass seeking and "Reading the tariff…"; skeleton codes. **Error:** a calm panel with the problem in plain words, Try again, and the request reference.
- Footer line (muted, once): the tariff snapshot and "A licensed broker approves every code before it is used."

### 5.2 Landing (`/`)
Top bar: mark + name, theme, **Sign in**. Hero: title at 52 px (two lines max), one 18 px line under it, the box (Classify), three sample chips. Directly below, the tumbler's answer card (live from the public sample), labelled "Sample answer"; choosing another sample replaces it, and its layers open like the real thing. Below the fold, three tiles (icon, 2–3 word title, one line): **Cited rulings · Every duty · Broker sign-off**. Footer: the compliance line once, small.

### 5.3 Review (`/review`)
Title "Review" with the waiting count. Chips: All · Unsure · Differs · Ruling changed · Always · Canada (each with a count). Table: Product (title, SKU muted) · Proposed (code) · Why (badge) · Waiting. Selecting a row opens the **decision drawer** (640 px):
- head: product, SKU, into, value; the reason badge and its one-line detail;
- **Facts**: the listing and the spec sheet quoted, deciding phrases on the highlighter; questions asked and answered;
- **Your code**: the proposed code with the 10-cell pin input beneath; changed digits marked, the struck heading text and the new one, "Also change Canada", rulings relied on;
- **Reason**: three choices and a required sentence; "Next round learns" in a soft panel;
- sticky footer: Approve (A) · Ask (Q) · Save correction (C).
Importers see the same drawer read-only, and can answer a broker's question there.

### 5.4 Binder (`/products/[sku]`)
Header card: product title (the page title), SKU and category muted, standing badge, the current US and Canada codes, "Approved · v4 · 17 Feb", and an **Export** menu (PDF · Everything as ZIP, with progress). Tabs:
- **History**: a vertical timeline, newest first. Each version: kind ("Re-approved"), date, who, and the one-line why. Opening it shows only the fields that changed, before → after. This replaces the revision matrix and keeps the same data.
- **Evidence**: files with who and when. **Entries**: entry number, date, code, duty paid. **Record**: chain verified, fingerprint, kept until, the retention reason and the CBSA advance-ruling note.

### 5.5 Ruling (`/rulings/[key]`)
Title: the ruling number. Status badge, date, subject in one line. Tabs: **Holding** (quoted, marked) · **Letter** (the full text) · **Compare** (shown when opened from an answer; first tab then): the fact table (Fact · Yours · The ruling's · Match), and **Side by side** opens the Ark Splitter with your evidence and the letter.

### 5.6 Watch, Lab, Settings, Activity, Products, Library, Sign-in, Not found
Each follows §4: one title, one primary list or card, detail behind a row, a tab or a drawer. The Lab keeps every measured number and the two-person sign-off; it only reorders them so the round in use and three numbers come first.

## 6. Type

| Role | Face | Package (pinned) | Use |
|---|---|---|---|
| Headings and UI | **Plus Jakarta Sans** (variable 200–800) | `@fontsource-variable/plus-jakarta-sans` 5.2.8 | everything that is words |
| Codes and amounts | **Reddit Mono** (variable 200–900) | `@fontsource-variable/reddit-mono` 5.2.8 | tariff codes, ruling numbers, rates, money, fingerprints |

Courier Prime and Instrument Sans are retired (recorded in `~/Work/_playbook/TYPE_REGISTRY.md`). **Heading style: calm product sans, sentence case, weight 600, −0.02 em, one per screen.** The code is the headline of the answer, set in mono.

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `--text-display` | clamp(36px, 4.4vw, 52px) / 1.08 | 600, −0.03em | landing title only |
| `--text-title` | 26px / 1.25 (22 on phones) | 600, −0.02em | the one page title |
| `--text-code-xl` | clamp(28px, 2.6vw, 36px) / 1 | mono 500 | answer codes |
| `--text-lead` | 17px / 1.55 | 450 | the one-line reason |
| `--text-body` | 15px / 1.55 | 400 | rows, drawers |
| `--text-label` | 13px / 1.4 | 550, ink-2 | field and group labels |
| `--text-small` | 12.5px / 1.4 | 450, muted | meta |

## 7. Palette

| Token | Light | Dark | Use |
|---|---|---|---|
| `paper` (page) | `#F7F7F5` | `#0E0E10` | page background |
| `card` | `#FFFFFF` | `#17171A` | cards, bars, drawers |
| `paper-2` | `#F1F1EE` | `#1E1E22` | hover, table heads, quiet fills |
| `paper-3` | `#E7E7E3` | `#2A2A2F` | skeletons, the goods-value bar |
| `ink` | `#18181B` | `#EDEDEF` | text, primary buttons |
| `ink-2` | `#44444C` | `#C4C4CA` | secondary text |
| `muted` | `#6B6B74` | `#93939C` | labels, meta |
| `rule` | `#E4E4E0` | `#2B2B30` | hairlines and borders |
| `hi` (highlighter) | `#FBE27A` | `#D9BE45` | heading digits band, marked passages only |
| `hi-soft` | `#FDF3C4` | `#3A3216` | changed cells, current version |
| `ok` | `#17784E` | `#5CC994` | Strong match, approved |
| `warn` | `#9A5A06` | `#E2AE5A` | Needs a broker, assumed, pending |
| `bad` | `#B8322A` | `#F2766C` | differs, revoked, errors |

The highlighter is the only accent and is never a button or a background area. Focus is a 2 px ink ring with a 2 px offset (`ink` flips in dark). Contrast: ink on card 17.4:1 (dark 15.6:1); muted on card 5.3:1 (dark 6.3:1); ok/warn/bad on card ≥ 4.9:1 in both themes; ink on hi 14.2:1. Duty-bar segments stay monochrome (ink, ink-2 70 %, hatched for legally open, muted for fees), always with a labelled row.

## 8. Components (Ark UI, re-themed)

Recipes in `src/ui/recipes.ts`: `button` (ink · outline · ghost · danger; 8 px radius; 36/40/44 px), `card`, `badge` (pill, dot + word), `chip` (filter toggle), `field`, `table`, `tabs` (underline in ink), `segment`, `drawer` (right panel), `sheet` (centred dialog), `floating` (popover, menu, hover card: card + soft shadow), `accordionRow`.

Ark parts in use: Accordion (answer layers, path steps, Watch items, binder history), Dialog (ruling drawer, decision drawer, sheets), HoverCard (verdict detail, duty line source), Tooltip (GRI rules, keyboard hints), Combobox (the box), Select (Into, From, roles), FileUpload (spec or photo), Tabs (home, binder, ruling, lab, settings), SegmentGroup (Library switch, Into / Made in), Popover (shipment), Checkbox (USMCA, "also change Canada"), RadioGroup (correction reason), PinInput (10-digit correction), ToggleGroup (filters), Splitter (side by side), Menu (person, export, phone nav), Toast (bottom right), Clipboard (copy code), Pagination, Progress (exports, jobs), Steps (training rounds), Switch (settings), TreeView (tariff outline).

## 9. Motion

Quiet and short: fades and 4–8 px rises at 160–220 ms (`cubic-bezier(.2,.8,.2,1)`), accordion height at 200 ms, drawers slide 16 px in at 220 ms, toasts fade up. The compass keeps three moves: **seek** (loading), **settle** (strong match, 1.1 s, once), **waver** (needs a broker, three loops). The highlighter band sweeps once under the heading digits when an answer arrives. `prefers-reduced-motion` shows final frames.

## 10. Copy

Second person to importers, colleague-to-colleague to brokers. No jargon on the surface: "the classifier", "word matching", "training round", "rulings it hasn't seen". Forbidden words from STANDARDS §4 still apply. No percentages for confidence on an answer. Dates come from the server's demo clock.

## 11. What did not change (data rules)

- A duty line without a source or effective date is not rendered, and the layer says one was left out.
- Ruling numbers come only from the API; statuses (in force, modified, revoked, cited for contrast) are always shown.
- Every page asks only for what its role may see. The Lab offers a sign-off only when the API says the viewer can sign, and a round goes live only after five checks and two different signatures.
- Mock mode (`npm run dev:mock`) serves the same contract from fixtures.

## 12. How this differs from the rest of the portfolio

Calm is shared with Vortex v2 by the owner's choice; identity is not. Vortex is a left-sidebar workflow tool in Inter with a neutral zinc palette and a blue focus. Tariff Compass is a **top-bar desk** whose screens open on **one answer object** (an answer card, a binder card, an in-use card), set in **Plus Jakarta Sans with Reddit Mono codes**, on a **warm off-white page with a yellow highlighter** used only to mark heading digits and quoted passages, with the **compass** as the mark and the loading state.

## 13. References used for v3

- Vortex AI v2 shots (`~/Work/_playbook/design/vortex-ai/shots-v2/`): one title, one object, rows that open, detail in drawers.
- Necessa landing: one promise, one action, one product view under the hero.
- Earlier research (Perplexity citation layers, He & Liu 2026 on source transparency, Westlaw status flags, Zonos's note that a confidence score is not a probability, TariffLens's "alternatives considered", Flexport's duty stack): kept as behaviour (status on every ruling, no percentages, every layer with its source), now behind layers instead of on the surface.
