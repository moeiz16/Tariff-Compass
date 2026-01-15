"""Tariff change watch (API_CONTRACT §1.11)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from tariffcompass.api.schemas.common import Money
from tariffcompass.core.wire import Wire

ChangeKind = Literal[
    "legal_pending", "duty_layer", "ruling_modified", "ruling_revoked", "new_rulings", "schedule_revision"
]


class AffectedOut(Wire):
    product_id: str
    sku: str
    title: str
    effect: str  # "Duty would fall from $4,361.25 to $1,881.25 if those duties end"
    recheck: Literal["unchanged", "needs_review", "re_approved"]
    recheck_label: str
    duty_before: Money | None = None
    duty_after: Money | None = None


class WatchItemOut(Wire):
    id: str
    date: date | None  # None while pending
    date_label: str  # "PENDING" | "16 FEB 2026"
    date_note: str | None  # "argued 5 Nov 2025"
    kind: ChangeKind
    kind_label: str
    headline: str
    body: str
    knows: list[str]  # What we know
    unknowns: list[str]  # What we don't
    affected_count: int  # "64 of your products"
    affected: list[AffectedOut]  # top 5; GET /watch/{id} returns all
    source_label: str
    source_url: str


class WatchOut(Wire):
    items: list[WatchItemOut]
    last_checked_at: datetime
    checks: list[str]  # what Watch checks every morning
    quiet_message: str


class HomeChange(Wire):
    id: str
    headline: str
    affected_count: int
    consequence: str


class RecentAnswer(Wire):
    id: str
    query_text: str
    us_code: str | None
    verdict: Literal["strong", "broker"]
    verdict_label: str
    created_at: datetime
    created_by: str


class HomeOut(Wire):
    date_line: str  # "Thursday 19 February 2026 · tariffs current as of this morning, 06:00 PT"
    recent: list[RecentAnswer]
    changes: list[HomeChange]
