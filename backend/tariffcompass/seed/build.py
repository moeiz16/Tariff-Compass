"""Build the sample organisations (docs/DATA.md "Seed plan"). Deterministic and relative to the demo clock.

History is replayed in date order so the activity record reads like the weeks before the demo day: binders
opened and decided in January and February, this week's decisions, the open docket, the training rounds and
this morning's change check. Answers are written by the real classification core (through `services`); every
ruling cited is a real CBP ruling from the corpus; training rounds come only from the core's committed run
reports, never from invented figures.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from functools import partial
from typing import Any

import structlog
from django.db import transaction

from tariffcompass import clock, codes, services
from tariffcompass.catalog import answers, binder
from tariffcompass.catalog.evidence import store
from tariffcompass.catalog.models import Answer, Entry, Product
from tariffcompass.lab import reports
from tariffcompass.lab.models import SignOff, TrainingRound
from tariffcompass.platform import audit
from tariffcompass.platform.models import Engagement, Job, Membership, Organisation, User
from tariffcompass.review import lessons
from tariffcompass.review.models import AlwaysReviewRule, Decision, Question, ReviewItem, TrainingExample
from tariffcompass.seed import documents
from tariffcompass.seed.catalog import BY_SKU, PRODUCTS, Item
from tariffcompass.seed.people import DEMO_PEOPLE, SAMPLE_BROKER_SLUG, SAMPLE_IMPORTER_SLUG, SAMPLE_PASSWORD

log = structlog.get_logger("tariffcompass.seed")
RNG_SEED = 20260219


# ── Corrections: what the classifier first proposed for each family, and the broker's reason ─────────────
# (family → (proposed US, proposed CA or None to keep, reason kind, reason))
WRONG: dict[str, tuple[str, str | None, str, str]] = {
    "vacuum": ("9617003000", None, "facts_differ", "Capacity is 591 ml, so it is a vessel not exceeding one litre"),
    "double_wall": (
        "9617001000",
        "9617000000",
        "facts_differ",
        "Air-insulated with no vacuum between the walls, so it is a steel household article of 7323, "
        "not a vacuum vessel of 9617",
    ),
    "ss_cook": ("7323930080", None, "heading_misread", "Saucepans and frying pans are kitchen ware, suffix 60"),
    "al_cook": ("7615102025", None, "facts_differ", "Pressed and forged aluminium, not cast"),
    "food": (
        "3924102000",
        None,
        "heading_misread",
        "Storage containers aren't plates, cups or bowls; they are other tableware and kitchenware",
    ),
    "knife": ("8211929060", None, "heading_misread", "Kitchen knives have their own statistical suffix"),
    "bike": (
        "8513102000",
        "8513101000",
        "facts_differ",
        "Made to be mounted and used on a bicycle, so it is lighting equipment of 8512, not a portable lamp of 8513",
    ),
    "torch": ("8512102000", "8512100000", "facts_differ", "Hand-held with no bicycle mount, so a flashlight of 8513"),
    "power_bank": ("8507600010", None, "heading_misread", "Not a vehicle's main battery; the other lithium-ion line"),
    "speaker": ("8518210000", None, "facts_differ", "Two drivers in one enclosure make it multiple loudspeakers"),
    "speaker1": ("8518220000", None, "facts_differ", "One driver: a single loudspeaker in its enclosure"),
    "charger": ("8504409520", None, "facts_differ", "The output is 30 W, not over 50 W"),
    "pullover": ("6110202010", None, "facts_differ", "Cut and sized for women, so the women's suffix"),
    "tee": ("6109100060", None, "facts_differ", "Men's T-shirt, not women's"),
    "base": ("6109901065", None, "facts_differ", "Men's top, not women's"),
    "fleece": (
        "6110303010",
        "6110300091",
        "heading_misread",
        "Full-zip jacket with pockets: a jacket of heading 6101, not a sweater of 6110",
    ),
    "anorak": ("6202402005", None, "facts_differ", "Men's garment: heading 6201"),
    "rain_w": ("6201402015", None, "facts_differ", "Women's garment: heading 6202"),
    "sock": ("6115969020", None, "facts_differ", "Cotton is the main fibre by weight"),
    "sock_syn": ("6115959000", None, "facts_differ", "Nylon and polyester predominate, not cotton"),
    "glove": ("6116939400", None, "facts_differ", "No fourchettes between the fingers"),
    "tent": ("6306229030", None, "ruling_elsewhere", "A backpacking tent, as in NY N304023"),
    "tarp": ("6306221000", None, "heading_misread", "A flat tarp isn't a tent"),
    "sleeping": ("9404304000", None, "facts_differ", "Synthetic fill; there is no down"),
    "lantern": ("9405418440", None, "facts_differ", "No solar panel, so not photovoltaic"),
    "stove": ("7321111060", None, "heading_misread", "It is a stove, not 'other' cooking appliances"),
    "stake": ("7326200090", None, "facts_differ", "Forged steel, not an article of wire"),
    "backpack": ("4202923131", None, "heading_misread", "Backpacks have their own suffix"),
    "duffel": ("4202923120", None, "heading_misread", "A duffel isn't a backpack"),
}

DOCKET = [  # sku, kind, days waiting, into, with
    ("NB-KT-0388", "differs", 3, "both", "broker"),
    ("NB-KT-0297", "differs", 1, "both", "broker"),
    ("NB-EL-0215", "unsure", 2, "both", "broker"),
    ("NB-OD-0731", "unsure", 4, "both", "broker"),
    ("NB-OD-0734", "ruling_changed", 3, "both", "broker"),
    ("NB-EL-0560", "always_review", 6, "both", "broker"),
    ("NB-EL-0563", "always_review", 5, "both", "broker"),
    ("NB-KT-0611", "always_review", 2, "both", "broker"),
    ("NB-KT-0645", "always_review", 1, "both", "broker"),
    ("NB-OD-0702", "always_review", 0, "both", "broker"),
    ("NB-AP-0118", "unsure", 2, "CA", "broker2"),
    ("NB-AP-0177", "unsure", 1, "CA", "broker2"),
    ("NB-AP-0207", "requested", 0, "both", "broker"),
    ("NB-BG-0807", "unsure", 1, "both", "broker"),
    ("NB-AP-0137", "unsure", 4, "both", "broker"),
]
PROPOSED_ONLY = ["NB-EL-0413", "NB-AP-0213", "NB-OD-0797", "NB-KT-0737", "NB-BG-0827"]
REVOKED_RELIED = ("NY N284187", "HQ H289250", date(2021, 10, 7))  # (relied on, revoked by, on)


@dataclass
class Ctx:
    north: Organisation
    drift: Organisation
    people: dict[str, User]
    roles: dict[str, str]
    rules: dict[str, AlwaysReviewRule] = field(default_factory=dict)
    products: dict[str, Product] = field(default_factory=dict)
    timeline: list[tuple[datetime, int, Callable[[], object]]] = field(default_factory=list)

    def at(self, when: datetime, fn: Callable[[], object]) -> None:
        self.timeline.append((when, len(self.timeline), fn))


def local_dt(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm), clock.local(clock.now()).tzinfo)


def today() -> date:
    return clock.today()


def demo_day(month: int, day: int) -> date:
    """A date in the demo's history window, shifted with the demo clock (19 Feb 2026 by default)."""
    anchor = date(2026, 2, 19)
    return today() - (anchor - date(2026, month, day))


# ── People ──────────────────────────────────────────────────────────────────────────────────────────────
def people_and_orgs() -> Ctx:
    north = Organisation.objects.create(
        name="Northbound Goods Co.",
        slug=SAMPLE_IMPORTER_SLUG,
        kind="importer",
        locations=["Vancouver, BC", "Seattle, WA"],
        timezone="America/Vancouver",
        is_sample=True,
        settings={
            "into": ["US", "CA"],
            "made_in": "CN",
            "ports": ["Seattle (3001)", "Vancouver (809)"],
            "always_send_to_broker": False,
        },
    )
    drift = Organisation.objects.create(
        name="Driftwood Customs Brokers",
        slug=SAMPLE_BROKER_SLUG,
        kind="broker",
        locations=["Blaine, WA", "Surrey, BC"],
        timezone="America/Vancouver",
        is_sample=True,
    )
    eng = Engagement.objects.create(
        broker_org=drift, importer_org=north, countries=["US", "CA"], started_on=demo_day(1, 6) - timedelta(days=310)
    )
    rows = [
        ("compliance", DEMO_PEOPLE["compliance"], north, "compliance", None, "", "#1F7A4D"),
        ("importer", DEMO_PEOPLE["importer"], north, "importer", None, "", "#8F5207"),
        ("admin", DEMO_PEOPLE["admin"], north, "admin", None, "", "#3A3A36"),
        (
            "broker",
            DEMO_PEOPLE["broker"],
            drift,
            "broker",
            eng,
            "Licensed customs broker (US), sample licence 34812",
            "#B42318",
        ),
        (
            "broker2",
            {
                "email": "rafael.ouellet@driftwood.example",
                "full_name": "Rafael Ouellet",
                "title": "Licensed customs broker, Canadian entries",
            },
            drift,
            "broker",
            eng,
            "Licensed customs broker (Canada), sample licence 7741",
            "#5A5A54",
        ),
    ]
    people: dict[str, User] = {}
    roles: dict[str, str] = {}
    for key, p, home, role, engagement, licence, color in rows:
        u = User.objects.create_user(
            p["email"], SAMPLE_PASSWORD, full_name=p["full_name"], licence=licence, avatar_color=color
        )
        Membership.objects.create(org=home, user=u, role=role, title=p["title"])
        if engagement is not None:
            Membership.objects.create(org=north, user=u, role="broker", title=p["title"], engagement=engagement)
        people[key], roles[key] = u, role
    return Ctx(north, drift, people, roles)


# ── Helpers that write history at a given moment ────────────────────────────────────────────────────────
def shipment(item: Item) -> dict[str, Any]:
    return {
        "value": str(item.value),
        "currency": "USD",
        "quantity": item.qty,
        "transport": item.transport,
        "value_cad": str(item.value_cad),
    }


def deciding(item: Item, note: str | None = None) -> dict[str, str] | None:
    if item.deciding is None:
        return None
    key, label, value, source = item.deciding
    return {"key": key, "label": label, "value": value, "source_note": note or source}


def run_answer(ctx: Ctx, p: Product, who: str, when: datetime, *, evidence: list | None = None) -> Answer:
    q: dict[str, Any] = {
        "text": p.listing_text,
        "made_in": p.made_in,
        "into": list(p.into),
        "product_id": str(p.pk),
        "evidence_ids": [str(e.pk) for e in evidence or []],
        "confirmed_facts": [],
        "shipment": {
            "value": {"amount": p.shipment["value"], "currency": "USD"},
            "quantity": p.shipment["quantity"],
            "transport": p.shipment["transport"],
        },
    }
    spec = " ".join(e.extracted_text for e in evidence or [] if e.extracted_text)
    facts = tuple(f for e in evidence or [] for f in (e.photo_facts or []))
    live = TrainingRound.objects.filter(org=ctx.north, status="live").values_list("n", flat=True).first()
    ans, payload = answers.run_core(
        q,
        spec_text=spec,
        photo_facts=facts,
        product_id=str(p.pk),
        shipment=p.shipment,
        classifier_round=live,
        broker="Driftwood",
    )
    a = Answer.objects.create(
        org=ctx.north,
        product=p,
        created_by=ctx.people[who],
        query_text=q["text"],
        made_in=p.made_in,
        us_code=codes.digits(ans.us.code) if ans.us else "",
        ca_code=codes.digits(ans.ca.code) if ans.ca else "",
        verdict=ans.verdict,
        payload=answers.jsonable(payload),
        lm_label=ans.lm_label,
        program_version=ans.program_version,
        first_stage_version=payload["provenance"]["first_stage_version"],
        search_version=payload["provenance"]["search_version"],
        classifier_round=live,
    )
    Answer.objects.filter(pk=a.pk).update(created_at=when)
    a.created_at = when
    audit.record(
        ctx.north,
        "answer.created",
        f"{ctx.people[who].full_name} classified {p.sku}: "
        f"{codes.fmt(a.us_code) if a.us_code else '-'} ({a.payload['verdict']['word_label']})",
        actor=ctx.people[who],
        actor_role=ctx.roles[who],
        target_type="product",
        target_id=str(p.pk),
        details={"label": p.sku, "answer": str(a.pk), "verdict": a.verdict},
        at=when,
    )
    return a


def propose(
    ctx: Ctx,
    p: Product,
    item: Item,
    when: datetime,
    *,
    us: str,
    ca: str,
    who: str = "importer",
    answer: Answer | None = None,
    evidence: list[str] | None = None,
    fact: dict | None = None,
) -> None:
    binder.append(
        p,
        "proposed",
        actor=ctx.people[who],
        actor_role=ctx.roles[who],
        us_code=us,
        ca_code=ca,
        standing="proposed",
        deciding_fact=fact if fact is not None else deciding(item),
        evidence=evidence or ["Listing"],
        rulings_relied=list(item.rulings),
        why="Classified from the listing.",
        answer=answer,
        action="answer.saved",
        summary=f"{ctx.people[who].full_name} saved a proposed code for {p.sku}",
        at=when,
    )


def decide(
    ctx: Ctx,
    p: Product,
    item: Item,
    when: datetime,
    *,
    kind: str,
    who: str = "broker",
    proposed_us: str,
    proposed_ca: str,
    reason_kind: str = "",
    reason: str = "",
    used_in: int | None = None,
    review_kind: str = "requested",
    relied: list[str] | None = None,
    why: str = "",
) -> ReviewItem:
    """A closed review item: opened a little before `when`, decided at `when` (approve or correct)."""
    u = ctx.people[who]
    opened = when - timedelta(hours=26)
    ri = ReviewItem.objects.create(
        org=ctx.north,
        product=p,
        kind=review_kind,
        detail="Sent for review before the first entry.",
        into="both",
        proposed_us=proposed_us,
        proposed_ca=proposed_ca,
        value=item.value,
        status="corrected" if kind == "corrected" else "approved",
        assigned_to=u,
        version=2,
        created_at=opened,
        decided_at=when,
    )
    final_us, final_ca = item.us, item.ca
    if kind == "corrected":
        lesson = lessons.lesson(
            reason_kind=reason_kind,
            reason=reason,
            proposed_us=proposed_us,
            final_us=final_us,
            proposed_ca=proposed_ca,
            final_ca=final_ca,
        )
        v = binder.append(
            p,
            "corrected",
            actor=u,
            actor_role="broker",
            us_code=final_us,
            ca_code=final_ca,
            standing="approved",
            why=reason + ".",
            rulings_relied=relied,
            action="review.corrected",
            summary=f"{u.full_name} ({u.licence}) corrected {p.sku} from {codes.fmt(proposed_us)} to "
            f"{codes.fmt(final_us)}",
            at=when,
        )
        d = Decision.objects.create(
            org=ctx.north,
            item=ri,
            action="correct",
            final_us=final_us,
            final_ca=final_ca,
            reason_kind=reason_kind,
            reason=reason,
            lesson=lesson,
            decided_by=u,
            licence=u.licence,
            binder_version=v.n,
            created_at=when,
        )
        ex = TrainingExample(
            org=ctx.north, product=p, decision=d, lesson=lesson, used_in_round=used_in, created_at=when, payload={}
        )
        ex.payload = lessons.example_payload(
            example_id=str(ex.pk),
            sku=p.sku,
            text=p.listing_text,
            made_in=p.made_in,
            into=list(p.into),
            proposed_us=proposed_us,
            proposed_ca=proposed_ca,
            us_code=final_us,
            ca_code=final_ca,
            reason_kind=reason_kind,
            reason=reason,
            lesson_text=lesson,
            ruling_relied=None,
            deciding_fact=None,
            decided_by=u.full_name,
            decided_on=clock.local(when).date().isoformat(),
        )
        ex.save()
    else:
        prior = p.versions.filter(kind__in=binder.DECIDED_KINDS).exists()
        v = binder.append(
            p,
            "re_approved" if prior else "approved",
            actor=u,
            actor_role="broker",
            us_code=final_us,
            ca_code=final_ca,
            standing="approved",
            rulings_relied=relied,
            why=why or "Approved as proposed.",
            action="review.approved",
            summary=f"{u.full_name} ({u.licence}) approved {p.sku} as {codes.fmt(final_us)}",
            at=when,
        )
        Decision.objects.create(
            org=ctx.north,
            item=ri,
            action="approve",
            final_us=final_us,
            final_ca=final_ca,
            reason=why,
            decided_by=u,
            licence=u.licence,
            binder_version=v.n,
            created_at=when,
        )
    return ri


def entry_duty(item: Item, country: str, on: date) -> Decimal:
    code = item.us if country == "US" else item.ca
    lc = answers.landed_cost(country, code, item.made_in, shipment(item), as_of=on)
    return lc.charges_total


# ── The parts of the story ──────────────────────────────────────────────────────────────────────────────
def make_products(ctx: Ctx) -> None:
    opened = local_dt(demo_day(1, 5), 9)
    for item in PRODUCTS:
        listing = item.listing
        if item.sku == "NB-KT-0388":  # the supplier's new listing (the classifier reads "insulated")
            listing = (
                "20 oz double-wall stainless steel camp tumbler, insulated, with a sliding lid. Keeps drinks "
                "cold for hours. Holds 591 ml."
            )
        p = Product.objects.create(
            org=ctx.north,
            sku=item.sku,
            title=item.title,
            category=item.category,
            made_in=item.made_in,
            into=list(item.into),
            listing_text=listing,
            unit_value=item.unit,
            currency="USD",
            shipment=shipment(item),
            material=item.material,
            created_by=ctx.people["importer"],
            created_at=opened,
            updated_at=opened,
        )
        ctx.products[item.sku] = p


def make_rules(ctx: Ctx) -> None:
    maya = ctx.people["compliance"]
    when = local_dt(demo_day(1, 8), 11)
    for key, kind, value, label in (
        ("lithium", "material", "lithium", "Anything with lithium cells"),
        ("steel", "chapter", "73", "Steel articles (Section 232 metal content)"),
        ("aluminium", "heading", "7615", "Aluminium kitchenware (Section 232 metal content)"),
        ("value", "value_over", "25000", "Entries over $25,000"),
    ):
        r = AlwaysReviewRule.objects.create(
            org=ctx.north, kind=kind, value=value, label=label, created_by=maya, created_at=when
        )
        ctx.rules[key] = r
        audit.record(
            ctx.north,
            "rule.created",
            f"{maya.full_name} added a review rule: {label}",
            actor=maya,
            actor_role="compliance",
            target_type="rule",
            target_id=str(r.pk),
            details={"kind": kind, "value": value, "label": label},
            at=when,
        )
        when += timedelta(minutes=4)


def hero_tumbler(ctx: Ctx) -> None:
    item = BY_SKU["NB-KT-0412"]
    p = ctx.products[item.sku]
    jordan, dana = ctx.people["importer"], ctx.people["broker"]
    t1 = local_dt(demo_day(1, 12), 9, 14)
    label, pdf = documents.spec_sheet(item.sku)
    spec = store(
        ctx.north,
        pdf,
        file_name="TC-20-spec-sheet-v3.pdf",
        kind="spec_sheet",
        uploaded_by=jordan,
        product=p,
        label=label,
    )
    pic = store(
        ctx.north,
        documents.photo(item.sku),
        file_name="TC-20-photo.png",
        kind="photo",
        uploaded_by=jordan,
        product=p,
        label="Photo",
    )
    a = run_answer(ctx, p, "importer", t1, evidence=[spec, pic])
    propose(
        ctx,
        p,
        item,
        t1 + timedelta(minutes=3),
        us=item.us,
        ca=item.ca,
        answer=a,
        evidence=["Listing", label, "Photo"],
        fact={
            "key": "between_walls",
            "label": "Between the walls",
            "value": "A vacuum",
            "source_note": "read from 'insulated'",
        },
    )
    t2 = local_dt(demo_day(1, 14), 15, 40)
    email_label, email = documents.supplier_email(item.sku)
    store(
        ctx.north,
        email,
        file_name="supplier-email-2026-01-14.pdf",
        kind="supplier_email",
        uploaded_by=jordan,
        product=p,
        label=email_label,
    )
    binder.append(
        p,
        "question_answered",
        actor=jordan,
        actor_role="importer",
        standing="proposed",
        deciding_fact={
            "key": "between_walls",
            "label": "Between the walls",
            "value": "A vacuum",
            "source_note": "confirmed by the supplier",
        },
        evidence=["Listing", label, "Photo", email_label],
        why="Asked the supplier what is between the walls; they confirmed it is vacuum-sealed.",
        action="answer.fact_confirmed",
        summary=f"{jordan.full_name} recorded the supplier's answer for {p.sku}",
        at=t2,
    )
    t3 = local_dt(demo_day(1, 15), 10, 12)
    binder.append(
        p,
        "approved",
        actor=dana,
        actor_role="broker",
        standing="approved",
        why="Vacuum-sealed per the supplier. Heading 9617 names vacuum vessels (GRI 1); HQ H303684 "
        "classifies vacuum-insulated stainless containers there. Capacity under one litre (GRI 6).",
        action="review.approved",
        summary=f"{dana.full_name} ({dana.licence}) approved {p.sku} as {codes.fmt(item.us)}",
        at=t3,
    )
    t4 = local_dt(demo_day(2, 17), 10, 12)
    binder.append(
        p,
        "re_approved",
        actor=dana,
        actor_role="broker",
        standing="approved",
        why="Re-checked against 2026 HTSUS Revision 3 (in force 12 Feb): the line is unchanged.",
        action="binder.rechecked",
        summary=f"{dana.full_name} re-approved {p.sku} after the Revision 3 re-check",
        at=t4,
    )
    for n, (country, day, number) in enumerate(
        (
            ("US", demo_day(2, 2), "DW3-0412871-4"),
            ("CA", demo_day(2, 10), "13952-0412-2026-0118"),
            ("US", demo_day(2, 16), "DW3-0413350-9"),
        )
    ):
        Entry.objects.create(
            org=ctx.north,
            product=p,
            entry_number=number,
            country=country,
            entered_on=day,
            code=item.us if country == "US" else item.ca,
            duty_paid=entry_duty(item, country, day),
            currency="USD" if country == "US" else "CAD",
        )
        del n


def history(ctx: Ctx, rng: random.Random) -> None:
    """Every other binder: proposed, then approved or corrected, this week or earlier."""
    skip = {"NB-KT-0412", *[d[0] for d in DOCKET], *PROPOSED_ONLY}
    rest = [i for i in PRODUCTS if i.sku not in skip]
    rng.shuffle(rest)
    week, earlier = rest[:40], rest[40:]
    week_corr = [i for i in week if i.family in WRONG][:9]
    week_ask = [i for i in week if i not in week_corr][:3]
    early_days = {
        i.sku: demo_day(1, 12) + timedelta(days=(n * 31) // max(1, len(earlier))) for n, i in enumerate(earlier)
    }
    january = [i for i in earlier if i.family in WRONG and early_days[i.sku] < demo_day(2, 1)]
    february = [i for i in earlier if i.family in WRONG and early_days[i.sku] >= demo_day(2, 1)]
    early_corr = january[:8] + february[:14]
    # at least two corrections change the heading (a light read as a torch, an air-insulated tumbler as vacuum)
    for fam in ("bike", "double_wall"):
        if not any(i.family == fam for i in early_corr + week_corr):
            cand = next((i for i in earlier if i.family == fam and i not in early_corr), None)
            if cand is not None:
                early_corr[0] = cand

    def schedule(
        item: Item, opened: datetime, decided: datetime, *, corrected: bool, used_in: int | None, asked: bool = False
    ) -> None:
        p = ctx.products[item.sku]
        wrong = WRONG.get(item.family)
        prop_us, prop_ca = (wrong[0], wrong[1] or item.ca) if corrected and wrong else (item.us, item.ca)
        if item.family == "vacuum" and item.us == "9617003000" and corrected:
            prop_us = "9617001000"
        who = (
            "broker2" if prop_us[:4] == item.us[:4] and item.category == "apparel" and rng.random() < 0.3 else "broker"
        )
        ctx.at(opened, lambda: propose(ctx, p, item, opened, us=prop_us, ca=prop_ca, fact=deciding(item)))
        if asked:
            q_at = decided - timedelta(hours=8)
            a_at = decided - timedelta(hours=3)

            def ask_and_answer() -> None:
                ri = ReviewItem.objects.create(
                    org=ctx.north,
                    product=p,
                    kind="requested",
                    detail="Sent for review before the first entry.",
                    into="both",
                    proposed_us=prop_us,
                    proposed_ca=prop_ca,
                    value=item.value,
                    status="answered",
                    assigned_to=ctx.people[who],
                    version=3,
                    created_at=opened,
                )
                text = f"Can you confirm the main material of the {item.title.lower()} by weight?"
                q = Question.objects.create(
                    org=ctx.north,
                    item=ri,
                    asked_by=ctx.people[who],
                    asked_at=q_at,
                    text=text,
                    options=[],
                    answer=f"{(item.material or 'As listed').capitalize()}, per the supplier's bill of materials.",
                    answered_by=ctx.people["importer"],
                    answered_at=a_at,
                )
                Decision.objects.create(
                    org=ctx.north,
                    item=ri,
                    action="ask",
                    reason=text,
                    decided_by=ctx.people[who],
                    licence=ctx.people[who].licence,
                    created_at=q_at,
                )
                Decision.objects.create(
                    org=ctx.north,
                    item=ri,
                    action="answer",
                    reason=q.answer,
                    decided_by=ctx.people["importer"],
                    created_at=a_at,
                )
                audit.record(
                    ctx.north,
                    "review.asked",
                    f"{ctx.people[who].full_name} asked Northbound about {p.sku}",
                    actor=ctx.people[who],
                    actor_role="broker",
                    target_type="product",
                    target_id=str(p.pk),
                    details={"label": p.sku, "question": text},
                    at=q_at,
                )
                binder.append(
                    p,
                    "question_answered",
                    actor=ctx.people["importer"],
                    actor_role="importer",
                    standing="in_review",
                    why=f"{ctx.people[who].full_name} asked: {text}",
                    action="review.answered",
                    summary=f"{ctx.people['importer'].full_name} answered the broker's question on {p.sku}",
                    at=a_at,
                )
                ReviewItem.objects.filter(pk=ri.pk).update(status="approved", decided_at=decided, version=4)
                v = binder.append(
                    p,
                    "approved",
                    actor=ctx.people[who],
                    actor_role="broker",
                    us_code=item.us,
                    ca_code=item.ca,
                    standing="approved",
                    why="Approved after the material was confirmed.",
                    action="review.approved",
                    summary=f"{ctx.people[who].full_name} "
                    f"({ctx.people[who].licence}) approved {p.sku} as {codes.fmt(item.us)}",
                    at=decided,
                )
                Decision.objects.create(
                    org=ctx.north,
                    item=ri,
                    action="approve",
                    final_us=item.us,
                    final_ca=item.ca,
                    decided_by=ctx.people[who],
                    licence=ctx.people[who].licence,
                    binder_version=v.n,
                    created_at=decided,
                )

            ctx.at(q_at, ask_and_answer)
            return
        if corrected and wrong:
            ctx.at(
                decided,
                lambda: decide(
                    ctx,
                    p,
                    item,
                    decided,
                    kind="corrected",
                    who=who,
                    proposed_us=prop_us,
                    proposed_ca=prop_ca,
                    reason_kind=wrong[2],
                    reason=wrong[3],
                    used_in=used_in,
                ),
            )
        else:
            ctx.at(
                decided,
                lambda: decide(
                    ctx, p, item, decided, kind="approved", who=who, proposed_us=prop_us, proposed_ca=prop_ca
                ),
            )

    week_days = [demo_day(2, 13) + timedelta(days=i) for i in range(7)]
    for i, item in enumerate(week):
        day = week_days[i % 7]
        decided = local_dt(day, 9 + (i % 7), (i * 13) % 60)
        if decided > clock.now() - timedelta(minutes=30):
            decided = clock.now() - timedelta(hours=2, minutes=i)
        opened = decided - timedelta(days=1 + i % 3, hours=3)
        schedule(item, opened, decided, corrected=item in week_corr, used_in=None, asked=item in week_ask)
    for i, item in enumerate(earlier):
        day = early_days[item.sku]
        decided = local_dt(day, 10 + i % 6, (i * 7) % 60)
        opened = decided - timedelta(days=2, hours=1)
        used = 7 if day < demo_day(2, 1) else None
        schedule(item, opened, decided, corrected=item in early_corr, used_in=used)
    for i, sku in enumerate(PROPOSED_ONLY):
        item = BY_SKU[sku]
        when = clock.now() - timedelta(hours=30 - i * 5)
        ctx.at(when, partial(propose, ctx, ctx.products[item.sku], item, when, us=item.us, ca=item.ca))


def docket(ctx: Ctx) -> None:
    """Driftwood's open docket: about fifteen items waiting 0–6 days."""
    for idx, (sku, kind, days, into, with_) in enumerate(DOCKET):
        item = BY_SKU[sku]
        p = ctx.products[sku]
        opened = clock.now() - timedelta(days=days, hours=1 + idx % 5, minutes=(idx * 11) % 60)

        def build(item=item, p=p, kind=kind, into=into, with_=with_, opened=opened, idx=idx) -> None:
            evidence = []
            if item.sku in documents.SPEC_SHEETS and item.sku != "NB-KT-0412":
                label, pdf = documents.spec_sheet(item.sku)
                evidence.append(
                    store(
                        ctx.north,
                        pdf,
                        file_name=f"{item.sku.lower()}-spec-sheet.pdf",
                        kind="spec_sheet",
                        uploaded_by=ctx.people["importer"],
                        product=p,
                        label=label,
                    )
                )
            if item.sku in documents.PHOTOS and item.sku != "NB-KT-0412":
                evidence.append(
                    store(
                        ctx.north,
                        documents.photo(item.sku),
                        file_name=f"{item.sku.lower()}.png",
                        kind="photo",
                        uploaded_by=ctx.people["importer"],
                        product=p,
                        label="Photo",
                    )
                )
            a = run_answer(
                ctx, p, "importer" if idx % 3 else "compliance", opened - timedelta(minutes=2), evidence=evidence
            )
            us = a.us_code or item.us
            ca = a.ca_code or item.ca
            last = p.versions.filter(kind__in=binder.DECIDED_KINDS).order_by("-n").first()
            binder.append(
                p,
                "proposed",
                actor=a.created_by,
                actor_role="importer",
                us_code=us,
                ca_code=ca,
                standing="in_review",
                deciding_fact=deciding(item),
                evidence=["Listing", *[e.label for e in evidence]],
                rulings_relied=[
                    r["id"]
                    for r in a.payload.get("rulings", [])
                    if r["status"]["kind"] == "in_force" and "different_heading" not in r.get("match", [])
                ]
                or list(item.rulings),
                why=a.payload.get("holding_sentence", ""),
                answer=a,
                action="answer.saved",
                summary=f"{a.created_by.full_name if a.created_by else 'Northbound'} saved the answer to the {p.sku} binder",
                at=opened - timedelta(minutes=1),
            )
            detail, rule, change, misread, phrases = docket_detail(ctx, item, kind, us, last)
            if kind == "ruling_changed":
                us, ca = item.us, item.ca
            ri = ReviewItem.objects.create(
                org=ctx.north,
                product=p,
                answer=a,
                kind=kind,
                detail=detail,
                into=into,
                proposed_us=us,
                proposed_ca=ca,
                previous_us=last.us_code if last else "",
                value=item.value,
                status="waiting",
                assigned_to=ctx.people[with_],
                rule=rule,
                ruling_change=change,
                misread=misread,
                deciding_phrases=phrases,
                leaning=a.verdict == "broker",
                created_at=opened,
                note="New supplier in Mexico: can we claim USMCA?" if kind == "requested" else "",
            )
            Product.objects.filter(pk=p.pk).update(standing="in_review")
            audit.record(
                ctx.north,
                "review.opened",
                f"{p.sku} went to Driftwood: {ri.get_kind_display().lower()}",
                target_type="product",
                target_id=str(p.pk),
                details={"label": p.sku, "kind": kind},
                at=opened,
            )
            if item.sku == "NB-EL-0563":
                q_at = opened + timedelta(hours=3)
                text = "Is the solar panel built in, or a separate panel packed with the power bank?"
                Question.objects.create(
                    org=ctx.north,
                    item=ri,
                    asked_by=ctx.people["broker"],
                    asked_at=q_at,
                    text=text,
                    options=["Built in", "Packed separately"],
                )
                Decision.objects.create(
                    org=ctx.north,
                    item=ri,
                    action="ask",
                    reason=text,
                    decided_by=ctx.people["broker"],
                    licence=ctx.people["broker"].licence,
                    created_at=q_at,
                )
                ReviewItem.objects.filter(pk=ri.pk).update(status="asked", version=2)
                audit.record(
                    ctx.north,
                    "review.asked",
                    f"Dana Whitlock asked Northbound about {p.sku}",
                    actor=ctx.people["broker"],
                    actor_role="broker",
                    target_type="product",
                    target_id=str(p.pk),
                    details={"label": p.sku, "question": text},
                    at=q_at,
                )

        ctx.at(opened - timedelta(minutes=3), build)

        # earlier history for the items whose story needs it
        if sku == "NB-KT-0388":
            t1, t2 = local_dt(demo_day(1, 5), 10), local_dt(demo_day(1, 6), 11, 20)
            ctx.at(t1, partial(propose, ctx, p, item, t1, us=item.us, ca=item.ca))
            ctx.at(
                t2,
                partial(
                    decide,
                    ctx,
                    p,
                    item,
                    t2,
                    kind="approved",
                    proposed_us=item.us,
                    proposed_ca=item.ca,
                    why="Air-insulated per the spec sheet: heading 7323.",
                ),
            )
        if sku == "NB-KT-0297":
            t1, t2 = local_dt(demo_day(1, 19), 9, 30), local_dt(demo_day(1, 20), 14, 5)
            ctx.at(t1, partial(propose, ctx, p, item, t1, us=item.us, ca=item.ca))
            ctx.at(
                t2,
                partial(
                    decide,
                    ctx,
                    p,
                    item,
                    t2,
                    kind="approved",
                    proposed_us=item.us,
                    proposed_ca=item.ca,
                    relied=["NY N297165"],
                    why="Following NY N297165 (insulated steel tumblers, 7323).",
                ),
            )
        if sku == "NB-OD-0734":
            t1, t2 = local_dt(demo_day(1, 10), 9), local_dt(demo_day(1, 13), 16, 40)
            ctx.at(t1, partial(propose, ctx, p, item, t1, us=item.us, ca=item.ca))
            ctx.at(
                t2,
                partial(
                    decide,
                    ctx,
                    p,
                    item,
                    t2,
                    kind="approved",
                    proposed_us=item.us,
                    proposed_ca=item.ca,
                    relied=[REVOKED_RELIED[0]],
                    why=f"Lamp of heading 9405, as in {REVOKED_RELIED[0]}.",
                ),
            )


def docket_detail(ctx: Ctx, item: Item, kind: str, us: str, last) -> tuple[str, Any, Any, str, list]:
    rule = None
    change = None
    misread = ""
    phrases: list[dict[str, Any]] = []
    if kind == "differs":
        prev = last.us_code if last else item.us
        detail = f"Proposed {codes.fmt(us)}; the last approved code was {codes.fmt(prev)}."
        if item.sku == "NB-KT-0388":
            _, lines = documents.SPEC_SHEETS[item.sku]
            text = " ".join(lines)
            start = text.find("air-insulated")
            phrases = (
                [{"source": "spec_sheet", "start": start, "end": start + len("air-insulated")}] if start >= 0 else []
            )
            misread = "It read “insulated” in the new listing as vacuum-insulated; the spec sheet says air-insulated."
        if item.sku == "NB-KT-0297":
            detail += " HQ H303684 puts vacuum-insulated stainless containers in 9617."
    elif kind == "unsure":
        detail = {
            "NB-EL-0215": "One fact decides it: does the lamp head also work as a hand torch?",
            "NB-OD-0731": "A lantern with a power-bank port: lamp of 9405 or battery of 8507?",
            "NB-AP-0118": "Canada splits brushed cotton pullovers (6110.20.00.12) from other cotton pullovers.",
            "NB-AP-0177": "Canada: confirm the shell is nylon (6202.40.00.10) and not polyester.",
            "NB-BG-0807": "A backpack with a padded laptop sleeve: backpack or briefcase-type case?",
            "NB-AP-0137": "Merino-blend: which fibre predominates by weight decides the line.",
        }.get(item.sku, "The classifier wasn't sure.")
    elif kind == "ruling_changed":
        relied, by, on = REVOKED_RELIED
        detail = f"Binder v2 relied on {relied}, which {by} revoked."
        change = {"kind": "revoked", "by_id": by, "date": on.isoformat()}
    elif kind == "always_review":
        rule = ctx.rules[
            {
                "NB-EL-0560": "lithium",
                "NB-EL-0563": "lithium",
                "NB-KT-0611": "steel",
                "NB-KT-0645": "aluminium",
                "NB-OD-0702": "value",
            }[item.sku]
        ]
        detail = f"Always reviewed: {rule.label}."
        if item.sku == "NB-OD-0702":
            detail = f"Always reviewed: entry value ${item.value:,.0f} is over $25,000."
    else:
        detail = "Sent for review by Jordan Tse: new supplier in Mexico; does USMCA apply?"
    return detail, rule, change, misread, phrases


# ── Lab rounds (only from the core's committed reports) ─────────────────────────────────────────────────
ROUNDS = {
    4: ("retired", demo_day(1, 2) - timedelta(days=31), "Live through January; retired when round 6 went live."),
    5: ("not_made_live", demo_day(1, 6), "Worse on knitted apparel, so round 4 stayed live."),
    6: ("live", demo_day(1, 28), "Trained on rulings plus the first broker corrections."),
    7: ("waiting_signoff", demo_day(2, 19), "Trained on rulings plus broker corrections up to 31 Jan."),
}


def lab_rounds(ctx: Ctx) -> int:
    maya, dana = ctx.people["compliance"], ctx.people["broker"]
    made = 0
    for n, (status, trained, note) in ROUNDS.items():
        report = reports.committed(n)
        if report is None:
            log.warning("seed_round_missing", round=n, hint="run `make optimize ROUND=n` to produce its report")
            continue
        loaded = reports.load(report)
        started = local_dt(trained, 6, 10) if n == 7 else local_dt(trained, 8, 30)

        def build(
            n=n, status=status, trained=trained, note=note, report=report, loaded=loaded, started=started
        ) -> None:
            r = TrainingRound.objects.create(
                org=ctx.north,
                n=n,
                status=status,
                note=note,
                trained_on=trained,
                lm_label=loaded.lm_label,
                reflection_lm_label=loaded.reflection_lm_label,
                data_snapshot=loaded.data_snapshot,
                seed=loaded.seed,
                report=report,
                program_path=loaded.program_path,
                started_by=maya,
                created_at=started,
            )
            audit.record(
                ctx.north,
                "lab.round_finished",
                f"Training round {n} finished and is waiting for sign-off",
                target_type="round",
                target_id=str(n),
                details={"round": n},
                at=started + timedelta(minutes=9),
            )
            checks = [{"key": g.get("key"), "passed": g.get("passed")} for g in report.get("gates", [])]
            if status in ("live", "retired"):
                go_live = local_dt(trained + timedelta(days=2), 15, 30)
                for who, minute in ((maya, 0), (dana, 42)):
                    s_at = go_live - timedelta(minutes=60 - minute)
                    SignOff.objects.create(
                        round=r,
                        user=who,
                        role="compliance" if who == maya else "broker",
                        statement=who.full_name,
                        checks=checks,
                        signed_at=s_at,
                    )
                    audit.record(
                        ctx.north,
                        "lab.signed",
                        f"{who.full_name} signed training round {n}",
                        actor=who,
                        actor_role="compliance" if who == maya else "broker",
                        target_type="round",
                        target_id=str(n),
                        details={"round": n},
                        at=s_at,
                    )
                r.live_from = go_live
                if status == "retired":
                    r.live_to = local_dt(ROUNDS[6][1] + timedelta(days=2), 15, 30)
                r.save(update_fields=["live_from", "live_to"])
                audit.record(
                    ctx.north,
                    "lab.made_live",
                    f"Training round {n} went live, signed by {maya.full_name} and {dana.full_name}",
                    target_type="round",
                    target_id=str(n),
                    details={"round": n},
                    at=go_live,
                )
            if status == "waiting_signoff":
                s_at = local_dt(trained, 9, 48)
                if s_at < clock.now():
                    SignOff.objects.create(
                        round=r, user=maya, role="compliance", statement=maya.full_name, checks=checks, signed_at=s_at
                    )
                    audit.record(
                        ctx.north,
                        "lab.signed",
                        f"{maya.full_name} signed training round {n} (1 of 2)",
                        actor=maya,
                        actor_role="compliance",
                        target_type="round",
                        target_id=str(n),
                        details={"round": n, "signatures": 1},
                        at=s_at,
                    )

        ctx.at(started, build)
        made += 1
    return made


def morning_check(ctx: Ctx) -> dict[str, Any]:
    from tariffcompass.watch.scan import scan

    at = local_dt(today(), 6, 0)
    result = scan(ctx.north)
    job = Job.objects.create(
        org=ctx.north,
        kind="watch_scan",
        status="succeeded",
        progress=1.0,
        message="Checked every binder",
        result=result,
        created_at=at,
        started_at=at,
        finished_at=at + timedelta(seconds=40),
    )
    audit.record(
        ctx.north,
        "watch.scanned",
        f"Checked {result['products']} binders against {result['changes']} changes",
        target_type="watch",
        target_id=str(job.pk),
        details=result,
        at=at + timedelta(seconds=40),
    )
    return result


# ── Entry point ─────────────────────────────────────────────────────────────────────────────────────────
def exists() -> bool:
    return Organisation.objects.filter(slug=SAMPLE_IMPORTER_SLUG).exists()


def build() -> dict[str, Any]:
    rng = random.Random(RNG_SEED)  # noqa: S311 - a reproducible sample, not security
    services.reset()
    with transaction.atomic():
        ctx = people_and_orgs()
        make_products(ctx)
        make_rules(ctx)
        audit.record(
            ctx.north,
            "org.created",
            "Northbound Goods Co. joined Tariff Compass (sample organisation)",
            target_type="org",
            target_id=str(ctx.north.pk),
            at=local_dt(demo_day(1, 5), 8, 30),
        )
        rounds = lab_rounds(ctx)
        ctx.at(local_dt(demo_day(1, 12), 9, 0), partial(hero_tumbler, ctx))
        history(ctx, rng)
        docket(ctx)
        for _, _, fn in sorted(ctx.timeline, key=lambda t: (t[0], t[1])):
            fn()
    result = morning_check(ctx)
    audit.record(
        ctx.north,
        "seed.loaded",
        "Sample data loaded for the demo (Northbound Goods Co. and Driftwood Customs Brokers)",
        target_type="org",
        target_id=str(ctx.north.pk),
    )
    return {
        "products": Product.objects.filter(org=ctx.north).count(),
        "docket": ReviewItem.objects.filter(org=ctx.north, status__in=("waiting", "asked", "answered")).count(),
        "corrections_waiting": TrainingExample.objects.filter(org=ctx.north, used_in_round__isnull=True).count(),
        "rounds": rounds,
        "watch": result["affected"],
    }
