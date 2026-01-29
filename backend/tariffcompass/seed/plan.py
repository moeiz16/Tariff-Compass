"""Which sample binders the seed decides, when, and how, as a pure function of the catalogue (no database).

The seed replays this plan; the classification core reads the same broker corrections for the demo's training
rounds (`corrections_for_round(7)`), so the corrections a round learned from are exactly the ones in the seeded
docket history. Same catalogue and demo day give the same plan, ids included.
"""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from tariffcompass.review import lessons
from tariffcompass.seed.catalog import PRODUCTS, Item

ANCHOR = date(2026, 2, 19)  # the default demo day; every date below shifts with TARIFF_COMPASS_DEMO_TODAY
RNG_SEED = 20260219
NAMESPACE = uuid.UUID("6f1f6d1e-8e2a-4c55-9a0e-2a7c1b9e4d10")
BROKERS = {"broker": "Dana Whitlock", "broker2": "Rafael Ouellet"}

# family → (what the classifier first proposed for US, for Canada or None to keep, reason kind, broker's reason)
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

DOCKET_SKUS = (
    "NB-KT-0388",
    "NB-KT-0297",
    "NB-EL-0215",
    "NB-OD-0731",
    "NB-OD-0734",
    "NB-EL-0560",
    "NB-EL-0563",
    "NB-KT-0611",
    "NB-KT-0645",
    "NB-OD-0702",
    "NB-AP-0118",
    "NB-AP-0177",
    "NB-AP-0207",
    "NB-BG-0807",
    "NB-AP-0137",
)
PROPOSED_ONLY = ("NB-EL-0413", "NB-AP-0213", "NB-OD-0797", "NB-KT-0737", "NB-BG-0827")


def demo_day(today: date, month: int, day: int) -> date:
    return today - (ANCHOR - date(2026, month, day))


@dataclass(frozen=True)
class Plan:
    week: list[Item]  # decided in the seven days before the demo day
    earlier: list[Item]  # decided from 12 Jan to 11 Feb
    week_corrections: list[Item]
    week_questions: list[Item]
    early_corrections: list[Item]
    decided_on: dict[str, date]  # sku → day decided
    used_in_round: dict[str, int | None]  # sku → training round that learned from the correction


def plan(today: date = ANCHOR) -> Plan:
    rng = random.Random(RNG_SEED)  # noqa: S311 - a reproducible sample, not security
    skip = {"NB-KT-0412", *DOCKET_SKUS, *PROPOSED_ONLY}
    rest = [i for i in PRODUCTS if i.sku not in skip]
    rng.shuffle(rest)
    week, earlier = rest[:40], rest[40:]
    week_corr = [i for i in week if i.family in WRONG][:9]
    week_ask = [i for i in week if i not in week_corr][:3]
    decided = {i.sku: demo_day(today, 2, 13) + timedelta(days=n % 7) for n, i in enumerate(week)}
    decided |= {
        i.sku: demo_day(today, 1, 12) + timedelta(days=(n * 31) // max(1, len(earlier))) for n, i in enumerate(earlier)
    }
    feb1 = demo_day(today, 2, 1)
    january = [i for i in earlier if i.family in WRONG and decided[i.sku] < feb1]
    february = [i for i in earlier if i.family in WRONG and decided[i.sku] >= feb1]
    early_corr = january[:8] + february[:14]
    # at least two corrections change the heading (a light read as a torch, an air-insulated tumbler as vacuum)
    for fam in ("bike", "double_wall"):
        if not any(i.family == fam for i in early_corr + week_corr):
            cand = next((i for i in earlier if i.family == fam and i not in early_corr), None)
            if cand is not None:
                early_corr[0] = cand
    used = {i.sku: (7 if decided[i.sku] < feb1 else None) for i in early_corr}
    used |= {i.sku: None for i in week_corr}
    return Plan(week, earlier, week_corr, week_ask, early_corr, decided, used)


def proposed_for(item: Item, corrected: bool) -> tuple[str, str]:
    wrong = WRONG.get(item.family)
    if not (corrected and wrong):
        return item.us, item.ca
    us, ca = wrong[0], wrong[1] or item.ca
    if item.family == "vacuum" and item.us == "9617003000":
        us = "9617001000"
    return us, ca


def broker_for(item: Item, proposed_us: str) -> str:
    """Rafael takes some Canadian-facing apparel suffix questions; Dana everything else (stable per SKU)."""
    pick = int(hashlib.sha256(item.sku.encode()).hexdigest(), 16) % 10
    return "broker2" if proposed_us[:4] == item.us[:4] and item.category == "apparel" and pick < 3 else "broker"


def example_id(sku: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"correction:{sku}"))


def correction(item: Item, decided_on: date) -> dict[str, Any]:
    """The training example for a seeded correction, in the format the optimiser reads."""
    wrong = WRONG[item.family]
    prop_us, prop_ca = proposed_for(item, True)
    text = lessons.lesson(
        reason_kind=wrong[2],
        reason=wrong[3],
        proposed_us=prop_us,
        final_us=item.us,
        proposed_ca=prop_ca,
        final_ca=item.ca,
    )
    return lessons.example_payload(
        example_id=example_id(item.sku),
        sku=item.sku,
        text=item.listing,
        made_in=item.made_in,
        into=list(item.into),
        proposed_us=prop_us,
        proposed_ca=prop_ca,
        us_code=item.us,
        ca_code=item.ca,
        reason_kind=wrong[2],
        reason=wrong[3],
        lesson_text=text,
        ruling_relied=None,
        deciding_fact=None,
        decided_by=BROKERS[broker_for(item, prop_us)],
        decided_on=decided_on.isoformat(),
    )


def corrections(today: date = ANCHOR) -> list[tuple[dict[str, Any], int | None]]:
    """Every seeded correction with the round that learned from it (None = waiting for the next round)."""
    p = plan(today)
    items = sorted(p.early_corrections + p.week_corrections, key=lambda i: (p.decided_on[i.sku], i.sku))
    return [(correction(i, p.decided_on[i.sku]), p.used_in_round[i.sku]) for i in items]


def corrections_for_round(n: int, today: date = ANCHOR) -> list[dict[str, Any]]:
    """The broker corrections training round `n` learned from (round 7: those decided before 1 Feb)."""
    return [c for c, used in corrections(today) if used == n]
