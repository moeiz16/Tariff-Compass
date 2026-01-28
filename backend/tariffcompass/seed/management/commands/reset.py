"""manage.py reset: delete the local database, uploads and exports, re-anchor the demo clock, migrate and seed.

The search index (data/index) is left alone: the search engine rebuilds it when missing (`make build-index`).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from tariffcompass import clock
from tariffcompass.platform.config import tc


class Command(BaseCommand):
    help = "Delete the local database, re-anchor the demo clock, migrate and seed"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--yes", action="store_true", help="skip the confirmation")

    def handle(self, *args, **options) -> None:
        if not options["yes"]:
            raise CommandError("This deletes the local database. Re-run with --yes.")
        db = settings.DATABASES["default"]
        connections.close_all()
        if db["ENGINE"].endswith("sqlite3") and db["NAME"] != ":memory:":
            for suffix in ("", "-wal", "-shm"):
                Path(f"{db['NAME']}{suffix}").unlink(missing_ok=True)
        else:
            call_command("flush", interactive=False, verbosity=0)
        media = Path(settings.MEDIA_ROOT)
        for folder in (media, media.parent / "exports"):
            if folder.is_dir() and settings.DATA_DIR in folder.parents:
                shutil.rmtree(folder)
        cfg = tc()
        anchor = cfg.get("CLOCK_ANCHOR")
        if anchor:
            Path(anchor).unlink(missing_ok=True)
        clock.install(cfg["DEMO_TODAY"], cfg["DEMO_TIME"] or None, anchor_file=anchor)
        call_command("migrate", verbosity=0)
        call_command("seed")
