"""Toolchain smoke: search engine, classical first stage, tuning, tracking and the job queue.

Runs offline on synthetic text in a temporary directory:
- Tantivy: build a BM25 index, query it, read back stored fields and a snippet;
- scikit-learn: TF-IDF + logistic regression and a linear SVM, calibrated, top-k;
- LightGBM: a multiclass chapter classifier on the TF-IDF matrix, with per-feature contributions;
- Optuna: a short seeded study; MLflow (skinny): a run logged to a SQLite store;
- Huey: the SQLite storage enqueues and executes a task in immediate mode and through the store.
Prints one line per check and the first-stage p95 latency.
"""

from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

DOCS = [
    ("NY N312345", "9617", "double wall vacuum insulated stainless steel tumbler with lid 20 oz"),
    ("NY N312346", "9617", "vacuum flask bottle stainless steel insulated 750 ml"),
    ("NY N312347", "7323", "stainless steel mixing bowl household kitchen article single wall"),
    ("NY N312348", "7323", "steel cookware pot kitchen household article of steel"),
    ("NY N312349", "8512", "bicycle headlight led rechargeable lighting equipment for cycles"),
    ("NY N312350", "8512", "bicycle tail light signalling equipment usb rechargeable"),
    ("NY N312351", "8513", "portable electric torch flashlight battery operated"),
    ("NY N312352", "6110", "knitted cotton pullover sweater mens"),
    ("NY N312353", "6110", "womens knit pullover cardigan cotton"),
    ("NY N312354", "8507", "lithium ion power bank battery 10000 mah"),
    ("NY N312355", "8507", "lithium ion battery pack rechargeable for lantern"),
    ("NY N312356", "4202", "backpack outer surface of textile materials hiking"),
] * 4


def check(name: str, fn) -> None:
    t0 = time.perf_counter()
    detail = fn()
    print(f"ok  {name:<10} {time.perf_counter() - t0:6.2f}s  {detail}")


def tantivy_check(tmp: Path) -> str:
    import tantivy

    sb = tantivy.SchemaBuilder()
    sb.add_text_field("ruling", stored=True, tokenizer_name="raw")
    sb.add_text_field("code", stored=True, tokenizer_name="raw")
    sb.add_text_field("body", stored=True, tokenizer_name="en_stem")
    schema = sb.build()
    (tmp / "idx").mkdir()
    index = tantivy.Index(schema, path=str(tmp / "idx"))
    w = index.writer(heap_size=15_000_000, num_threads=1)
    for rid, code, body in DOCS[:12]:
        w.add_document(tantivy.Document(ruling=rid, code=code, body=body))
    w.commit()
    w.wait_merging_threads()
    index.reload()
    s = index.searcher()
    q = index.parse_query("insulated vacuum tumbler", ["body"])
    hits = s.search(q, 3).hits
    top = s.doc(hits[0][1])
    snip = tantivy.SnippetGenerator.create(s, q, schema, "body").snippet_from_doc(top)
    return f"tantivy {getattr(tantivy, '__version__', '0.27')}: top={top['ruling'][0]} code={top['code'][0]} bm25={hits[0][0]:.2f} snippet='{snip.to_html()[:48]}'"


def ml_check(tmp: Path) -> str:
    import lightgbm as lgb
    import numpy as np
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC

    texts = [d[2] for d in DOCS]
    y = np.array([d[1] for d in DOCS])
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    X = vec.fit_transform(texts)
    lr = LogisticRegression(max_iter=500, C=4.0).fit(X, y)
    svm = CalibratedClassifierCV(LinearSVC(C=1.0), cv=3).fit(X, y)
    labels = sorted(set(y))
    yi = np.array([labels.index(v) for v in y])
    gbm = lgb.LGBMClassifier(n_estimators=40, num_leaves=7, min_child_samples=2, verbose=-1, n_jobs=1).fit(X, yi)
    contrib = gbm.predict_proba(X[:1], pred_contrib=True)
    probe = vec.transform(["insulated vacuum bottle"])
    top3 = np.argsort(-lr.predict_proba(probe)[0])[:3]
    lat = []
    for _ in range(200):
        t0 = time.perf_counter()
        p = lr.predict_proba(vec.transform(["rechargeable bike light with usb"]))
        lat.append((time.perf_counter() - t0) * 1000)
    p95 = statistics.quantiles(lat, n=20)[18]
    return (
        f"lr top3={[lr.classes_[i] for i in top3]} svm={svm.predict(probe)[0]} lgbm={labels[int(gbm.predict(probe)[0])]} "
        f"contrib_shape={np.asarray(contrib).shape} first-stage p95={p95:.2f}ms (p={p.max():.2f})"
    )


def optuna_mlflow_check(tmp: Path) -> str:
    import mlflow
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=7))
    study.optimize(lambda t: -((t.suggest_float("c", 0.01, 10, log=True) - 2.0) ** 2), n_trials=15)
    mlflow.set_tracking_uri(f"sqlite:///{tmp / 'mlflow.db'}")
    mlflow.set_experiment("smoke")
    with mlflow.start_run() as run:
        mlflow.log_params(study.best_params)
        mlflow.log_metric("top1", 0.91)
    got = mlflow.get_run(run.info.run_id).data.metrics["top1"]
    return f"optuna {optuna.__version__} best c={study.best_params['c']:.2f}; mlflow-skinny {mlflow.__version__} logged top1={got}"


def huey_check(tmp: Path) -> str:
    from huey import SqliteHuey

    h = SqliteHuey("smoke", filename=str(tmp / "huey.db"))

    @h.task()
    def add(a: int, b: int) -> int:
        return a + b

    res = add(2, 3)
    pending = h.pending_count()
    task = h.dequeue()
    h.execute(task)
    value = res.get()
    h.immediate = True
    return f"SqliteHuey queued={pending} result={value} immediate={add(4, 5)()}"


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        check("tantivy", lambda: tantivy_check(tmp))
        check("ml", lambda: ml_check(tmp))
        check("optuna", lambda: optuna_mlflow_check(tmp))
        check("huey", lambda: huey_check(tmp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
