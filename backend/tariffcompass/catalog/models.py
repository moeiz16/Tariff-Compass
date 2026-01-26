"""Catalog tables: products, their evidence, classification answers, the append-only binder and entries.

Every row carries `org` (tenancy). Codes are stored as bare digits and formatted at the edge (`codes.fmt`).
A binder version is never edited: each decision appends one, linked to its audit event (the fingerprint).
"""

from __future__ import annotations

import uuid

from django.db import models

from tariffcompass import clock
from tariffcompass.platform.models import AuditEvent, Organisation, User

CATEGORIES = [
    ("outdoor", "Outdoor gear"),
    ("electronics", "Small electronics"),
    ("apparel", "Apparel"),
    ("kitchen", "Kitchenware"),
    ("bags", "Bags"),
    ("other", "Other"),
]
STANDINGS = [
    ("proposed", "Proposed"),
    ("in_review", "With the broker"),
    ("approved", "Approved"),
    ("needs_recheck", "Needs a re-check"),
    ("withdrawn", "Withdrawn"),
]
VERSION_KINDS = [
    ("proposed", "Proposed"),
    ("question_answered", "Question answered"),
    ("approved", "Approved"),
    ("corrected", "Corrected"),
    ("re_approved", "Re-approved"),
    ("withdrawn", "Withdrawn"),
]
EVIDENCE_KINDS = [
    ("spec_sheet", "Spec sheet"),
    ("photo", "Photo"),
    ("listing", "Listing"),
    ("supplier_email", "Supplier email"),
    ("other", "Other"),
]


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="products")
    sku = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=16, choices=CATEGORIES, default="other")
    made_in = models.CharField(max_length=2, default="CN")
    into = models.JSONField(default=list)  # ["US", "CA"]
    listing_text = models.TextField(blank=True, default="")
    unit_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    # typical shipment: {"value": "12500.00", "currency": "USD", "quantity": 1000, "transport": "ocean"}
    shipment = models.JSONField(default=dict, blank=True)
    us_code = models.CharField(max_length=10, blank=True, default="")
    ca_code = models.CharField(max_length=10, blank=True, default="")
    standing = models.CharField(max_length=16, choices=STANDINGS, default="proposed")
    material = models.CharField(max_length=60, blank=True, default="")  # "stainless steel", "lithium-ion cells"
    hidden_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(default=clock.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["org", "sku"], name="uniq_product_sku")]
        indexes = [models.Index(fields=["org", "category"]), models.Index(fields=["org", "standing"])]
        ordering = ["sku"]

    def __str__(self) -> str:
        return self.sku


class Evidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="evidence")
    kind = models.CharField(max_length=16, choices=EVIDENCE_KINDS, default="other")
    label = models.CharField(max_length=120, blank=True, default="")  # "Spec sheet v3", "Supplier email 14 Jan"
    file_name = models.CharField(max_length=200)
    path = models.CharField(max_length=400, blank=True, default="")  # relative to MEDIA_ROOT
    mime = models.CharField(max_length=60, blank=True, default="")
    size = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    pages = models.PositiveIntegerField(null=True, blank=True)
    extracted_text = models.TextField(blank=True, default="")
    photo_facts = models.JSONField(default=list, blank=True)
    certain = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    uploaded_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self) -> str:
        return self.file_name


class Answer(models.Model):
    """One classification answer, immutable: the full AnswerOut payload plus what produced it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="answers")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=clock.now)
    query_text = models.TextField()
    made_in = models.CharField(max_length=2, default="CN")
    us_code = models.CharField(max_length=10, blank=True, default="")
    ca_code = models.CharField(max_length=10, blank=True, default="")
    verdict = models.CharField(max_length=8)  # strong | broker
    payload = models.JSONField()  # AnswerOut (snake_case), without id/created fields
    lm_label = models.CharField(max_length=120, default="offline simulator")
    program_version = models.CharField(max_length=80, blank=True, default="")
    first_stage_version = models.CharField(max_length=80, blank=True, default="")
    search_version = models.CharField(max_length=80, blank=True, default="")
    classifier_round = models.PositiveIntegerField(null=True, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["org", "created_at"])]

    def __str__(self) -> str:
        return f"Answer {self.pk}"


class BinderVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="versions")
    n = models.PositiveIntegerField()
    kind = models.CharField(max_length=20, choices=VERSION_KINDS)
    at = models.DateTimeField(default=clock.now)
    us_code = models.CharField(max_length=10, blank=True, default="")
    ca_code = models.CharField(max_length=10, blank=True, default="")
    standing = models.CharField(max_length=16, choices=STANDINGS)
    deciding_fact = models.JSONField(null=True, blank=True)  # {key, label, value, source_note}
    evidence = models.JSONField(default=list, blank=True)  # labels
    rulings_relied = models.JSONField(default=list, blank=True)  # ruling ids ("NY N321134")
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    decided_role = models.CharField(max_length=16, blank=True, default="")
    why = models.TextField(blank=True, default="")
    answer = models.ForeignKey(Answer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    audit_event = models.ForeignKey(AuditEvent, null=True, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "n"], name="uniq_binder_version")]
        ordering = ["product", "n"]

    def __str__(self) -> str:
        return f"{self.product_id} v{self.n}"


class Entry(models.Model):
    """A customs entry that used the product's code (shown in the binder foot)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="entries")
    entry_number = models.CharField(max_length=40)
    country = models.CharField(max_length=2)
    entered_on = models.DateField()
    code = models.CharField(max_length=10)
    duty_paid = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")

    class Meta:
        ordering = ["-entered_on"]

    def __str__(self) -> str:
        return self.entry_number
