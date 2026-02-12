"""The first stage's model card (docs/MODEL_CARD.md), written from its training report so the two never drift."""

from __future__ import annotations

import json
from pathlib import Path

from tariffcompass.classify.dataset import artifact_dir


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render(report: dict, labels: dict | None) -> str:
    s = report["test"]["systems"]
    sh = s["shipped"]
    split = report["split"]
    cal = report["calibration"]
    drift = report["drift"]
    lines = [
        "# Model card: the first stage (word matching)",
        "",
        "Written from `classify/artifacts/first_stage_report.json` by `manage.py train`; numbers below are measured,",
        "not claimed.",
        "",
        "## What it does",
        "",
        "Given a product description, it ranks the HTSUS headings that could hold it and passes the top five to the",
        "classifier program, with a calibrated probability for each and the words that pushed each one up. It is also",
        "the classical baseline the program must beat (the Lab calls it “word matching”). It never decides a code on",
        "its own and nothing it says is filed.",
        "",
        "## Data",
        "",
        "CBP CROSS rulings (NY and HQ letters, 2014 to August 2025) from a public mirror, cleaned as described in",
        "`docs/DATA.md`: labels are re-derived from each letter's own holding, and a ruling becomes a labelled example",
        "only when its holding agrees with the stated tariff number at the heading, all its holdings share one",
        "six-digit subheading and its ruling number can be trusted.",
    ]
    if labels:
        lines += [
            "",
            f"- Letters read: {labels['read']:,}; with a classification holding: {labels['with_holding']:,}.",
            f"- Holding agrees with the stated number at the heading: {labels['holding_agrees_heading']:,}; "
            f"disagrees (dropped as labels and never cited): {labels['disagree_heading']:,}.",
            f"- Holdings across several subheadings (dropped as labels): {labels['multi_subheading']:,}.",
            f"- Labelled examples: **{labels['labelled']:,}**.",
        ]
    lines += [
        "",
        "The model's input is the product as the letter describes it before any legal analysis (the subject line and",
        "the facts, cut at the first sentence that names a heading, a tariff number, the HTSUS or a rule, with all",
        "tariff numbers removed), so the holding never leaks into the features.",
        "",
        "## Splits (by date, no leakage across time)",
        "",
        f"- {split['rule']}.",
        f"- Train {split['counts']['train']:,} · validation {split['counts']['val']:,} · test "
        f"{split['counts']['test']:,} (test window {split['testWindow'][0]} to {split['testWindow'][1]}).",
        f"- The test set was frozen (ids and SHA-256 `{split['hashes']['test'][:16]}…` in `splits.json`) before any",
        "  tuning. Tuning, model choice, pruning and calibration read only the validation set.",
        f"- Headings with fewer than two training rulings are not classes ({report['classes']} classes); "
        f"{report['testHeadingsUnseen']} test rulings fall in headings the model has never seen and count as misses.",
        "",
        "## Models compared (test set, measured once at the end)",
        "",
        "| Model | Heading top-1 | top-3 | top-5 | Chapter top-1 | top-3 |",
        "|---|---|---|---|---|---|",
    ]
    for key, name in (
        ("shipped", f"Shipped: {report['pruning']['model'].replace('_', ' ')}, pruned + calibrated"),
        ("logistic_regression", "Logistic regression (TF-IDF), unpruned"),
        ("linear_svm", "Linear SVM (TF-IDF), unpruned"),
    ):
        r = s[key]
        lines.append(
            f"| {name} | {pct(r['heading']['top1'])} | {pct(r['heading']['top3'])} | {pct(r['heading']['top5'])} | "
            f"{pct(r['chapter']['top1'])} | {pct(r['chapter']['top3'])} |"
        )
    lg = s["lightgbm_chapter"]["chapter"]
    lines += [
        f"| LightGBM on SVD(160) of the TF-IDF + text facts (chapters only) | – | – | – | {pct(lg['top1'])} | "
        f"{pct(lg['top3'])} |",
        "",
        f"Champion rule: {report['champion']['rule']}. Validation scores: "
        + "; ".join(f"{k.replace('_', ' ')} top-5 {pct(v['top5'])}" for k, v in report["validation"].items())
        + ".",
        f"Optuna studies (seeded TPE): logistic regression C = {report['studies']['logistic_regression']['best']}, "
        f"linear SVM C = {report['studies']['linear_svm']['best']}, "
        f"LightGBM {report['studies']['lightgbm_chapter']['best']}.",
        f"Pruning keeps each heading's {report['pruning']['chosen']} strongest weights (the smallest level within "
        "half a",
        "point of the unpruned model on validation, or the largest level tried); weights are stored as float16.",
        "",
        "## Calibration",
        "",
        f"{cal['method']}. Temperature {cal['temperature']}. Expected calibration error on validation "
        f"{cal['eceValBefore']} before → {cal['eceValAfter']} after; on the test set {sh['ece']}.",
        "",
        "| Confidence band (test) | Rulings | Mean confidence | Accuracy |",
        "|---|---|---|---|",
    ]
    for row in report["test"]["reliability"]:
        lines.append(
            f"| {row['from']:.2f}–{row['to']:.2f} | {row['n']} | {row['confidence']:.3f} | {row['accuracy']:.3f} |"
        )
    conf = report["test"]["confusionByChapter"]
    lines += [
        "",
        "## Where it goes wrong (test, by chapter of the predicted heading)",
        "",
        "Most frequent confusions (gold chapter → predicted chapter): "
        + ", ".join(f"{c['gold']}→{c['predicted']} ({c['n']})" for c in conf["topConfusions"][:8])
        + ".",
        "",
        "## Drift",
        "",
        f"- Chapter-mix PSI, training vs the newest rulings: {drift['trainVsTest']['psi']} "
        f"({drift['trainVsTest']['reading']}); training vs validation {drift['trainVsValidation']['psi']}.",
        "- Chapters that moved most: "
        + ", ".join(
            f"{m['chapter']} ({m['train']:.3f} → {m['new']:.3f})" for m in drift["trainVsTest"]["mostMoved"][:4]
        )
        + ".",
        "- By month as new rulings arrive: "
        + ", ".join(f"{m['month']} {m['psi']} (n={m['n']})" for m in drift["byMonth"])
        + ". A month with few rulings swings widely; the monthly series is a watch signal, not a verdict.",
        "",
        "## Serving",
        "",
        f"- p95 {report['latencyMs']['p95']} ms per description on this laptop (gate: < 150 ms); artefacts "
        f"{sum(report['artifactBytes'].values()) / 1e6:.1f} MB (JSON vocabulary, sparse float16 weights, no pickles).",
        "- Tracked in MLflow (local SQLite store, `mlruns/`, git-ignored); registered as `tariff-compass-first-stage`.",
        "",
        "## Champion and challenger",
        "",
        "Word matching (this model, with the closest retrieved ruling's line under its top heading and a calibrated",
        "confidence word) is what answers in the product. The DSPy program is a challenger: it can only answer after a",
        "training round passes all five checks against word matching and two people sign it live. With the offline",
        "simulator no round passes (see `eval/RESULTS.md`); a run with a real LM is the honest test of the program.",
        "",
        "The simulator's noise model, and why: each score the simulated LM compares gets a deterministic offset of up",
        "to ±0.03 to ±0.05 from a hash of the product and the option, so close calls between two headings or lines can",
        "go either way, as an LM's do, while clear calls never flip; and without an instruction against it, a",
        "top-listed ruling under a neighbouring heading is cited as support in 30 of 100 answers, the commonest",
        "citation slip a hurried reader makes. Nothing in the noise reads a gold label. Details in ADR 0003.",
        "",
        "## How the test set was used",
        "",
        "Once, for the final measurement above. An earlier end-to-end run of the training command (a pipeline check",
        "with one trial per study) also printed test figures; nothing was chosen from them. The champion rule (top-5",
        "on validation) and every threshold were fixed in code beforehand, and the gates in `eval/gates.toml` predate",
        "both runs. After training, the input normalisation gained a Canadian/British-to-US spelling map",
        "(“aluminium” → “aluminum”); CBP's letters use US spelling, so the measured figures are unaffected. The",
        "program's training rounds and the evaluation read the test set again while the pipeline was being fixed;",
        "the last of those readings, after the final fixes, is the one reported in `eval/RESULTS.md` and was the",
        "final look.",
        "",
        "## Limits",
        "",
        "- It reads words, not products: an article described with a heading's own words is easy; one described only",
        "  by brand or function is not. The program, the rulings and a broker sit between it and any code.",
        "- Coverage follows CBP's caseload: headings with few rulings are weak or absent (9617 has four letters since",
        "  2014), and the newest rulings lean towards chapters the training years saw less.",
        "- No people are scored, so there is no fairness analysis; nothing personal is a feature.",
        "",
    ]
    return "\n".join(lines)


def write(repo_dir: Path) -> Path:
    report = json.loads((artifact_dir() / "first_stage_report.json").read_text())
    lp = artifact_dir() / "labels_report.json"
    labels = json.loads(lp.read_text()) if lp.exists() else None
    out = repo_dir / "docs" / "MODEL_CARD.md"
    out.write_text(render(report, labels) + "\n")
    return out
