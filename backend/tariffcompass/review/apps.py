from __future__ import annotations

from django.apps import AppConfig


class ReviewConfig(AppConfig):
    name = "tariffcompass.review"
    label = "review"
    verbose_name = "Broker review"
    default_auto_field = "django.db.models.BigAutoField"
