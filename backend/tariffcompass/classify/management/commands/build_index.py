"""manage.py build_index (classification workstream; see the Makefile)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Build the Tantivy indexes over rulings and tariff text"

    def handle(self, *args, **options) -> None:
        raise CommandError("not implemented yet")
