"""manage.py seed: the sample organisations (docs/DATA.md "Seed plan"), dated by the demo clock.

Idempotent: if the sample organisation exists it does nothing (use `make reset` to start again).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from tariffcompass import clock
from tariffcompass.seed import build
from tariffcompass.seed.people import DEMO_PEOPLE, SAMPLE_PASSWORD


class Command(BaseCommand):
    help = "Seed Northbound Goods Co. and Driftwood Customs Brokers (idempotent, demo-clock dated)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--yes", action="store_true", help="skip the confirmation (kept for make targets)")

    def handle(self, *args, **options) -> None:
        if build.exists():
            self.stdout.write("Sample data is already loaded (make reset starts again).")
            return
        self.stdout.write(f"Seeding sample data as of {clock.today().isoformat()}…")
        result = build.build()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {result['products']} products, {result['docket']} docket items, "
                f"{result['corrections_waiting']} corrections waiting, {result['rounds']} training rounds."
            )
        )
        self.stdout.write("Watch flags: " + ", ".join(f"{k} {v}" for k, v in result["watch"].items()))
        self.stdout.write(
            "Sample sign-in (any of): "
            + ", ".join(p["email"] for p in DEMO_PEOPLE.values())
            + f" · password {SAMPLE_PASSWORD} · or use demo sign-in by role"
        )
