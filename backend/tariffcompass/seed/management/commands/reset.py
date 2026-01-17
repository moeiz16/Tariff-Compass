"""manage.py reset (Platform & API; see docs/DATA.md for the seed plan)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Delete the local database and indexes, re-anchor the demo clock, migrate and seed"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--yes", action="store_true", help="skip the confirmation")

    def handle(self, *args, **options) -> None:
        raise CommandError("not implemented yet")
