# ADR 0005: Duty layers as dated data, legal status as data, and one demo clock

**Status:** accepted

## Context

US duties in 2025–2026 changed often and by different instruments: executive orders under IEEPA, Section 301 and
232 actions, fee schedules, and the end of de minimis. Their lawfulness was in question: the IEEPA case was argued
at the Supreme Court on 5 November 2025 and undecided on the demo date. Canada added surtax orders. A landed-cost
estimate is only useful if every number says where it comes from and since when, and the product must be
reproducible as of a chosen day.

## Decision

1. **Every layer is a record** in `duties/data/layers.json`: id, country, kind (base, remedy, emergency, fee, tax,
   surtax, preference), authority, Chapter 99 numbers, rate, scope, stacking and exclusion rules,
   `effectiveFrom`, `effectiveTo`, `legalStatus`, `verified` and source URLs. The engine refuses a layer without a
   source and an effective date; the UI refuses to render a line without them.
2. **Legal status is a field, not a code path.** On 19 Feb 2026 every IEEPA layer reads "pending at the Supreme
   Court (argued 5 Nov 2025)". The receipt hatches those lines and the Watch bulletin explains what is known and
   what is not. The product never states an outcome; a change in status is a new record with its own source and
   date.
3. **One clock.** `clock.py` is the only source of "now". `TARIFF_COMPASS_DEMO_TODAY` (default 2026-02-19) shifts
   Django's `timezone.now`; `TARIFF_COMPASS_DEMO_TIME` pins the time of day, anchored in `data/demo-clock.json` so
   the API, the worker and management commands agree. Every response carries `X-Tariff-Compass-Now`; the web app
   follows it. Sessions and rate limits keep the real wall clock. "Tariffs as of" uses the data snapshot date.
4. **Editions are pinned.** The demo reads 2026 HTSUS Revision 3 (in force 12–25 Feb 2026) and Canada's T2026
   (from 1 Jan 2026).

## Consequences

- Screenshots, the seed and the eval are reproducible on a fixed day.
- Moving the demo clock past a layer's change date without updating the data would show stale layers; the duty
  engine warns when the clock is past the newest layer's verification date.
- Curating layers is manual work with sources; it is small (33 layers) and reviewed like code.
