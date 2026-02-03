# ruff: noqa: N806
"""The first stage: features identical to scikit-learn's, persistence, calibrated output, the shipped model."""

from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from tariffcompass.classify import train
from tariffcompass.classify.first_stage import LinearFirstStage, load_first_stage
from tariffcompass.contracts import FirstStage, ProductQuery

TEXTS = [
    "double wall vacuum insulated stainless steel tumbler 20 oz",
    "stainless steel mixing bowl household kitchen article",
    "rechargeable led bicycle headlight usb",
    "knitted cotton pullover sweater, men's",
    "lithium-ion power bank 10000 mah",
    "backpack with outer surface of polyester",
] * 3


def test_the_json_vectoriser_reproduces_scikit_learn_exactly():
    vec, word, char = train.fit_vectoriser(TEXTS)
    ours = sp.vstack([vec.transform_one(t) for t in TEXTS])
    theirs = train.transform(word, char, TEXTS)
    assert abs(ours - theirs).max() < 1e-5


def test_save_load_round_trip_and_calibrated_top_k(tmp_path):
    vec, word, char = train.fit_vectoriser(TEXTS)
    X = train.transform(word, char, TEXTS)
    heads = ["9617", "7323", "8512", "6110", "8507", "4202"]
    y = np.array([i % 6 for i in range(len(TEXTS))])
    from sklearn.linear_model import LogisticRegression

    lr = LogisticRegression(C=10, max_iter=300).fit(X, y)
    m = LinearFirstStage(vec, sp.csr_matrix(lr.coef_.T), lr.intercept_, heads, 1.3, "t")
    m.save(tmp_path, {})
    back = LinearFirstStage.load(tmp_path)
    r = back.predict(ProductQuery("vacuum insulated tumbler"), k=3)
    assert r.headings[0].code == "9617" and len(r.headings) == 3
    assert abs(sum(back.proba(back.vec.transform_one("vacuum"))[0]) - 1.0) < 1e-5
    assert r.chapters[0].code == "96" and r.headings[0].why_terms


def test_metrics_helpers():
    P = np.array([[0.7, 0.2, 0.1], [0.1, 0.2, 0.7]])
    assert train.topk_hits(P, ["a", "b", "c"], ["a", "b"], (1, 2)) == {"top1": 0.5, "top2": 1.0}
    e, table = train.ece(np.array([0.9, 0.9, 0.2]), np.array([True, False, False]))
    assert 0 < e < 1 and sum(r["n"] for r in table) == 3
    assert train.prune(np.arange(12, dtype=float).reshape(6, 2), 2).nnz == 4


def test_the_shipped_first_stage_is_fast_and_ranks_the_obvious():
    fs = load_first_stage()
    assert isinstance(fs, FirstStage)
    r = fs.predict(ProductQuery("Men's knitted cotton pullover sweater, crew neck"), k=5)
    assert "61" in [c.code for c in r.chapters[:3]]
    assert r.elapsed_ms < 150
    assert abs(sum(c.probability for c in r.headings) - 1.0) <= 1.0


@pytest.mark.parametrize("text", ["", "x"])
def test_empty_input_still_answers(text):
    assert load_first_stage().predict(ProductQuery(text), k=2).headings
