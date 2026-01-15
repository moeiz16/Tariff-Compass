from __future__ import annotations

from django.apps import AppConfig


class WatchConfig(AppConfig):
    name = "tariffcompass.watch"
    label = "watch"
    verbose_name = "Tariff change watch"
    default_auto_field = "django.db.models.BigAutoField"
