"""Tariff text (API_CONTRACT §1.7) and landed cost with its duty layers (§1.8), over the core's search engine
and duty engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.http import HttpRequest

from tariffcompass import codes, services
from tariffcompass.api import labels
from tariffcompass.api.schemas.landed import DutyLayerOut, LandedCostIn, LandedCostOut
from tariffcompass.api.schemas.rulings import SectionOut, TariffLineOut, TariffOutline
from tariffcompass.catalog import answers
from tariffcompass.contracts import LandedCostQuery, TariffLine
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform.config import tc
from tariffcompass.platform.context import requires

router = WireRouter()  # /tariff
landed_router = WireRouter()  # /landed-cost
layers_router = WireRouter()  # /duty-layers

EDITIONS = {
    "US": "HTSUS 2026 Revision 3 (in force from 12 Feb 2026)",
    "CA": "Customs Tariff T2026 (from 1 Jan 2026)",
}

# The 21 sections and 97 chapters of the Harmonized System (chapter 77 is reserved).
SECTIONS: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "I",
        "Live animals; animal products",
        [
            ("01", "Live animals"),
            ("02", "Meat and edible meat offal"),
            ("03", "Fish and crustaceans"),
            ("04", "Dairy produce; eggs; honey"),
            ("05", "Other products of animal origin"),
        ],
    ),
    (
        "II",
        "Vegetable products",
        [
            ("06", "Live trees and plants"),
            ("07", "Edible vegetables"),
            ("08", "Edible fruit and nuts"),
            ("09", "Coffee, tea, maté and spices"),
            ("10", "Cereals"),
            ("11", "Milling products"),
            ("12", "Oil seeds"),
            ("13", "Lac; gums, resins"),
            ("14", "Vegetable plaiting materials"),
        ],
    ),
    ("III", "Animal or vegetable fats and oils", [("15", "Fats and oils")]),
    (
        "IV",
        "Prepared foodstuffs; beverages; tobacco",
        [
            ("16", "Preparations of meat or fish"),
            ("17", "Sugars"),
            ("18", "Cocoa"),
            ("19", "Preparations of cereals"),
            ("20", "Preparations of vegetables or fruit"),
            ("21", "Miscellaneous edible preparations"),
            ("22", "Beverages and vinegar"),
            ("23", "Food industry residues"),
            ("24", "Tobacco"),
        ],
    ),
    (
        "V",
        "Mineral products",
        [("25", "Salt, sulphur, earths and stone"), ("26", "Ores, slag and ash"), ("27", "Mineral fuels and oils")],
    ),
    (
        "VI",
        "Products of the chemical industries",
        [
            ("28", "Inorganic chemicals"),
            ("29", "Organic chemicals"),
            ("30", "Pharmaceutical products"),
            ("31", "Fertilisers"),
            ("32", "Tanning or dyeing extracts; paints"),
            ("33", "Essential oils; cosmetics"),
            ("34", "Soap, waxes"),
            ("35", "Albuminoidal substances; glues"),
            ("36", "Explosives; matches"),
            ("37", "Photographic goods"),
            ("38", "Miscellaneous chemical products"),
        ],
    ),
    ("VII", "Plastics and rubber", [("39", "Plastics and articles thereof"), ("40", "Rubber and articles thereof")]),
    (
        "VIII",
        "Hides, skins, leather; travel goods",
        [
            ("41", "Raw hides and skins; leather"),
            ("42", "Articles of leather; handbags and travel goods"),
            ("43", "Furskins"),
        ],
    ),
    ("IX", "Wood, cork and plaiting", [("44", "Wood and articles of wood"), ("45", "Cork"), ("46", "Basketware")]),
    (
        "X",
        "Pulp, paper and paperboard",
        [("47", "Pulp of wood"), ("48", "Paper and paperboard"), ("49", "Printed books and matter")],
    ),
    (
        "XI",
        "Textiles and textile articles",
        [
            ("50", "Silk"),
            ("51", "Wool"),
            ("52", "Cotton"),
            ("53", "Other vegetable textile fibres"),
            ("54", "Man-made filaments"),
            ("55", "Man-made staple fibres"),
            ("56", "Wadding, felt; twine"),
            ("57", "Carpets"),
            ("58", "Special woven fabrics"),
            ("59", "Coated textile fabrics"),
            ("60", "Knitted or crocheted fabrics"),
            ("61", "Apparel, knitted or crocheted"),
            ("62", "Apparel, not knitted"),
            ("63", "Other made-up textile articles"),
        ],
    ),
    (
        "XII",
        "Footwear, headgear, umbrellas",
        [
            ("64", "Footwear"),
            ("65", "Headgear"),
            ("66", "Umbrellas, walking sticks"),
            ("67", "Prepared feathers; artificial flowers"),
        ],
    ),
    (
        "XIII",
        "Stone, ceramic and glass",
        [("68", "Articles of stone, plaster, cement"), ("69", "Ceramic products"), ("70", "Glass and glassware")],
    ),
    ("XIV", "Pearls, precious stones and metals", [("71", "Pearls, precious stones and metals; jewellery")]),
    (
        "XV",
        "Base metals and articles of base metal",
        [
            ("72", "Iron and steel"),
            ("73", "Articles of iron or steel"),
            ("74", "Copper"),
            ("75", "Nickel"),
            ("76", "Aluminium"),
            ("77", "(Reserved)"),
            ("78", "Lead"),
            ("79", "Zinc"),
            ("80", "Tin"),
            ("81", "Other base metals"),
            ("82", "Tools, cutlery of base metal"),
            ("83", "Miscellaneous articles of base metal"),
        ],
    ),
    (
        "XVI",
        "Machinery and electrical equipment",
        [("84", "Machinery and mechanical appliances"), ("85", "Electrical machinery and equipment")],
    ),
    (
        "XVII",
        "Vehicles, aircraft, vessels",
        [
            ("86", "Railway locomotives"),
            ("87", "Vehicles other than railway"),
            ("88", "Aircraft"),
            ("89", "Ships and boats"),
        ],
    ),
    (
        "XVIII",
        "Optical, medical and precision instruments; clocks; music",
        [("90", "Optical and medical instruments"), ("91", "Clocks and watches"), ("92", "Musical instruments")],
    ),
    ("XIX", "Arms and ammunition", [("93", "Arms and ammunition")]),
    (
        "XX",
        "Miscellaneous manufactured articles",
        [
            ("94", "Furniture; bedding; lamps"),
            ("95", "Toys, games and sports equipment"),
            ("96", "Miscellaneous manufactured articles"),
        ],
    ),
    ("XXI", "Works of art and antiques", [("97", "Works of art, collectors' pieces and antiques")]),
]


def line_out(line: TariffLine, *, has_children: bool | None = None) -> dict[str, Any]:
    d = codes.digits(line.code)
    if has_children is None:
        has_children = len(d) < 10
    return {
        "country": line.country,
        "code": codes.fmt(d),
        "digits": d,
        "level": line.level,
        "level_label": labels.LEVELS.get(line.level, line.level),
        "indent": line.indent,
        "text": line.text,
        "full_text": line.full_text,
        "unit": line.unit,
        "general_rate": line.general_rate,
        "special": line.special,
        "has_children": has_children,
    }


def _country(country: str) -> str:
    c = country.upper()
    if c not in ("US", "CA"):
        raise Problem(404, "not_found", "Tariff text is for US or CA.")
    return c


@router.get("/sections", response=list[SectionOut], auth=None)
def sections(request: HttpRequest) -> list[dict[str, Any]]:
    return [
        {"section": s, "title": t, "chapters": [{"chapter": c, "title": ct, "reserved": c == "77"} for c, ct in chs]}
        for s, t, chs in SECTIONS
    ]


@router.get("/{country}/search", response=list[TariffLineOut])
@requires("tariff:read")
def search(request: HttpRequest, country: str, q: str = "", under: str | None = None, k: int = 20) -> list[dict]:
    c = _country(country)
    lines = services.retriever().tariff(
        q,
        country=c,  # type: ignore[arg-type]
        under=codes.digits(under) if under else None,
        k=max(1, min(k, 100)),
    )
    return [line_out(ln) for ln in lines]


@router.get("/{country}/lines/{code}", response=TariffOutline)
@requires("tariff:read")
def outline(request: HttpRequest, country: str, code: str) -> dict:
    c = _country(country)
    d = codes.digits(code)
    retr = services.retriever()
    line = retr.tariff_line(c, d)  # type: ignore[arg-type]
    if line is None:
        raise Problem(404, "not_found", "That code isn't a line of the tariff in force.")
    ancestors = []
    for n in (2, 4, 6, 8):
        if n < len(d):
            a = retr.tariff_line(c, d[:n])  # type: ignore[arg-type]
            if a is not None:
                ancestors.append(line_out(a, has_children=True))
    children = retr.tariff_children(c, d)  # type: ignore[arg-type]
    return {
        "line": line_out(line, has_children=bool(children)),
        "ancestors": ancestors,
        "children": [line_out(ch) for ch in children],
        "notes": list(line.notes),
        "edition_label": EDITIONS[c],
    }


# ── Landed cost ─────────────────────────────────────────────────────────────────────────────────────────
@landed_router.post("", response=LandedCostOut)
@requires("classify:read")
def landed_cost(request: HttpRequest, body: LandedCostIn) -> dict:
    try:
        value = Decimal(body.value.amount)
        metal = Decimal(body.metal_content_value.amount) if body.metal_content_value else None
    except InvalidOperation as exc:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "value.amount", "message": "Use a number like 12500.00."}],
        ) from exc
    d = codes.digits(body.code)
    if len(d) not in (8, 10):
        raise Problem(
            422,
            "unknown_code",
            "Give the full code.",
            errors=[{"field": "code", "message": "Give an eight- or ten-digit code."}],
        )
    lc = services.duties().landed_cost(
        LandedCostQuery(
            country=body.country,
            code=d,
            made_in=body.made_in,
            customs_value=value,
            currency=body.value.currency,
            quantity=body.quantity,
            transport=body.transport,
            usmca_answers=tuple(sorted(body.usmca_answers.items())),
            metal_content_value=metal,
            as_of=answers.SNAPSHOT_DATE,
        )
    )
    return answers.landed_out(lc)


@layers_router.get("", response=list[DutyLayerOut])
@requires("classify:read")
def duty_layers(request: HttpRequest, country: str = "US", asOf: str | None = None) -> list[dict]:
    c = _country(country)
    try:
        as_of = date.fromisoformat(asOf) if asOf else answers.SNAPSHOT_DATE
    except ValueError as exc:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "asOf", "message": "Use a date like 2026-02-19."}],
        ) from exc
    out = []
    raw = _raw_layers()
    for layer in services.duties().layers_in_force(c, as_of):  # type: ignore[arg-type]
        extra = raw.get(layer.id, {})
        out.append(
            {
                "id": layer.id,
                "country": layer.country,
                "kind": layer.kind,
                "kind_label": labels.LAYER_KINDS.get(layer.kind, layer.kind),
                "name": layer.name,
                "authority": layer.authority,
                "chapter99": list(layer.chapter99),
                "scope": extra.get("scope", ""),
                "rate": extra.get("rate", ""),
                "effective_from": layer.effective_from,
                "effective_to": layer.effective_to,
                "legal_status": layer.legal_status,
                "legal_status_open": answers.legal_open(layer.legal_status),
                "sources": list(layer.sources),
            }
        )
    return out


def _raw_layers() -> dict[str, dict[str, Any]]:
    import json

    data = json.loads(Path(tc()["DUTY_LAYERS_PATH"]).read_text())
    return {layer["id"]: layer for layer in data["layers"]}
