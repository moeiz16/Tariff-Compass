"""Review tables: the broker's docket, decisions, questions to the importer, training examples and
always-review rules. A correction is a Decision plus a TrainingExample in the format the optimiser reads
(`review.lessons.example_payload`)."""

from __future__ import annotations

import uuid

from django.db import models

from tariffcompass import clock
from tariffcompass.catalog.models import Answer, Product
from tariffcompass.platform.models import Organisation, User

KINDS = [
    ("unsure", "Classifier unsure"),
    ("differs", "Differs from last code"),
    ("ruling_changed", "Ruling changed"),
    ("always_review", "Always reviewed"),
    ("requested", "Sent for review"),
]
STATUSES = [
    ("waiting", "Waiting"),
    ("asked", "Question asked"),
    ("answered", "Question answered"),
    ("approved", "Approved"),
    ("corrected", "Corrected"),
    ("withdrawn", "Withdrawn"),
]
OPEN_STATUSES = ("waiting", "asked", "answered")
RULE_KINDS = [
    ("heading", "Heading"),
    ("chapter", "Chapter"),
    ("material", "Material"),
    ("value_over", "Entry value over"),
    ("origin", "Made in"),
    ("keyword", "Words in the description"),
]


class AlwaysReviewRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=16, choices=RULE_KINDS)
    value = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.label


class ReviewItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    answer = models.ForeignKey(Answer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    kind = models.CharField(max_length=16, choices=KINDS)
    detail = models.CharField(max_length=300)
    into = models.CharField(max_length=4, default="both")  # US | CA | both
    proposed_us = models.CharField(max_length=10, blank=True, default="")
    proposed_ca = models.CharField(max_length=10, blank=True, default="")
    previous_us = models.CharField(max_length=10, blank=True, default="")
    value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=12, choices=STATUSES, default="waiting")
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    rule = models.ForeignKey(AlwaysReviewRule, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    # {kind, by_id, date, text} when the binder relied on a ruling that changed
    ruling_change = models.JSONField(null=True, blank=True)
    misread = models.TextField(blank=True, default="")
    deciding_phrases = models.JSONField(default=list, blank=True)  # [{source, start, end}]
    leaning = models.BooleanField(default=False)
    note = models.TextField(blank=True, default="")  # the importer's note when sent
    version = models.PositiveIntegerField(default=1)  # bumps on every decision (409 already_decided)
    created_at = models.DateTimeField(default=clock.now)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["org", "status"])]

    def __str__(self) -> str:
        return f"Review {self.pk} ({self.kind})"


class Decision(models.Model):
    ACTIONS = [("approve", "Approved"), ("correct", "Corrected"), ("ask", "Asked"), ("answer", "Answered")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    item = models.ForeignKey(ReviewItem, on_delete=models.CASCADE, related_name="decisions")
    action = models.CharField(max_length=8, choices=ACTIONS)
    final_us = models.CharField(max_length=10, blank=True, default="")
    final_ca = models.CharField(max_length=10, blank=True, default="")
    reason_kind = models.CharField(max_length=20, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    ruling_relied = models.CharField(max_length=20, blank=True, default="")
    lesson = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    licence = models.CharField(max_length=200, blank=True, default="")
    binder_version = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.item_id}"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    item = models.ForeignKey(ReviewItem, on_delete=models.CASCADE, related_name="questions")
    asked_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    asked_at = models.DateTimeField(default=clock.now)
    text = models.TextField()
    options = models.JSONField(default=list, blank=True)
    answer = models.TextField(blank=True, default="")
    answered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["asked_at"]

    def __str__(self) -> str:
        return self.text[:40]


class TrainingExample(models.Model):
    """A labelled example for the next training round (from a broker correction or a citation flag)."""

    SIGNALS = [("correction", "Correction"), ("citation", "Ruling doesn't apply")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL, related_name="+")
    decision = models.OneToOneField(Decision, null=True, blank=True, on_delete=models.SET_NULL, related_name="example")
    signal = models.CharField(max_length=12, choices=SIGNALS, default="correction")
    payload = models.JSONField()  # the agreed dict (review.lessons.example_payload)
    lesson = models.TextField()
    used_in_round = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.lesson[:60]
