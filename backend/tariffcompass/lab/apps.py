from __future__ import annotations

from django.apps import AppConfig


class LabConfig(AppConfig):
    name = "tariffcompass.lab"
    label = "lab"
    verbose_name = "Optimisation lab"
    default_auto_field = "django.db.models.BigAutoField"
