from __future__ import annotations

from django.apps import AppConfig


class ClassifyConfig(AppConfig):
    name = "tariffcompass.classify"
    label = "classify"
    verbose_name = "Classifier"
    default_auto_field = "django.db.models.BigAutoField"
