"""Duty engine: the hand-checked landed-cost set, stacking rules, sources and dates on every line."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings

from tariffcompass.contracts import DutyEngine, LandedCostQuery
from tariffcompass.duties.engine import DutyDataError, LayeredDutyEngine, build_engine, parse_rate

SET = Path(settings.REPO_DIR) / "eval" / "sets" / "landed_cost_20.json"
PRODUCTS = json.loads(SET.read_text())["products"]
DAY = date(2026, 2, 19)


@pytest.fixture(scope="module")
def engine():
    return build_engine()


def query(p: dict) -> LandedCostQuery:
    return LandedCostQuery(
        p["country"],
        p["code"],
        p["madeIn"],
        Decimal(p["value"]),
        currency=p["currency"],
        transport=p["transport"],
        usmca_answers=tuple(p["answers"].items()),
        metal_content_value=Decimal(p["metalContentValue"]) if p["metalContentValue"] else None,
        as_of=DAY,
    )


def test_engine_satisfies_the_protocol(engine):
    assert isinstance(engine, DutyEngine)


def test_the_hand_checked_set_has_twenty_products_with_working():
    assert len(PRODUCTS) == 20
    assert all(p["working"] for p in PRODUCTS)


@pytest.mark.parametrize("p", PRODUCTS, ids=[p["id"] for p in PRODUCTS])
def test_landed_cost_matches_the_hand_checked_figure_to_the_cent(engine, p):
    lc = engine.landed_cost(query(p))
    assert {ln.layer_id: str(ln.amount) for ln in lc.lines} == p["expected"]["lines"]
    assert str(lc.charges_total) == p["expected"]["chargesTotal"]
    assert lc.landed_total == Decimal(p["value"]) + lc.charges_total


def test_hero_tumbler_is_3458_93_and_958_93_without_the_emergency_duties(engine):
    lc = engine.landed_cost(LandedCostQuery("US", "9617001000", "CN", Decimal("12500"), as_of=DAY))
    assert lc.charges_total == Decimal("3458.93")
    assert lc.effective_rate == Decimal("0.2720")
    alt = dict(lc.what_could_change)
    assert alt["If the pending emergency duties end"] == Decimal("13458.93")
    assert any("List 4B" in n.why for n in lc.not_applied)


def test_every_line_has_a_source_and_an_effective_date_and_ieepa_lines_are_open(engine):
    for p in PRODUCTS:
        for ln in engine.landed_cost(query(p)).lines:
            assert ln.source and ln.source_url.startswith("https://") and ln.effective_from
            if "IEEPA" in ln.layer_id:
                assert ln.legal_status and "Supreme Court" in ln.legal_status
            else:
                assert ln.legal_status is None


def test_de_minimis_is_listed_as_not_applied_on_every_us_entry(engine):
    lc = engine.landed_cost(LandedCostQuery("US", "8512102000", "CN", Decimal("300"), transport="courier", as_of=DAY))
    assert any(n.name.startswith("De minimis") and "29 Aug 2025" in n.why for n in lc.not_applied)


def test_mexico_origin_asks_the_three_usmca_questions(engine):
    lc = engine.landed_cost(LandedCostQuery("US", "6110202010", "MX", Decimal("1000"), transport="truck", as_of=DAY))
    assert [q.key for q in lc.questions] == ["usmca_origin", "usmca_certificate", "usmca_claim"]
    assert any(ln.layer_id == "US-IEEPA-MX" for ln in lc.lines)


def test_232_without_a_metal_value_charges_the_full_value_and_asks_for_it(engine):
    lc = engine.landed_cost(LandedCostQuery("US", "7323930060", "CN", Decimal("1000"), as_of=DAY))
    steel = next(ln for ln in lc.lines if ln.layer_id == "US-232-STEEL")
    assert steel.amount == Decimal("500.00")
    assert any(q.key == "metal_content_value" for q in lc.questions)
    assert not any(ln.layer_id == "US-IEEPA-RECIP-CN" and ln.amount for ln in lc.lines)


def test_unknown_lines_and_specific_rates_are_refused(engine):
    with pytest.raises(DutyDataError):
        engine.landed_cost(LandedCostQuery("US", "9999999999", "CN", Decimal("100"), as_of=DAY))


def test_a_date_outside_the_verified_periods_is_not_given_a_rate(engine):
    lc = engine.landed_cost(LandedCostQuery("US", "9617001000", "CN", Decimal("1000"), as_of=date(2025, 6, 1)))
    assert not any(ln.layer_id == "US-IEEPA-CN-FENTANYL" for ln in lc.lines)
    assert any(n.why == "No verified rate for this date." for n in lc.not_applied)


def test_layers_in_force_carry_sources_and_the_open_legal_status(engine):
    layers = engine.layers_in_force("US", DAY)
    ids = {layer.id for layer in layers}
    assert {"US-MFN", "US-IEEPA-CN-FENTANYL", "US-MPF"} <= ids
    assert all(layer.sources for layer in layers)
    assert all("Supreme Court" in (layer.legal_status or "") for layer in layers if "IEEPA" in layer.id)
    assert "CA-GST" in {layer.id for layer in engine.layers_in_force("CA", DAY)}


def test_a_layer_without_a_source_is_refused(tmp_path):
    raw = json.loads(Path(settings.TARIFF_COMPASS["DUTY_LAYERS_PATH"]).read_text())
    raw["layers"][0]["sources"] = []
    bad = tmp_path / "layers.json"
    bad.write_text(json.dumps(raw))
    with pytest.raises(DutyDataError):
        LayeredDutyEngine(bad, Path(settings.TARIFF_COMPASS["DUTY_LAYERS_PATH"]).with_name("rules.json"))


@pytest.mark.parametrize(("text", "rate"), [("7.2%", Decimal("0.072")), ("Free", Decimal("0")), ("2.2¢/kg + 5%", None)])
def test_rates_are_read_only_when_ad_valorem(text, rate):
    assert parse_rate(text) == rate
