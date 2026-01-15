from __future__ import annotations

from django.apps import AppConfig


class DutiesConfig(AppConfig):
    name = "tariffcompass.duties"
    label = "duties"
    verbose_name = "Landed cost"
    default_auto_field = "django.db.models.BigAutoField"
