"""manage.py optimize: one GEPA training round, its report and the optimised program JSON.

    manage.py optimize --round 7 --seed 7 --budget 900 [--corrections corrections.json]

Writes classify/artifacts/rounds/round-<n>.report.json (the RoundReport the Lab shows),
round-<n>.details.json (every system's scores, the learned instructions, snapshot hashes) and
round-<n>.program.json (the optimised program) and round-<n>.confidence.json (its calibrated confidence word).
A round answers in the product only after it passes its checks and two people sign it live in the Lab.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from tariffcompass.contracts import RoundRequest


class Command(BaseCommand):
    help = "Run a GEPA training round and write its report"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--round", type=int, default=1)
        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--budget", type=int, default=600, help="GEPA metric calls")
        parser.add_argument("--train-n", type=int, default=240)
        parser.add_argument("--val-n", type=int, default=120)
        parser.add_argument("--test-n", type=int, default=0, help="limit the test set (0 = all; smoke runs only)")
        parser.add_argument("--corrections", default="", help="JSON list of broker corrections (TrainingExample dicts)")

    def handle(self, *args, **o) -> None:
        from tariffcompass.classify.optimize import GepaOptimizer

        corrections: tuple[dict, ...] = ()
        if o["corrections"]:
            corrections = tuple(json.loads(Path(o["corrections"]).read_text()))
        from tariffcompass.adapters import lm as lm_adapter

        req = RoundRequest(
            round_n=o["round"],
            seed=o["seed"],
            train_ids=(),
            val_ids=(),
            test_ids=(),
            corrections=corrections,
            budget_metric_calls=o["budget"],
            lm_label=lm_adapter.lm_label("task"),
            reflection_lm_label=lm_adapter.lm_label("reflection"),
        )
        opt = GepaOptimizer(train_n=o["train_n"], val_n=o["val_n"], test_n=o["test_n"] or None)
        report, extra = opt.run_full(req, progress=lambda f, s, m: self.stdout.write(f"{f:4.0%} {m}"))
        for d in report.by_depth:
            self.stdout.write(
                f"{d.system:<14} chapter {d.chapter:.3f}  heading {d.heading:.3f}  six {d.subheading:.3f}  "
                f"ten {d.full_code:.3f}  (n={d.n})"
            )
        for g in report.gates:
            self.stdout.write(
                f"{'PASS' if g['passed'] else 'FAIL'}  {g['label']}: {g['value']} (threshold {g['threshold']})"
            )
        self.stdout.write(f"answers written by: {report.lm_label}; reflection: {report.reflection_lm_label}")
        c = extra["confidence"]["optimised"]
        self.stdout.write(
            f"calibrated Strong match: threshold {c['threshold']}; validation {c['validation']}; test {c['test']}"
        )
        self.stdout.write(f"done in {extra['seconds']}s")
