from __future__ import annotations

from django.apps import AppConfig


class SeedConfig(AppConfig):
    name = "tariffcompass.seed"
    label = "seed"
    verbose_name = "Demo data"
    default_auto_field = "django.db.models.BigAutoField"
