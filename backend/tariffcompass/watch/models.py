"""Watch tables: dated changes in the law or the data (global), and the products each one touches
(per organisation). A change with no date is pending (the Supreme Court IEEPA case)."""

from __future__ import annotations

import uuid

from django.db import models

from tariffcompass import clock
from tariffcompass.catalog.models import Product
from tariffcompass.platform.models import Organisation

KINDS = [
    ("legal_pending", "Pending decision"),
    ("duty_layer", "Duty change"),
    ("ruling_modified", "Ruling modified"),
    ("ruling_revoked", "Ruling revoked"),
    ("new_rulings", "New rulings"),
    ("schedule_revision", "Tariff revision"),
]
RECHECKS = [("unchanged", "Unchanged"), ("needs_review", "Needs review"), ("re_approved", "Re-approved")]


class Change(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=80, unique=True)  # "scotus-ieepa", "hts-2026-rev3"
    kind = models.CharField(max_length=20, choices=KINDS)
    date = models.DateField(null=True, blank=True)
    date_note = models.CharField(max_length=120, blank=True, default="")
    headline = models.CharField(max_length=300)
    body = models.TextField()
    knows = models.JSONField(default=list, blank=True)
    unknowns = models.JSONField(default=list, blank=True)
    source_label = models.CharField(max_length=200)
    source_url = models.URLField(max_length=400)
    layer_ids = models.JSONField(default=list, blank=True)  # duty layers it concerns (layers.json ids)
    ruling_id = models.CharField(max_length=20, blank=True, default="")
    headings = models.JSONField(default=list, blank=True)  # 4/6/8-digit prefixes it touches
    countries = models.JSONField(default=list, blank=True)  # US / CA
    origins = models.JSONField(default=list, blank=True)  # made-in countries it touches ([] = all)
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["-date"]

    def __str__(self) -> str:
        return self.key


class AffectedProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    change = models.ForeignKey(Change, on_delete=models.CASCADE, related_name="affected")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="+")
    effect = models.CharField(max_length=300)
    recheck = models.CharField(max_length=16, choices=RECHECKS, default="unchanged")
    duty_before = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    duty_after = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    checked_at = models.DateTimeField(default=clock.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["change", "product"], name="uniq_affected")]
        ordering = ["-duty_before"]

    def __str__(self) -> str:
        return f"{self.change_id} → {self.product_id}"
