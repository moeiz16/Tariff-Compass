"""Product facts read from a description, the distinctions that decide between neighbouring headings, and the
fact-by-fact comparison of a product with a ruling's article.

A fact carries where it came from: *stated* (the words are in the description), *read* (inferred from other
words, e.g. "insulated" read as a vacuum between the walls), *assumed* (a default), *unknown* (not stated).
Read and unknown facts that decide between two headings make the answer "Needs a broker".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tariffcompass.contracts import Fact, FactCompare


@dataclass(frozen=True)
class FactRule:
    key: str
    label: str
    patterns: tuple[tuple[str, str], ...]  # (regex, value) in priority order: the first match wins


RULES: tuple[FactRule, ...] = (
    FactRule("material", "Material", (
        (r"\bstainless(?:[ -]steel)?\b", "Stainless steel"), (r"\b(?:carbon |cold[- ]rolled )?steel\b", "Steel"),
        (r"\balumin(?:i)?um\b", "Aluminium"), (r"\bcast iron\b", "Cast iron"), (r"\bcopper\b", "Copper"),
        (r"\bglass\b", "Glass"), (r"\bceramic|porcelain|stoneware\b", "Ceramic"),
        (r"\bpolypropylene|polyethylene|abs\b|\bplastics?\b|\bsilicone\b|\bpvc\b", "Plastic"),
        (r"\bcotton\b", "Cotton"), (r"\bpolyester|nylon|man-made fib|synthetic fib|acrylic\b", "Man-made fibres"),
        (r"\bwool|merino\b", "Wool"), (r"\bleather\b", "Leather"), (r"\bwood(?:en)?|bamboo\b", "Wood"),
    )),
    FactRule("between_walls", "Between the walls", (
        (r"\bno vacuum|not vacuum|without (?:a )?vacuum|air[- ]insulated|only air\b", "Air"),
        (r"\bvacuum\b|air (?:has been |is )?removed|evacuated\b", "A vacuum"),
    )),
    FactRule("construction", "Construction", (
        (r"\bknit(?:ted)?\b|\bcrochet", "Knitted"), (r"\bwoven\b", "Woven"),
        (r"\bdouble[- ]wall(?:ed)?\b", "Double-walled"), (r"\bsingle[- ]wall(?:ed)?\b", "Single-walled"),
        (r"\bcast\b", "Cast"), (r"\bstamped|pressed\b", "Pressed"),
    )),
    FactRule("power", "Power", (
        (r"\blithium[- ]ion|li-ion|lithium\b", "Lithium-ion battery"), (r"\brechargeable|usb[- ]?c?\b", "Rechargeable"),
        (r"\bbatter(?:y|ies)\b", "Batteries"), (r"\bmains|plug[- ]in|120 ?v|ac adapter\b", "Mains"),
        (r"\bsolar\b", "Solar"),
    )),
    FactRule("use", "Use", (
        (r"\b(?:bicycle|bike)\b.*\b(?:detach\w*|removable)\b", "On a bicycle; the lamp head detaches"),
        (r"\bbicycle|bike|cycling\b", "On a bicycle"),
        (r"\bhand[- ]held|handheld|flashlight|torch\b", "Held in the hand"),
        (r"\bhead ?lamp|headlamp\b", "Worn on the head"), (r"\bcamp(?:ing)?\b", "Camping"),
        (r"\bkitchen|cook(?:ing|ware)\b", "Kitchen"), (r"\bbeverage|drink(?:ing)?\b", "Holding drinks"),
        (r"\bhik(?:e|ing)|outdoor\b", "Outdoors"),
    )),
    FactRule("wearer", "Made for", (
        (r"\bwomen'?s|ladies|female\b", "Women"), (r"\bmen'?s\b|\bmale\b", "Men"),
        (r"\bgirls'?\b", "Girls"), (r"\bboys'?\b", "Boys"), (r"\bchildren|kids|infant|baby\b", "Children"),
        (r"\bunisex\b", "Anyone"),
    )),
    FactRule("form", "What it is", (
        (r"\btumbler\b", "A tumbler"), (r"\bbottle|flask\b", "A bottle or flask"), (r"\bmug\b", "A mug"),
        (r"\bpullover|sweater|jumper|cardigan\b", "A pullover"), (r"\bt-shirt|tee\b", "A T-shirt"),
        (r"\bjacket|coat|anorak|parka\b", "A jacket"), (r"\bbackpack|rucksack|knapsack\b", "A backpack"),
        (r"\bpower bank|battery pack\b", "A battery pack"), (r"\bcharger|power adapter|power supply\b", "A charger"),
        (r"\bspeaker\b", "A loudspeaker"), (r"\blantern\b", "A lantern"),
        (r"\bhead ?light|tail ?light|bike light\b", "A light"),
        (r"\bpot|pan|skillet|saucepan|wok\b", "A cooking vessel"), (r"\bcontainer|canister|jar\b", "A container"),
        (r"\btent\b", "A tent"), (r"\bsleeping bag\b", "A sleeping bag"), (r"\bglove|mitten\b", "Gloves"),
        (r"\bsock\b", "Socks"), (r"\bstake|peg\b", "Stakes or pegs"), (r"\bknife|knives\b", "A knife"),
    )),
)  # fmt: skip

_CAPACITY = re.compile(r"(\d+(?:\.\d+)?)\s*(fl\.?\s*oz|oz|ounces?|ml|millilit(?:er|re)s?|l\b|lit(?:er|re)s?)", re.I)
_INFERRED = (
    # (fact key, trigger, value read, note)
    ("between_walls", r"\binsulat(?:ed|ion)\b", "A vacuum", "read from 'insulated'"),
    ("between_walls", r"\bdouble[- ]wall(?:ed)?\b", "A vacuum", "read from 'double-wall'"),
)


def capacity_litres(text: str) -> float | None:
    m = _CAPACITY.search(text)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2).lower()
    if unit.startswith(("oz", "fl", "ounce")):
        return round(n * 0.0295735, 3)
    if unit.startswith("m"):
        return round(n / 1000, 3)
    return n


def extract(text: str, confirmed: tuple[tuple[str, str], ...] = ()) -> list[Fact]:
    """Facts from the description, with their sources; confirmed facts (the deciding question) win."""
    t = text.lower()
    facts: dict[str, Fact] = {}
    for rule in RULES:
        for pat, value in rule.patterns:
            m = re.search(pat, t)
            if m:
                facts[rule.key] = Fact(rule.key, rule.label, value, "stated", f"your description: '{m.group(0)}'")
                break
    if "between_walls" not in facts:
        for key, pat, value, note in _INFERRED:
            if re.search(pat, t):
                facts[key] = Fact(key, "Between the walls", value, "read", note)
                break
    cap = capacity_litres(text)
    if cap is not None:
        ml = round(cap * 1000)
        facts["capacity"] = Fact(
            "capacity", "Capacity", f"{ml} ml" if cap < 1 else f"{cap:g} litres", "stated", "your description"
        )
    for key, answer in confirmed:
        label = next((r.label for r in RULES if r.key == key), key.replace("_", " ").capitalize())
        facts[key] = Fact(key, label, answer, "stated", "confirmed by you")
    order = [r.key for r in RULES] + ["capacity"]
    return sorted(facts.values(), key=lambda f: order.index(f.key) if f.key in order else 99)


@dataclass(frozen=True)
class Distinction:
    key: str
    label: str
    question: str
    options: tuple[tuple[str, str, str], ...]  # (answer key, label, heading it leads to)
    leads: dict[str, str] = field(default_factory=dict)  # fact value read from a description → heading


DISTINCTIONS: dict[frozenset[str], Distinction] = {
    frozenset({"9617", "7323"}): Distinction(
        "between_walls", "Between the walls", "Is there a vacuum between the walls, or only air?",
        (("vacuum", "It's vacuum-sealed", "9617"), ("air", "Only air between the walls", "7323")),
        {"A vacuum": "9617", "Air": "7323"},
    ),
    frozenset({"9617", "7615"}): Distinction(
        "between_walls", "Between the walls", "Is there a vacuum between the walls, or only air?",
        (("vacuum", "It's vacuum-sealed", "9617"), ("air", "Only air between the walls", "7615")),
        {"A vacuum": "9617", "Air": "7615"},
    ),
    frozenset({"9617", "3924"}): Distinction(
        "between_walls", "Between the walls", "Is there a vacuum between the walls, or only air?",
        (("vacuum", "It's vacuum-sealed", "9617"), ("air", "Only air between the walls", "3924")),
        {"A vacuum": "9617", "Air": "3924"},
    ),
    frozenset({"8512", "8513"}): Distinction(
        "use", "Use", "Is it made only to ride on the bike, or does it also work as a hand torch?",
        (("bike", "Only on the bike", "8512"), ("torch", "It also works as a hand torch", "8513")),
        {"On a bicycle": "8512", "Held in the hand": "8513"},
    ),
    frozenset({"8507", "8504"}): Distinction(
        "form", "What it does", "Does it store energy in its own cells, or only convert power from the wall?",
        (("stores", "It stores energy (a battery pack)", "8507"), ("converts", "It only converts power", "8504")),
        {"A battery pack": "8507", "A charger": "8504"},
    ),
    frozenset({"8513", "9405"}): Distinction(
        "power", "Power", "Does it run on its own batteries and get carried by hand, or plug into the mains?",
        (("own", "Its own batteries, carried by hand", "8513"), ("mains", "It plugs into the mains", "9405")),
        {"Batteries": "8513", "Rechargeable": "8513", "Mains": "9405"},
    ),
    frozenset({"6110", "6109"}): Distinction(
        "form", "What it is", "Is it a pullover or sweater, or a T-shirt or vest?",
        (("pullover", "A pullover or sweater", "6110"), ("tshirt", "A T-shirt or vest", "6109")),
        {"A pullover": "6110", "A T-shirt": "6109"},
    ),
    frozenset({"6110", "6201"}): Distinction(
        "construction", "Construction", "Is the fabric knitted, or woven?",
        (("knit", "Knitted", "6110"), ("woven", "Woven", "6201")),
        {"Knitted": "6110", "Woven": "6201"},
    ),
    frozenset({"6101", "6201"}): Distinction(
        "construction", "Construction", "Is the fabric knitted, or woven?",
        (("knit", "Knitted", "6101"), ("woven", "Woven", "6201")),
        {"Knitted": "6101", "Woven": "6201"},
    ),
}  # fmt: skip


def distinction(a: str, b: str, text_a: str = "", text_b: str = "") -> Distinction:
    d = DISTINCTIONS.get(frozenset({a, b}))
    if d is not None:
        return d
    return Distinction(
        "heading_terms",
        "What the article is",
        f"Which describes it better: “{_short(text_a)}” or “{_short(text_b)}”?",
        ((a, _short(text_a), a), (b, _short(text_b), b)),
    )


def _short(text: str, n: int = 70) -> str:
    t = text.split(";")[0].split(":")[0].strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def compare(product: list[Fact], ruling_text: str) -> list[FactCompare]:
    """Fact by fact: the product's facts against the same facts read from the ruling's letter."""
    theirs = {f.key: f for f in extract(ruling_text[:3000])}
    out = []
    for f in product:
        if f.key == "capacity":
            rc = capacity_litres(ruling_text[:3000])
            yours = capacity_litres(f.value.replace("litres", "l")) if "litre" in f.value else capacity_litres(f.value)
            if rc is None or yours is None:
                continue
            rv = f"{round(rc * 1000)} ml" if rc < 1 else f"{rc:g} litres"
            same_band = (yours <= 1) == (rc <= 1) and (yours <= 2) == (rc <= 2)
            out.append(
                FactCompare(f.label, f.value, rv, "same" if rv == f.value else ("close" if same_band else "differs"))
            )
            continue
        t = theirs.get(f.key)
        if t is None:
            continue
        if t.value == f.value:
            match = "same"
        elif {t.value, f.value} <= {"Steel", "Stainless steel"} or {t.value, f.value} <= {
            "Rechargeable",
            "Batteries",
            "Lithium-ion battery",
        }:
            match = "close"
        else:
            match = "differs"
        out.append(FactCompare(f.label, f.value, t.value, match))  # type: ignore[arg-type]
    return out[:6]


# ── stated facts against a tariff line's words (GRI 6: a line that contradicts a stated fact is ruled out) ──
_LINE_MATERIALS: tuple[tuple[str, str], ...] = (
    (r"\bkashmir\b|\bcashmere\b", "cashmere"),
    (r"\bwool\b|fine animal hair", "wool"),
    (r"\bcotton\b", "cotton"),
    (r"\bsilk\b", "silk"),
    (r"\bflax\b|\blinen\b", "flax"),
    (r"man-made fib|synthetic fib|artificial fib", "man-made"),
    (r"\bstainless steel\b", "stainless steel"),
    (r"\bcast iron\b", "cast iron"),
    (r"\baluminum\b|\baluminium\b", "aluminium"),
    (r"\bplastics?\b", "plastic"),
    (r"\bglass\b", "glass"),
    (r"\bporcelain\b|\bchina\b|\bceramic\b", "ceramic"),
    (r"\bwood\b", "wood"),
    (r"\bleather\b", "leather"),
    (r"\btextile", "textile"),
)
# what each stated material is compatible with on a line
_COMPATIBLE = {
    "Cotton": {"cotton", "textile"},
    "Man-made fibres": {"man-made", "textile"},
    "Wool": {"wool", "cashmere", "textile"},
    "Stainless steel": {"stainless steel"},
    "Steel": {"stainless steel", "cast iron"},
    "Cast iron": {"cast iron"},
    "Aluminium": {"aluminium"},
    "Plastic": {"plastic"},
    "Glass": {"glass"},
    "Ceramic": {"ceramic"},
    "Wood": {"wood"},
    "Leather": {"leather"},
}
_GENDER = (
    (r"\bmen'?s\b", "Men"),
    (r"\bboys'?\b", "Boys"),
    (r"\bwomen'?s\b", "Women"),
    (r"\bgirls'?\b", "Girls"),
)


def stated_materials(text: str) -> set[str]:
    """Every material the description states (a tent can be polyester with aluminium poles)."""
    rule = next(r for r in RULES if r.key == "material")
    t = text.lower()
    return {value for pat, value in rule.patterns if re.search(pat, t)}


def line_conflicts(facts: list[Fact], segment: str, text: str = "") -> str | None:
    """The stated fact a tariff line's words contradict, or None. Only stated or confirmed facts rule a line out;
    a line that names no material, construction or wearer never conflicts, and a line that names several
    materials conflicts only when none of them fits."""
    stated = {f.key: f.value for f in facts if f.source == "stated"}
    s = segment.lower()
    materials = stated_materials(text) if text else ({stated["material"]} if "material" in stated else set())
    compatible = set().union(*(_COMPATIBLE.get(m, set()) for m in materials)) if materials else set()
    if compatible and any(m in _COMPATIBLE for m in materials):
        named = {name for pat, name in _LINE_MATERIALS if re.search(pat, s)}
        if named and not (named & compatible):
            return f"material ({', '.join(sorted(materials))})"
    construction = stated.get("construction")
    if construction == "Woven" and re.search(r"(?<!not )knitted or crocheted", s):
        return "construction (woven)"
    if construction == "Knitted" and re.search(r"not knitted|other than knitted", s):
        return "construction (knitted)"
    wearer = stated.get("wearer")
    if wearer in ("Men", "Women", "Boys", "Girls"):
        named = {g for pat, g in _GENDER if re.search(pat, s)}
        if named and wearer not in named:
            return f"wearer ({wearer.lower()})"
    return None
