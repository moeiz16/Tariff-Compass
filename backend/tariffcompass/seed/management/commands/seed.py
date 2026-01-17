"""manage.py seed (Platform & API; see docs/DATA.md for the seed plan)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Seed Northbound Goods Co. and Driftwood Customs Brokers (idempotent, demo-clock dated)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--yes", action="store_true", help="skip the confirmation")

    def handle(self, *args, **options) -> None:
        raise CommandError("not implemented yet")
