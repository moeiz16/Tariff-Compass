"""The DSPy program and the offline simulator's policies: behaviour, instructions, and an end-to-end answer."""

from __future__ import annotations

import json

import dspy
import pytest
from django.conf import settings

from tariffcompass.adapters import lm_sim
from tariffcompass.adapters.lm_sim import SimulatorLM
from tariffcompass.classify import evidence as ev
from tariffcompass.classify.program import TariffProgram, assemble, build_evidence
from tariffcompass.contracts import ProductQuery
from tariffcompass.search import engine

TUMBLER = "20 oz double-wall vacuum insulated stainless steel tumbler with sliding lid"


@pytest.fixture(scope="module")
def retriever(tmp_path_factory):
    cfg = settings.TARIFF_COMPASS
    old = cfg["INDEX_DIR"]
    cfg["INDEX_DIR"] = str(tmp_path_factory.mktemp("index"))
    try:
        yield engine.build_retriever(sample=True)
    finally:
        cfg["INDEX_DIR"] = old


@pytest.fixture(scope="module")
def first_stage():
    from tariffcompass import services

    return services.first_stage()


def test_candidate_ranking_follows_probability_and_precedent_by_instruction():
    block = "9617 | p=0.600 | precedent=0.100 | Vacuum flasks\n7323 | p=0.300 | precedent=0.900 | Table, kitchen"
    base = lm_sim._candidates({"product": "x", "candidates": block}, "")
    assert base["headings"].startswith("9617")
    tuned = lm_sim._candidates(
        {"product": "x", "candidates": block}, "RULE: weigh precedent at 1.0 when ranking candidates"
    )
    assert tuned["headings"].startswith("7323")


def test_gri_applies_the_section_note_and_learned_preferences():
    headings = (
        "7323 | rank=1 | p=0.5 | precedent=0.6 | excludes=none | notes=none | Table, kitchen or other household articles of iron or steel\n"
        "9617 | rank=2 | p=0.4 | precedent=0.4 | excludes=none | notes=Section XV, Note 1(m) excludes chapters 72-83 | Vacuum flasks and other vacuum vessels"
    )
    out = lm_sim._gri({"product": "vacuum flask of steel", "headings": headings, "rulings": ""}, "")
    assert out["heading"] == "9617" and "Section XV, Note 1(m)" in out["set_aside"]
    plain = headings.replace("notes=Section XV, Note 1(m) excludes chapters 72-83", "notes=none")
    rule = "RULE: prefer 9617 over 7323 when the product mentions 'flask'"
    assert lm_sim._gri({"product": "steel flask", "headings": plain, "rulings": ""}, rule)["heading"] == "9617"


def test_subheading_reads_capacity_and_follows_close_precedent():
    lines = (
        "9617001000 | Vacuum flasks: Vessels: Having a capacity not exceeding 1 liter\n"
        "9617003000 | Vacuum flasks: Vessels: Having a capacity exceeding 1 liter but not exceeding 2 liters\n"
        "9617004000 | Vacuum flasks: Vessels: Having a capacity exceeding 2 liters"
    )
    assert lm_sim._subheading({"product": "a 40 oz vacuum bottle", "lines": lines}, "")["code"] == "9617003000"
    assert lm_sim._subheading({"product": "a 20 oz vacuum tumbler", "lines": lines}, "")["code"] == "9617001000"
    with_prec = "precedent: NY N1 → 9617004000 (sim 0.950)\n" + lines
    assert lm_sim._subheading({"product": "a vacuum jug", "lines": with_prec}, "")["code"] == "9617004000"


def test_citation_rule_keeps_neighbours_out_of_support():
    rulings = (
        "[1] NY N2 | 7323 | in_force | 2018-06-11 | sim=1.0 | x\n[2] NY N1 | 9617 | in_force | 2021-12-03 | sim=0.9 | y"
    )
    strict = lm_sim._cite(
        {"product": "p", "decision": "heading=9617 | us=9617001000 | gri=GRI 1", "rulings": rulings},
        "RULE: cite as support only rulings under the chosen heading",
    )
    first = strict["sentences"].splitlines()[0]
    assert "[2]" in first and "[1]" not in first
    assert any(s.startswith("By contrast") and "[1]" in s for s in strict["sentences"].splitlines())


def test_confidence_thresholds_come_from_the_instructions():
    agree = {"agreement": "agreeing=2 | cited=2 | first_stage_p=0.5 | margin=0.12 | precedent=0.5 | runner_up=7323"}
    assert lm_sim._confidence(agree, "")["verdict"] == "strong"
    assert lm_sim._confidence(agree, "RULE: say broker when the margin is below 0.2")["verdict"] == "broker"


def test_reflection_writes_rules_from_feedback_deterministically():
    fb = (
        "Wrong heading. FB[heading] chose=7323 expected=9617 words=vacuum precedent_expected=0.6 precedent_chose=0.2\n"
        "FB[cite] wrong_support=1\nFB[confidence] margin=0.05 agreeing=1 right=no\nFB[confidence] margin=0.4 agreeing=2 right=yes"
    )
    inputs = {"current_instruction": "Apply the General Rules.", "examples_with_feedback": fb}
    a = lm_sim.tariff_reflection_policy(["new_instruction"], inputs, "")["new_instruction"]
    assert a == lm_sim.tariff_reflection_policy(["new_instruction"], inputs, "")["new_instruction"]
    assert "RULE: prefer 9617 over 7323 when the product mentions 'vacuum'" in a
    assert "RULE: cite as support only rulings under the chosen heading" in a
    assert "RULE: weigh precedent at 0.5 when choosing the heading" in a
    assert "RULE: say broker when the margin is below" in a


def test_the_simulator_never_sees_a_gold_label(retriever, first_stage):
    q = ProductQuery(TUMBLER)
    e = build_evidence(q, first_stage.predict(q), retriever)
    blob = json.dumps(e)
    assert "gold" not in blob and "expected" not in blob


def test_end_to_end_answer_for_the_hero_tumbler(retriever, first_stage):
    q = ProductQuery(TUMBLER, made_in="CN")
    first = first_stage.predict(q)
    e = build_evidence(q, first, retriever)
    with dspy.context(lm=SimulatorLM(), adapter=dspy.ChatAdapter()):
        pred = TariffProgram()(product=ev.product_text(q), evidence=json.dumps(e))
    ans = assemble(q, e, pred, lm_label="offline simulator", version="test", timings={})
    assert ans.us and ans.us.code == "9617001000"
    assert ans.ca and ans.ca.code.startswith("9617")
    assert ans.citations and all(0 < n <= len(ans.citations) for c in ans.reason for n in c.cites)
    support = [c for c in ans.citations if "same_heading" in c.match]
    assert support and all(c.ruling.status != "revoked" for c in support)
    levels = [s.level for s in ans.path]
    assert levels[:3] == ["section", "chapter", "heading"] and levels[-1] == "suffix"
    heading_step = ans.path[2]
    assert heading_step.code == "9617" and heading_step.gri.startswith("GRI")
    assert any(a.ref == "Heading 9617" for a in ans.tariff_authorities)
    assert ans.lm_label == "offline simulator"
    if ans.verdict == "broker":
        assert ans.deciding_question or ans.alternative


def test_gepa_runs_offline_and_saves_a_program(retriever, first_stage, tmp_path):
    from datetime import date

    from tariffcompass.classify.dataset import Example
    from tariffcompass.classify.optimize import WordTable, make_metric, to_dspy

    items = [
        Example("A1", date(2020, 1, 1), "stainless steel vacuum flask 750 ml", "9617", "9617001000", ("9617001000",)),
        Example("A2", date(2020, 1, 2), "stainless steel mixing bowl", "7323", "7323930080", ("7323930080",)),
        Example("A3", date(2020, 1, 3), "vacuum insulated food jar of steel", "9617", "9617001000", ("9617001000",)),
        Example("A4", date(2020, 1, 4), "steel saucepan with handle", "7323", "7323930060", ("7323930060",)),
    ]
    exs = [to_dspy(e, first_stage, retriever, date(2030, 1, 1)) for e in items]
    lm = SimulatorLM()
    with dspy.context(lm=lm, adapter=dspy.ChatAdapter()):
        gepa = dspy.GEPA(
            metric=make_metric(WordTable(items)),
            reflection_lm=SimulatorLM(role="reflection"),
            max_metric_calls=40,
            reflection_minibatch_size=2,
            use_merge=False,
            num_threads=1,
            seed=1,
            track_stats=False,
        )
        out = gepa.compile(TariffProgram(), trainset=exs, valset=exs)
    path = tmp_path / "p.json"
    out.save(str(path))
    again = TariffProgram()
    again.load(str(path))
    assert {n for n, _ in again.named_predictors()} == {"candidates", "gri", "subheading", "cite", "confidence"}
