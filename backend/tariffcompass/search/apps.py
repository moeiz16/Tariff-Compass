from __future__ import annotations

from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "tariffcompass.search"
    label = "search"
    verbose_name = "Search engine"
    default_auto_field = "django.db.models.BigAutoField"
