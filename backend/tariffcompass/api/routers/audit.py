"""The activity record (API_CONTRACT §1.14): the organisation's hash chain, its verification and a CSV export."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from tariffcompass import clock
from tariffcompass.api.routers.common import day_month_time, paginate
from tariffcompass.api.schemas.common import Page
from tariffcompass.api.schemas.platform import AuditRow, ChainOut
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform import actions, audit, roles
from tariffcompass.platform.context import ctx_of, requires
from tariffcompass.platform.models import AuditEvent, Organisation

router = WireRouter()


def _day(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": field, "message": "Use a date like 2026-02-19."}],
        ) from exc


def filtered(
    org: Organisation,
    *,
    action: str | None = None,
    actor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> QuerySet[AuditEvent]:
    qs = AuditEvent.objects.filter(org=org)
    if action:
        qs = qs.filter(action__startswith=action) if action.endswith(".") else qs.filter(action=action)
    if actor:
        qs = qs.filter(actor_name__icontains=actor)
    zone = clock.local(clock.now()).tzinfo
    if d := _day(date_from, "from"):
        qs = qs.filter(created_at__gte=datetime.combine(d, time.min, zone))
    if d := _day(date_to, "to"):
        qs = qs.filter(created_at__lte=datetime.combine(d, time.max, zone))
    if target_type:
        qs = qs.filter(target_type=target_type)
    if target_id:
        qs = qs.filter(target_id=target_id)
    return qs.order_by("-id")


def row(e: AuditEvent) -> dict:
    return {
        "id": e.id,
        "at": e.created_at,
        "actor_name": e.actor_name,
        "actor_role": e.actor_role,
        "actor_role_label": roles.ROLE_LABELS.get(e.actor_role, ""),
        "action": e.action,
        "action_label": actions.label(e.action),
        "summary": e.summary,
        "target_type": e.target_type,
        "target_id": e.target_id,
        "target_label": str((e.details or {}).get("label", "")) or e.target_id,
        "fingerprint": audit.fingerprint(e.hash),
    }


@router.get("", response=Page[AuditRow])
@requires("audit:read")
def list_audit(
    request: HttpRequest,
    action: str | None = None,
    actor: str | None = None,
    to: str | None = None,
    targetType: str | None = None,  # noqa: N803 - query names are camelCase on the wire
    targetId: str | None = None,  # noqa: N803
    page: int = 1,
    pageSize: int = 25,  # noqa: N803
) -> dict:
    org = ctx_of(request).need_org()
    qs = filtered(
        org,
        action=action,
        actor=actor,
        date_from=request.GET.get("from"),
        date_to=to,
        target_type=targetType,
        target_id=targetId,
    )
    out = paginate(qs, page, pageSize)
    out["items"] = [row(e) for e in out["items"]]
    return out


def chain_out(org: Organisation) -> dict:
    check = audit.verify(org)
    at = datetime.fromisoformat(check.checked_at)
    sentence = (
        f"Chain verified {day_month_time(at)}"
        if check.ok
        else f"The record was altered at entry {check.broken_at}; every entry after it is unverified."
    )
    return {
        "ok": check.ok,
        "events": check.events,
        "broken_at": check.broken_at,
        "checked_at": at,
        "sentence": sentence,
    }


@router.get("/verify", response=ChainOut)
@requires("audit:read")
def verify(request: HttpRequest) -> dict:
    return chain_out(ctx_of(request).need_org())


@router.get("/export.csv")
@requires("audit:read")
def export_csv(
    request: HttpRequest,
    action: str | None = None,
    actor: str | None = None,
    to: str | None = None,
    targetType: str | None = None,  # noqa: N803
    targetId: str | None = None,  # noqa: N803
) -> HttpResponse:
    org = ctx_of(request).need_org()
    qs = filtered(
        org,
        action=action,
        actor=actor,
        date_from=request.GET.get("from"),
        date_to=to,
        target_type=targetType,
        target_id=targetId,
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "at", "actor", "role", "action", "summary", "target_type", "target_id", "prev_hash", "hash"])
    for e in qs.order_by("id").iterator():
        w.writerow(
            [
                e.id,
                e.created_at.isoformat(),
                e.actor_name,
                roles.ROLE_LABELS.get(e.actor_role, ""),
                e.action,
                _csv_safe(e.summary),
                e.target_type,
                e.target_id,
                e.prev_hash,
                e.hash,
            ]
        )
    resp = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="activity-{org.slug}-{clock.today().isoformat()}.csv"'
    return resp


def _csv_safe(text: str) -> str:
    """Spreadsheet formula injection guard."""
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text
