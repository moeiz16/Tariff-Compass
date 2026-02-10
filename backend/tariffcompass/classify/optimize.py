"""Training rounds: GEPA optimises the program's instructions on rulings + broker corrections (ADR 0003).

Reproducible by construction: a round records its seed, the metric-call budget, the LMs used, and a SHA-256 of
the examples it used. The split is the frozen one (classify/dataset.py): GEPA trains on the older part of the
validation window plus broker corrections, checks candidates on the newer part, and the round is measured once
on the test set (the newest rulings), which nothing in the round has seen. Every example's evidence is gathered
as of its own date (validation) or as of the test window's start (test), so no ruling is ever found by its own
text or by anything newer.

Three systems are measured on the same test rulings: word matching (the first stage's top heading, then the
closest older ruling's line under it), the unoptimised program and the optimised program, at chapter, heading,
six-digit and ten-digit depth.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from pathlib import Path

import dspy
import numpy as np

from tariffcompass.classify import dataset, drift
from tariffcompass.classify import evidence as ev
from tariffcompass.classify.dataset import Example
from tariffcompass.classify.program import TariffProgram, artifact_dir
from tariffcompass.contracts import DepthAccuracy, Optimizer, ProductQuery, RoundReport, RoundRequest
from tariffcompass.search.sections import chapter_title

EVIDENCE_VERSION = "ev-7"  # bump when evidence.build changes
NORTHBOUND_CHAPTERS = ("39", "42", "61", "62", "63", "66", "73", "76", "82", "85", "94", "95", "96")
DEPTHS = ("chapter", "heading", "subheading", "full_code")
Progress = Callable[[float, str, str], None]


# ── examples with evidence ──────────────────────────────────────────────────────────────────────────────
class EvidenceCache:
    """Evidence per (example, cutoff, search version, first-stage version), kept in data/cache between rounds."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.rows: dict[str, str] = {}
        if path is not None and path.exists():
            for line in path.open(encoding="utf-8"):
                k, _, v = line.partition("\t")
                self.rows[k] = v.rstrip("\n")

    def get(self, key: str, make: Callable[[], str]) -> str:
        if key not in self.rows:
            self.rows[key] = make()
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(f"{key}\t{self.rows[key]}\n")
        return self.rows[key]


_NO_CACHE = EvidenceCache(None)


def to_dspy(e: Example, first_stage, retriever, before: date, cache: EvidenceCache = _NO_CACHE) -> dspy.Example:
    q = ProductQuery(e.text, made_in=e.made_in)
    key = (
        f"{e.id}|{before}|{getattr(retriever, 'version', '')}|{getattr(first_stage, 'version', '')}|{EVIDENCE_VERSION}"
    )
    evidence = cache.get(key, lambda: json.dumps(ev.build(q, first_stage.predict(q, k=5), retriever, before=before)))
    return dspy.Example(
        product=ev.product_text(q),
        evidence=evidence,
        id=e.id,
        issued=e.issued.isoformat(),
        gold_heading=e.heading,
        gold_six=e.six,
        gold_tens=list(e.tens),
        lesson=e.lesson,
        source=e.source,
    ).with_inputs("product", "evidence")


_UNINFORMATIVE_WORDS = (
    "made item items article articles percent over under about with each also into used using size sizes model "
    "number style color colour inch inches feet cm mm product products piece pieces set sets approximately "
    "measures measuring consist consists composed comprised designed intended feature features include includes "
    "including other type types like such available sold imported"
)
UNINFORMATIVE = frozenset(_UNINFORMATIVE_WORDS.split())


class WordTable:
    """Which words point to which heading, from training rulings only (used to write GEPA's feedback)."""

    def __init__(self, examples: list[Example]) -> None:
        self.by_heading: dict[str, Counter] = defaultdict(Counter)
        for e in examples:
            self.by_heading[e.heading].update(ev.stems(e.text))

    def pointing(self, text: str, gold: str, chose: str, n: int = 2) -> list[str]:
        g, c = self.by_heading.get(gold, Counter()), self.by_heading.get(chose, Counter())
        gt, ct = sum(g.values()) or 1, sum(c.values()) or 1
        scored = []
        for w in ev.stems(text):
            if g[w] < 3 or w in UNINFORMATIVE or w.isdigit() or len(w) < 4:
                continue
            s = math.log((g[w] + 1) / gt) - math.log((c[w] + 1) / ct)
            if s > 1.0:
                scored.append((s, w))
        return [w for _, w in sorted(scored, reverse=True)[:n]]


def depth_hits(
    pred_code: str, pred_heading: str, gold_heading: str, gold_six: str, gold_tens: list[str]
) -> dict[str, bool | None]:
    return {
        "chapter": pred_heading[:2] == gold_heading[:2],
        "heading": pred_heading == gold_heading,
        "subheading": pred_code[:6] == gold_six,
        "full_code": (pred_code in gold_tens) if gold_tens else None,
    }


def make_metric(words: WordTable):
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        h = depth_hits(pred.us_code, pred.heading, gold.gold_heading, gold.gold_six, list(gold.gold_tens))
        e = json.loads(gold.evidence)
        support_rows = [r for r in pred.cited if r["id"] in set(pred.support_ids)]
        bad_cites = [r for r in support_rows if r["heading"] != pred.heading]
        six_right = bool(h["subheading"])
        calibrated = (pred.verdict == "strong") == six_right  # "Strong match" when right, "Needs a broker" when not
        score = 0.1 * bool(h["chapter"]) + 0.4 * bool(h["heading"]) + 0.2 * six_right + 0.15 * bool(h["full_code"])
        score += 0.05 * (1.0 if not bad_cites else 0.0) + 0.1 * calibrated
        votes = e.get("votes", {})
        fb: list[str] = []
        runner = ev.runner_up(pred.heading, pred.set_aside)
        agree_line = ev.render_agreement(e, pred.heading, pred.cited, pred.sentences, runner, gold.product)
        a = dict(p.split("=", 1) for p in [x.strip() for x in agree_line.split("|")] if "=" in p)
        if not h["heading"]:
            pw = ",".join(w.replace(" ", "_") for w in words.pointing(gold.product, gold.gold_heading, pred.heading))
            in_cands = gold.gold_heading in [c["heading"] for c in e["candidates"]]
            fb.append(
                f"Wrong heading: chose {pred.heading}, expected {gold.gold_heading}"
                + (f"; words that point to {gold.gold_heading}: {pw.replace(',', ', ')}" if pw else "")
                + ("" if in_cands else "; the expected heading was not among the candidates")
                + f". FB[heading] chose={pred.heading} expected={gold.gold_heading} words={pw or 'none'} "
                f"precedent_expected={votes.get(gold.gold_heading, 0.0)} precedent_chose={votes.get(pred.heading, 0.0)}"
            )
            if pred_name == "candidates" and in_cands and pred.order.index(gold.gold_heading) > 0:
                fb.append(
                    f"The expected heading was ranked {pred.order.index(gold.gold_heading) + 1}. FB[candidates] "
                    f"expected={gold.gold_heading} precedent_expected={votes.get(gold.gold_heading, 0.0)}"
                )
        elif not six_right or h["full_code"] is False:
            exp = (list(gold.gold_tens) or [gold.gold_six])[0]
            near = next((r for r in e["rulings"].get(pred.heading, []) if r["status"] != "revoked"), None)
            held = (near["code"] if near and len(near["code"]) == 10 else "") if near else ""
            line_text = e["us_text"].get(exp, "")
            pw = ",".join(w for w in ev.stems(gold.product) & ev.stems(line_text))[:40]
            fb.append(
                f"Right heading, wrong line: chose {pred.us_code}, expected {exp} (“{line_text[:80]}”). "
                f"FB[line] chose={pred.us_code} expected={exp} precedent_held={held or 'none'} "
                f"precedent_sim={near.get('sim', 0) if near else 0} words={pw or 'none'}"
            )
        else:
            fb.append("Right heading and line.")
        if bad_cites:
            fb.append(
                f"Cited {', '.join(r['id'] for r in bad_cites)} (heading {bad_cites[0]['heading']}) as support for a "
                f"{pred.heading} answer. FB[cite] wrong_support={len(bad_cites)}"
            )
        fb.append(
            f"Said {pred.verdict}; the six-digit code was {'right' if six_right else 'wrong'}. FB[confidence] "
            f"margin={a.get('margin', '0')} agreeing={a.get('agreeing', '0')} precedent={a.get('precedent', '0')} "
            f"right={'yes' if six_right else 'no'}"
        )
        if gold.lesson:
            fb.append(f"Broker's lesson: {gold.lesson}")
        if pred_name == "confidence":
            fb = [f for f in fb if "FB[confidence]" in f or f.startswith("Broker")]
            return dspy.Prediction(score=1.0 if calibrated else 0.0, feedback="\n".join(fb))
        if pred_name == "cite":
            fb = [f for f in fb if "FB[cite]" in f] or ["Every cited ruling shares the answer's heading."]
        if pred_name == "subheading":
            fb = [f for f in fb if "FB[line]" in f or "Right heading and line" in f or "Wrong heading" in f]
        return dspy.Prediction(score=score, feedback="\n".join(fb))

    return metric


# ── measuring ───────────────────────────────────────────────────────────────────────────────────────────
def _row(ex: dspy.Example, pred, ms: float) -> dict:
    from tariffcompass.classify.confidence import features

    e = json.loads(ex.evidence)
    support = [r for r in pred.cited if r["id"] in set(pred.support_ids)]
    return {
        "id": ex.id,
        "heading": pred.heading,
        "code": pred.us_code,
        "verdict": pred.verdict,
        "support": [(r["id"], r["heading"], r["status"]) for r in support],
        "x": features(e, pred.heading, pred.us_code, pred.cited, pred.support_ids, ex.product),
        "ms": ms,
    }


def run_program(program: TariffProgram, examples: list[dspy.Example], lm) -> list[dict]:
    out = []
    with dspy.context(lm=lm, adapter=dspy.ChatAdapter()):
        for ex in examples:
            t0 = time.perf_counter()
            pred = program(product=ex.product, evidence=ex.evidence)
            out.append(_row(ex, pred, (time.perf_counter() - t0) * 1000))
    return out


def word_matching(examples: list[dspy.Example], first_stage=None, train=None) -> list[dict]:
    """The classical baseline, exactly as it answers when no round is live: the first stage's top heading, the
    closest retrieved ruling's line under it (else a GRI 6 walk down its lines), no LM."""
    from tariffcompass.classify.program import word_matching_prediction

    out = []
    for ex in examples:
        t0 = time.perf_counter()
        pred = word_matching_prediction(json.loads(ex.evidence), ex.product)
        out.append(_row(ex, pred, (time.perf_counter() - t0) * 1000))
    return out


def right_six(preds: list[dict], examples: list[dspy.Example]) -> list[bool]:
    gold = {ex.id: ex for ex in examples}
    return [p["code"][:6] == gold[p["id"]].gold_six for p in preds]


def apply_calibrator(preds: list[dict], cal) -> list[dict]:
    return [{**p, "verdict": cal.verdict(p["x"])} for p in preds]


def score(preds: list[dict], examples: list[dspy.Example]) -> dict:
    gold = {ex.id: ex for ex in examples}
    tot: dict[str, list[bool]] = {d: [] for d in DEPTHS}
    per_ch: dict[str, list[bool]] = defaultdict(list)
    strong_said = strong_right = broker_said = broker_wrong = 0
    sup = sup_ok = revoked_support = 0
    for p in preds:
        g = gold[p["id"]]
        h = depth_hits(p["code"], p["heading"], g.gold_heading, g.gold_six, list(g.gold_tens))
        for d in DEPTHS:
            if h[d] is not None:
                tot[d].append(bool(h[d]))
        per_ch[g.gold_heading[:2]].append(bool(h["heading"]))
        if p["verdict"] == "strong":
            strong_said += 1
            strong_right += bool(h["subheading"])
        elif p["verdict"] == "broker":
            broker_said += 1
            broker_wrong += not h["subheading"]
        for _, heading, status in p["support"]:
            sup += 1
            sup_ok += heading == p["heading"]
            revoked_support += status == "revoked"
    acc = {d: round(sum(v) / len(v), 4) if v else 0.0 for d, v in tot.items()}
    return {
        "accuracy": acc,
        "n": {d: len(v) for d, v in tot.items()},
        "perChapter": {c: {"n": len(v), "heading": round(sum(v) / len(v), 4)} for c, v in sorted(per_ch.items())},
        "calibration": {
            "strong": {"said": strong_said, "right": strong_right},
            "broker": {"said": broker_said, "firstGuessWrong": broker_wrong},
        },
        "citations": {
            "support": sup,
            "sameHeading": sup_ok,
            "precision": round(sup_ok / sup, 4) if sup else 1.0,
            "revokedAsSupport": revoked_support,
        },
        "latencyMs": {"p95": round(float(np.percentile([p["ms"] for p in preds], 95)), 2) if preds else 0.0},
    }


def sha(examples: list[dspy.Example]) -> str:
    h = hashlib.sha256()
    for ex in sorted(examples, key=lambda x: x.id):
        h.update(
            f"{ex.id}\t{ex.gold_heading}\t{ex.gold_six}\t{hashlib.sha256(ex.product.encode()).hexdigest()}\n".encode()
        )
    return h.hexdigest()


# ── the round ───────────────────────────────────────────────────────────────────────────────────────────
class GepaOptimizer:
    def __init__(self, *, train_n: int = 240, val_n: int = 120, test_n: int | None = None) -> None:
        self.train_n, self.val_n, self.test_n = train_n, val_n, test_n

    def run(self, request: RoundRequest, progress: object | None = None) -> RoundReport:
        report, _ = self.run_full(request, progress)
        return report

    def run_full(self, request: RoundRequest, progress: object | None = None) -> tuple[RoundReport, dict]:
        from tariffcompass import services
        from tariffcompass.adapters import lm as lm_adapter
        from tariffcompass.search import engine

        def say(f: float, stage: str, msg: str) -> None:
            if callable(progress):
                try:
                    progress(f, stage, msg)
                except TypeError:
                    progress(f)

        t_start = time.perf_counter()
        rng = random.Random(request.seed)  # noqa: S311 (sampling examples, not security)
        say(0.02, "loading", "Reading the rulings and the frozen split…")
        rulings, _, _ = engine.load_corpus()
        splits = dataset.load_splits(rulings)
        retriever = services.retriever()
        first = services.first_stage()
        val = sorted(splits.val, key=lambda e: (e.issued, e.id))
        cut = int(len(val) * 0.6)
        pool_train, pool_val = val[:cut], val[cut:]
        if request.val_ids:
            ids = set(request.val_ids)
            pool_val = [e for e in val if e.id in ids] or pool_val
        if request.train_ids:
            ids = set(request.train_ids)
            pool_train = [e for e in val if e.id in ids] or pool_train
        tr = rng.sample(pool_train, min(self.train_n, len(pool_train)))
        va = rng.sample(pool_val, min(self.val_n, len(pool_val)))
        corrections = dataset.correction_examples(request.corrections)
        test = splits.test
        if request.test_ids:
            ids = set(request.test_ids)
            test = [e for e in test if e.id in ids] or test
        if self.test_n:
            test = sorted(test, key=lambda e: e.id)[: self.test_n]
        test_from = date.fromisoformat(splits.meta["testFrom"])
        say(0.08, "evidence", f"Gathering evidence for {len(tr) + len(va) + len(corrections)} training examples…")
        from django.conf import settings

        cache = EvidenceCache(Path(str(settings.TARIFF_COMPASS["INDEX_DIR"])).parent / "cache" / "evidence.tsv")
        d_tr = [to_dspy(e, first, retriever, e.issued, cache) for e in tr]
        d_tr += [to_dspy(e, first, retriever, test_from, cache) for e in corrections]
        d_va = [to_dspy(e, first, retriever, e.issued, cache) for e in va]
        say(0.2, "evidence", f"Gathering evidence for {len(test)} rulings it hasn't seen…")
        d_te = [to_dspy(e, first, retriever, test_from, cache) for e in test]
        words = WordTable(splits.train + tr + corrections)
        metric = make_metric(words)
        task_lm, refl_lm = lm_adapter.task_lm(), lm_adapter.reflection_lm()
        lm_label, refl_label = lm_adapter.lm_label("task"), lm_adapter.lm_label("reflection")

        say(0.3, "optimising", "Improving the classifier's instructions from rulings and broker corrections…")
        student = TariffProgram()
        t0 = time.perf_counter()
        with dspy.context(lm=task_lm, adapter=dspy.ChatAdapter()):
            gepa = dspy.GEPA(
                metric=metric,
                reflection_lm=refl_lm,
                max_metric_calls=request.budget_metric_calls,
                reflection_minibatch_size=4,
                candidate_selection_strategy="pareto",
                use_merge=False,
                num_threads=1,
                seed=request.seed,
                track_stats=False,
            )
            optimised = gepa.compile(student, trainset=d_tr, valset=d_va)
        gepa_s = time.perf_counter() - t0

        from tariffcompass.classify import confidence as conf_mod
        from tariffcompass.classify.program import calibrator_path

        say(0.7, "calibrating", "Calibrating the confidence word on validation rulings no round used…")
        used = {e.id for e in tr} | {e.id for e in va}
        held = [e for e in val if e.id not in used]
        d_held = [to_dspy(e, first, retriever, e.issued, cache) for e in held]
        held_opt = run_program(optimised, d_held, task_lm)
        held_wm = word_matching(d_held)
        cal_opt = conf_mod.fit([p["x"] for p in held_opt], right_six(held_opt, d_held))
        cal_wm = conf_mod.fit([p["x"] for p in held_wm], right_six(held_wm, d_held))

        say(0.75, "testing", f"Testing on {len(d_te)} rulings it hasn't seen…")
        wm_preds = apply_calibrator(word_matching(d_te), cal_wm)
        unopt_preds = run_program(TariffProgram(), d_te, task_lm)
        opt_raw = run_program(optimised, d_te, task_lm)
        opt_preds = apply_calibrator(opt_raw, cal_opt)
        base, unopt, opt = score(wm_preds, d_te), score(unopt_preds, d_te), score(opt_preds, d_te)
        opt_lm_verdict = score(opt_raw, d_te)["calibration"]
        live = None  # word matching is what is in use until a round passes its checks and is signed live
        conf_report = {
            "method": "Platt-scaled logistic model over the answer's evidence; threshold for 90 in 100 on validation",
            "heldOutValidation": len(d_held),
            "optimised": {
                "threshold": cal_opt.threshold,
                "validation": cal_opt.validation,
                "test": conf_mod.measure(cal_opt, [p["x"] for p in opt_raw], right_six(opt_raw, d_te)),
                "lmVerdictTest": opt_lm_verdict,
            },
            "wordMatching": {
                "threshold": cal_wm.threshold,
                "validation": cal_wm.validation,
                "test": conf_mod.measure(cal_wm, [p["x"] for p in wm_preds], right_six(wm_preds, d_te)),
            },
        }

        rounds = artifact_dir() / "rounds"
        rounds.mkdir(parents=True, exist_ok=True)
        program_file = rounds / f"round-{request.round_n}.program.json"
        optimised.save(str(program_file))
        cal_opt.save(calibrator_path(request.round_n))
        cal_wm.save(calibrator_path(None))
        instructions = {name: p.signature.instructions for name, p in optimised.named_predictors()}

        by_depth = [
            _depth("word_matching", base, len(d_te)),
            _depth("unoptimised", unopt, len(d_te)),
            _depth("optimised", opt, len(d_te)),
        ]
        if live is not None:
            by_depth.append(_depth("live", live, len(d_te)))
        before = base  # the system in use: word matching
        test_ch = Counter(e.chapter for e in test)
        by_chapter = []
        for ch, n in test_ch.most_common():
            b = before["perChapter"].get(ch, {}).get("heading", 0.0)
            a = opt["perChapter"].get(ch, {}).get("heading", 0.0)
            by_chapter.append(
                {
                    "chapter": ch,
                    "title": chapter_title(ch),
                    "tested": n,
                    "before": b,
                    "after": a,
                    "newRulings": n,
                    "moving": abs(a - b) >= 0.05,
                }
            )
        psi = drift.chapter_psi([e.chapter for e in splits.train], [e.chapter for e in test])
        drift_out = {
            "newRulings": len(test),
            "mostMoved": [m["chapter"] for m in psi["mostMoved"][:3]],
            "psi": psi["psi"],
            "sentence": (
                f"The mix of chapters in the newest rulings shows a {psi['reading']} against the "
                f"training rulings (PSI {psi['psi']:.2f})."
            ),
        }
        gates = _gates(opt, before)
        learned = tuple(c.lesson for c in corrections if c.lesson)[:3] or _learned_from(instructions)
        seconds = time.perf_counter() - t_start
        report = RoundReport(
            round_n=request.round_n,
            data_snapshot=sha(d_tr + d_va + d_te),
            test_window=(min(e.issued for e in test), max(e.issued for e in test)),
            by_depth=tuple(by_depth),
            by_chapter=tuple(by_chapter),
            calibration=opt["calibration"],
            citation_precision=opt["citations"]["precision"],
            latency_ms={"programP95": opt["latencyMs"]["p95"]},
            drift_psi=drift_out,
            learned=learned,
            gates=tuple(gates),
            program_path=str(program_file.relative_to(artifact_dir().parent.parent.parent)),
            lm_label=lm_label,
            reflection_lm_label=refl_label,
            seed=request.seed,
        )
        extra = {
            "systems": {
                "word_matching": base,
                "unoptimised": unopt,
                "optimised": opt,
                **({"live": live} if live else {}),
            },
            "confidence": conf_report,
            "instructions": instructions,
            "counts": {"train": len(d_tr), "corrections": len(corrections), "val": len(d_va), "test": len(d_te)},
            "budgetMetricCalls": request.budget_metric_calls,
            "gepaSeconds": round(gepa_s, 1),
            "seconds": round(seconds, 1),
            "snapshots": {
                "train": sha(d_tr),
                "val": sha(d_va),
                "test": sha(d_te),
                "splitTestHash": splits.meta["hashes"]["test"],
            },
            "predictions": {"optimised": [{k: p[k] for k in ("id", "heading", "code", "verdict")} for p in opt_preds]},
        }
        _write_report(report, extra)
        say(1.0, "done", "Training round finished.")
        return report, extra


def _depth(system: str, scored: dict, n: int) -> DepthAccuracy:
    a = scored["accuracy"]
    return DepthAccuracy(system, a["chapter"], a["heading"], a["subheading"], a["full_code"], n)  # type: ignore[arg-type]


def _learned_from(instructions: dict[str, str]) -> tuple[str, ...]:
    out = []
    for text in instructions.values():
        for line in text.splitlines():
            m = line.strip()
            if m.startswith("RULE: prefer"):
                parts = m.split()
                out.append(
                    f"When a description mentions {m.split('mentions ', 1)[1]}, heading {parts[2]} is "
                    f"preferred over {parts[4]}."
                )
            elif m.startswith("RULE: cite as support only"):
                out.append("Only rulings under the chosen heading are cited as support; others are cited for contrast.")
            elif m.startswith("RULE: say broker when the margin"):
                out.append(
                    f"Answers send to a broker when the first two headings are close (gap below {m.split()[-1]})."
                )
    return tuple(dict.fromkeys(out))[:3]


def _gates(opt: dict, in_use: dict) -> list[dict]:
    """The five checks before signing, against what is in use (word matching until a round is signed live)."""
    who = "word matching (in use)"
    s = opt["calibration"]["strong"]
    strong_rate = s["right"] / s["said"] if s["said"] else 0.0
    worst = 0.0
    for ch in NORTHBOUND_CHAPTERS:
        b, a = in_use["perChapter"].get(ch), opt["perChapter"].get(ch)
        if b and a:
            worst = min(worst, a["heading"] - b["heading"])
    full, head = opt["accuracy"]["full_code"], opt["accuracy"]["heading"]
    rows = [
        ("full_code_vs_live", f"Full-code accuracy at least as good as {who}", full, in_use["accuracy"]["full_code"],
         full >= in_use["accuracy"]["full_code"]),
        ("heading_vs_live", f"Heading accuracy at least as good as {who}", head, in_use["accuracy"]["heading"],
         head >= in_use["accuracy"]["heading"]),
        ("chapter_regression", "No chapter Northbound imports gets worse by more than 3 points", round(worst, 4),
         -0.03, worst >= -0.03),
        ("strong_right", "“Strong match” right at least 90 times in 100", round(strong_rate, 4), 0.90,
         s["said"] > 0 and strong_rate >= 0.90),
        ("citation_precision", "Cited rulings share the answer's heading at least 95 times in 100",
         opt["citations"]["precision"], 0.95, opt["citations"]["precision"] >= 0.95),
    ]  # fmt: skip
    return [
        {"key": k, "label": label, "passed": bool(p), "value": v, "threshold": t, "plain": label}
        for k, label, v, t, p in rows
    ]


def _write_report(report: RoundReport, extra: dict) -> Path:
    rounds = artifact_dir() / "rounds"
    path = rounds / f"round-{report.round_n}.report.json"
    try:
        from tariffcompass.lab.reports import dump  # the platform's serialiser, when present

        body = dump(report)
    except ImportError:
        body = _dump(report)
    path.write_text(json.dumps(body, indent=1) + "\n")
    (rounds / f"round-{report.round_n}.details.json").write_text(json.dumps(extra, indent=1, default=str) + "\n")
    return path


def _dump(report: RoundReport) -> dict:
    d = asdict(report)
    d["test_window"] = [report.test_window[0].isoformat(), report.test_window[1].isoformat()]
    return json.loads(json.dumps(d, default=str))


def build_optimizer() -> Optimizer:
    return GepaOptimizer()
