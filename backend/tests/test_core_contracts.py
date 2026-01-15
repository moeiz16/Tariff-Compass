from __future__ import annotations

from datetime import date
from decimal import Decimal

import dspy
import pytest

from tariffcompass import codes, fakes, services
from tariffcompass.adapters.embeddings import FakeEmbeddings, cosine
from tariffcompass.adapters.lm_sim import SimulatorEngine, SimulatorLM, field_in, render
from tariffcompass.adapters.vision import FakeVision
from tariffcompass.contracts import (
    ClassifierProgram,
    DutyEngine,
    FirstStage,
    LandedCostQuery,
    Optimizer,
    ProductQuery,
    Retriever,
)


def test_code_formatting_follows_each_schedule():
    assert codes.fmt("9617001000") == "9617.00.10.00"
    assert codes.fmt("9617.00.1000") == "9617.00.10.00"
    assert codes.fmt_as_quoted_by_cbp("9617001000") == "9617.00.1000"
    assert codes.fmt("961700") == "9617.00"
    assert codes.heading("9617.00.10.00") == "9617"


def test_fakes_satisfy_the_protocols():
    assert isinstance(fakes.FakeRetriever(), Retriever)
    assert isinstance(fakes.FakeFirstStage(), FirstStage)
    assert isinstance(fakes.FakeProgram(), ClassifierProgram)
    assert isinstance(fakes.FakeDutyEngine(), DutyEngine)
    assert isinstance(fakes.FakeOptimizer(), Optimizer)


def test_fake_pipeline_answers_the_tumbler_with_citations():
    q = ProductQuery("20 oz double-wall vacuum insulated stainless tumbler", made_in="CN")
    first = fakes.FakeFirstStage().predict(q)
    assert first.headings[0].code == "9617"
    ans = fakes.FakeProgram().classify(q, first, fakes.FakeRetriever())
    assert ans.us and ans.us.code == "9617001000"
    assert all(c <= len(ans.citations) for claim in ans.reason for c in claim.cites)


def test_fake_landed_cost_has_a_source_and_date_on_every_line():
    lc = fakes.FakeDutyEngine().landed_cost(LandedCostQuery("US", "9617001000", "CN", Decimal("12500")))
    assert lc.lines and all(line.source and line.effective_from for line in lc.lines)
    assert lc.charges_total == Decimal("900.00")
    assert lc.tariffs_as_of == date(2026, 2, 19)


def test_services_fall_back_to_fakes_until_the_core_lands(monkeypatch):
    monkeypatch.setenv("CORE_BACKEND", "fake")
    services.reset()
    assert isinstance(services.retriever(), fakes.FakeRetriever)
    services.reset()


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Outputs will be a JSON object", '{"heading": "9617"}'),
        ("… [[ ## completed ## ]] …", "[[ ## heading ## ]]\n9617\n\n[[ ## completed ## ]]"),
        ("plain", "<heading>\n9617\n</heading>"),
    ],
)
def test_simulator_answers_in_the_adapter_format(prompt, expected):
    assert render(prompt, {"heading": "9617"}) == expected


def test_simulator_reads_fields_in_any_format():
    assert field_in("<product>\nflask\n</product>", "product") == "flask"
    assert field_in("[[ ## product ## ]]\nflask\n\n[[ ## rulings ## ]]\nx", "product") == "flask"


def test_a_dspy_program_runs_on_the_simulator():
    class Pick(dspy.Signature):
        """Pick a heading."""

        product: str = dspy.InputField()
        heading: str = dspy.OutputField()

    engine = SimulatorEngine(task=lambda outs, ins, p: {"heading": "9617" if "vacuum" in ins["product"] else "0000"})
    with dspy.context(lm=SimulatorLM(engine=engine)):
        assert dspy.Predict(Pick)(product="vacuum flask").heading == "9617"


def test_offline_adapters_are_deterministic():
    emb = FakeEmbeddings()
    a, b = emb.embed(["vacuum insulated tumbler", "vacuum insulated tumbler"])
    assert a == b and abs(cosine(a, b) - 1.0) < 1e-9
    facts = FakeVision().describe(b"\x89PNG\r\n\x1a\n....", "image/png")
    assert not facts.certain and "PNG" in facts.sentences[0]
