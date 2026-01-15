"""manage.py train (classification workstream; see the Makefile)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Train the classical first stage (logged to MLflow)"

    def handle(self, *args, **options) -> None:
        raise CommandError("not implemented yet")
