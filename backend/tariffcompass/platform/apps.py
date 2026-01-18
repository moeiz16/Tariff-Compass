from __future__ import annotations

from django.apps import AppConfig


class PlatformConfig(AppConfig):
    name = "tariffcompass.platform"
    label = "platform"
    verbose_name = "Platform"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # One switch for "now" across the API, the worker and management commands (tariffcompass/clock.py).
        # Not while generating migrations: Django's own `default=timezone.now` fields would look changed.
        import sys

        if "makemigrations" in sys.argv:
            return
        from django.conf import settings

        from tariffcompass import clock

        cfg = settings.TARIFF_COMPASS
        clock.install(cfg["DEMO_TODAY"], cfg["DEMO_TIME"] or None, anchor_file=cfg["CLOCK_ANCHOR"])
