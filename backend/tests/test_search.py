"""Search engine over the committed sample: BM25 + reranker, filters, statuses, snippets, tariff text."""

from __future__ import annotations

from datetime import date

import pytest
from django.conf import settings

from tariffcompass.contracts import Retriever
from tariffcompass.search import engine


@pytest.fixture(scope="module")
def retriever(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("index")
    cfg = settings.TARIFF_COMPASS
    old = cfg["INDEX_DIR"]
    cfg["INDEX_DIR"] = str(tmp)
    try:
        yield engine.build_retriever(sample=True)
    finally:
        cfg["INDEX_DIR"] = old


def test_it_is_a_retriever(retriever):
    assert isinstance(retriever, Retriever)


def test_bm25_finds_the_tumbler_rulings_and_the_reranker_follows_the_first_stage(retriever):
    q = "20 oz double-wall vacuum insulated stainless steel tumbler with lid"
    plain = retriever.rulings(q, k=10)
    assert plain and {h.heading for h in plain} & {"9617", "7323"}
    led = retriever.rulings(q, k=10, heading_probs={"9617": 0.9})
    assert led[0].heading == "9617"
    assert all(h.rerank >= led[i + 1].rerank for i, h in enumerate(led[:-1]))


def test_heading_filter_and_snippets(retriever):
    hits = retriever.rulings("stainless steel vacuum bottle", headings=["9617"], k=5)
    assert hits and all(h.heading == "9617" for h in hits)
    text, spans = hits[0].passages[0]
    assert spans and all(0 <= s.start < s.end <= len(text) for s in spans)


def test_a_cutoff_hides_rulings_issued_on_or_after_it(retriever):
    hits = retriever.rulings("stainless steel bottle", k=20, before=date(2019, 1, 1))
    assert hits and all(h.issued < date(2019, 1, 1) for h in hits)
    later = retriever.with_cutoff(date(2019, 1, 1)).rulings("stainless steel bottle", k=20)
    assert all(h.issued < date(2019, 1, 1) for h in later)


def test_the_hero_rulings_resolve_with_their_real_numbers(retriever):
    doc = retriever.ruling("HQ H303684")
    assert doc and "Revocation of NY N297758" in doc.subject and doc.source_url.endswith("/H303684")
    assert retriever.ruling("NY N321134").code == "9617001000"
    assert retriever.ruling("NY N297165").code.startswith("7323")
    noted = retriever.ruling("NY N297758")
    assert noted.status == "revoked" and noted.status_by == "HQ H303684"
    assert noted.text.startswith("The letter for NY N297758 is not in the corpus")


def test_empty_query_lists_newest_first_and_browse_pages(retriever):
    hits = retriever.rulings("", k=5)
    assert [h.issued for h in hits] == sorted((h.issued for h in hits), reverse=True)
    page, total = retriever.browse("vacuum", heading="9617", limit=2)
    assert total >= len(page) >= 1


def test_tariff_text_lines_rates_and_children(retriever):
    line = retriever.tariff_line("US", "9617.00.10.00")
    assert line and line.general_rate == "7.2%" and "Vacuum flasks" in line.full_text
    assert retriever.tariff_line("CA", "9617000000").general_rate == "7.5%"
    kids = retriever.tariff_children("US", "9617")
    assert kids and all(k.code.startswith("9617") for k in kids)
    found = retriever.tariff("vacuum flask", country="US", k=5)
    assert any(f.code.startswith("9617") for f in found)
