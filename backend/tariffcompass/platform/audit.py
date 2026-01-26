"""The activity record: an append-only SHA-256 hash chain per organisation.

Each event's hash covers the previous event's hash and the event's own canonical content, so editing or
deleting any past entry breaks every hash after it. `verify(org)` re-computes the chain; the binder export
and Settings › Activity show the result ("Chain verified 19 Feb, 10:30") and an event's short fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from django.db import transaction

from tariffcompass import clock
from tariffcompass.platform.models import AuditEvent, Organisation, User

GENESIS = "0" * 64


def _canonical(event: AuditEvent) -> str:
    payload = {
        "org": str(event.org_id) if event.org_id else None,
        "actor": str(event.actor_id) if event.actor_id else None,
        "actorName": event.actor_name,
        "action": event.action,
        "targetType": event.target_type,
        "targetId": event.target_id,
        "summary": event.summary,
        "details": event.details,
        "createdAt": event.created_at.isoformat(timespec="microseconds"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(prev_hash: str, event: AuditEvent) -> str:
    return hashlib.sha256((prev_hash + _canonical(event)).encode()).hexdigest()


def fingerprint(hash_: str) -> str:
    """The short form shown in the UI and printed in binders (first 12 hex characters, grouped)."""
    return f"{hash_[:4]}·{hash_[4:8]}·{hash_[8:12]}"


def record(
    org: Organisation | None,
    action: str,
    summary: str,
    *,
    actor: User | None = None,
    actor_role: str = "",
    target_type: str = "",
    target_id: str = "",
    details: dict[str, Any] | None = None,
    ip: str = "",
    at: datetime | None = None,
) -> AuditEvent:
    """Append one event to the organisation's chain (atomic; SQLite runs it as BEGIN IMMEDIATE).

    `at` back-dates the event (the sample seed replays its history in order); it defaults to the demo clock.
    """
    with transaction.atomic():
        last = AuditEvent.objects.filter(org=org).order_by("-id").only("hash").first()
        event = AuditEvent(
            org=org,
            actor=actor,
            actor_name=actor.full_name if actor else "Tariff Compass",
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            summary=summary,
            details=details or {},
            ip=ip,
            prev_hash=last.hash if last else GENESIS,
            created_at=(at or clock.now()).astimezone(UTC),  # hashed as stored: UTC
        )
        event.hash = compute_hash(event.prev_hash, event)
        event.save(force_insert=True)
    return event


@dataclass(frozen=True)
class ChainCheck:
    ok: bool
    events: int
    broken_at: int | None  # id of the first event whose hash doesn't match
    checked_at: str


def verify(org: Organisation | None) -> ChainCheck:
    prev = GENESIS
    count = 0
    for event in AuditEvent.objects.filter(org=org).order_by("id").iterator():
        count += 1
        if event.prev_hash != prev or compute_hash(prev, event) != event.hash:
            return ChainCheck(False, count, event.id, clock.now_iso())
        prev = event.hash
    return ChainCheck(True, count, None, clock.now_iso())
