"""Platform tables: users, organisations, memberships, broker engagements, invitations, sign-in failures,
the per-organisation audit hash chain and background jobs. Shapes follow docs/API_CONTRACT.md Part 2."""

from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from tariffcompass import clock


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        if not email:
            raise ValueError("email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    # e.g. "Licensed customs broker (US), licence 34812": printed on approvals and binders
    licence = models.CharField(max_length=200, blank=True, default="")
    avatar_color = models.CharField(max_length=9, default="#3A3A36")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=clock.now)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        db_table = "platform_user"

    def __str__(self) -> str:
        return self.email


class Organisation(models.Model):
    KINDS = [("importer", "Importer"), ("broker", "Customs broker firm")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    kind = models.CharField(max_length=10, choices=KINDS, default="importer")
    locations = models.JSONField(default=list, blank=True)  # ["Vancouver, BC", "Seattle, WA"]
    timezone = models.CharField(max_length=64, default="America/Vancouver")
    settings = models.JSONField(default=dict, blank=True)  # OrgSettings overrides (API_CONTRACT §1.14)
    is_sample = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Engagement(models.Model):
    """A broker firm serves an importer: its brokers act inside the importer's organisation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broker_org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="clients")
    importer_org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="brokers")
    countries = models.JSONField(default=list)  # ["US", "CA"]: which entries the firm files
    started_on = models.DateField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["broker_org", "importer_org"], name="uniq_engagement")]

    def __str__(self) -> str:
        return f"{self.broker_org_id} serves {self.importer_org_id}"


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16)  # platform.roles.ROLES
    title = models.CharField(max_length=120, blank=True, default="")
    # set when a broker firm's person acts inside an importer's organisation
    engagement = models.ForeignKey(Engagement, null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["org", "user"], name="uniq_membership_org_user")]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.org_id} as {self.role}"


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=16)
    token_hash = models.CharField(max_length=64, unique=True)  # HMAC-SHA256 of the token; shown once
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["org", "email"])]

    def __str__(self) -> str:
        return f"Invitation {self.id} ({self.role})"


class LoginFailure(models.Model):
    """Failed sign-ins per email: 5 within 15 minutes pauses that email for 15 minutes (real wall clock)."""

    id = models.BigAutoField(primary_key=True)
    email = models.CharField(max_length=254, db_index=True)
    ip = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(db_index=True)

    def __str__(self) -> str:
        return f"Failed sign-in {self.id}"


class AuditEvent(models.Model):
    """Append-only, per-organisation SHA-256 hash chain (platform.audit). Never updated or deleted."""

    id = models.BigAutoField(primary_key=True)
    org = models.ForeignKey(Organisation, null=True, on_delete=models.PROTECT, related_name="+")
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    actor_name = models.CharField(max_length=200, default="Tariff Compass")
    actor_role = models.CharField(max_length=16, blank=True, default="")
    action = models.CharField(max_length=80, db_index=True)  # e.g. review.corrected
    target_type = models.CharField(max_length=40, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    summary = models.CharField(max_length=400)  # one plain sentence, shown in Activity
    details = models.JSONField(default=dict, blank=True)
    ip = models.CharField(max_length=64, blank=True, default="")
    prev_hash = models.CharField(max_length=64)
    hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["org", "id"]),
            models.Index(fields=["org", "target_type", "target_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.id} {self.action}"


class Job(models.Model):
    """A background job (Huey task) the web app can follow by polling or SSE (API_CONTRACT §1.16)."""

    STATUSES = [("queued", "Queued"), ("running", "Running"), ("succeeded", "Done"), ("failed", "Failed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organisation, null=True, on_delete=models.CASCADE, related_name="jobs")
    kind = models.CharField(
        max_length=40, db_index=True
    )  # classify | training_round | index_build | watch_scan | binder_export | ingest
    status = models.CharField(max_length=10, choices=STATUSES, default="queued")
    progress = models.FloatField(default=0.0)  # 0..1
    stage = models.CharField(max_length=60, blank=True, default="")
    message = models.CharField(max_length=300, blank=True, default="")  # plain words for the UI
    params = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.CharField(max_length=500, blank=True, default="")
    huey_task_id = models.CharField(max_length=64, blank=True, default="")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=clock.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["org", "kind", "status"])]

    def __str__(self) -> str:
        return f"{self.kind} {self.status}"
