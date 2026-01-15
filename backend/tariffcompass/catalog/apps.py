from __future__ import annotations

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = "tariffcompass.catalog"
    label = "catalog"
    verbose_name = "Products and binders"
    default_auto_field = "django.db.models.BigAutoField"
