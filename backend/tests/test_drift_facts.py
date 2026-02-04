"""Drift (PSI, simulated tariff revision) and product facts."""

from __future__ import annotations

from tariffcompass.classify import drift, facts
from tariffcompass.search.engine import load_schedules


def test_psi_is_zero_for_the_same_mix_and_grows_with_a_shift():
    same = drift.chapter_psi(["61"] * 50 + ["85"] * 50, ["61"] * 50 + ["85"] * 50)
    assert same["psi"] == 0.0 and same["reading"] == "stable"
    moved = drift.chapter_psi(["61"] * 80 + ["85"] * 20, ["61"] * 20 + ["85"] * 80)
    assert moved["psi"] > 0.25 and moved["reading"] == "large shift"
    assert moved["mostMoved"][0]["chapter"] in ("61", "85")


def test_a_simulated_revision_flags_exactly_the_affected_products():
    us, _ = load_schedules(sample=True)
    new = drift.simulate_revision(
        us, split="9617001000", renumber=("8512102000", "8512103000"), retext="8513", remove="6110202010"
    )
    changes = drift.detect_revision(us, new)
    kinds = {(c.kind, c.code) for c in changes}
    assert ("split", "9617001000") in kinds and ("removed", "8512102000") in kinds
    assert ("text_changed", "8513") in kinds and ("removed", "6110202010") in kinds
    products = {
        "tumbler": "9617001000",
        "bike light": "8512102000",
        "torch": "8513102000",
        "pullover": "6110202010",
        "pot": "7323930060",
    }
    hit = drift.affected(products.items(), changes)
    assert set(hit) == {"tumbler", "bike light", "torch", "pullover"}


def test_facts_say_where_they_came_from():
    fs = {f.key: f for f in facts.extract("20 oz double-wall insulated stainless steel tumbler")}
    assert fs["material"].value == "Stainless steel" and fs["material"].source == "stated"
    assert fs["between_walls"].source == "read" and "insulated" in fs["between_walls"].source_note
    assert fs["capacity"].value == "591 ml"
    stated = {f.key: f for f in facts.extract("vacuum insulated tumbler", (("between_walls", "Air"),))}
    assert stated["between_walls"].value == "Air" and stated["between_walls"].source_note == "confirmed by you"


def test_the_tumbler_distinction_and_a_fact_by_fact_comparison():
    d = facts.distinction("9617", "7323")
    assert d.key == "between_walls" and {o[2] for o in d.options} == {"9617", "7323"}
    generic = facts.distinction("4202", "6307", "Trunks, suitcases", "Other made up articles")
    assert generic.key == "heading_terms"
    rows = facts.compare(
        facts.extract("stainless steel vacuum bottle, 500 ml"),
        "A stainless steel bottle with a vacuum between the walls, 17 ounces.",
    )
    assert {r.fact: r.match for r in rows}["Material"] == "same"
