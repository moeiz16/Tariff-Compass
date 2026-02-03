# ruff: noqa: N803, N806  (X, P: matrices, by the usual convention)
"""Training the classical first stage (`manage.py train`), in the order STANDARDS §3b asks for.

Problem: given a product description, rank the HTSUS headings that could hold it, so the program reasons over
five candidates instead of 1,200. Metric: top-5 heading accuracy (does the right heading reach the program?),
with top-1 heading and top-3 chapter accuracy reported beside it; probabilities must be calibrated because the
program and the "Needs a broker" decision read them.

1. Freeze the split by date (dataset.freeze) before anything is tuned.
2. Features: TF-IDF word 1–2 grams + character 3–5 grams, fitted on training rulings only.
3. Baseline: multinomial logistic regression; challenger 1: linear SVM; challenger 2: LightGBM over SVD-reduced
   TF-IDF plus simple text facts, at chapter level. Each tuned with a seeded Optuna study on validation.
4. Calibration: one temperature fitted on validation (Platt-style); ECE and a reliability table before/after.
5. Pruning: keep each heading's strongest weights; the smallest level within half a point of the full model on
   validation ships, and the shipped model is what is measured.
6. The test set (newest rulings) is measured once, at the end, for every system.
7. Everything is logged to MLflow (local SQLite store under mlruns/), and the shipped model is registered.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
import warnings
from collections import Counter, defaultdict
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as sp
from django.conf import settings

from tariffcompass.classify import dataset, drift
from tariffcompass.classify.first_stage import LinearFirstStage, Vectoriser, model_dir, normalise, softmax
from tariffcompass.search import engine

SEED = 7
MIN_TRAIN_PER_HEADING = 2
WORD_FEATURES, CHAR_FEATURES = 30_000, 30_000
PRUNE_LEVELS = (300, 600, 1200, 2400, 4800)
REPORT_FILE = "first_stage_report.json"

Log = Callable[[str], None]


# ── metrics ─────────────────────────────────────────────────────────────────────────────────────────────
def topk_hits(P: np.ndarray, classes: list[str], gold: list[str], ks=(1, 3, 5)) -> dict[str, float]:
    index = {c: i for i, c in enumerate(classes)}
    order = np.argsort(-P, axis=1)[:, : max(ks)]
    out = {}
    for k in ks:
        hit = [index.get(g, -1) in order[i, :k] for i, g in enumerate(gold)]
        out[f"top{k}"] = round(float(np.mean(hit)), 4) if gold else 0.0
    return out


def ece(conf: np.ndarray, correct: np.ndarray, bins: int = 15) -> tuple[float, list[dict]]:
    edges = np.linspace(0, 1, bins + 1)
    total, table = 0.0, []
    for lo, hi in pairwise(edges):
        m = (conf > lo) & (conf <= hi)
        if not m.any():
            continue
        acc, cf = float(correct[m].mean()), float(conf[m].mean())
        total += m.mean() * abs(acc - cf)
        table.append(
            {
                "from": round(float(lo), 3),
                "to": round(float(hi), 3),
                "n": int(m.sum()),
                "confidence": round(cf, 4),
                "accuracy": round(acc, 4),
            }
        )
    return round(float(total), 4), table


def fit_temperature(logits: np.ndarray, gold_idx: np.ndarray) -> float:
    from scipy.optimize import minimize_scalar

    mask = gold_idx >= 0
    lg, gi = logits[mask], gold_idx[mask]

    def nll(t: float) -> float:
        p = softmax(lg / t)
        return float(-np.log(np.clip(p[np.arange(len(gi)), gi], 1e-12, None)).mean())

    return float(minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded").x)


def confusion_by_chapter(pred: list[str], gold: list[str], top: int = 12) -> dict:
    pairs = Counter((g, p) for g, p in zip(gold, pred, strict=True) if g != p)
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for g, p in zip(gold, pred, strict=True):
        per[g][0] += 1
        per[g][1] += g == p
    chapters = [c for c, _ in Counter(gold).most_common(top)]
    matrix = [
        [sum(1 for g, p in zip(gold, pred, strict=True) if g == a and p == b) for b in chapters] for a in chapters
    ]
    return {
        "chapters": chapters,
        "matrix": matrix,
        "topConfusions": [{"gold": g, "predicted": p, "n": n} for (g, p), n in pairs.most_common(15)],
        "perChapter": {c: {"n": v[0], "accuracy": round(v[1] / v[0], 4)} for c, v in sorted(per.items())},
    }


# ── features ────────────────────────────────────────────────────────────────────────────────────────────
def fit_vectoriser(texts: list[str]) -> tuple[Vectoriser, object, object]:
    from sklearn.feature_extraction.text import TfidfVectorizer

    word = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, max_df=0.5, max_features=WORD_FEATURES, sublinear_tf=True, dtype=np.float32
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=3,
        max_df=0.5,
        max_features=CHAR_FEATURES,
        sublinear_tf=True,
        dtype=np.float32,
    )
    norm = [normalise(t) for t in texts]
    word.fit(norm)
    char.fit(norm)
    return Vectoriser.from_sklearn(word, char), word, char


def transform(word, char, texts: list[str]) -> sp.csr_matrix:
    norm = [normalise(t) for t in texts]
    return sp.hstack([word.transform(norm), char.transform(norm)]).tocsr().astype(np.float32)


def text_facts(texts: list[str]) -> np.ndarray:
    rows = []
    for t in texts:
        words = t.split()
        rows.append(
            [
                np.log1p(len(t)),
                np.log1p(len(words)),
                sum(ch.isdigit() for ch in t) / max(len(t), 1),
                t.count("%") > 0,
                " of " in t,
            ]
        )
    return np.asarray(rows, dtype=np.float32)


def prune(coef: np.ndarray, keep: int | None) -> sp.csc_matrix:
    """Keep each heading's `keep` largest-magnitude weights. coef: (n_features, n_headings)."""
    if keep is None or keep >= coef.shape[0]:
        return sp.csc_matrix(coef)
    rows, cols, vals = [], [], []
    for j in range(coef.shape[1]):
        col = coef[:, j]
        idx = np.argpartition(-np.abs(col), keep)[:keep]
        rows.append(idx)
        cols.append(np.full(len(idx), j))
        vals.append(col[idx])
    return sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=coef.shape)


# ── the run ─────────────────────────────────────────────────────────────────────────────────────────────
def run(*, trials: dict[str, int] | None = None, log: Log = print, mlflow_on: bool = True) -> dict:
    warnings.filterwarnings("ignore")
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    import optuna
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC

    trials = {"lr": 5, "svm": 4, "lgbm": 6, **(trials or {})}
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    t_start = time.perf_counter()
    rulings, _, is_sample = engine.load_corpus()
    frozen = dataset.artifact_dir() / dataset.SPLITS_FILE
    if not frozen.exists():
        meta = dataset.freeze(dataset.make_splits(rulings), rulings)
        log(f"froze the split: {meta['counts']} (test hash {meta['hashes']['test'][:12]})")
    sp_ = dataset.load_splits(rulings)
    train, val, test = sp_.train, sp_.val, sp_.test
    log(
        f"split: {len(train)} train · {len(val)} validation · {len(test)} test (frozen "
        f"{sp_.meta['hashes']['test'][:12]})"
    )

    counts = Counter(e.heading for e in train)
    classes = sorted(h for h, n in counts.items() if n >= MIN_TRAIN_PER_HEADING)
    cidx = {c: i for i, c in enumerate(classes)}
    tr = [e for e in train if e.heading in cidx]
    y_tr = np.asarray([cidx[e.heading] for e in tr])
    vec, word, char = fit_vectoriser([e.text for e in tr])
    X_tr = transform(word, char, [e.text for e in tr])
    X_va = transform(word, char, [e.text for e in val])
    X_te = transform(word, char, [e.text for e in test])
    g_va = [e.heading for e in val]
    gi_va = np.asarray([cidx.get(h, -1) for h in g_va])
    log(
        f"features: {X_tr.shape[1]} ({vec.n_word} word, {X_tr.shape[1] - vec.n_word} character); "
        f"{len(classes)} headings"
    )
    report: dict = {
        "problem": "rank HTSUS headings for a product description; ship top-k candidates to the program",
        "primaryMetric": "top-5 heading accuracy on the newest rulings",
        "split": {k: v for k, v in sp_.meta.items() if k != "ids"},
        "classes": len(classes),
        "features": {"word": vec.n_word, "char": X_tr.shape[1] - vec.n_word},
        "trainUsed": len(tr),
        "valHeadingsUnseen": int((gi_va < 0).sum()),
        "testHeadingsUnseen": sum(1 for e in test if e.heading not in cidx),
        "sample": is_sample,
        "studies": {},
    }

    # Baseline: logistic regression
    lr_cache: dict[float, Any] = {}

    def lr_obj(trial) -> float:
        c = trial.suggest_float("C", 0.5, 60.0, log=True)
        m = LogisticRegression(C=c, solver="saga", max_iter=80, tol=1e-3, random_state=SEED).fit(X_tr, y_tr)
        lr_cache[c] = m
        return topk_hits(m.predict_proba(X_va), classes, g_va, (5,))["top5"]

    t0 = time.perf_counter()
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(lr_obj, n_trials=trials["lr"])
    lr: Any = lr_cache[study.best_params["C"]]
    lr_cache.clear()
    report["studies"]["logistic_regression"] = _study_row(study, time.perf_counter() - t0)
    log(
        f"logistic regression: C={study.best_params['C']:.2f} validation top-5 {study.best_value:.3f} "
        f"({time.perf_counter() - t0:.0f}s)"
    )

    # Challenger 1: linear SVM
    svm_cache: dict[float, Any] = {}

    def svm_obj(trial) -> float:
        c = trial.suggest_float("C", 0.02, 2.0, log=True)
        m = LinearSVC(C=c, random_state=SEED).fit(X_tr, y_tr)
        svm_cache[c] = m
        return topk_hits(m.decision_function(X_va), classes, g_va, (5,))["top5"]

    t0 = time.perf_counter()
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(svm_obj, n_trials=trials["svm"])
    svm: Any = svm_cache[study.best_params["C"]]
    svm_cache.clear()
    report["studies"]["linear_svm"] = _study_row(study, time.perf_counter() - t0)
    log(f"linear SVM: C={study.best_params['C']:.3f} validation top-5 {study.best_value:.3f}")

    # Challenger 2: LightGBM at chapter level on SVD-reduced TF-IDF + text facts
    lgbm_out = _lightgbm(X_tr, X_va, X_te, tr, val, test, trials["lgbm"], log)
    report["studies"]["lightgbm_chapter"] = lgbm_out["study"]

    # Champion on validation (primary metric top-5 heading), then calibration and pruning
    linear = {
        "logistic_regression": (lr.coef_.T.astype(np.float32), lr.intercept_.astype(np.float32)),
        "linear_svm": (svm.coef_.T.astype(np.float32), svm.intercept_.astype(np.float32)),
    }
    val_rows = {}
    temps = {}
    for name, (cf, ic) in linear.items():
        lg = np.asarray(X_va @ cf) + ic
        temps[name] = fit_temperature(lg, gi_va)
        val_rows[name] = topk_hits(softmax(lg / temps[name]), classes, g_va)
    champ = max(val_rows, key=lambda n: (val_rows[n]["top5"], val_rows[n]["top1"]))
    report["validation"] = val_rows
    log(f"champion on validation: {champ} {val_rows[champ]}")
    coef, intercept = linear[champ]
    full_va = val_rows[champ]
    prune_rows = []
    chosen = None
    for keep in PRUNE_LEVELS:
        c = prune(coef, keep)
        lg = np.asarray((X_va @ c).todense()) + intercept
        t = fit_temperature(lg, gi_va)
        hits = topk_hits(softmax(lg / t), classes, g_va)
        prune_rows.append({"keep": keep, **hits, "nonzeros": int(c.nnz)})
        if chosen is None and hits["top1"] >= full_va["top1"] - 0.005 and hits["top5"] >= full_va["top5"] - 0.005:
            chosen = (keep, c, t)
    if chosen is None:
        keep = PRUNE_LEVELS[-1]
        c = prune(coef, keep)
        chosen = (keep, c, fit_temperature(np.asarray((X_va @ c).todense()) + intercept, gi_va))
    keep, coef_p, temp = chosen
    coef_p = coef_p.tocsc()
    coef_p.data = coef_p.data.astype(np.float16).astype(np.float32)  # the precision it is stored at
    report["pruning"] = {"model": champ, "full": full_va, "levels": prune_rows, "chosen": keep}
    log(f"pruning: keep {keep} weights per heading (validation top-5 {full_va['top5']:.3f} unpruned)")

    short = "svm" if champ == "linear_svm" else "lr"
    version = f"first-stage-{short}-{sp_.meta['hashes']['test'][:8]}-k{keep}"
    shipped = LinearFirstStage(vec, coef_p.tocsr(), intercept, classes, temp, version)
    # check the shipped vectoriser reproduces scikit-learn's features exactly
    probe = [e.text for e in val[:50]]
    diff = (
        float(abs(sp.vstack([vec.transform_one(t) for t in probe]) - transform(word, char, probe)).max())
        if probe
        else 0.0
    )
    report["vectoriserParity"] = round(diff, 6)

    # Calibration report (validation, before/after), then the test set, once
    lg_va = shipped.logits(X_va)
    p_raw, p_cal = softmax(lg_va), softmax(lg_va / temp)
    corr_va = np.asarray([classes[i] == g for i, g in zip(p_cal.argmax(1), g_va, strict=True)])
    e_raw, _ = ece(p_raw.max(1), corr_va)
    e_cal, rel_va = ece(p_cal.max(1), corr_va)
    report["calibration"] = {
        "method": "temperature scaling on validation (Platt-style, one parameter)",
        "temperature": round(temp, 4),
        "eceValBefore": e_raw,
        "eceValAfter": e_cal,
        "reliabilityVal": rel_va,
    }

    g_te = [e.heading for e in test]
    chap_classes = shipped.chapters
    gold_ch = [h[:2] for h in g_te]
    P_te = shipped.proba(X_te)
    sh_hits = topk_hits(P_te, classes, g_te)
    ch_hits = topk_hits(shipped.chapter_proba(P_te), chap_classes, gold_ch)
    corr_te = np.asarray([classes[i] == g for i, g in zip(P_te.argmax(1), g_te, strict=True)])
    e_te, rel_te = ece(P_te.max(1), corr_te)
    systems: dict = {"shipped": {"model": champ, "heading": sh_hits, "chapter": ch_hits, "ece": e_te}}
    for name, (cf, ic) in linear.items():
        P = softmax((np.asarray(X_te @ cf) + ic) / temps[name])
        systems[name] = {
            "heading": topk_hits(P, classes, g_te),
            "chapter": topk_hits(_chapter_sum(P, classes, chap_classes), chap_classes, gold_ch),
        }
    systems["lightgbm_chapter"] = {"chapter": lgbm_out["test"]}
    pred_h = [classes[i] for i in P_te.argmax(1)]
    report["test"] = {
        "n": len(test),
        "window": sp_.meta.get("testWindow"),
        "systems": systems,
        "reliability": rel_te,
        "confusionByChapter": confusion_by_chapter([p[:2] for p in pred_h], gold_ch),
    }
    report["champion"] = _champion(report, champ)
    log(
        f"test ({len(test)} newest rulings): heading top-1 {sh_hits['top1']:.3f} top-5 "
        f"{sh_hits['top5']:.3f}; chapter top-3 {ch_hits['top3']:.3f}; ECE {e_te:.3f}"
    )

    # Drift as new rulings arrive: chapter mix of each test month against training
    months: dict[str, list[str]] = defaultdict(list)
    for e in test:
        months[e.issued.strftime("%Y-%m")].append(e.chapter)
    train_ch = [e.chapter for e in train]
    report["drift"] = {
        "trainVsTest": drift.chapter_psi(train_ch, [e.chapter for e in test]),
        "trainVsValidation": drift.chapter_psi(train_ch, [e.chapter for e in val]),
        "byMonth": [
            {"month": m, "n": len(v), **{k: drift.chapter_psi(train_ch, v)[k] for k in ("psi", "reading")}}
            for m, v in sorted(months.items())
        ],
        "predictedMixTrainVsTest": drift.chapter_psi(train_ch, [p[:2] for p in pred_h]),
    }

    # Latency of the shipped first stage on single queries
    from tariffcompass.contracts import ProductQuery

    lat = []
    for e in test[:300]:
        t0 = time.perf_counter()
        shipped.predict(ProductQuery(e.text), k=5)
        lat.append((time.perf_counter() - t0) * 1000)
    report["latencyMs"] = {
        "p50": round(float(np.percentile(lat, 50)), 2),
        "p95": round(float(np.percentile(lat, 95)), 2),
        "n": len(lat),
    }

    d = model_dir()
    shipped.save(
        d, {"trainedOn": len(tr), "pruneKeep": keep, "seed": SEED, "splitTestHash": sp_.meta["hashes"]["test"]}
    )
    report["artifactBytes"] = {p.name: p.stat().st_size for p in d.iterdir()}
    report["seconds"] = round(time.perf_counter() - t_start, 1)
    report["version"] = version
    out = dataset.artifact_dir() / REPORT_FILE
    out.write_text(json.dumps(report, indent=1) + "\n")
    if mlflow_on:
        report["mlflow"] = _track(report, d, out, log)
        out.write_text(json.dumps(report, indent=1) + "\n")
    return report


def _chapter_sum(P: np.ndarray, classes: list[str], chapters: list[str]) -> np.ndarray:
    idx = np.asarray([chapters.index(c[:2]) for c in classes])
    out = np.zeros((P.shape[0], len(chapters)))
    np.add.at(out.T, idx, P.T)  # type: ignore[arg-type]
    return out


def _study_row(study, seconds: float) -> dict:
    return {
        "best": {k: round(v, 4) for k, v in study.best_params.items()},
        "valTop5": round(study.best_value, 4),
        "trials": [
            {**{k: round(v, 4) for k, v in t.params.items()}, "valTop5": round(t.value, 4)} for t in study.trials
        ],
        "seconds": round(seconds, 1),
    }


def _champion(report: dict, champ: str) -> dict:
    v = report["validation"]
    return {
        "shipped": f"{champ.replace('_', ' ')} (pruned, temperature-calibrated)",
        "rule": "highest validation top-5 heading accuracy, then top-1 (decided before the test set is read)",
        "validation": v,
        "lightgbm": "LightGBM ranks chapters only and is kept as a challenger; it is compared at chapter level.",
        "promotion": "A challenger replaces the shipped model only through the Lab's two-signature sign-off.",
    }


def _lightgbm(X_tr, X_va, X_te, tr, val, test, n_trials: int, log: Log) -> dict:
    import lightgbm as lgb
    import optuna
    from sklearn.decomposition import TruncatedSVD

    t0 = time.perf_counter()
    svd = TruncatedSVD(n_components=160, random_state=SEED, algorithm="randomized", n_iter=4)
    Z_tr = np.hstack([svd.fit_transform(X_tr), text_facts([e.text for e in tr])])
    Z_va = np.hstack([svd.transform(X_va), text_facts([e.text for e in val])])
    Z_te = np.hstack([svd.transform(X_te), text_facts([e.text for e in test])])
    counts = Counter(e.chapter for e in tr)
    chapters = sorted(c for c, n in counts.items() if n >= 5)
    ci = {c: i for i, c in enumerate(chapters)}
    keep = np.asarray([e.chapter in ci for e in tr])
    y = np.asarray([ci[e.chapter] for e in tr if e.chapter in ci])
    y_va = np.asarray([ci.get(e.chapter, -1) for e in val])
    va_mask = y_va >= 0
    g_va, g_te = [e.chapter for e in val], [e.chapter for e in test]
    models: dict[int, Any] = {}

    def obj(trial) -> float:
        params = {
            "num_leaves": trial.suggest_int("num_leaves", 7, 31),
            "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.2, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 40),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 5.0, log=True),
        }
        m = lgb.LGBMClassifier(
            objective="multiclass",
            n_estimators=250,
            subsample=0.8,
            subsample_freq=1,
            random_state=SEED,
            n_jobs=2,
            verbose=-1,
            **params,
        )
        m.fit(
            Z_tr[keep], y, eval_set=[(Z_va[va_mask], y_va[va_mask])], callbacks=[lgb.early_stopping(20, verbose=False)]
        )
        models[trial.number] = m
        return topk_hits(np.asarray(m.predict_proba(Z_va)), chapters, g_va, (1,))["top1"]

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(obj, n_trials=n_trials)
    best: Any = models[study.best_trial.number]
    hits = topk_hits(best.predict_proba(Z_te), chapters, g_te, (1, 3, 5))
    contrib = best.predict_proba(Z_te[:1], pred_contrib=True)
    log(
        f"LightGBM (chapters): validation top-1 {study.best_value:.3f}; test top-3 {hits['top3']:.3f} "
        f"({time.perf_counter() - t0:.0f}s)"
    )
    return {
        "study": {
            "best": study.best_params,
            "valTop1": round(study.best_value, 4),
            "bestIteration": int(getattr(best, "best_iteration_", 0) or 0),
            "chapters": len(chapters),
            "features": "SVD(160) of the TF-IDF + 5 text facts",
            "contributionsShape": list(np.asarray(contrib).shape),
            "seconds": round(time.perf_counter() - t0, 1),
        },
        "test": hits,
    }


def register(run_id: str, name: str = "tariff-compass-first-stage") -> int:
    """Register the run's first_stage artefacts as a new version of the registered model."""
    from mlflow.exceptions import MlflowException
    from mlflow.tracking import MlflowClient

    client = MlflowClient()
    with contextlib.suppress(MlflowException):  # already registered
        client.create_registered_model(name)
    run = client.get_run(run_id)
    mv = client.create_model_version(name, f"{run.info.artifact_uri}/first_stage", run_id=run_id)
    return int(mv.version)


def _track(report: dict, model_path: Path, report_path: Path, log: Log) -> dict:
    try:
        import mlflow

        cfg = settings.TARIFF_COMPASS
        Path(str(cfg["MLFLOW_TRACKING_URI"]).replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
        mlflow.set_tracking_uri(str(cfg["MLFLOW_TRACKING_URI"]))
        exp = mlflow.get_experiment_by_name("first-stage")
        if exp is None:
            mlflow.create_experiment("first-stage", artifact_location=Path(str(cfg["MLFLOW_ARTIFACT_ROOT"])).as_uri())
        mlflow.set_experiment("first-stage")
        with mlflow.start_run(run_name=report["version"]) as run:
            mlflow.log_params(
                {
                    "classes": report["classes"],
                    "pruneKeep": report["pruning"]["chosen"],
                    "champion": report["pruning"]["model"],
                    "seed": SEED,
                    **{f"lr_{k}": v for k, v in report["studies"]["logistic_regression"]["best"].items()},
                    **{f"svm_{k}": v for k, v in report["studies"]["linear_svm"]["best"].items()},
                }
            )
            for system, vals in report["test"]["systems"].items():
                for level, hits in vals.items():
                    if isinstance(hits, dict) and level in ("heading", "chapter"):
                        for k, v in hits.items():
                            mlflow.log_metric(f"test_{system}_{level}_{k}", v)
            mlflow.log_metric("test_ece", report["test"]["systems"]["shipped"]["ece"])
            mlflow.log_metric("latency_p95_ms", report["latencyMs"]["p95"])
            mlflow.log_metric("psi_train_vs_test", report["drift"]["trainVsTest"]["psi"])
            mlflow.log_artifacts(str(model_path), artifact_path="first_stage")
            mlflow.log_artifact(str(report_path))
            run_id = run.info.run_id
        registered = None
        try:
            registered = register(run_id)
        except Exception as exc:  # registry unavailable on this store: the run is still tracked
            log(f"registry skipped: {exc}")
        return {"experiment": "first-stage", "runId": run_id, "registeredVersion": registered}
    except Exception as exc:  # tracking must never break training
        log(f"MLflow tracking skipped: {exc}")
        return {"error": str(exc)}
