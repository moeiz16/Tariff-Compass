# Tariff Compass API contract (v1)

The binding reference for Tariff Compass's module boundaries. The web app builds against Part 1 (HTTP). Part 2 is
the data model, Part 3 the in-process interfaces between the classification core and the platform, Part 4 the
wording rules, Part 5 the conventions for changing this document.

Changing a shape here means changing it in the same commit as the code. The code half lives in
`backend/tariffcompass/api/schemas/*.py` (wire shapes, Pydantic via Django Ninja), `api/labels.py` (every
code-to-words dictionary), `contracts.py` (in-process interfaces), `platform/roles.py` (roles and permissions) and
`duties/data/layers.json` (dated duty layers).

---

# Part 1: HTTP API

## 1.0 Screens and the endpoints behind them

The information architecture is in `frontend/DESIGN.md` §0 and §3: **the search box is the navigation**. Scopes
under the box (Answer · Rulings · Tariff text · My products · Review · Watch · Lab) are search verticals; the avatar
menu holds Settings, Activity, Switch organisation and Sign out.

| Route | Screen | Endpoints |
|---|---|---|
| `/` | Front page (public): one box, sample chips, a live sample answer, three feature tiles | `GET /auth/session`, `GET /public/samples`, `GET /public/samples/{key}`, `POST /public/classify` |
| `/signin` | Stepped sign-in (email → password → organisation), or try as a sample person | `GET /auth/csrf`, `POST /auth/login`, `POST /auth/demo`, `POST /auth/switch-org` |
| `/home` | Signed-in home: the box, then Recent and Changes as tabs | `GET /home`, `GET /scopes/counts` |
| `/answer?q=…` | Answer card (codes, word, one line of why, deciding question), then layers: why, rulings, landed cost, facts, law text; the ruling drawer | `POST /classify`, `GET /answers/{id}`, `POST /answers/{id}/facts`, `POST /evidence`, `POST /landed-cost`, `POST /answers/{id}/save`, `POST /answers/{id}/send-to-broker`, `POST /answers/{id}/citations/{n}/feedback` |
| `/rulings` | Library: rulings (status + subject per hit) | `GET /rulings` |
| `/rulings/[id]` | A ruling: holding, then tabs Compare (fact table, side by side) · Letter · Related | `GET /rulings/{key}`, `GET /rulings/{key}/compare?answerId=&n=` |
| `/tariff` | Library: tariff text as an outline (TreeView) | `GET /tariff/{country}/search`, `GET /tariff/{country}/lines/{code}`, `GET /tariff/sections` |
| `/products` | My products | `GET /products`, `POST /products` |
| `/products/[sku]` | Binder: current codes, then tabs History · Evidence · Entries · Record; exports | `GET /products/{sku}`, `GET /products/{sku}/binder`, `POST /products/{sku}/evidence`, `POST /products/{sku}/binder/export` → job, `GET /exports/{id}/download` |
| `/review`, `/review/[id]` | Review queue; a row opens the decision drawer | `GET /review`, `GET /review/{id}`, `POST /review/{id}/lesson`, `POST /review/{id}/approve`, `POST /review/{id}/correct`, `POST /review/{id}/ask`, `POST /review/{id}/answer` |
| `/watch` | Dated changes; each opens to what is known and the products it touches | `GET /watch`, `GET /watch/{id}`, `POST /watch/scan` → job |
| `/lab`, `/lab/rounds/[n]` | In use, rounds, then tabs Accuracy · Confidence · Chapters · Learned · Sign-off | `GET /lab`, `GET /lab/rounds/{n}`, `POST /lab/rounds` → job, `POST /lab/rounds/{n}/sign` |
| `/settings/*` | Defaults, people and roles, your broker, records, always-review rules | `GET/PATCH /settings`, `GET /org/members`, `PATCH/DELETE /org/members/{id}`, `GET/POST /org/invitations`, `DELETE /org/invitations/{id}`, `GET /roles`, `GET /org/brokers`, `GET/POST /rules`, `PATCH/DELETE /rules/{id}` |
| `/activity` | Activity record with chain verification | `GET /audit`, `GET /audit/verify`, `GET /audit/export.csv` |
| (any) | Job progress (training round, export, scan) | `GET /jobs/{id}`, SSE `GET /jobs/{id}/events` |

## 1.1 Conventions

- **Base path `/api/v1`.** The web app (SolidStart on :3050) forwards `/api/**` to the API on :8050 through a
  same-origin catch-all route (`frontend/src/routes/api/[...path].ts`) that streams both ways, so cookies, CSRF and
  SSE work without CORS.
- **camelCase on the wire**, snake_case in Python (`core/wire.py`: `Wire` base schema, `WireRouter` serialises by
  alias). Maps keep their keys as written: `details` (audit), `result` (jobs), `labels` (meta).
- **Plain-words fields.** Every code the UI might show travels with its words: `verdict.word` + `wordLabel`,
  `status.kind` + `kindLabel`, `kind` + `kindLabel`, `role` + `roleLabel`, `level` + `levelLabel`. The web app never
  maps codes to words itself, except through the static dictionaries in `GET /meta` → `labels`. No label contains
  a technical term (Part 4).
- **Tariff codes.** Formatted strings in the official grouping: US and Canadian ten-digit codes as `9617.00.10.00`
  (Canada: tariff item `9617.00.00` + suffix `00`). `digits` carries the bare digits, `headingDigits` the four
  drawn on the highlighter. Codes quoted from a CBP letter keep CBP's grouping in `codeAsQuoted` (`9617.00.1000`).
  Inputs accept codes with or without dots.
- **Rulings.** `id` is the ruling as people write it (`NY N321134`, `HQ H303684`); `key` is the path form
  (`ny-n321134`). Every ruling links to CBP CROSS (`url`). Only real rulings appear; nothing is invented.
- **Dates and money.** Timestamps are ISO-8601 UTC with offset; calendar dates `YYYY-MM-DD`. The web app shows them
  in the organisation's zone (America/Vancouver for the sample). Money is `{ amount: "3400.00", currency: "USD" }`
  (decimal string, never a float). Rates are strings as printed (`"7.2%"`, `"Free"`).
- **Demo clock.** "Today" and "now" come from the server clock (`clock.py`), which `TARIFF_COMPASS_DEMO_TODAY`
  (default `2026-02-19`) shifts and `TARIFF_COMPASS_DEMO_TIME` (e.g. `10:30`) can pin, shared by every process
  through `data/demo-clock.json`. **Every response carries `X-Tariff-Compass-Now`** (ISO-8601 UTC). The web app
  keeps the offset to the browser clock (`frontend/src/lib/clock.ts`) and never trusts the browser clock for
  business time. `GET /meta` and `GET /auth/session` also return `clock: { now, today, timezone, demo, demoToday,
  demoTime }`.
- **"Tariffs as of"** uses the data snapshot (`meta.snapshot`), not the wall clock.
- Every response carries `X-Request-ID` (echoed when the client sends a well-formed one) and the security headers in
  `core/middleware.py`; API responses carry `Cache-Control: no-store`.
- **Untrusted text.** Listings, spec sheets, supplier emails, questions and answers are rendered as plain text only
  (no HTML, no markdown, no autolinks). Marked spans are character offsets into the text they refer to.

### Errors: RFC 7807

Every error is `application/problem+json` (`core/errors.py`):

```json
{ "type": "https://tariffcompass.dev/problems/validation_error", "title": "Some fields need attention",
  "status": 422, "code": "validation_error", "detail": "One or more fields are invalid.",
  "errors": [{ "field": "reason", "message": "Give a reason for the change." }], "requestId": "…" }
```

| Status | `code` | When |
|---|---|---|
| 400 | `bad_request` | malformed JSON or query |
| 401 | `not_authenticated`, `session_expired`, `invalid_credentials` | no or ended session; wrong email/password (generic, with `triesLeft`) |
| 403 | `forbidden` | permission missing |
| 403 | `csrf_failed` | unsafe method without a valid `X-CSRFToken` |
| 403 | `no_active_org` | signed in but no active organisation |
| 404 | `not_found` | unknown id **or another organisation's id** (never 403 for cross-tenant ids) |
| 404 | `not_in_demo` | `POST /public/classify` for a product the public demo doesn't know |
| 409 | `already_decided`, `stale_version` | a review item decided by someone else (with `current`, the row as it is now); a binder or setting changed meanwhile |
| 409 | `needs_second_signature`, `same_person`, `gates_failed` | training-round promotion rules |
| 410 | `expired` | invitation past its expiry |
| 413 | `payload_too_large` | JSON body over 256 KB; file over 10 MB |
| 415 | `unsupported_media_type` | evidence other than PDF, JPEG, PNG or WebP |
| 422 | `validation_error`, `weak_password`, `unknown_code` | field errors; a code that isn't a line of the tariff in force |
| 423 | `sign_in_paused` | five failed sign-ins for an email in 15 minutes (with `retryAfterSeconds`) |
| 429 | `rate_limited` | with `Retry-After` seconds |
| 500 | `internal_error` | logged with the request id |
| 503 | `unavailable` | a dependency is down (the web proxy also uses this when the API is unreachable) |

### Pagination

List endpoints marked *(paged)* accept `?page=1&pageSize=25` (max 100) and return
`Page<T> = { items, page, pageSize, total, totalPages }`. Filters are query parameters. Default order is stated
per endpoint.

### Rate limits

Sliding per minute, per user (or IP when signed out): `auth` 10 (login, demo sign-in, invitation accept),
`public` 20 (`/public/*`), `classify` 30, `api` 300. Health, metrics and SSE streams are exempt. Sign-in pauses one
email for 15 minutes after 5 failures (`423 sign_in_paused`), on the real wall clock.

## 1.2 Auth and session (cookie + CSRF)

- `tc_session`: httpOnly, `SameSite=Lax`, `Secure` in production; server-side Django session. **Idle expiry 30 min,
  absolute 12 h**, on the real wall clock (never the demo clock).
- `tc_csrf`: readable cookie; echo it in **`X-CSRFToken`** on every POST/PUT/PATCH/DELETE. `GET /auth/csrf` sets it.
- Flow: `GET /auth/csrf` → `POST /auth/login` (or `POST /auth/demo`) → use the app. The client calls
  `POST /auth/refresh` at most every 5 minutes while active. On `401 session_expired` the app returns to `/signin`
  and back to the current route afterwards.
- Passwords: Argon2id; at least 12 characters, not common, not similar to the email (`422 weak_password`).
- Audited: `auth.login`, `auth.login_failed`, `auth.logout`, `auth.password_changed`, `auth.org_switched`.

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/auth/csrf` | – | `204` + `tc_csrf` cookie |
| GET | `/auth/session` | – | `SessionOut { me: Me \| null, clock, demoSignIn, demoPeople[] }`, **always 200** |
| POST | `/auth/login` | `LoginIn { email, password }` | `Me` |
| POST | `/auth/demo` | `DemoSignInIn { role: importer\|broker\|compliance\|admin }` | `Me` for the sample person with that role (Jordan Tse, Dana Whitlock, Maya Lindqvist, Priscilla Mensah). Only when the sample organisation exists and `DEMO_SIGN_IN` is on; else `404` |
| POST | `/auth/signup` | `SignupIn { email, password, fullName, orgName, kind }` | `201 Me` (new organisation, `admin` membership) |
| POST | `/auth/logout` | – | `204` |
| POST | `/auth/refresh` | – | `SessionTimes { expiresAt, absoluteExpiresAt }` |
| POST | `/auth/switch-org` | `SwitchOrgIn { orgId }` | `Me` (brokers switch between the importers they serve) |
| POST | `/auth/password` | `PasswordIn { currentPassword, newPassword }` | `204` (other sessions ended) |

```text
UserOut       = { id, email, fullName, licence, avatarColor }
OrgOut        = { id, name, slug, kind: importer|broker, kindLabel, locations[], timezone, isSample }
OrgSummary    = { id, name, kind, role, roleLabel, viaBroker: string|null, isSample }
MembershipOut = { role, roleLabel, title, permissions: string[] }
Me            = { user, activeOrg: OrgOut|null, membership: MembershipOut|null, orgs: OrgSummary[],
                  session: { expiresAt, absoluteExpiresAt } }
DemoPerson    = { role, roleLabel, fullName, title, orgName }
```

## 1.3 Organisations, members, roles, your broker

Roles and permissions (`platform/roles.py`; `membership.permissions` is the source of truth for the UI):

| Role | Label | Can |
|---|---|---|
| `importer` | Importer | classify, keep products and binders, export binders, send to the broker, answer the broker's questions |
| `broker` | Licensed customs broker | classify, decide review items (approve, correct, ask), manage always-review rules, read the Lab and co-sign rounds |
| `compliance` | Compliance lead | everything an importer can, plus always-review rules, watch scans, start training rounds, sign rounds, settings and the activity record |
| `admin` | Administrator | people, roles, invitations, organisation settings, the activity record |

Brokers act inside an importer's organisation through an **engagement** (Driftwood serves Northbound for US and
Canadian entries). A broker membership carries `viaBroker` so the UI can say "Dana Whitlock · Driftwood".

| Method | Path | Permission | Body | Response |
|---|---|---|---|---|
| GET | `/org/members` | `settings:read` | – | `MemberOut[] { id, user, role, roleLabel, title, viaBroker, joinedAt }` |
| PATCH | `/org/members/{id}` | `members:manage` | `MemberPatch { role?, title? }` | `MemberOut` (`409 last_admin` if it would remove the last admin) |
| DELETE | `/org/members/{id}` | `members:manage` | – | `204` |
| GET | `/org/invitations` | `members:manage` | – | `InvitationOut[]` |
| POST | `/org/invitations` | `members:manage` | `InvitationIn { email, role }` | `201 InvitationOut` with `link` (shown once; 7-day expiry) |
| DELETE | `/org/invitations/{id}` | `members:manage` | – | `204` |
| POST | `/invitations/{token}/accept` | public | `AcceptInvitationIn { fullName?, password? }` | `Me` |
| GET | `/roles` | signed in | – | `RoleOut[] { role, roleLabel, description, permissions }` |
| GET | `/org/brokers` | `settings:read` | – | `EngagementOut[] { id, brokerOrg, importerOrg, countries, countriesLabel, startedOn, people }` |

## 1.4 Meta, home and scope counts

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health` | public | `HealthOut { status, version, now, checks }` (also `/health` and `/health/ready` at the root) |
| GET | `/meta` | public | `MetaOut` |
| GET | `/home` | signed in | `HomeOut { dateLine, recent: RecentAnswer[], changes: HomeChange[] }` |
| GET | `/scopes/counts?q=` | signed in | `ScopeCounts { rulings, products, review, watch }` (the small numbers beside each scope) |

```text
MetaOut     = { product, version, clock, snapshot: SnapshotOut, scopes: {key,label}[], labels: {dict: {code: words}},
                origins: {key,label}[] }
SnapshotOut = { usHts: "HTSUS 2026 Revision 3", usHtsInForce: ["2026-02-12", null] (no end date published), caTariff: "Customs Tariff T2026",
                caTariffFrom: "2026-01-01", dutyLayersAsOf: "2026-02-19", rulingsCount, rulingsNewest,
                label: "Tariffs as of Thu 19 Feb 2026" }
RecentAnswer = { id, queryText, usCode, verdict, verdictLabel, createdAt, createdBy }
HomeChange   = { id, headline, affectedCount, consequence }
```

`labels` dictionaries: `countries, verdicts, factSources, rulingStatuses, matches, rulingMatch, levels, gri, layerKinds,
transport, categories, standings, versionKinds, reviewKinds, reviewStatuses, reasonKinds, changeKinds, recheck,
roundStatuses, jobStatuses, jobKinds`.

## 1.5 Classify, answers and evidence

A classification produces an immutable **answer** (stored with the classifier round, first-stage version, search
version and the LM that wrote it). It never files anything. Always-review rules and the verdict decide whether a
review item opens.

| Method | Path | Permission | Body | Response |
|---|---|---|---|---|
| POST | `/evidence` (multipart: `file`, `kind?`) | `classify:run` | PDF spec sheet, or JPEG/PNG/WebP photo, ≤ 10 MB | `201 EvidenceOut` (spec-sheet text extracted; photo read through the vision adapter) |
| POST | `/classify` | `classify:run` | `ClassifyIn` | `200 AnswerOut` (synchronous; < 1 s offline, < 6 s with a cloud LM) |
| GET | `/answers?mine=true` *(paged)* | `classify:read` | – | `AnswerSummary[]`, newest first |
| GET | `/answers/{id}` | `classify:read` | – | `AnswerOut` |
| POST | `/answers/{id}/facts` | `classify:run` | `ConfirmedFact { key, answer }` | `AnswerOut` (a new answer re-run with the fact; the binder records the question, the answer and who gave it) |
| POST | `/answers/{id}/save` | `products:write` | `SaveToBinderIn { productId? \| newProduct? }` | `BinderVersion` (v1 Proposed, or a new version) |
| POST | `/answers/{id}/send-to-broker` | `review:submit` | `SendToBrokerIn { note }` | `ReviewRow` (`kind: requested`) |
| POST | `/answers/{id}/citations/{n}/feedback` | `review:decide` | `CitationFeedbackIn { reason }` | `204` ("This ruling doesn't apply": recorded as a correction signal for the next round) |
| GET | `/public/samples` | public | – | `{ key, title, madeIn, query }[]` (the landing's "Try a sample") |
| GET | `/public/samples/{key}` | public | – | `AnswerOut` with `sample: true` |
| POST | `/public/classify` | public | `PublicClassifyIn { text }` | `AnswerOut` (`sample: true`) when the text matches a sample product, else `404 not_in_demo` |

```text
ClassifyIn = { text (3–8000), madeIn: "CN", into: ["US","CA"], productId?, evidenceIds: [], confirmedFacts: ConfirmedFact[],
               shipment?: { value: Money, quantity, transport: ocean|air|truck|rail|courier } }

EvidenceOut = { id, kind: spec_sheet|photo|listing|supplier_email|other, kindLabel, fileName, pages?, extractedText,
                photoFacts: string[], certain, sha256, uploadedBy, uploadedAt }

AnswerOut = {
  id, query: ClassifyIn, madeInLabel, createdAt, createdBy, tariffsAsOf, snapshotLabel, sample,
  us: CodeOut|null, ca: CodeOut|null,                                    # answer card codes
  verdict: { word: strong|broker, wordLabel: "Strong match"|"Needs a broker", sentence,
             agreeing, cited, inForce, agreementBar: { n, kind: same|contrast|differs }[],
             byDepth: { level: heading|full_code, levelLabel, word, wordLabel }[] },   # word = the full-code word
  alternative?: { code: CodeOut, condition, dutyAtStake },              # "Also possible, if the torch use is real"
  decidingQuestion?: { factKey, question, options: { key, label, leadsTo }[], notSureLabel },
  holdingSentence,                                                       # "The tumbler is classified in subheading 9617.00.10.00, HTSUS, and …"
  issue,                                                                 # ¶2, one sentence
  facts: { key, label, value, source: stated|read|assumed|unknown, sourceLabel, sourceNote, decides }[],   # ¶1
  reason: { text, cites: int[], marked: Span[] }[],                      # ¶0 In short (3–4 sentences)
  path: { level, levelLabel, code, text, gri, griLabel, why, cites[],    # ¶3 Law and analysis (accordion + gutter spine)
          notNeighbours: { code, text, reason, cite? }[], countryNote? }[],
  rulings: CitedRulingOut[],                                             # numbered citations [1]…[n] (drawers, peek, ¶5)
  tariffAuthorities: { ref, quote }[],                                   # ¶5 Heading 9617, Section XV Note 1, GRI 1, GRI 6
  landed: LandedCostOut[],                                               # ¶4, one per country in `into` when a shipment is known
  productId?, reviewItemId?,
  provenance: { classifierRound, firstStageVersion, searchVersion, lmLabel },   # binder export and Lab only
  timings: { firstStageMs, searchMs, programMs, dutiesMs, totalMs }
}
CodeOut = { country, countryLabel, code, digits, headingDigits, text, headingText, leaning }   # leaning → dashed amber underline
CitedRulingOut = { n, id, key, date, subject, status: RulingStatusOut, holding, markedSpans: Span[],
                   match: (same_heading|same_subheading|different_heading)[], matchLabels[],
                   factCompare: { fact, yours, theirs, match: same|close|differs, matchLabel }[], supports: int[], url }
RulingStatusOut = { kind: in_force|modified|revoked|contrast, kindLabel, text ("Revoked by HQ H303684, 7 Jul 2021"), byId?, date? }
Span = { start, end }
```

Rules the program guarantees (and the eval checks): every claim cites at least one ruling or tariff authority; a
revoked ruling is cited only for contrast; `agreeing` counts cited rulings reaching the same heading;
`verdict.word = broker` always comes with `decidingQuestion` or an `alternative`; no percentage appears anywhere.

## 1.6 Rulings and the two-pane compare

| Method | Path | Permission | Query / body | Response |
|---|---|---|---|---|
| GET | `/rulings` *(paged)* | `rulings:read` | `q`, `heading`, `status`, `from`, `to`, `sort=relevance\|newest` | `Page<RulingSummary>` |
| GET | `/rulings/{key}` | `rulings:read` | – | `RulingDetail` |
| GET | `/rulings/{key}/compare` | `rulings:read` | `answerId`, `n?` | `CompareOut` |

```text
RulingSummary = { id, key, issued, subject, code, codeAsQuoted, heading, status: RulingStatusOut, holding, snippet, snippetMarks: Span[] }
RulingDetail  = RulingSummary + { category, codes[], text, paragraphs: Span[], related: { id, key, relation, relationLabel }[],
                                  alsoCitedIn: { productId, sku, title }[], sourceUrl }
CompareOut    = { ruling: RulingDetail, citedAs, productTitle, madeInLabel,
                  ruleQuote,                       # 19 CFR 177.9(b)(2): rulings apply only to identical articles
                  alignment: FactCompareOut[],     # Fact · yours · match · the ruling's
                  evidence: { kind, label, text, marked: Span[] }[],   # left pane
                  rulingMarked: Span[] }           # right pane: supporting passages in reading order
```

## 1.7 Tariff text

| Method | Path | Permission | Query | Response |
|---|---|---|---|---|
| GET | `/tariff/sections` | public | – | `SectionOut[] { section: "I".."XXI", title, chapters: { chapter, title, reserved }[] }` (the 97; chapter 77 reserved) |
| GET | `/tariff/{country}/search` | `tariff:read` | `q`, `under?`, `k?` | `TariffLineOut[]` |
| GET | `/tariff/{country}/lines/{code}` | `tariff:read` | – | `TariffOutline { line, ancestors[], children[], notes[], editionLabel }` (e.g. "HTSUS 2026 Revision 3 (in force from 12 Feb 2026)") (unknown code → `404`) |

```text
TariffLineOut = { country, code, digits, level, levelLabel, indent, text, fullText, unit, generalRate, special, hasChildren }
```

## 1.8 Landed cost and duty layers

The duty engine reads `duties/data/layers.json`. **Every line carries a source and an effective date; the UI
refuses to render a line without them.** Charges add on the same customs value; they don't compound.

| Method | Path | Permission | Body / query | Response |
|---|---|---|---|---|
| POST | `/landed-cost` | `classify:read` | `LandedCostIn` | `LandedCostOut` (restack on every control change; < 30 ms) |
| GET | `/duty-layers?country=&asOf=` | `classify:read` | – | `DutyLayerOut[]` (layers in force on `asOf`, default the snapshot date) |

```text
LandedCostIn  = { country, code, madeIn, value: Money, quantity, transport, usmcaAnswers: { key: bool }, metalContentValue?: Money }
LandedCostOut = { country, countryLabel, code, madeIn, madeInLabel, value, quantity, transport, transportLabel,
                  lines: LayerLineOut[], notApplied: { name, why }[], chargesTotal, landedTotal, perUnit,
                  effectiveRate: "+27.2%", questions: { key, question, answer }[],
                  whatCouldChange: { label, landedTotal, chargesTotal }[], tariffsAsOf, snapshotLabel }
LayerLineOut  = { letter: "a", layerId, kind: base|remedy|emergency|fee|tax|surtax|preference, kindLabel, name,
                  rate, amount: Money, plain, source, sourceUrl, chapter99?, effectiveFrom, effectiveTo?,
                  legalStatus?, legalStatusOpen }    # legalStatusOpen → hatched segment and ⚠ on the receipt
DutyLayerOut  = { id, country, kind, kindLabel, name, authority, chapter99[], scope, rate, effectiveFrom, effectiveTo?,
                  legalStatus?, legalStatusOpen, sources[] }
```

Behaviour: Mexico-origin goods into the US return the three USMCA questions in `questions`; "yes to all three"
drops the MFN and the Mexico IEEPA duty, each waived line moving to `notApplied` with why. `whatCouldChange` covers
"If the pending emergency duties end", other origins (China / Vietnam / Mexico, qualifying and not) and, when the
verdict is "Needs a broker", the total under the alternative code.

## 1.9 Products and the binder

The binder is the product's reasonable-care record: one version per decision, append-only, each linked to its
audit event. Records are kept five years from the latest US entry (19 CFR 163.4) and six years from the latest
Canadian import (CBSA Memorandum D17-1-21); `keptUntil` is the later of the two that apply (a product with no
entries yet counts from its latest decision). Deleting a product hides it and keeps the record until then.

| Method | Path | Permission | Body / query | Response |
|---|---|---|---|---|
| GET | `/products` *(paged)* | `products:read` | `q`, `category`, `madeIn`, `standing`, `sort` | `Page<ProductSummary>` |
| POST | `/products` | `products:write` | `ProductIn` | `201 ProductDetail` |
| GET | `/products/{sku}` | `products:read` | – | `ProductDetail` |
| PATCH | `/products/{sku}` | `products:write` | `ProductPatch` | `ProductDetail` |
| DELETE | `/products/{sku}` | `products:write` | – | `204` (hidden; kept until its retention date) |
| POST | `/products/{sku}/evidence` (multipart) | `products:write` | `file`, `kind`, `label?` | `201 EvidenceOut` |
| GET | `/products/{sku}/binder` | `products:read` | – | `BinderOut` |
| POST | `/products/{sku}/binder/export` | `binder:export` | `ExportIn { format: pdf\|zip }` | `202 JobAccepted` → job `result: ExportResult` |
| GET | `/exports/{id}/download` | `binder:export` | – | the file (`application/pdf` or `application/zip`) |

```text
ProductSummary = { id, sku, title, category, categoryLabel, madeIn, madeInLabel, usCode, caCode, standing, standingLabel,
                   versions, lastDecidedAt, inReview }
ProductDetail  = ProductSummary + { listingText, unitValue, evidence: EvidenceOut[], latestAnswerId }
BinderOut      = { product, openedOn, keptUntil, retentionNote, versions: BinderVersion[] (oldest first),
                   approval: { by: PersonRef, at, version, sentence }|null, evidence[], entries: EntryOut[],
                   record: { chainVerified, checkedAt, events, fingerprint }, advanceRuling: string|null }
BinderVersion  = { n, kind: proposed|question_answered|approved|corrected|re_approved|withdrawn, kindLabel, at,
                   usCode, caCode, standing, standingLabel, decidingFact: { label, value, sourceNote }|null,
                   evidence: string[], rulingsRelied: { id, key, statusLabel }[], decidedBy: PersonRef|null, why,
                   fingerprint, current, changed: ("usCode"|"caCode"|"standing"|"decidingFact"|"evidence"|"rulingsRelied"|"decidedBy"|"why")[] }
EntryOut       = { entryNumber, country, enteredOn, code, dutyPaid }
ExportResult   = { downloadUrl, fileName, bytes, pages, fingerprint, recordFingerprint }
PersonRef      = { id, fullName, role, roleLabel, licence }
```

`changed` drives the matrix: unchanged cells render the ditto mark 〃, changed cells the soft highlighter. The PDF
prints the record fingerprint on every page; the ZIP holds the PDF, the ruling texts relied on, the evidence files
and the product's slice of the activity record. `advanceRuling` offers a CBSA advance-ruling request draft
(Memorandum D11-11-3) for products imported into Canada.

## 1.10 Broker review: docket, decisions, rules

| Method | Path | Permission | Body / query | Response |
|---|---|---|---|---|
| GET | `/review` | `review:read` | `filter=all\|unsure\|differs\|ruling_changed\|always\|ca`, `q`, `sort=waiting\|value\|product`, `page` | `DocketOut` |
| GET | `/review/{id}` | `review:read` | – | `DecisionRecord` |
| POST | `/review/{id}/lesson` | `review:decide` | `LessonIn { usCode?, caCode?, reasonKind, reason }` | `LessonOut { lesson, redline: RedlineCell[] }` (live as the broker types; no side effects) |
| POST | `/review/{id}/approve` | `review:decide` | `ApproveIn { note }` | `DecisionOut` (binder version "approved"/"re_approved") |
| POST | `/review/{id}/correct` | `review:decide` | `CorrectIn { usCode?, caCode?, reasonKind, reason (≥10 chars), rulingRelied?, alsoChangeCa }` | `DecisionOut` with `lesson`; the correction becomes a training example (`422 unknown_code` if the code isn't a line in force) |
| POST | `/review/{id}/ask` | `review:decide` | `AskIn { question, options[] }` | `DecisionOut` (status `asked`) |
| POST | `/review/{id}/answer` | `review:answer` | `AnswerQuestionIn { answer }` | `DecisionOut` (status `answered`; back to the broker) |
| GET | `/rules` | `review:read` | – | `RuleOut[]` |
| POST | `/rules` | `rules:manage` | `RuleIn { kind, value, label }` | `201 RuleOut` |
| PATCH | `/rules/{id}` | `rules:manage` | `RulePatch { active?, label? }` | `RuleOut` |
| DELETE | `/rules/{id}` | `rules:manage` | – | `204` |

```text
DocketOut  = { counts: { all, unsure, differs, rulingChanged, always, ca }, oldestLabel, items: ReviewRow[], total,
               week: { approved, corrected, questions }, nextRound: { round, correctionsWaiting }, emptyMessage }
ReviewRow  = { id, productId, sku, productTitle, waitingSince, waitingLabel, into: US|CA|both, intoLabel,
               proposedUs: CodeOut|null, proposedCa: CodeOut|null, kind: unsure|differs|ruling_changed|always_review|requested,
               kindLabel, detail, value: Money|null, withName, status, statusLabel }
DecisionRecord = { row, listing, specSheet, specSheetFile, uploadedBy, uploadedAt,
                   decidingPhrases: { source: listing|spec_sheet, span }[], misread, previousUs, rulingsRelied[],
                   rulingChange: RulingStatusOut|null, rule, answerId, questions: QuestionOut[] }
RedlineCell = { index: 0..9, proposed, yours, changed }
DecisionOut = { item: ReviewRow, binderVersion, lesson, toast }   # toast: "Corrected · NB-KT-0388 → 7323.93.00.80 · binder v3"
RuleOut     = { id, kind: heading|chapter|material|value_over|origin|keyword, kindLabel, value, label, active, createdBy, createdAt, matches }
```

Concurrency: deciding an item that someone else decided returns `409 already_decided` with the current row.
Every decision is audited with the broker's name and licence and lands in the binder.

## 1.11 Watch

| Method | Path | Permission | Query | Response |
|---|---|---|---|---|
| GET | `/watch` | `watch:read` | `q`, `from`, `to`, `kind` | `WatchOut { items: WatchItemOut[], lastCheckedAt, checks[], quietMessage }` |
| GET | `/watch/{id}` | `watch:read` | – | `WatchItemOut` with every affected product |
| POST | `/watch/scan` | `watch:manage` | – | `202 JobAccepted` (re-checks binders against the layers, rulings and tariff edition in force) |

```text
WatchItemOut = { id (the change's key, e.g. "scotus-ieepa"), date|null, dateLabel ("PENDING" | "16 FEB 2026"), dateNote ("argued 5 Nov 2025"), kind, kindLabel,
                 headline, body, knows[], unknowns[], affectedCount, affected: AffectedOut[] (top 5), sourceLabel, sourceUrl }
AffectedOut  = { productId, sku, title, effect, recheck: unchanged|needs_review|re_approved, recheckLabel, dutyBefore?, dutyAfter? }
```

## 1.12 Lab: training rounds and sign-off

All figures come from a round's `RoundReport` (Part 3), measured on rulings the classifier hasn't seen. A round
is in use only when it **passed all five checks and was signed by two different people holding `lab:sign`**
(in the sample: Maya, then Dana). Until a round qualifies, word matching (the classical first stage) is in use and
every round is a challenger; `lab.live.live_round()` is what the classifier reads. Promotion keeps the previous live round one step away; approved answers keep their codes; nothing is
re-filed.

| Method | Path | Permission | Body | Response |
|---|---|---|---|---|
| GET | `/lab` | `lab:read` | – | `LabOut { rounds: RoundStrip[], live, candidate, correctionsWaiting, inUse: { kind: word_matching\|round, round, label, fullCode, heading, sentence } }` |
| GET | `/lab/rounds/{n}` | `lab:read` | – | `RoundOut` |
| POST | `/lab/rounds` | `lab:run` | `StartRoundIn { note }` | `202 JobAccepted` (one round at a time; `409 conflict` while one runs) |
| POST | `/lab/rounds/{n}/sign` | `lab:sign` | `SignIn { statement }` (the signer types their name) | `RoundOut`; the second signature makes it live (`409 same_person`, `409 gates_failed`) |

```text
RoundStrip = { n, status: training|waiting_signoff|live|not_made_live|retired|failed, statusLabel, trainedOn, note }
RoundOut   = { n, status, statusLabel, trainedOn, testCount, testFrom, testTo, snapshot, rerunNote, lede,
               byDepth: { level: chapter|heading|subheading|full_code, levelLabel, wordMatching, live, candidate, unoptimised }[],
               confidence: { strong: ConfidenceCell, broker: ConfidenceCell },     # "right 87 times in 100"
               byChapter: { chapter, title, tested, before, after, change, changeLabel, newRulings, moving }[],
               learned: string[], drift: { newRulings, mostMoved, psi, sentence }, checks: { key, label, passed, value, threshold }[],
               signOff: { required: 2, signatures: { name, role, roleLabel, signedAt, statement }[], canSign, willPromote, note },
               runBy }   # "offline simulator" or the cloud LM: shown only in the Lab as "Answers written by"
ConfidenceCell = { said, right, per100, sentence }
```

The five checks before signing: full-code accuracy at least the live round's; heading accuracy at least the live
round's; no chapter Northbound imports worse by more than 3 points; "Strong match" right at least 90 times in 100;
citation precision at least 0.95.

## 1.13 Settings

| Method | Path | Permission | Body | Response |
|---|---|---|---|---|
| GET | `/settings` | `settings:read` | – | `OrgSettingsOut { into[], madeIn, ports[], alwaysSendToBroker, retentionYears (US: 5, 19 CFR 163.4), retentionYearsCa (6, CBSA D17-1-21), retentionNote, deletingNote, brokerName }` |
| PATCH | `/settings` | `settings:manage` | `OrgSettingsPatch` | `OrgSettingsOut` |

## 1.14 Activity record (audit)

| Method | Path | Permission | Query | Response |
|---|---|---|---|---|
| GET | `/audit` *(paged)* | `audit:read` | `action`, `actor`, `from`, `to`, `targetType`, `targetId` | `Page<AuditRow { id, at, actorName, actorRole, actorRoleLabel, action, actionLabel, summary, targetType, targetId, targetLabel, fingerprint }>` |
| GET | `/audit/verify` | `audit:read` | – | `ChainOut { ok, events, brokenAt, checkedAt, sentence }` ("Chain verified 19 Feb, 10:30") |
| GET | `/audit/export.csv` | `audit:read` | same filters | CSV |

Audited actions include `auth.*`, `product.created|updated|hidden`, `answer.created|saved|sent_to_broker`,
`evidence.added`, `review.approved|corrected|asked|answered`, `rule.created|changed|removed`,
`binder.exported`, `watch.scanned`, `lab.round_started|signed|made_live`, `member.*`, `settings.changed`.

## 1.15 Jobs and progress

Long work runs on the Huey worker: training rounds, index builds, watch scans, binder exports, data ingestion.
Start endpoints return `202 JobAccepted { jobId, statusUrl, eventsUrl }`.

| Method | Path | Response |
|---|---|---|
| GET | `/jobs/{id}` | `JobOut { id, kind, kindLabel, status: queued\|running\|succeeded\|failed, statusLabel, progress (0..1), stage, message, result, error, createdAt, finishedAt }` |
| GET | `/jobs/{id}/events` | SSE. Events: `progress` (`JobOut`), `done` (`JobOut`), `failed` (`JobOut`); a comment heartbeat every 15 s; the stream closes after `done`/`failed` or 300 s (reconnect with `Last-Event-ID`) |

Job `result` maps are camelCase like the rest of the wire (`ExportResult` → `downloadUrl`, `fileName`, …).
Polling fallback: `GET /jobs/{id}` every second. `message` is plain words for the UI ("Testing on 1,240 rulings it
hasn't seen…").

## 1.16 Health and metrics

`GET /health` (liveness), `GET /health/ready` (database), `GET /metrics` (Prometheus text: request counts and
latency, classification stage timings, job outcomes). No auth; not under `/api/v1`.

---

# Part 2: Data model

Tables by app (all domain rows carry `org`; ids are UUIDs unless noted). Platform tables exist from the first
migration; the others are added by their apps.

| App | Table | Key fields |
|---|---|---|
| platform | `User` | email, full_name, licence, avatar_color, Argon2 password |
| platform | `Organisation` | name, slug, kind (importer\|broker), locations, timezone, settings (JSON), is_sample |
| platform | `Engagement` | broker_org → importer_org, countries, started_on, active |
| platform | `Membership` | org, user, role, title, engagement (for broker memberships) |
| platform | `Invitation` | org, email, role, token_hash, expires_at |
| platform | `LoginFailure` | email, ip, created_at |
| platform | `AuditEvent` | org, actor, action, target, summary, details, prev_hash, hash (per-org chain) |
| platform | `Job` | org, kind, status, progress, stage, message, params, result, error, huey_task_id |
| catalog | `Product`, `Evidence`, `Answer`, `BinderVersion`, `Entry` | see `catalog/models.py` |
| review | `ReviewItem`, `Decision`, `Question`, `TrainingExample`, `AlwaysReviewRule` | see `review/models.py` |
| watch | `Change`, `AffectedProduct` | see `watch/models.py` |
| lab | `TrainingRound`, `SignOff` | see `lab/models.py` |

Indexes and stores outside the database: `data/index/` (Tantivy), `classify/artifacts/` (first-stage models and
optimised program JSON for the demo rounds), `mlruns/` (MLflow, git-ignored), `data/uploads/` (evidence files),
`data/huey.db` (queue).

---

# Part 3: In-process interfaces (`backend/tariffcompass/contracts.py`)

The API reaches the classification core only through five protocols, obtained from `tariffcompass.services`
(`services.retriever()`, `.first_stage()`, `.program()`, `.duties()`, `.optimizer()`). While an implementation is
missing, `services` falls back to the deterministic fakes in `tariffcompass.fakes` (and `CORE_BACKEND=fake` forces
them in tests). Value objects are frozen dataclasses; codes are bare digits inside, formatted at the edge
(`codes.fmt`).

| Interface | Methods | Real implementation | Fake |
|---|---|---|---|
| `Retriever` | `rulings(text, headings?, k)`, `ruling(id)`, `tariff(text, country, under?, k)`, `tariff_line(country, code)`, `tariff_children(country, code)` | `search/engine.py: build_retriever()` (Tantivy BM25 + reranker) | `FakeRetriever` (three real tumbler rulings) |
| `FirstStage` | `predict(query, k) → FirstStageResult` (top-k chapters and headings, calibrated, with the words that drove them) | `classify/first_stage.py: load_first_stage()` | `FakeFirstStage` (keyword table) |
| `ClassifierProgram` | `classify(query, first_stage, retriever) → ProgramAnswer` | `classify/program.py: load_program()` (DSPy: CandidateHeadings, GriReasoning, ChooseSubheading, SelectCitations, Confidence) | `FakeProgram` (the tumbler answer) |
| `DutyEngine` | `landed_cost(LandedCostQuery) → LandedCost`, `layers_in_force(country, as_of)` | `duties/engine.py: build_engine()` | `FakeDutyEngine` (MFN only) |
| `Optimizer` | `run(RoundRequest, progress) → RoundReport` | `classify/optimize.py: build_optimizer()` (GEPA) | `FakeOptimizer` |

Value objects: `ProductQuery`, `RulingHit`, `RulingDoc`, `TariffLine`, `Candidate`, `FirstStageResult`,
`CodeChoice`, `Fact`, `DecidingQuestion`, `Claim`, `NotNeighbour`, `PathStep`, `FactCompare`, `Citation`,
`TariffAuthority`, `ProgramAnswer`, `DutyLayer`, `LandedCostQuery`, `LayerLine`, `NotApplied`, `OriginQuestion`,
`LandedCost`, `RoundRequest`, `DepthAccuracy`, `RoundReport`. The API maps `ProgramAnswer` + `LandedCost` to
`AnswerOut` and `RoundReport` to `RoundOut`.

**Adapters** (`backend/tariffcompass/adapters/`), each with a protocol and an offline default:

| Adapter | Protocol | Default | Live (opt-in) |
|---|---|---|---|
| LM (`lm.py`) | `task_lm()`, `reflection_lm()` return DSPy LMs; `lm_label(role)` | `SimulatorLM` (`lm_sim.py`): a DSPy engine answering in whatever format the adapter asks, through deterministic task and reflection policies | `dspy.LM(LITELLM_MODEL)` with `LLM_FAKE=false` and `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` (DSPy's own client; LiteLLM only for other providers) |
| Vision (`vision.py`) | `VisionAdapter.describe(image, mime) → PhotoFacts` | `FakeVision`: recognises the seed's sample photos by SHA-256, otherwise reports no product facts | Gemini vision with `VISION_FAKE=false` |
| Embeddings (`embeddings.py`) | `EmbeddingAdapter.embed(texts)` | `FakeEmbeddings`: hashed bag of words, 256 dims | Jina or Cohere free tiers (`EMBEDDINGS=jina\|cohere`) |

**Jobs** (`jobs.py`): tasks live in each app's `tasks.py` (autodiscovered by `run_huey`); `run_job(job_id, fn)`
records status, progress, result and errors on the `Job` row; `Progress(fraction, stage, message)` is passed to
long tasks.

---

# Part 4: Wording rules

The audience is importers, brokers and compliance leads, not engineers (`frontend/DESIGN.md`).

- **Never in rendered text or labels:** RAG, retrieval, embeddings, vector, rerank, LLM, model or provider names,
  LiteLLM, prompt, tokens, SQL, architecture, pipeline, latency, fallback, cache, DSPy, GEPA, TF-IDF, score, model.
  `provenance.lmLabel` and `RoundOut.runBy` exist for the binder export and the Lab's "Answers written by" line only.
- **Use:** "the classifier", "word matching" (the classical baseline), "training round", "rulings it hasn't seen",
  "Strong match" / "Needs a broker", "the fact that decides it".
- **No percentages for confidence.** Accuracy is reported as frequencies ("right 87 times in 100").
- **Compliance language:** "designed to support reasonable-care record keeping"; never "compliant" or "certified".
  Nothing is filed automatically; a licensed broker approves every code before it is used on an entry.
- **Legal status:** IEEPA layers say "Pending at the Supreme Court (argued 5 Nov 2025)" on the demo date and never
  state an outcome.

---

# Part 5: Changing this contract

- A shape change lands in one commit with: this document, `api/schemas`, the router, its tests and (if user
  facing) the web client types.
- New codes need a label in `api/labels.py` and in `GET /meta`.
- `contracts.py` changes need the fake updated and `tests/test_core_contracts.py` passing.
- New duty layers need a source URL, an effective date and a legal status, or the engine refuses to load them.
