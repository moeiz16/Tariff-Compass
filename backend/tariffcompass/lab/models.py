"""Lab tables: training rounds and their sign-offs.

The classification core produces each round's `RoundReport` (contracts.Optimizer); this app stores it
(`lab.reports.dump`) and serves it. A round goes live only with two signatures from two different people
holding `lab:sign`; the previous live round is retired and stays one step away.
"""

from __future__ import annotations

import uuid

from django.db import models

from tariffcompass import clock
from tariffcompass.platform.models import Job, Organisation, User

STATUSES = [
    ("training", "Training"),
    ("waiting_signoff", "Waiting for sign-off"),
    ("live", "Live"),
    ("not_made_live", "Not made live"),
    ("retired", "Retired"),
    ("failed", "Didn't finish"),
]


class TrainingRound(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="+")
    n = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=STATUSES, default="training")
    note = models.CharField(max_length=500, blank=True, default="")
    trained_on = models.DateField(null=True, blank=True)
    lm_label = models.CharField(max_length=120, default="offline simulator")
    reflection_lm_label = models.CharField(max_length=120, default="offline simulator")
    data_snapshot = models.CharField(max_length=64, blank=True, default="")
    seed = models.PositiveIntegerField(default=7)
    report = models.JSONField(null=True, blank=True)  # lab.reports.dump(RoundReport)
    program_path = models.CharField(max_length=300, blank=True, default="")
    corrections_used = models.PositiveIntegerField(default=0)
    live_from = models.DateTimeField(null=True, blank=True)
    live_to = models.DateTimeField(null=True, blank=True)
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    started_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["org", "n"], name="uniq_round")]
        ordering = ["n"]

    def __str__(self) -> str:
        return f"Round {self.n}"


class SignOff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    round = models.ForeignKey(TrainingRound, on_delete=models.CASCADE, related_name="signoffs")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    role = models.CharField(max_length=16)
    statement = models.CharField(max_length=200)
    checks = models.JSONField(default=list)  # the five checks as they stood when signed
    signed_at = models.DateTimeField(default=clock.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["round", "user"], name="uniq_signoff")]
        ordering = ["signed_at"]

    def __str__(self) -> str:
        return f"{self.user_id} signed {self.round_id}"
