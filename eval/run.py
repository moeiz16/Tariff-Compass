"""Evaluation gates (docs/adr/0006, eval/gates.toml) → eval/RESULTS.md and eval/report.json.

    cd backend && .venv/bin/python ../eval/run.py [--round N] [--remeasure]

What is measured here, and from where:
- accuracy by depth (word matching, unoptimised program, optimised program), "Needs a broker" calibration and
  citation precision come from the training round's report (classify/artifacts/rounds/round-<n>.details.json),
  measured on the frozen test set (the newest rulings). `--remeasure` re-runs the three systems on the test set
  when data/ is present, and checks the numbers reproduce;
- first-stage top-k, calibration and drift come from the first stage's training report (first_stage_report.json);
- landed cost (the hand-checked set of 20), the simulated tariff revision and both latencies are measured now.
The script exits non-zero when any gate fails. Thresholds are read from gates.toml and never adjusted here.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import tomllib
from datetime import date
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tariffcompass.settings")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import django  # noqa: E402

django.setup()

from tariffcompass.classify import drift  # noqa: E402
from tariffcompass.classify.program import artifact_dir  # noqa: E402
from tariffcompass.contracts import LandedCostQuery, ProductQuery  # noqa: E402

DAY = date(2026, 2, 19)


def live_round() -> int | None:
    from tariffcompass.classify.program import live_round as signed

    return signed() or latest_round()


def latest_round() -> int | None:
    rounds = sorted(
        int(p.name.split("-")[1].split(".")[0]) for p in (artifact_dir() / "rounds").glob("round-*.details.json")
    )
    return rounds[-1] if rounds else None


def landed_cost_set(release: dict) -> dict:
    from tariffcompass.duties.engine import build_engine

    eng = build_engine()
    doc = json.loads((REPO / release["landed_cost"]["hand_checked_set"]).read_text())
    rows = []
    for p in doc["products"]:
        q = LandedCostQuery(
            p["country"],
            p["code"],
            p["madeIn"],
            Decimal(p["value"]),
            currency=p["currency"],
            transport=p["transport"],
            usmca_answers=tuple(p["answers"].items()),
            metal_content_value=Decimal(p["metalContentValue"]) if p["metalContentValue"] else None,
            as_of=DAY,
        )
        lc = eng.landed_cost(q)
        got = {ln.layer_id: str(ln.amount) for ln in lc.lines}
        ok = got == p["expected"]["lines"] and str(lc.charges_total) == p["expected"]["chargesTotal"]
        rows.append(
            {
                "id": p["id"],
                "product": p["product"],
                "expected": p["expected"]["chargesTotal"],
                "got": str(lc.charges_total),
                "exact": ok,
            }
        )
    return {"n": len(rows), "exact": sum(r["exact"] for r in rows), "rows": rows}


def revision_check() -> dict:
    from tariffcompass.search.engine import load_schedules

    us, _ = load_schedules()
    new = drift.simulate_revision(
        us, split="9617001000", renumber=("8512102000", "8512103000"), retext="8513", remove="6110202010"
    )
    changes = drift.detect_revision(us, new)
    lc = json.loads((REPO / "eval" / "sets" / "landed_cost_20.json").read_text())["products"]
    products = [(p["id"], p["code"].replace(".", "")) for p in lc if p["country"] == "US"]
    expected = {
        pid for pid, code in products if code in ("9617001000", "8512102000", "6110202010") or code.startswith("8513")
    }
    flagged = drift.affected(products, changes)
    return {
        "changes": [c.detail for c in changes],
        "products": len(products),
        "expectedAffected": sorted(expected),
        "flagged": sorted(flagged),
        "detected": set(flagged) == expected,
    }


def latencies() -> dict:
    from tariffcompass import services

    first = services.first_stage()
    retr = services.retriever()
    prog = services.program()
    texts = [
        "20 oz double-wall vacuum insulated stainless steel tumbler with sliding lid",
        "Rechargeable LED bicycle headlight, 800 lumens, USB-C, handlebar mount",
        "Men's knitted cotton pullover sweater, crew neck",
        "Lithium-ion power bank 10,000 mAh with two USB outputs",
        "Stainless steel saucepan with glass lid, 2 quart",
        "Backpack with outer surface of polyester, laptop sleeve",
        "LED camp lantern with rechargeable battery and USB output",
        "Plastic food storage containers with snap lids, set of 10",
    ]
    t0 = time.perf_counter()
    warm = ProductQuery("stainless steel vacuum bottle")
    prog.classify(warm, first.predict(warm), retr)
    cold = round((time.perf_counter() - t0) * 1000, 1)
    fs, full = [], []
    for i in range(120):
        q = ProductQuery(texts[i % len(texts)] + ("" if i < len(texts) else f" item {i}"))
        t0 = time.perf_counter()
        r = first.predict(q, k=5)
        fs.append((time.perf_counter() - t0) * 1000)
        if i < 40:
            t1 = time.perf_counter()
            prog.classify(q, r, retr)
            full.append((time.perf_counter() - t1) * 1000 + fs[-1])
    p95 = lambda xs: round(statistics.quantiles(xs, n=20)[18], 2)  # noqa: E731
    return {
        "firstStageP95": p95(fs),
        "answerP95": p95(full),
        "coldStartMs": cold,
        "firstStage": getattr(first, "version", ""),
        "program": getattr(prog, "version", ""),
        "lm": getattr(prog, "lm_label", ""),
        "retriever": getattr(retr, "version", ""),
    }


def phrasing_check() -> dict:
    """The public samples in paraphrases written before any result was seen (eval/sets/paraphrases.json),
    through the classifier in use: how many land on the expected heading."""
    from tariffcompass import services

    first, retr, prog = services.first_stage(), services.retriever(), services.program()
    doc = json.loads((HERE / "sets" / "paraphrases.json").read_text())
    rows = []
    for s in doc["samples"]:
        for text in s["texts"]:
            q = ProductQuery(text, made_in="CN")
            a = prog.classify(q, first.predict(q, k=5), retr)
            code = a.us.code if a.us else ""
            rows.append(
                {
                    "sample": s["key"],
                    "text": text,
                    "code": code,
                    "verdict": a.verdict,
                    "byDepth": dict(a.verdict_by_depth),
                    "rightHeading": code[:4] == s["expectedHeading"],
                }
            )
    by = {}
    for s in doc["samples"]:
        mine = [r for r in rows if r["sample"] == s["key"]]
        by[s["key"]] = {"right": sum(r["rightHeading"] for r in mine), "n": len(mine)}
    return {"bySample": by, "rows": rows}


def remeasure(n: int) -> dict:
    """Re-run the three systems on the frozen test set and compare with the round's report."""
    from tariffcompass import services
    from tariffcompass.adapters import lm as lm_adapter
    from tariffcompass.classify import dataset, optimize
    from tariffcompass.classify.program import TariffProgram
    from tariffcompass.search import engine

    rulings, _, sample = engine.load_corpus()
    if sample:
        return {"skipped": "data/ not present"}
    sp = dataset.load_splits(rulings)
    first, retr = services.first_stage(), services.retriever()
    test_from = date.fromisoformat(sp.meta["testFrom"])
    ex = [optimize.to_dspy(e, first, retr, test_from) for e in sp.test]
    prog = TariffProgram()
    prog.load(str(artifact_dir() / "rounds" / f"round-{n}.program.json"))
    lm = lm_adapter.task_lm()
    return {
        "word_matching": optimize.score(optimize.word_matching(ex, first, sp.train), ex)["accuracy"],
        "unoptimised": optimize.score(optimize.run_program(TariffProgram(), ex, lm), ex)["accuracy"],
        "optimised": optimize.score(optimize.run_program(prog, ex, lm), ex)["accuracy"],
    }


def gate(rows: list, key: str, label: str, value, threshold, passed: bool, kind: str = "release") -> None:
    rows.append(
        {"key": key, "label": label, "value": value, "threshold": threshold, "passed": bool(passed), "kind": kind}
    )


def in_use_confidence() -> dict | None:
    """The in-use confidence word's report: its rule, validation fit and the one test measurement under that rule."""
    from tariffcompass.classify.recalibrate import report_path

    return json.loads(report_path().read_text()) if report_path().exists() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=None, help="default: the signed-live round, else the latest")
    ap.add_argument("--remeasure", action="store_true")
    a = ap.parse_args()
    gates = tomllib.loads((HERE / "gates.toml").read_text())
    pro, rel = gates["promotion"], gates["release"]
    n = a.round or live_round()
    fs_report = json.loads((artifact_dir() / "first_stage_report.json").read_text())
    details = json.loads((artifact_dir() / "rounds" / f"round-{n}.details.json").read_text()) if n else None
    rnd = json.loads((artifact_dir() / "rounds" / f"round-{n}.report.json").read_text()) if n else None
    rows: list[dict] = []

    # ── promotion checks: may the challenger round replace what is in use? (never fail the build) ──
    systems = details["systems"] if details else {}
    acc = {k: v["accuracy"] for k, v in systems.items()}
    if acc:
        for depth in pro["optimised_beats_word_matching"]:
            gate(
                rows,
                f"beats_word_matching_{depth}",
                f"Round {n} beats word matching at {depth.replace('_', ' ')}",
                acc["optimised"][depth],
                acc["word_matching"][depth],
                acc["optimised"][depth] > acc["word_matching"][depth],
                "promotion",
            )
        for depth in pro["optimised_beats_unoptimised"]:
            gate(
                rows,
                f"beats_unoptimised_{depth}",
                f"Round {n} beats the unoptimised program at {depth.replace('_', ' ')}",
                acc["optimised"][depth],
                acc["unoptimised"][depth],
                acc["optimised"][depth] > acc["unoptimised"][depth],
                "promotion",
            )
        cal = systems["optimised"]["calibration"]
        s_rate = cal["strong"]["right"] / cal["strong"]["said"] if cal["strong"]["said"] else 0.0
        gate(
            rows,
            "challenger_strong_right",
            f"Round {n}'s “Strong match” right (six digits)",
            round(s_rate, 4),
            pro["challenger_strong_match_right_min"],
            cal["strong"]["said"] > 0 and s_rate >= pro["challenger_strong_match_right_min"],
            "promotion",
        )

    # ── release gates: what is in use (word matching until a round is signed live) ──
    shipped = fs_report["test"]["systems"]["shipped"]
    fs_g = rel["first_stage"]
    gate(
        rows,
        "first_stage_top5_heading",
        "First stage: right heading in its top 5",
        shipped["heading"]["top5"],
        fs_g["top5_heading_min"],
        shipped["heading"]["top5"] >= fs_g["top5_heading_min"],
    )
    gate(
        rows,
        "first_stage_top3_chapter",
        "First stage: right chapter in its top 3",
        shipped["chapter"]["top3"],
        fs_g["top3_chapter_min"],
        shipped["chapter"]["top3"] >= fs_g["top3_chapter_min"],
    )
    conf_g = rel["confidence"]
    iu = in_use_confidence()
    t = (iu or {}).get("test") or {}
    said = int(t.get("strongSaid", 0))
    s_prec = t.get("precision")
    gate(
        rows,
        "strong_right",
        "In use: “Strong match” right (six digits)",
        s_prec if said else f"never said (0 of {t.get('n', 0)})",
        conf_g["strong_match_right_min"],
        said >= conf_g["strong_match_said_min"] and (s_prec or 0.0) >= conf_g["strong_match_right_min"],
    )
    b_said, b_wrong = int(t.get("brokerSaid", 0)), int(t.get("brokerFirstGuessWrong", 0))
    b_rate = b_wrong / b_said if b_said else 0.0
    gate(
        rows,
        "broker_catches_wrong",
        "In use: “Needs a broker” caught a wrong first guess",
        round(b_rate, 4),
        conf_g["broker_catches_wrong_min"],
        b_rate >= conf_g["broker_catches_wrong_min"],
    )
    cit_g = rel["citations"]
    cit = systems.get("word_matching", {}).get("citations") or {"precision": 0.0, "revokedAsSupport": 0}
    gate(
        rows,
        "citation_precision",
        "In use: cited rulings share the answer's heading",
        cit["precision"],
        cit_g["precision_min"],
        cit["precision"] >= cit_g["precision_min"],
    )
    gate(
        rows,
        "revoked_as_support",
        "In use: revoked rulings cited as support",
        cit["revokedAsSupport"],
        cit_g["revoked_as_support_max"],
        cit["revokedAsSupport"] <= cit_g["revoked_as_support_max"],
    )
    lc = landed_cost_set(rel)
    gate(
        rows,
        "landed_cost",
        "Landed cost exact on the hand-checked set",
        f"{lc['exact']}/{lc['n']}",
        rel["landed_cost"]["exact_match_min"],
        lc["exact"] / lc["n"] >= rel["landed_cost"]["exact_match_min"],
    )
    rev = revision_check()
    gate(
        rows,
        "simulated_revision",
        "A simulated tariff revision flags every affected product (and only those)",
        f"{len(rev['flagged'])}/{len(rev['expectedAffected'])}",
        True,
        rev["detected"],
    )
    psi = fs_report["drift"]["trainVsTest"]
    gate(rows, "psi_reported", "Chapter-mix drift (PSI) reported", psi["psi"], "reported", psi is not None)
    lat = latencies()
    lat_g = rel["latency"]
    gate(
        rows,
        "first_stage_p95",
        "First stage p95 (ms)",
        lat["firstStageP95"],
        lat_g["first_stage_p95_ms_max"],
        lat["firstStageP95"] <= lat_g["first_stage_p95_ms_max"],
    )
    gate(
        rows,
        "answer_p95_offline",
        "Full answer p95 offline (ms)",
        lat["answerP95"],
        lat_g["answer_p95_ms_max_offline"],
        lat["answerP95"] <= lat_g["answer_p95_ms_max_offline"],
    )
    re_ = remeasure(n) if (a.remeasure and n) else None
    phr = phrasing_check()

    report = {
        "round": n,
        "lm": rnd["lm_label"] if rnd else None,
        "reflectionLm": rnd["reflection_lm_label"] if rnd else None,
        "testWindow": rnd["test_window"] if rnd else fs_report["test"]["window"],
        "testCount": details["counts"]["test"] if details else fs_report["test"]["n"],
        "accuracy": acc,
        "firstStage": {k: fs_report["test"]["systems"][k] for k in fs_report["test"]["systems"]},
        "firstStageCalibration": {
            "test_ece": shipped.get("ece"),
            **{k: fs_report["calibration"][k] for k in ("method", "temperature", "eceValBefore", "eceValAfter")},
        },
        "calibration": systems.get("optimised", {}).get("calibration") if systems else None,
        "citations": systems.get("optimised", {}).get("citations") if systems else None,
        "inUseCitations": systems.get("word_matching", {}).get("citations") if systems else None,
        "inUseConfidence": iu,
        "corpus": corpus_label(),
        "landedCost": lc,
        "drift": {"psi": fs_report["drift"]["trainVsTest"], "byMonth": fs_report["drift"]["byMonth"], "revision": rev},
        "latency": lat,
        "remeasured": re_,
        "phrasing": phr,
        "gates": rows,
        "releasePassed": all(r["passed"] for r in rows if r["kind"] == "release"),
        "promoted": all(r["passed"] for r in rows if r["kind"] == "promotion") and bool(acc),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
    (HERE / "RESULTS.md").write_text(markdown(report, fs_report, details))
    print("Release gates (what is in use; any failure fails the build):")
    for r in (r for r in rows if r["kind"] == "release"):
        print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['label']}: {r['value']} (threshold {r['threshold']})")
    print(f"Promotion checks for round {n} (a failure means the round is not promoted, not a build failure):")
    for r in (r for r in rows if r["kind"] == "promotion"):
        print(f"  {'pass' if r['passed'] else 'not met'}  {r['label']}: {r['value']} (against {r['threshold']})")
    print(f"Round {n}: {'may be signed live' if report['promoted'] else 'not promoted; word matching stays in use'}.")
    print(f"Release gates: {'all pass' if report['releasePassed'] else 'FAILED'}.")
    return 0 if report["releasePassed"] else 1


def corpus_label() -> str:
    """Which rulings the live measurements (latency, phrasing) ran over: the full corpus or the committed sample."""
    from tariffcompass.search import engine

    rulings, _, sample = engine.load_corpus()
    return f"committed sample fixtures ({len(rulings)} rulings)" if sample else f"full corpus ({len(rulings)} rulings)"


def pct(x) -> str:
    return f"{x * 100:.1f}" if isinstance(x, int | float) else str(x)


def in_use_confidence_md(r: dict) -> list[str]:
    iu = r.get("inUseConfidence")
    if not iu:
        return []
    v, t, prev = iu["validation"], iu.get("test") or {}, iu["previous"]
    best = v.get("bestLowerBound") or {}
    ci = r.get("inUseCitations") or {}
    thr = "none reaches it" if iu["threshold"] > 1 else str(iu["threshold"])
    out = [
        "## The confidence word in use (word matching)",
        "",
        f"**Rule, declared before the test set was read for it:** {iu['ruleText']}",
        "",
        "| Rule | Threshold | Validation: right when Strong | lower bound | coverage | Test: right when Strong | coverage |",
        "|---|---|---|---|---|---|---|",
        f"| earlier: point estimate ≥ 0.90 | {prev['threshold']} | {prev['validation'].get('precision')} | – | "
        f"{prev['validation'].get('coverage')} | {prev['test'].get('precision')} | {prev['test'].get('coverage')} |",
        f"| in use: 95% lower bound ≥ 0.90 | {thr} | {v.get('precision') or '–'} | {v.get('precisionLowerBound') or '–'} | "
        f"{v.get('coverage')} | {t.get('precision') or '–'} | {t.get('coverage')} |",
        "",
        f"Fitted on {iu['fittedFrom']['heldOut']} validation rulings no training round used (rebuilt from round "
        f"{iu['fittedFrom']['round']}'s seed and checked against its snapshot hash; the earlier rule reproduces the "
        "earlier threshold exactly).",
        "",
    ]
    if best:
        out.append(
            f"The best any threshold reaches on validation is a lower bound of {best['lowerBound']} "
            f"({best['right']} right of {best['said']} Strong answers), short of 0.90. So under the rule word matching "
            "never says “Strong match”: every answer it gives says “Needs a broker”, and the release gate for the "
            "word fails because a word that is never said proves nothing. That is a known limitation, not a "
            "threshold to loosen."
            if iu["threshold"] > 1
            else f"At the chosen threshold the lower bound is {v.get('precisionLowerBound')}."
        )
        out.append("")
    if t:
        out.append(
            f"On the test set (one look, after the rule was fixed): “Strong match” said {t['strongSaid']} times, "
            f"“Needs a broker” {t['brokerSaid']} times; the first guess was wrong in {t['brokerFirstGuessWrong']} of those."
        )
        out.append("")
    if ci:
        out.append(
            f"Word matching's citations: {ci['sameHeading']} of {ci['support']} supporting citations share the "
            f"answer's heading ({ci['precision']}); revoked rulings cited as support: {ci['revokedAsSupport']}."
        )
    return [*out, ""]


def markdown(r: dict, fs: dict, details: dict | None) -> str:
    lm = r["lm"] or "n/a"
    out = [
        "# Evaluation results",
        "",
        "Generated by `make eval` (`eval/run.py`) from the committed artefacts and fresh measurements. Every accuracy is",
        f"measured on the frozen test set: the {r['testCount']} newest labelled rulings ({r['testWindow'][0]} to {r['testWindow'][1]}),",
        "which no model, tuning step or optimisation round has seen (see `classify/artifacts/splits.json` for the ids and",
        "the SHA-256 of the set).",
        "",
        f"**Which LM wrote the program's answers: {lm}** (GEPA reflection: {r['reflectionLm'] or 'n/a'}). Numbers from the",
        "offline simulator measure the pipeline and the optimisation loop with a deterministic, documented stand-in for a",
        "language model (`adapters/lm_sim.py`); they are not a language model's accuracy. No free-tier key was configured",
        "when these numbers were produced, so there is no live-LM table yet." if lm == "offline simulator" else "",
        "",
        f"## Accuracy by depth (round {r['round']}, n = {r['testCount']})",
        "",
        "| System | LM | Chapter | Heading | 6 digits | 10 digits |",
        "|---|---|---|---|---|---|",
    ]
    names = {
        "word_matching": "Word matching (TF-IDF first stage + nearest ruling)",
        "unoptimised": "Program, unoptimised",
        "optimised": "Program, GEPA-optimised",
        "live": "Program, previous live round",
    }
    for k, v in r["accuracy"].items():
        out.append(
            f"| {names.get(k, k)} | {'none (classical)' if k == 'word_matching' else lm} | {pct(v['chapter'])} | {pct(v['heading'])} | {pct(v['subheading'])} | {pct(v['full_code'])} |"
        )
    if details:
        nn = details["systems"]["optimised"]["n"]
        out += [
            "",
            f"Ten-digit accuracy counts the {nn['full_code']} test rulings whose letter holds a ten-digit code; the other depths count all {nn['heading']}.",
        ]
    s = fs["test"]["systems"]
    out += [
        "",
        "**Reading this table.** With the offline simulator, the optimised program beats the unoptimised one at",
        "six and ten digits but does not beat word matching: its rule-following heading step is slightly worse than",
        "trusting the first stage's top heading, and word matching's nearest-ruling line is a strong ten-digit",
        "baseline. So the round's promotion checks are not met and it is not promoted: word matching stays in use. That",
        "is the champion/challenger rule working, not a failed build; the thresholds were not changed.",
        "",
        "**How the test set was used.** While the pipeline was being fixed the rounds were run several times and each",
        "run printed its test figures. The fixes came from the training logs, the saved instructions, the validation",
        "window and the sample catalogue (never from the test set): module-specific reflection, calibration in the round",
        "score, the first stage's probability as a prior, outright exclusion by a section note, tariff-text search by",
        "the article's words, a calibrated confidence word with its threshold chosen on validation, section and chapter",
        "notes as data, tariff lines that contradict a stated fact ruled out, and a calibrated word per depth. After the",
        "last of those fixes the test set was measured once more, for these tables. No gate or threshold was changed.",
        "After that look the in-use confidence word's threshold rule was replaced (see below); the new rule was fixed",
        "on validation and the test set was then read once more, for that word only. That is one further look, and it",
        "is counted here. A fresh test window (rulings after August 2025) is the clean check.",
        "",
        "**What is in use.** A round answers only after it passes all five checks and two people sign it live. While",
        "none qualifies, word matching (the classical first stage, calibrated) answers in the product and the program",
        "is a challenger. The program's numbers here come from the offline simulator; its honest test is a run with a",
        "real LM, for example with a free Groq or Gemini key:",
        "",
        "```bash",
        "export LLM_FAKE=false GROQ_API_KEY=…  # or GEMINI_API_KEY=… with LITELLM_MODEL=gemini/gemini-2.5-flash",
        "export LITELLM_MODEL=groq/llama-3.3-70b-versatile LITELLM_REFLECTION_MODEL=gemini/gemini-2.5-flash",
        "cd backend && .venv/bin/python manage.py optimize --round 8 --seed 8 --budget 300 --train-n 60 --val-n 40",
        "cd .. && make eval",
        "```",
        "",
        "## First stage (classical, no LM)",
        "",
        f"Shipped: {fs['champion']['shipped']}; chosen by {fs['champion']['rule']}.",
        "",
        "| Model | Heading top-1 | top-3 | top-5 | Chapter top-1 | top-3 |",
        "|---|---|---|---|---|---|",
    ]
    for k in ("shipped", "logistic_regression", "linear_svm"):
        out.append(
            f"| {k.replace('_', ' ')} | {pct(s[k]['heading']['top1'])} | {pct(s[k]['heading']['top3'])} | {pct(s[k]['heading']['top5'])} | {pct(s[k]['chapter']['top1'])} | {pct(s[k]['chapter']['top3'])} |"
        )
    lg = s["lightgbm_chapter"]["chapter"]
    out.append(f"| LightGBM (chapters only) | – | – | – | {pct(lg['top1'])} | {pct(lg['top3'])} |")
    c = r["firstStageCalibration"]
    out += [
        "",
        f"Calibration: {c['method']}; ECE on validation {c['eceValBefore']} → {c['eceValAfter']}; on the test set {c['test_ece']}.",
        "",
    ]
    out += in_use_confidence_md(r)
    out += [
        "## Confidence and citations (round " + str(r["round"]) + ", a challenger)",
        "",
    ]
    conf = (details or {}).get("confidence")
    if conf:
        out += [
            f"The confidence word is calibrated ({conf['method']}), fitted on {conf['heldOutValidation']} validation",
            "rulings that no training round used; the threshold is chosen there and only measured on the test set.",
            "The thresholds below are the ones fitted when the round ran, under the earlier point-estimate rule; the",
            "word in use now follows the lower-bound rule above, and the next round is fitted with it.",
            "",
            "| System | Threshold | Validation: right when Strong | coverage | Test: right when Strong | coverage | "
            "Wrong answers sent to a broker (test) | ECE (test) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for key, name in (("optimised", "Program, GEPA-optimised"), ("wordMatching", "Word matching")):
            c = conf[key]
            v, t = c["validation"], c["test"]
            out.append(
                f"| {name} | {c['threshold']} | {v.get('precision')} | {v.get('coverage')} | {t['precision']} | "
                f"{t['coverage']} | {t['wrongCaught']} | {t['ece']} |"
            )
        lmv = conf["optimised"]["lmVerdictTest"]["strong"]
        out += [
            "",
            f"Before calibration the program's own confidence step said “Strong match” {lmv['said']} times and was "
            f"right {lmv['right']} times on the test set.",
            "",
        ]
    if r["calibration"]:
        st, br = r["calibration"]["strong"], r["calibration"]["broker"]
        out.append(f"- “Strong match” said {st['said']} times, right at six digits {st['right']} times.")
        out.append(
            f"- “Needs a broker” said {br['said']} times; the first guess was wrong {br['firstGuessWrong']} times."
        )
    if r["citations"]:
        ci = r["citations"]
        out.append(
            f"- Citation precision: {ci['sameHeading']} of {ci['support']} supporting citations share the answer's heading ({ci['precision']}); revoked rulings cited as support: {ci['revokedAsSupport']}."
        )
    if conf and conf.get("byDepth"):
        h = conf["byDepth"]["heading"]
        out += [
            "**Confidence by depth.** A calibrated word for the heading alone was fitted the same way (Strong only where",
            "it was right at least 90 times in 100 on validation). It met the bar on validation but not on the test set,",
            "and in the phrasing check it said Strong on wrong headings, so the product keeps the single full-code word;",
            "the per-depth word is measured here and switched off (`classify.program.HEADING_WORD_IN_USE`).",
            "",
            "| System | Depth | Threshold | Validation: right when Strong | coverage | Test: right when Strong | coverage |",
            "|---|---|---|---|---|---|---|",
        ]
        for key, name in (("wordMatching", "Word matching"), ("optimised", "Program, GEPA-optimised")):
            c = h[key]
            out.append(
                f"| {name} | heading | {c['threshold']} | {c['validation'].get('precision')} | "
                f"{c['validation'].get('coverage')} | {c['test']['precision']} | {c['test']['coverage']} |"
            )
            c6 = conf[key]
            out.append(
                f"| {name} | six digits | {c6['threshold']} | {c6['validation'].get('precision')} | "
                f"{c6['validation'].get('coverage')} | {c6['test']['precision']} | {c6['test']['coverage']} |"
            )
        out.append("")
    if r.get("phrasing"):
        out += ["## Phrasing robustness (the public samples, paraphrases written before any result)", ""]
        former = {s["key"] for s in json.loads((HERE / "sets" / "paraphrases.json").read_text())["samples"]
                  if s.get("formerSample")}  # fmt: skip
        for key, v in r["phrasing"]["bySample"].items():
            note = (
                " (a former public sample, replaced because word matching gets its heading wrong)"
                if key in former
                else ""
            )
            out.append(f"- {key}: {v['right']} of {v['n']} paraphrases land on the expected heading{note}.")
        out += [
            "",
            "Known limitation: a tumbler described as “vacuum sealed” or with “vacuum insulation” (rather than",
            "“vacuum insulated” or “vacuum between the walls”) lands on 7323 with “Needs a broker”. For those",
            "phrasings the first stage passes on no 9617 candidate, so the vacuum check that would move the answer to",
            "9617 never compares the two. The answer's verdict says the stated vacuum points to heading 9617 and asks a",
            "broker to check the heading; the classifier was not tuned on these paraphrases.",
            "",
        ]
    lc = r["landedCost"]
    rev = r["drift"]["revision"]
    out += [
        "",
        "## Landed cost, drift and latency",
        "",
        f"- Landed cost: {lc['exact']} of {lc['n']} hand-checked products exact to the cent (`eval/sets/landed_cost_20.json`).",
        f"- Chapter-mix PSI, training vs the newest rulings: {r['drift']['psi']['psi']} ({r['drift']['psi']['reading']}).",
        f"- Simulated tariff revision: {len(rev['changes'])} changes; flagged {', '.join(rev['flagged'])} (expected {', '.join(rev['expectedAffected'])}).",
        f"- Live measurements (latency, phrasing) ran over the {r['corpus']}.",
        f"- First stage p95: {r['latency']['firstStageP95']} ms. Full answer p95 offline ({r['latency']['lm']}): "
        f"{r['latency']['answerP95']} ms, after a first answer that opens the indexes ({r['latency']['coldStartMs']} ms).",
        "",
        "## Release gates (`eval/gates.toml` [release]): what is in use",
        "",
        "These decide whether the build ships: `make eval` exits non-zero, and CI fails, if any of them fails.",
        "",
        "| Gate | Value | Threshold | Result |",
        "|---|---|---|---|",
    ]
    for g in (g for g in r["gates"] if g["kind"] == "release"):
        out.append(f"| {g['label']} | {g['value']} | {g['threshold']} | {'pass' if g['passed'] else '**fail**'} |")
    out += [
        "",
        f"Release gates: **{'all pass' if r['releasePassed'] else 'not all pass'}**.",
        "",
        f"## Promotion checks (`eval/gates.toml` [promotion]): may round {r['round']} replace word matching?",
        "",
        "A round answers in the product only after it meets every check here and two people sign it live in the Lab.",
        "Not meeting one means the round is not promoted; it is reported here and in the Lab, and is not a build failure.",
        "",
        "| Check | Round | Against | Result |",
        "|---|---|---|---|",
    ]
    for g in (g for g in r["gates"] if g["kind"] == "promotion"):
        out.append(f"| {g['label']} | {g['value']} | {g['threshold']} | {'met' if g['passed'] else 'not met'} |")
    out += [
        "",
        f"Round {r['round']}: **{'may be signed live' if r['promoted'] else 'not promoted; word matching stays in use'}**.",
        "",
    ]
    return "\n".join(x for x in out if x is not None) + "\n"


if __name__ == "__main__":
    sys.exit(main())
