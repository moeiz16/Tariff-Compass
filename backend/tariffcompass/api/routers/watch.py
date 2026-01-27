"""Tariff change watch (API_CONTRACT §1.11), the signed-in front page and the scope counts (§1.4)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Count, Q
from django.http import HttpRequest
from ninja.responses import Status

from tariffcompass import clock, services
from tariffcompass.api import labels
from tariffcompass.api.routers.classify import summary as answer_summary
from tariffcompass.api.routers.common import job_accepted, money
from tariffcompass.api.schemas.platform import JobAccepted, ScopeCounts
from tariffcompass.api.schemas.watch import HomeOut, WatchItemOut, WatchOut
from tariffcompass.catalog.models import Answer, Product
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform.context import ctx_of, is_uuid, requires, signed_in
from tariffcompass.platform.models import Job, Organisation
from tariffcompass.review.models import OPEN_STATUSES, ReviewItem
from tariffcompass.watch.models import AffectedProduct, Change

router = WireRouter()  # /watch
home_router = WireRouter()  # /home, /scopes

CHECKS = [
    "The duty layers in force for each product's origin and code",
    "The tariff editions in force: the HTSUS revision and Canada's Customs Tariff",
    "The rulings your binders rely on: modified or revoked",
    "Pending legal decisions that could change a duty",
]


def date_label(ch: Change) -> str:
    return "PENDING" if ch.date is None else f"{ch.date.day} {ch.date.strftime('%b %Y').upper()}"


def affected_out(a: AffectedProduct) -> dict[str, Any]:
    return {
        "product_id": str(a.product_id),
        "sku": a.product.sku,
        "title": a.product.title,
        "effect": a.effect,
        "recheck": a.recheck,
        "recheck_label": labels.RECHECK.get(a.recheck, a.recheck),
        "duty_before": money(a.duty_before, a.currency),
        "duty_after": money(a.duty_after, a.currency),
    }


def item_out(ch: Change, org: Organisation, *, limit: int | None = 5) -> dict[str, Any]:
    qs = AffectedProduct.objects.filter(org=org, change=ch, product__hidden_at__isnull=True).select_related("product")
    total = qs.count()
    rows = qs.order_by("-duty_before", "product__sku")
    rows = rows[:limit] if limit else rows
    return {
        "id": ch.key,
        "date": ch.date,
        "date_label": date_label(ch),
        "date_note": ch.date_note or None,
        "kind": ch.kind,
        "kind_label": labels.CHANGE_KINDS.get(ch.kind, ch.kind),
        "headline": ch.headline,
        "body": ch.body,
        "knows": list(ch.knows or []),
        "unknowns": list(ch.unknowns or []),
        "affected_count": total,
        "affected": [affected_out(a) for a in rows],
        "source_label": ch.source_label,
        "source_url": ch.source_url,
    }


def ordered_changes() -> list[Change]:
    changes = list(Change.objects.all())
    return sorted(changes, key=lambda c: (c.date is not None, -(c.date.toordinal() if c.date else 0)))


def last_checked(org: Organisation):
    job = Job.objects.filter(org=org, kind="watch_scan", status="succeeded").order_by("-finished_at").first()
    if job and job.finished_at:
        return job.finished_at
    latest = (
        AffectedProduct.objects.filter(org=org).order_by("-checked_at").values_list("checked_at", flat=True).first()
    )
    return latest or clock.now()


@router.get("", response=WatchOut)
@requires("watch:read")
def bulletin(request: HttpRequest, q: str = "", to: str | None = None, kind: str | None = None) -> dict:
    org = ctx_of(request).need_org()
    items = ordered_changes()
    start = _day(request.GET.get("from"), "from")
    end = _day(to, "to")
    if kind:
        items = [c for c in items if c.kind == kind]
    if start:
        items = [c for c in items if c.date is None or c.date >= start]
    if end:
        items = [c for c in items if c.date is None or c.date <= end]
    if q.strip():
        term = q.strip().lower()
        items = [c for c in items if term in f"{c.headline} {c.body}".lower()]
    return {
        "items": [item_out(c, org) for c in items],
        "last_checked_at": last_checked(org),
        "checks": CHECKS,
        "quiet_message": "Nothing changed that touches your products since the last check.",
    }


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


@router.post("/scan", response={202: JobAccepted})
@requires("watch:manage")
def start_scan(request: HttpRequest):
    from tariffcompass.watch.tasks import watch_scan

    ctx = ctx_of(request)
    org = ctx.need_org()
    if Job.objects.filter(org=org, kind="watch_scan", status__in=("queued", "running")).exists():
        raise Problem(409, "conflict", "A check is already running.")
    job = Job.objects.create(
        org=org, kind="watch_scan", created_by=ctx.user, message="Re-checking every binder against the changes…"
    )
    watch_scan(str(job.pk))
    return Status(202, job_accepted(job))


@router.get("/{change_id}", response=WatchItemOut)
@requires("watch:read")
def item(request: HttpRequest, change_id: str) -> dict:
    org = ctx_of(request).need_org()
    ch = Change.objects.filter(key=change_id).first() or (
        Change.objects.filter(pk=change_id).first() if is_uuid(change_id) else None
    )
    if ch is None:
        raise Problem(404, "not_found", "We couldn't find that change.")
    return item_out(ch, org, limit=None)


# ── Home and scope counts ───────────────────────────────────────────────────────────────────────────────
def date_line() -> str:
    today = clock.today()
    return (
        f"{today.strftime('%A')} {today.day} {today.strftime('%B %Y')} · tariffs current as of this morning, 06:00 PT"
    )


def consequence(ch: Change, org: Organisation) -> str:
    top = AffectedProduct.objects.filter(org=org, change=ch).select_related("product").order_by("-duty_before").first()
    if top is None:
        return "None of your products are affected."
    return f"{top.product.sku}: {top.effect[:1].lower()}{top.effect[1:]}."


@home_router.get("/home", response=HomeOut)
@signed_in
def home(request: HttpRequest) -> dict:
    ctx = ctx_of(request)
    org = ctx.need_org()
    recent = Answer.objects.filter(org=org).select_related("created_by").order_by("-created_at")[:8]
    counts = dict(
        AffectedProduct.objects.filter(org=org, product__hidden_at__isnull=True)
        .values_list("change")
        .annotate(n=Count("id"))
        .values_list("change", "n")
    )
    changes = [c for c in ordered_changes() if counts.get(c.pk)]
    return {
        "date_line": date_line(),
        "recent": [{k: v for k, v in answer_summary(a).items() if k != "ca_code"} for a in recent],
        "changes": [
            {"id": c.key, "headline": c.headline, "affected_count": counts[c.pk], "consequence": consequence(c, org)}
            for c in changes[:4]
        ],
    }


@home_router.get("/scopes/counts", response=ScopeCounts)
@signed_in
def scope_counts(request: HttpRequest, q: str = "") -> dict:
    ctx = ctx_of(request)
    org = ctx.need_org()
    term = q.strip()
    products = Product.objects.filter(org=org, hidden_at__isnull=True)
    review = ReviewItem.objects.filter(org=org, status__in=OPEN_STATUSES)
    if term:
        products = products.filter(Q(sku__icontains=term) | Q(title__icontains=term) | Q(listing_text__icontains=term))
        review = review.filter(Q(product__sku__icontains=term) | Q(product__title__icontains=term))
    retr = services.retriever()
    browse = getattr(retr, "browse", None)
    if callable(browse):
        _, rulings = browse(term, limit=1)
    else:
        rulings = len(retr.rulings(term, k=500))
    watch = (
        Change.objects.count()
        if not term
        else sum(1 for c in Change.objects.all() if term.lower() in f"{c.headline} {c.body}".lower())
    )
    return {"rulings": rulings, "products": products.count(), "review": review.count(), "watch": watch}
