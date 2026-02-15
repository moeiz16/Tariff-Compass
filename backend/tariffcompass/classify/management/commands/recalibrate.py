"""manage.py recalibrate: re-fit the in-use confidence word under the declared threshold rule (validation only).

    manage.py recalibrate --seed 7 --train-n 400 --val-n 200 [--measure-test | --alternatives]

See classify/recalibrate.py. Without --measure-test nothing reads the test set.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Re-fit word matching's confidence word on validation; optionally measure it once on the test set"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--round", type=int, default=7, help="the round whose validation sample to rebuild")
        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--train-n", type=int, default=400)
        parser.add_argument("--val-n", type=int, default=200)
        parser.add_argument("--measure-test", action="store_true")
        parser.add_argument("--alternatives", action="store_true", help="choose the “Also possible” floor instead")

    def handle(self, *args, **o) -> None:
        from tariffcompass.classify import recalibrate

        kw = {"seed": o["seed"], "train_n": o["train_n"], "val_n": o["val_n"], "round_n": o["round"]}
        if o["alternatives"]:
            a = recalibrate.refit_alternatives(**kw)
            for row in a["sweep"]:
                self.stdout.write(f"floor {row['floor']}: shown {row['shown']}, right {row['right']} ({row['share']})")
            self.stdout.write(f"chosen floor {a['floor']} (target {a['target']})")
            return
        if o["measure_test"]:
            r = recalibrate.measure_test(**kw)
            self.stdout.write(f"test (one look): {r['test']}")
            return
        r = recalibrate.refit(**kw)
        self.stdout.write(f"reproduced the earlier word: threshold {r['reproduced']['threshold']}")
        self.stdout.write(f"rule: {r['ruleText']}")
        self.stdout.write(f"threshold {r['threshold']}; validation {r['validation']}")
