"""The two declared rules: where "Strong match" starts (a 95% lower bound, not a point estimate) and when a
neighbouring heading is offered as "Also possible" (a validated floor plus real support). Also: the public
samples are catalogue products and none is a hand-checked evaluation item."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import dspy
import numpy as np
import pytest

from tariffcompass.classify import confidence as conf
from tariffcompass.classify import program as prog
from tariffcompass.contracts import ProductQuery

REPO = Path(__file__).resolve().parents[2]


# ── the confidence word's threshold rule ────────────────────────────────────────────────────────────────
def test_lower_bound_matches_the_closed_form_and_is_below_the_point_estimate():
    # all right: the one-sided bound is alpha ** (1 / n)
    assert conf.precision_lower_bound(10, 10) == pytest.approx(0.05 ** (1 / 10), abs=1e-9)
    assert conf.precision_lower_bound(129, 141) < 129 / 141
    assert conf.precision_lower_bound(0, 50) == 0.0 and conf.precision_lower_bound(0, 0) == 0.0


def test_point_rule_accepts_what_the_lower_bound_rejects():
    # 100 answers at p 0.9 with 92 right: 92 in 100 is a pass for the point rule, not with sampling error
    p = np.array([0.9] * 100 + [0.2] * 100)
    y = np.array([1] * 92 + [0] * 8 + [0] * 100)
    assert conf.choose_threshold(p, y, rule="point") == 0.9
    assert conf.choose_threshold(p, y, rule="lower_bound") == 1.01
    assert conf.best_lower_bound(p, y)["lowerBound"] < 0.90


def test_lower_bound_rule_finds_a_threshold_when_the_evidence_is_there():
    p = np.array([0.95] * 120 + [0.5] * 80)
    y = np.array([1] * 119 + [0] + [1] * 30 + [0] * 50)
    t = conf.choose_threshold(p, y, rule="lower_bound")
    assert t == 0.95 and conf.precision_lower_bound(119, 120) >= 0.90


def test_never_sets_a_threshold_on_too_few_answers():
    p = np.array([0.99] * (conf.MIN_STRONG - 1) + [0.1] * 50)
    y = np.array([1] * (conf.MIN_STRONG - 1) + [0] * 50)
    assert conf.choose_threshold(p, y, rule="point") == 1.01


def test_the_word_in_use_follows_the_declared_rule_and_its_test_look_is_recorded():
    rep = json.loads((prog.artifact_dir() / "word_matching.confidence-report.json").read_text())
    saved = conf.Calibrator.load(prog.calibrator_path(None))
    assert rep["rule"] == conf.THRESHOLD_RULE == "lower_bound"
    assert saved.threshold == rep["threshold"] and saved.validation["rule"] == "lower_bound"
    assert rep["reproduced"]["threshold"] == rep["previous"]["threshold"]  # the earlier rule reproduces exactly
    assert rep["test"] is not None and "after this rule" in rep["testLook"]


# ── "Also possible" ─────────────────────────────────────────────────────────────────────────────────────
def evidence(cands: dict[str, float], votes: dict[str, float]) -> dict:
    return {"candidates": [{"heading": h, "p": p} for h, p in cands.items()], "votes": votes}


def aside(*heads: str) -> list:
    return [(h, "set aside", None) for h in heads]


def test_an_unsupported_low_probability_neighbour_is_not_offered():
    # the knitted pullover's old "Also possible": mattress supports, another chapter, no close ruling
    e = evidence({"6110": 0.74, "9404": 0.023}, {"6110": 1.0})
    assert prog.plausible_alternative(e, "6110", aside("9404"), ["6110", "9404"], floor=0.05) is None


def test_probability_alone_is_not_support():
    e = evidence({"8714": 0.6, "4016": 0.3}, {"8714": 1.0})
    assert prog.plausible_alternative(e, "8714", aside("4016"), ["8714", "4016"], floor=0.05) is None


def test_support_alone_is_not_enough_below_the_floor():
    e = evidence({"8714": 0.86, "4016": 0.013}, {"8714": 0.7, "4016": 0.3})
    assert prog.plausible_alternative(e, "8714", aside("4016"), ["8714", "4016"], floor=0.05) is None


def test_a_same_chapter_or_closely_ruled_neighbour_above_the_floor_is_offered():
    same = evidence({"6110": 0.6, "6109": 0.0, "6105": 0.2}, {"6110": 1.0})
    assert prog.plausible_alternative(same, "6110", aside("6105"), ["6110", "6105"], floor=0.05) == "6105"
    ruled = evidence({"8714": 0.6, "8512": 0.2}, {"8714": 0.5, "8512": 0.5})
    assert prog.plausible_alternative(ruled, "8714", aside("8512"), ["8714", "8512"], floor=0.05) == "8512"


def test_a_documented_pair_is_offered_whatever_the_first_stage_says():
    # 9617 against 7323 turns on whether there is a vacuum between the walls
    e = evidence({"7323": 0.9, "9617": 0.003}, {"7323": 1.0})
    assert prog.plausible_alternative(e, "7323", aside("9617"), ["7323", "9617"], floor=0.05) == "9617"


def test_the_next_plausible_neighbour_is_offered_when_the_first_is_not():
    e = evidence({"6110": 0.5, "9404": 0.02, "6105": 0.3}, {"6110": 1.0})
    assert prog.plausible_alternative(e, "6110", aside("9404", "6105"), ["6110"], floor=0.05) == "6105"


def test_the_floor_was_chosen_on_validation_and_never_on_the_test_set():
    doc = json.loads((prog.artifact_dir() / prog.ALTERNATIVE_FILE).read_text())
    assert doc["target"] == prog.ALTERNATIVE_TARGET and doc["floor"] == prog.alternative_floor()
    assert doc["floor"] in prog.ALTERNATIVE_FLOOR_GRID and doc["test"].startswith("not read")
    chosen = next(r for r in doc["sweep"] if r["floor"] == doc["floor"])
    assert chosen["share"] >= doc["target"] and chosen["shown"] >= prog.ALTERNATIVE_MIN_SHOWN
    lower = [r for r in doc["sweep"] if r["floor"] < doc["floor"]]
    assert all((r["share"] or 0) < doc["target"] or r["shown"] < prog.ALTERNATIVE_MIN_SHOWN for r in lower)


def _broker_pred(heading: str, code: str, others: list[str]) -> dspy.Prediction:
    return dspy.Prediction(
        order=[heading, *others],
        heading=heading,
        gri="GRI 1",
        set_aside=aside(*others),
        facts="",
        us_code=code,
        us_why="",
        ca_code="",
        ca_why="",
        cited=[],
        sentences=[(f"Word matching places the product in heading {heading}.", ())],
        support_ids=[],
        verdict="broker",
        deciding_fact="none",
        question="none",
    )


def _assemble_evidence(cands: dict[str, float], votes: dict[str, float]) -> dict:
    lines = {h: [(f"{h}000000", f"{h} line")] for h in cands}
    return {
        **evidence(cands, votes),
        "us_text": {f"{h}000000": f"{h} line" for h in cands},
        "ca_text": {},
        "heading_text": {h: f"Heading {h} text" for h in cands},
        "ca_heading_text": {},
        "us_lines": lines,
        "ca_lines": {},
        "rulings": {},
        "notes": {},
        "first_stage": [{"code": h, "p": p, "why": []} for h, p in cands.items()],
        "chapters": [],
        "line_words": {},
    }


def test_an_answer_without_a_plausible_neighbour_offers_no_alternative_and_no_question(monkeypatch):
    monkeypatch.setattr(prog, "alternative_floor", lambda: 0.05)
    q = ProductQuery("Women's crew-neck pullover, knitted, 100% cotton, ribbed cuffs and hem.")
    e = _assemble_evidence({"6110": 0.74, "9404": 0.023}, {"6110": 1.0})
    ans = prog.assemble(q, e, _broker_pred("6110", "6110000000", ["9404"]), lm_label="t", version="t", timings={})
    assert ans.alternative is None and ans.deciding_question is None and ans.duty_at_stake is None
    assert "9404" not in ans.issue and "no neighbouring heading has enough support" in ans.verdict_sentence
    assert not any("9404" in a.ref for a in ans.tariff_authorities)
    assert not any(f.decides for f in ans.facts)


def test_an_answer_with_a_documented_neighbour_keeps_its_alternative_and_question(monkeypatch):
    monkeypatch.setattr(prog, "alternative_floor", lambda: 0.05)
    q = ProductQuery("20 oz double-wall stainless steel tumbler, insulated, with a sliding lid.")
    e = _assemble_evidence({"7323": 0.9, "9617": 0.003}, {"7323": 1.0})
    ans = prog.assemble(q, e, _broker_pred("7323", "7323000000", ["9617"]), lm_label="t", version="t", timings={})
    assert ans.alternative is not None and ans.alternative.code.startswith("9617")
    assert ans.deciding_question is not None and ans.deciding_question.fact_key == "between_walls"
    assert "9617" in ans.issue


# ── the public samples ──────────────────────────────────────────────────────────────────────────────────
def test_public_samples_are_catalogue_products_and_not_hand_checked_items():
    from tariffcompass.catalog.samples import SAMPLES
    from tariffcompass.seed.catalog import _items

    hand_checked = json.loads((REPO / "eval" / "sets" / "landed_cost_20.json").read_text())["products"]
    checked_headings = {p["code"].replace(".", "")[:4] for p in hand_checked}
    catalogue_text = " ".join(f"{i.title} {i.listing}".lower() for i in _items())
    assert "bike-light" not in SAMPLES
    for key, s in SAMPLES.items():
        assert s["title"].lower().split()[-1] in catalogue_text, key
    sleeping = SAMPLES["sleeping-bag"]
    item = next(i for i in _items() if i.sku == "NB-OD-0744")
    assert sleeping["query"] == item.listing and sleeping["made_in"] == item.made_in
    assert item.us[:4] not in checked_headings


def test_the_lab_says_when_the_word_in_use_never_says_strong():
    from tariffcompass.lab.service import _in_use_word_note

    rep = json.loads((prog.artifact_dir() / "word_matching.confidence-report.json").read_text())
    note = _in_use_word_note()
    assert ("Needs a broker" in note) == (rep["threshold"] > 1.0)


def test_a_stated_deciding_fact_is_asked_as_a_confirmation_and_its_option_leads_to_the_answer(monkeypatch):
    monkeypatch.setattr(prog, "alternative_floor", lambda: 0.05)
    q = ProductQuery("20 oz double-wall stainless steel tumbler, vacuum insulated, with a sliding lid.")
    e = _assemble_evidence({"9617": 0.4, "7323": 0.5}, {"7323": 1.0})
    e["us_lines"]["9617"] = [
        ("9617001000", "Vacuum flasks: having a capacity not exceeding 1 liter"),
        ("9617006000", "Other"),
    ]
    ans = prog.assemble(q, e, _broker_pred("9617", "9617001000", ["7323"]), lm_label="t", version="t", timings={})
    dq = ans.deciding_question
    assert dq is not None and "The description says: a vacuum." in dq.question
    assert {k: code for k, _, code in dq.options}["vacuum"] == "9617001000"
    assert "states the fact that separates heading 9617 from heading 7323" in ans.verdict_sentence


def test_an_alternative_for_a_whole_article_is_never_a_parts_line(monkeypatch):
    monkeypatch.setattr(prog, "alternative_floor", lambda: 0.05)
    q = ProductQuery("Stainless insulated tumbler, 20 oz, double wall, vacuum sealed, slide lid")
    e = _assemble_evidence({"7323": 0.9, "9617": 0.003}, {"7323": 1.0})
    e["us_lines"]["9617"] = [
        ("9617001000", "Vacuum flasks and other vacuum vessels: Having a capacity not exceeding 1 liter"),
        ("9617006000", "Vacuum flasks and other vacuum vessels: Parts"),
    ]
    ans = prog.assemble(q, e, _broker_pred("7323", "7323000000", ["9617"]), lm_label="t", version="t", timings={})
    assert ans.alternative is not None and ans.alternative.code == "9617001000"
    assert ans.deciding_question is not None
    assert all(code != "9617006000" for _, _, code in ans.deciding_question.options)


def test_duty_at_stake_is_priced_on_the_shipment_not_described(monkeypatch):
    import re

    from tariffcompass.catalog import answers

    monkeypatch.setattr(prog, "alternative_floor", lambda: 0.05)
    q = ProductQuery("20 oz double-wall stainless steel tumbler, vacuum insulated, with a sliding lid.")
    e = _assemble_evidence({"9617": 0.4, "7323": 0.5}, {"7323": 1.0})
    e["us_lines"]["7323"] = [("7323930080", "Table, kitchen or other household articles: Of stainless steel: Other")]
    ans = prog.assemble(q, e, _broker_pred("9617", "9617001000", ["7323"]), lm_label="t", version="t", timings={})
    assert ans.alternative is not None and ans.duty_at_stake is None
    shipment = {"value": "12500.00", "currency": "USD", "quantity": 1000, "transport": "ocean"}
    main = answers.landed_cost("US", "9617001000", "CN", shipment)
    other = answers.landed_cost("US", ans.alternative.code, "CN", shipment)
    priced = answers.with_duty_at_stake(ans, [main], {"made_in": "CN"}, shipment)
    diff = other.charges_total - main.charges_total
    assert priced.duty_at_stake is not None
    stake = r"US\$[\d,]+\.\d\d (more|less) in US duty and fees on this shipment"
    assert re.fullmatch(stake, priced.duty_at_stake) or priced.duty_at_stake.startswith("the same")
    assert f"{abs(diff):,.2f}" in priced.duty_at_stake or diff == 0
    no_alt = answers.with_duty_at_stake(dataclasses.replace(ans, alternative=None), [main], {"made_in": "CN"}, shipment)
    assert no_alt.duty_at_stake is None


def test_a_stated_fact_pointing_to_a_neighbour_left_out_is_named_in_the_verdict(monkeypatch):
    # "vacuum sealed": the first stage passes on no 9617 candidate, so the answer stays 7323; the verdict says why
    # a broker should look, without changing the code
    monkeypatch.setattr(prog, "alternative_floor", lambda: 0.05)
    q = ProductQuery("Stainless insulated tumbler, 20 oz, double wall, vacuum sealed, slide lid")
    e = _assemble_evidence({"7323": 0.9, "3923": 0.01}, {"7323": 1.0})
    ans = prog.assemble(q, e, _broker_pred("7323", "7323000000", ["3923"]), lm_label="t", version="t", timings={})
    assert ans.us is not None and ans.us.code == "7323000000" and ans.alternative is None
    assert "points to heading 9617 rather than 7323" in ans.verdict_sentence


def test_canada_never_lands_on_a_parts_line_for_a_whole_article():
    from tariffcompass.classify import evidence as ev

    rows = [
        ("7323931000", "Of stainless steel: Parts for use in the manufacture of cookware"),
        ("7323939090", "Of stainless steel: Other"),
    ]
    assert ev.whole_article_rows(rows, "20 oz stainless tumbler") == rows[1:]
    assert ev.whole_article_rows(rows, "replacement parts for a stainless tumbler") == rows
