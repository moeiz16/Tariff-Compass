"""manage.py train: the classical first stage (see tariffcompass/classify/train.py), tracked in MLflow."""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Train the classical first stage (logged to MLflow)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--lr-trials", type=int, default=5)
        parser.add_argument("--svm-trials", type=int, default=4)
        parser.add_argument("--lgbm-trials", type=int, default=6)
        parser.add_argument("--no-mlflow", action="store_true")

    def handle(self, *args, **options) -> None:
        from tariffcompass.classify import train

        report = train.run(
            trials={"lr": options["lr_trials"], "svm": options["svm_trials"], "lgbm": options["lgbm_trials"]},
            log=lambda s: self.stdout.write(s),
            mlflow_on=not options["no_mlflow"],
        )
        self.stdout.write(f"done in {report['seconds']}s → {report['version']}")
