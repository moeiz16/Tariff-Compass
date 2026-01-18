"""Helpers shared by the routers: paging, money, dates in words, job acceptance."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db.models import QuerySet

from tariffcompass import clock
from tariffcompass.platform.models import Job

CENT = Decimal("0.01")


def page_params(page: int, page_size: int) -> tuple[int, int]:
    return max(1, int(page or 1)), max(1, min(100, int(page_size or 25)))


def paginate(items: QuerySet | Sequence[Any], page: int, page_size: int) -> dict[str, Any]:
    page, page_size = page_params(page, page_size)
    total = items.count() if isinstance(items, QuerySet) else len(items)
    start = (page - 1) * page_size
    return {
        "items": list(items[start : start + page_size]),
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


def money(amount: Decimal | float | int | str | None, currency: str = "USD") -> dict[str, str] | None:
    if amount is None:
        return None
    return {"amount": str(Decimal(str(amount)).quantize(CENT, ROUND_HALF_UP)), "currency": currency}


def money_words(amount: Decimal | None, currency: str = "USD") -> str:
    if amount is None:
        return ""
    sign = "C$" if currency == "CAD" else "$"
    return f"{sign}{Decimal(amount).quantize(CENT, ROUND_HALF_UP):,}"


def day_month(d: date | datetime) -> str:
    """'19 Feb' (local date for datetimes)."""
    if isinstance(d, datetime):
        d = clock.local(d)
    return f"{d.day} {d.strftime('%b')}"


def day_month_year(d: date | datetime) -> str:
    if isinstance(d, datetime):
        d = clock.local(d)
    return f"{d.day} {d.strftime('%b')} {d.year}"


def day_month_time(d: datetime) -> str:
    """'19 Feb, 10:30' in the organisation's zone."""
    loc = clock.local(d)
    return f"{loc.day} {loc.strftime('%b')}, {loc.strftime('%H:%M')}"


def ago_words(since: datetime) -> str:
    """'today' / '1 day' / '3 days' by calendar day in the local zone."""
    days = (clock.today() - clock.local(since).date()).days
    if days <= 0:
        return "today"
    return "1 day" if days == 1 else f"{days} days"


def job_accepted(job: Job) -> dict[str, str]:
    return {
        "job_id": str(job.pk),
        "status_url": f"/api/v1/jobs/{job.pk}",
        "events_url": f"/api/v1/jobs/{job.pk}/events",
    }
