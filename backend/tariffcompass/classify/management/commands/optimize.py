"""manage.py optimize (classification workstream; see the Makefile)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run a GEPA training round and write its report"

    def handle(self, *args, **options) -> None:
        raise CommandError("not implemented yet")
