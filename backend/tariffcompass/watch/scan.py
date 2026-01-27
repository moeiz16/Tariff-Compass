"""Tariff change watch: real dated events, and which of an organisation's products each one touches.

The events are the ones listed in docs/DATA.md, all dated on or before Thu 19 Feb 2026, with sources from
`duties/data/layers.json`. A scan re-checks every product's binder against them: duty changes are measured
with the duty engine on the day before and the day the change took effect; the pending IEEPA case compares
today's total with the total if those duties end (the engine's own "what could change" line). The product
never states the outcome of a pending case.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any

import structlog
from django.db import transaction

from tariffcompass import clock, codes
from tariffcompass.api.routers.common import money_words
from tariffcompass.catalog import answers
from tariffcompass.catalog.models import Product
from tariffcompass.platform.config import tc
from tariffcompass.platform.models import Organisation
from tariffcompass.watch.models import AffectedProduct, Change

log = structlog.get_logger("tariffcompass.watch")

PENDING_LABEL = "If the pending emergency duties end"
EU = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
}


@cache
def layer_sources() -> dict[str, list[str]]:
    data = json.loads(Path(tc()["DUTY_LAYERS_PATH"]).read_text())
    return {layer["id"]: list(layer.get("sources") or []) for layer in data["layers"]}


def _src(layer_id: str, fallback: str) -> str:
    srcs = layer_sources().get(layer_id) or []
    return srcs[0] if srcs else fallback


def definitions() -> list[dict[str, Any]]:
    """The changes Watch knows about, newest first (pending last-but-shown-first by the bulletin)."""
    return [
        {
            "key": "scotus-ieepa",
            "kind": "legal_pending",
            "date": None,
            "date_note": "argued 5 Nov 2025",
            "headline": "The Supreme Court has not yet decided whether the IEEPA duties are lawful",
            "body": "Learning Resources, Inc. v. Trump, with Trump v. V.O.S. Selections, was argued on 5 November "
            "2025. Until the Court decides, CBP keeps collecting the IEEPA duties, and every landed cost shows them "
            "as charged with their legal status open.",
            "knows": [
                "The duties are being collected on every entry today, at the rates in force.",
                "They are the opioid-linked duty and the reciprocal duties on China, the reciprocal duties on "
                "Vietnam and the EU, and the duties on non-USMCA goods from Mexico and Canada.",
                "Section 301, Section 232, MFN and the entry fees are not part of the case.",
            ],
            "unknowns": [
                "When the Court will decide, or what it will decide.",
                "Whether duties already paid would be refunded, and how.",
            ],
            "source_label": "Supreme Court docket 24-1287",
            "source_url": "https://www.supremecourt.gov/docket/docketfiles/html/public/24-1287.html",
            "layer_ids": [
                "US-IEEPA-CN-FENTANYL",
                "US-IEEPA-RECIP-CN",
                "US-IEEPA-RECIP-VN",
                "US-IEEPA-RECIP-EU",
                "US-IEEPA-MX",
                "US-IEEPA-CA",
            ],
            "countries": ["US"],
        },
        {
            "key": "hts-2026-rev3",
            "kind": "schedule_revision",
            "date": date(2026, 2, 12),
            "date_note": "",
            "headline": "2026 HTSUS Revision 3 is in force: none of your lines were renumbered or split",
            "body": "Revision 3 of the 2026 Harmonized Tariff Schedule took effect on 12 February 2026. Each binder's "
            "US code was checked against it; every line you use still exists with the same text and rate.",
            "knows": ["Revision 3 is the edition in force from 12 to 25 February 2026."],
            "unknowns": [],
            "source_label": "USITC HTS release list",
            "source_url": "https://hts.usitc.gov/reststop/releaseList",
            "countries": ["US"],
        },
        {
            "key": "s301-battery-2026",
            "kind": "duty_layer",
            "date": date(2026, 1, 1),
            "date_note": "",
            "headline": "Section 301 duty on lithium-ion non-EV batteries from China rose to 25%",
            "body": "From 1 January 2026, lithium-ion batteries other than for electric vehicles from China pay 25% "
            "under 9903.91.06, up from 7.5% under List 4A. Power banks are classified with these batteries.",
            "knows": ["The increase came from the four-year review of the Section 301 actions."],
            "unknowns": [],
            "source_label": "USTR Section 301 four-year review",
            "source_url": _src("US-301-4YR-BATTERY", "https://ustr.gov/"),
            "layer_ids": ["US-301-4YR-BATTERY"],
            "headings": ["850760"],
            "countries": ["US"],
            "origins": ["CN"],
        },
        {
            "key": "ca-steel-derivative-surtax",
            "kind": "duty_layer",
            "date": date(2025, 12, 26),
            "date_note": "",
            "headline": "Canada's surtax on steel derivative goods (SOR/2025-267) took effect",
            "body": "From 26 December 2025 Canada charges a 25% surtax on listed steel derivative goods, such as "
            "other articles of iron or steel of heading 7326. Steel kitchenware of heading 7323 is not listed.",
            "knows": ["The surtax adds to the MFN duty and GST is charged on top of both."],
            "unknowns": [],
            "source_label": "Canada Gazette, SOR/2025-267",
            "source_url": _src("CA-SURTAX-STEEL-DERIV", "https://gazette.gc.ca/"),
            "layer_ids": ["CA-SURTAX-STEEL-DERIV"],
            "headings": ["7326"],
            "countries": ["CA"],
        },
        {
            "key": "ieepa-cn-opioid-cut",
            "kind": "duty_layer",
            "date": date(2025, 11, 10),
            "date_note": "",
            "headline": "The opioid-linked IEEPA duty on goods from China was cut from 20% to 10%",
            "body": "Executive Order 14357 lowered the duty under 9903.01.24 to 10% from 10 November 2025. It still "
            "stacks on the normal duty, Section 301 and the reciprocal duty.",
            "knows": ["The lower rate applies to goods entered from 10 November 2025."],
            "unknowns": ["The legality of the duty is part of the pending Supreme Court case."],
            "source_label": "Executive Order 14357 (90 FR 50725)",
            "source_url": _src("US-IEEPA-CN-FENTANYL", "https://www.federalregister.gov/"),
            "layer_ids": ["US-IEEPA-CN-FENTANYL"],
            "countries": ["US"],
            "origins": ["CN"],
        },
        {
            "key": "hq-h289250-revocation",
            "kind": "ruling_revoked",
            "date": date(2021, 10, 7),
            "date_note": "",
            "headline": "HQ H289250 revoked NY N284187, a ruling on a lamp of heading 9405",
            "body": "CBP revoked NY N284187 and classified the lamp in subheading 9405.40.84 instead. A binder that "
            "still relies on NY N284187 needs a broker's re-check, even where the code stays the same.",
            "knows": [
                "A revoked ruling can't be relied on for reasonable care; the code may still be right on other grounds."
            ],
            "unknowns": [],
            "source_label": "CBP ruling HQ H289250",
            "source_url": "https://rulings.cbp.gov/ruling/H289250",
            "ruling_id": "HQ H289250",
        },
    ]


def ensure_changes() -> list[Change]:
    out = []
    for d in definitions():
        fields = {k: v for k, v in d.items() if k != "key"}
        fields.setdefault("layer_ids", [])
        fields.setdefault("headings", [])
        fields.setdefault("origins", [])
        ch, _ = Change.objects.update_or_create(key=d["key"], defaults=fields)
        out.append(ch)
    return out


def _shipment(p: Product) -> dict[str, Any] | None:
    s = dict(p.shipment or {})
    return s if s.get("value") else None


def _charges(country: str, p: Product, on: date) -> Decimal | None:
    code = p.us_code if country == "US" else p.ca_code
    ship = _shipment(p)
    if not code or ship is None:
        return None
    return answers.landed_cost(country, code, p.made_in, ship, as_of=on).charges_total


def _pending(p: Product) -> tuple[Decimal, Decimal] | None:
    ship = _shipment(p)
    if not p.us_code or ship is None or "US" not in (p.into or []):
        return None
    lc = answers.landed_cost("US", p.us_code, p.made_in, ship)
    if not any(answers.legal_open(ln.legal_status) for ln in lc.lines):
        return None
    after = next((total for label, total in lc.what_could_change if label == PENDING_LABEL), None)
    if after is None:
        return None
    value = lc.query.customs_value
    return lc.charges_total, after - value


def _touches(change: Change, p: Product) -> bool:
    if change.countries and not set(change.countries) & set(p.into or []):
        return False
    if change.origins and p.made_in not in change.origins:
        return False
    code = p.ca_code if change.countries == ["CA"] else p.us_code
    return not change.headings or any(code.startswith(h) for h in change.headings)


def assess(change: Change, p: Product) -> dict[str, Any] | None:
    """The row for one product, or None when the change doesn't touch it."""
    if change.key == "scotus-ieepa":
        res = _pending(p)
        if res is None:
            return None
        now_duty, without = res
        return {
            "effect": f"Duty would fall from {money_words(now_duty)} to {money_words(without)} if those duties end",
            "recheck": "unchanged",
            "duty_before": now_duty,
            "duty_after": without,
            "currency": "USD",
        }
    if change.kind in ("ruling_revoked", "ruling_modified"):
        from tariffcompass.catalog.rulings import status_of

        relied: list[str] = []
        for v in p.versions.order_by("-n"):  # the current version and the last decided one
            relied += [r for r in v.rulings_relied or [] if r not in relied]
            if v.kind in ("approved", "corrected", "re_approved"):
                break
        for rid in relied:
            st = status_of(rid)
            if st["kind"] in ("revoked", "modified") and st.get("by_id") == change.ruling_id:
                return {
                    "effect": f"Relies on {rid}, {st['text'][0].lower()}{st['text'][1:]}",
                    "recheck": "needs_review",
                    "duty_before": None,
                    "duty_after": None,
                    "currency": "USD",
                }
        return None
    if change.kind == "schedule_revision":
        if not p.us_code or "US" not in (p.into or []):
            return None
        re_approved = p.versions.filter(kind="re_approved", at__date__gte=change.date).exists()
        return {
            "effect": f"{codes.fmt(p.us_code)} is unchanged in Revision 3",
            "recheck": "re_approved" if re_approved else "unchanged",
            "duty_before": None,
            "duty_after": None,
            "currency": "USD",
        }
    if not _touches(change, p) or change.date is None:
        return None
    country = "CA" if change.countries == ["CA"] else "US"
    before = _charges(country, p, change.date - timedelta(days=1))
    after = _charges(country, p, change.date)
    if before is None or after is None:
        return None
    cur = "CAD" if country == "CA" and (p.shipment or {}).get("value_cad") else "USD"
    if before == after:
        return None
    verb = "rose" if after > before else "fell"
    return {
        "effect": f"Duty {verb} from {money_words(before, cur)} to {money_words(after, cur)} per shipment",
        "recheck": "unchanged",
        "duty_before": before,
        "duty_after": after,
        "currency": cur,
    }


def scan(org: Organisation, progress=None) -> dict[str, Any]:
    changes = ensure_changes()
    products = list(Product.objects.filter(org=org, hidden_at__isnull=True))
    counts: dict[str, int] = {}
    for i, change in enumerate(changes):
        if progress:
            progress(
                0.1 + 0.8 * i / max(1, len(changes)),
                change.key,
                f"Checking {len(products)} binders against: {change.headline[:120]}…",
            )
        rows = []
        for p in products:
            try:
                row = assess(change, p)
            except Exception as exc:  # one odd product never stops the scan
                log.warning("watch_assess_failed", change=change.key, sku=p.sku, error=str(exc))
                continue
            if row is not None:
                rows.append(AffectedProduct(org=org, change=change, product=p, checked_at=clock.now(), **row))
        with transaction.atomic():
            AffectedProduct.objects.filter(org=org, change=change).delete()
            AffectedProduct.objects.bulk_create(rows)
        counts[change.key] = len(rows)
    return {"changes": len(changes), "affected": counts, "products": len(products)}
