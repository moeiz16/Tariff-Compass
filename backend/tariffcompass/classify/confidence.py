"""The confidence word, calibrated: "Strong match" only when the code is right in at least 90 of 100 cases.

A Platt-scaled logistic model turns the answer's evidence into the probability that its six-digit code is right:
the first stage's probability for the chosen heading, its margin over the runner-up, whether the answer kept the
first stage's top heading, the share of retrieved rulings under that heading, how many cited rulings support it,
whether the deciding fact is stated for it (or against it, or only read), and whether the closest ruling under the
heading holds the chosen line. It is fitted on validation rulings that no training round used, and the threshold
is the lowest probability at which "Strong match" is right at least 90 times in 100 on those rulings. Everything
below the threshold says "Needs a broker". The test set only reports how this holds up.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import numpy as np

FEATURES = (
    "first_stage_p",
    "margin",
    "kept_first_stage_top",
    "precedent",
    "agreeing",
    "deciding_for",
    "deciding_against_or_read",
    "closest_ruling_holds_line",
)
TARGET_PRECISION = 0.90


def features(e: dict, heading: str, code: str, cited: list[dict], support_ids: list[str], product: str) -> list[float]:
    from tariffcompass.classify import evidence as ev

    p = {c["heading"]: c["p"] for c in e["candidates"]}
    ranked = sorted(p.values(), reverse=True)
    top = e["first_stage"][0]["code"] if e["first_stage"] else ""
    others = [v for h, v in p.items() if h != heading]
    support = [r for r in cited if r["id"] in set(support_ids)]
    agreeing = sum(1 for r in support if r["heading"] == heading)
    runner = next((h for h, _ in sorted(p.items(), key=lambda kv: -kv[1]) if h != heading), None)
    deciding = ev.deciding_status(product, heading, runner)
    near = next((r for r in e["rulings"].get(heading, []) if r["status"] != "revoked" and len(r["code"]) == 10), None)
    return (
        [
            p.get(heading, 0.0),
            p.get(heading, 0.0) - (max(others) if others else 0.0),
            1.0 if heading == top else 0.0,
            float(e["votes"].get(heading, 0.0)),
            float(min(agreeing, 4)),
            1.0 if deciding == "stated_for" else 0.0,
            1.0 if deciding in ("stated_against", "read") else 0.0,
            1.0 if near is not None and near["code"][:6] == code[:6] else 0.0,
        ]
        if ranked
        else [0.0] * len(FEATURES)
    )


@dataclass
class Calibrator:
    coef: list[float]
    intercept: float
    threshold: float  # "Strong match" at or above this probability
    fitted_on: int
    validation: dict  # precision, coverage, ece of the fit

    def probability(self, x: list[float]) -> float:
        z = self.intercept + sum(c * v for c, v in zip(self.coef, x, strict=True))
        return 1.0 / (1.0 + math.exp(-z))

    def verdict(self, x: list[float]) -> str:
        return "strong" if self.probability(x) >= self.threshold else "broker"

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({**self.__dict__, "features": FEATURES}, indent=1) + "\n")

    @classmethod
    def load(cls, path: Path) -> Calibrator:
        d = json.loads(path.read_text())
        d.pop("features", None)
        return cls(**d)


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in pairwise(edges):
        m = (p > lo) & (p <= hi)
        if m.any():
            total += m.mean() * abs(y[m].mean() - p[m].mean())
    return round(float(total), 4)


def fit(x: list[list[float]], y: list[bool], target: float = TARGET_PRECISION) -> Calibrator:
    from sklearn.linear_model import LogisticRegression

    X, Y = np.asarray(x, dtype=float), np.asarray(y, dtype=int)  # noqa: N806
    if len(set(Y.tolist())) < 2:
        return Calibrator([0.0] * len(FEATURES), 0.0, 1.01, len(Y), {"note": "one class only"})
    lr = LogisticRegression(C=1.0, max_iter=1000).fit(X, Y)
    p = lr.predict_proba(X)[:, 1]
    threshold = 1.01
    for t in sorted(set(np.round(p, 4).tolist())):
        m = p >= t
        if m.sum() >= 10 and Y[m].mean() >= target:
            threshold = float(t)
            break
    m = p >= threshold
    val = {
        "precision": round(float(Y[m].mean()), 4) if m.any() else None,
        "coverage": round(float(m.mean()), 4),
        "ece": ece(p, Y),
        "rightRate": round(float(Y.mean()), 4),
        "wrongCaught": round(float((~m & (Y == 0)).sum() / max((Y == 0).sum(), 1)), 4),
    }
    return Calibrator(
        [round(float(c), 6) for c in lr.coef_[0]], round(float(lr.intercept_[0]), 6), threshold, len(Y), val
    )


def measure(cal: Calibrator, x: list[list[float]], y: list[bool]) -> dict:
    p = np.asarray([cal.probability(v) for v in x])
    Y = np.asarray(y, dtype=int)  # noqa: N806
    m = p >= cal.threshold
    return {
        "n": len(Y),
        "strongSaid": int(m.sum()),
        "strongRight": int(Y[m].sum()),
        "precision": round(float(Y[m].mean()), 4) if m.any() else None,
        "coverage": round(float(m.mean()), 4),
        "brokerSaid": int((~m).sum()),
        "brokerFirstGuessWrong": int(((~m) & (Y == 0)).sum()),
        "wrongCaught": round(float(((~m) & (Y == 0)).sum() / max(int((Y == 0).sum()), 1)), 4),
        "ece": ece(p, Y),
    }
