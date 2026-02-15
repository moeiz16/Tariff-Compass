"""Re-fit the in-use confidence word (word matching's) under the declared threshold rule (confidence.THRESHOLD_RULE).

    manage.py recalibrate --seed 7 --train-n 400 --val-n 200            # validation only: fit, reproduce, save
    manage.py recalibrate --seed 7 --train-n 400 --val-n 200 --measure-test   # then read the test set once

The validation rulings are rebuilt exactly as the training round that fitted the current word did (same seed,
same sample sizes, same frozen split), and the reconstruction is checked two ways before anything is saved: the
round's validation snapshot hash must match, and fitting with the earlier rule must give back the saved
coefficients and threshold. The logistic fit is the same; only where "Strong match" starts changes.

Validation decides everything. `--measure-test` only measures the saved word on the frozen test set and records
that look in classify/artifacts/word_matching.confidence-report.json; it never changes the threshold.
"""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

from tariffcompass.classify import confidence as conf_mod
from tariffcompass.classify import dataset
from tariffcompass.classify.program import artifact_dir, calibrator_path

REPORT_FILE = "word_matching.confidence-report.json"


def report_path() -> Path:
    return artifact_dir() / REPORT_FILE


def _held_validation(seed: int, train_n: int, val_n: int, round_n: int):
    """The validation rulings no training round used, rebuilt as optimize.GepaOptimizer.run_full builds them."""
    from django.conf import settings

    from tariffcompass import services
    from tariffcompass.classify import optimize
    from tariffcompass.search import engine

    rulings, _, sample = engine.load_corpus()
    if sample:
        raise RuntimeError("the full rulings corpus (make fetch-data) is needed to rebuild the validation rulings")
    splits = dataset.load_splits(rulings)
    first, retriever = services.first_stage(), services.retriever()
    rng = random.Random(seed)  # noqa: S311 (sampling examples, not security)
    val = sorted(splits.val, key=lambda e: (e.issued, e.id))
    cut = int(len(val) * 0.6)
    pool_train, pool_val = val[:cut], val[cut:]
    tr = rng.sample(pool_train, min(train_n, len(pool_train)))
    va = rng.sample(pool_val, min(val_n, len(pool_val)))
    cache = optimize.EvidenceCache(Path(str(settings.TARIFF_COMPASS["INDEX_DIR"])).parent / "cache" / "evidence.tsv")
    d_va = [optimize.to_dspy(e, first, retriever, e.issued, cache) for e in va]
    details = json.loads((artifact_dir() / "rounds" / f"round-{round_n}.details.json").read_text())
    if optimize.sha(d_va) != details["snapshots"]["val"]:
        raise RuntimeError(f"the rebuilt validation sample doesn't match round {round_n}'s snapshot")
    used = {e.id for e in tr} | {e.id for e in va}
    held = [e for e in val if e.id not in used]
    d_held = [optimize.to_dspy(e, first, retriever, e.issued, cache) for e in held]
    return d_held, splits, first, retriever, cache


def refit(seed: int = 7, train_n: int = 400, val_n: int = 200, round_n: int = 7) -> dict:
    """Fit the in-use word under the declared rule on validation; save it and the validation half of the report."""
    from tariffcompass.classify import optimize

    d_held, *_ = _held_validation(seed, train_n, val_n, round_n)
    preds = optimize.word_matching(d_held)
    x, y = [p["x"] for p in preds], optimize.right_six(preds, d_held)
    earlier = json.loads(report_path().read_text()) if report_path().exists() else {}
    if earlier.get("test") is not None:
        raise RuntimeError("this rule was already measured on the test set; re-fitting now would not be clean")
    ref = earlier.get("previousWord") or {
        k: v for k, v in conf_mod.Calibrator.load(calibrator_path(None)).__dict__.items() if k != "validation"
    }
    old = conf_mod.fit(x, y, rule="point")
    if (old.coef, old.intercept, old.threshold) != (ref["coef"], ref["intercept"], ref["threshold"]):
        raise RuntimeError("fitting with the earlier rule doesn't reproduce the saved word; nothing was changed")
    new = conf_mod.fit(x, y, rule=conf_mod.THRESHOLD_RULE)
    previous = earlier.get("previous")
    if previous is None:
        details = json.loads((artifact_dir() / "rounds" / f"round-{round_n}.details.json").read_text())
        wm = details["confidence"]["wordMatching"]
        previous = {"rule": "point", "threshold": wm["threshold"], "validation": wm["validation"], "test": wm["test"]}
    new.save(calibrator_path(None))
    report = {
        "system": "word matching (in use)",
        "rule": conf_mod.THRESHOLD_RULE,
        "ruleText": (
            "Strong match starts at the lowest calibrated probability where, on the held-out validation rulings, "
            f"the one-sided {conf_mod.CONFIDENCE_LEVEL:.0%} Clopper-Pearson lower bound of the share of Strong "
            f"answers right at six digits is at least {conf_mod.TARGET_PRECISION:.2f} (and at least "
            f"{conf_mod.MIN_STRONG} answers say Strong)."
        ),
        "fittedFrom": {"round": round_n, "seed": seed, "trainN": train_n, "valN": val_n, "heldOut": len(d_held)},
        "reproduced": {"threshold": old.threshold, "coefficients": True},
        "previousWord": {"coef": ref["coef"], "intercept": ref["intercept"], "threshold": ref["threshold"]},
        "threshold": new.threshold,
        "validation": new.validation,
        "previous": previous,
        "test": None,
        "testLook": None,
    }
    report_path().write_text(json.dumps(report, indent=1) + "\n")
    return report


def measure_test(seed: int = 7, train_n: int = 400, val_n: int = 200, round_n: int = 7) -> dict:
    """Read the frozen test set once with the saved word; record the measurement and that the look was made."""
    from tariffcompass.classify import optimize

    report = json.loads(report_path().read_text())
    if report.get("test") is not None:
        raise RuntimeError("the test set was already measured for this rule; a second look would not be clean")
    _, splits, first, retriever, cache = _held_validation(seed, train_n, val_n, round_n)
    test_from = date.fromisoformat(splits.meta["testFrom"])
    d_te = [optimize.to_dspy(e, first, retriever, test_from, cache) for e in splits.test]
    cal = conf_mod.Calibrator.load(calibrator_path(None))
    preds = optimize.word_matching(d_te)
    report["test"] = conf_mod.measure(cal, [p["x"] for p in preds], optimize.right_six(preds, d_te))
    report["testLook"] = (
        "One further look at the test set, made after this rule and its threshold were fixed on validation. The "
        "test set had already been read many times while the pipeline was being fixed (eval/RESULTS.md); the "
        "earlier word's 87 in 100 came from one of those readings, so this rule was adopted after that look."
    )
    report_path().write_text(json.dumps(report, indent=1) + "\n")
    return report


def refit_alternatives(seed: int = 7, train_n: int = 400, val_n: int = 200, round_n: int = 7) -> dict:
    """Choose the "Also possible" floor on validation only: the lowest first-stage probability on the declared grid
    at which the alternatives the rule would show are the right heading at least ALTERNATIVE_TARGET of the time
    (over at least ALTERNATIVE_MIN_SHOWN shown). Written to classify/artifacts/alternative.json."""
    from tariffcompass.classify import program as prog

    d_held, *_ = _held_validation(seed, train_n, val_n, round_n)
    rows = []
    for ex in d_held:
        e = json.loads(ex.evidence)
        pred = prog.word_matching_prediction(e, ex.product)
        rows.append((e, pred.heading, list(pred.set_aside), list(pred.order), ex.gold_heading))
    sweep, floor = [], None
    for f in prog.ALTERNATIVE_FLOOR_GRID:
        shown = right = 0
        for e, heading, set_aside, order, gold in rows:
            alt = prog.plausible_alternative(e, heading, set_aside, order, floor=f)
            if alt is not None:
                shown += 1
                right += alt == gold
        share = round(right / shown, 4) if shown else None
        sweep.append({"floor": f, "shown": shown, "right": right, "share": share})
        if floor is None and shown >= prog.ALTERNATIVE_MIN_SHOWN and (share or 0.0) >= prog.ALTERNATIVE_TARGET:
            floor = f
    wrong = sum(1 for _, h, *_rest, g in rows if h != g)
    out = {
        "rule": (
            "Offer a neighbouring heading as “Also possible” only when it and the answer are a documented pair with "
            "a deciding fact (the disputes CBP's rulings turn on, such as 9617 against 7323), or when the first "
            "stage gives it at least `floor` of probability and it has real support (it shares the answer's chapter, "
            "or one of the product's ten closest rulings is held under it). `floor` is the lowest value on the "
            "declared grid at which the "
            f"alternatives shown on validation are the right heading at least {prog.ALTERNATIVE_TARGET:.0%} of the "
            f"time (over at least {prog.ALTERNATIVE_MIN_SHOWN} shown); none is shown if no value qualifies."
        ),
        "target": prog.ALTERNATIVE_TARGET,
        "floor": floor if floor is not None else 1.01,
        "fittedFrom": {"round": round_n, "seed": seed, "heldOut": len(rows), "answerHeadingWrong": wrong},
        "sweep": sweep,
        "test": "not read; the floor decides only what is displayed",
        "history": (
            "The documented-pair clause was added once, before this floor was chosen, after the first sweep "
            "dropped the vacuum question from a tumbler described without the word vacuum; the floor was then "
            "chosen again on validation under the amended rule. The test set was never read for it."
        ),
    }
    (prog.artifact_dir() / prog.ALTERNATIVE_FILE).write_text(json.dumps(out, indent=1) + "\n")
    return out
