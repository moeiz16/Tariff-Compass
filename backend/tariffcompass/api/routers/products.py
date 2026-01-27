"""Products and the binder (API_CONTRACT §1.9): list, create, change, hide, evidence, binder, exports."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db.models import Q
from django.http import FileResponse, HttpRequest
from ninja import File, Form, UploadedFile
from ninja.responses import Status

from tariffcompass import clock
from tariffcompass.api.routers.common import job_accepted, paginate
from tariffcompass.api.schemas.classify import EvidenceOut
from tariffcompass.api.schemas.common import Page
from tariffcompass.api.schemas.platform import JobAccepted
from tariffcompass.api.schemas.products import (
    BinderOut,
    ExportIn,
    ProductDetail,
    ProductIn,
    ProductPatch,
    ProductSummary,
)
from tariffcompass.catalog import binder
from tariffcompass.catalog.evidence import evidence_out, from_upload
from tariffcompass.catalog.export import export_root
from tariffcompass.catalog.models import Answer, Product
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform import audit
from tariffcompass.platform.context import Ctx, ctx_of, is_uuid, requires
from tariffcompass.platform.models import Job

router = WireRouter()
exports_router = WireRouter()

SORTS = {"sku": ("sku",), "title": ("title", "sku"), "recent": ("-updated_at", "sku"), "standing": ("standing", "sku")}


def get_product(ctx: Ctx, sku_or_id: str) -> Product:
    org = ctx.need_org()
    qs = Product.objects.filter(org=org, hidden_at__isnull=True)
    p = qs.filter(sku=sku_or_id).first() or (qs.filter(pk=sku_or_id).first() if is_uuid(sku_or_id) else None)
    if p is None:
        raise Problem(404, "not_found", "We couldn't find that product.")
    return p


def _money_in(m) -> tuple[Decimal | None, str]:
    if m is None:
        return None, "USD"
    try:
        return Decimal(m.amount).quantize(Decimal("0.01")), m.currency
    except InvalidOperation as exc:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "unitValue.amount", "message": "Use a number like 12.50."}],
        ) from exc


def detail(p: Product) -> dict:
    out = binder.summary(p)
    latest = Answer.objects.filter(product=p).order_by("-created_at").values_list("id", flat=True).first()
    out.update(
        listing_text=p.listing_text,
        unit_value={"amount": f"{p.unit_value:.2f}", "currency": p.currency} if p.unit_value is not None else None,
        evidence=[evidence_out(e) for e in p.evidence.select_related("uploaded_by").all()],
        latest_answer_id=str(latest) if latest else None,
    )
    return out


@router.get("", response=Page[ProductSummary])
@requires("products:read")
def list_products(
    request: HttpRequest,
    q: str = "",
    category: str | None = None,
    madeIn: str | None = None,
    standing: str | None = None,
    sort: str = "sku",
    page: int = 1,
    pageSize: int = 25,
) -> dict:
    ctx = ctx_of(request)
    qs = Product.objects.filter(org=ctx.org, hidden_at__isnull=True)
    if q.strip():
        term = q.strip()
        digits = "".join(ch for ch in term if ch.isdigit())
        cond = Q(sku__icontains=term) | Q(title__icontains=term) | Q(listing_text__icontains=term)
        if len(digits) >= 4:
            cond |= Q(us_code__startswith=digits) | Q(ca_code__startswith=digits)
        qs = qs.filter(cond)
    if category:
        qs = qs.filter(category=category)
    if madeIn:
        qs = qs.filter(made_in=madeIn.upper())
    if standing:
        qs = qs.filter(standing=standing)
    qs = qs.order_by(*SORTS.get(sort, SORTS["sku"]))
    out = paginate(qs, page, pageSize)
    out["items"] = binder.summaries(
        Product.objects.filter(pk__in=[p.pk for p in out["items"]]).order_by(*SORTS.get(sort, SORTS["sku"]))
    )
    return out


@router.post("", response={201: ProductDetail})
@requires("products:write")
def create_product(request: HttpRequest, body: ProductIn):
    ctx = ctx_of(request)
    org = ctx.need_org()
    sku = body.sku.strip().upper()
    if Product.objects.filter(org=org, sku=sku).exists():
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "sku", "message": "A product with this SKU already exists."}],
        )
    value, currency = _money_in(body.unit_value)
    into = (org.settings or {}).get("into") or ["US", "CA"]
    p = Product.objects.create(
        org=org,
        sku=sku,
        title=body.title.strip(),
        category=body.category,
        made_in=body.made_in,
        into=into,
        listing_text=body.listing_text,
        unit_value=value,
        currency=currency,
        created_by=ctx.user,
    )
    ctx.audit(
        "product.created",
        f"{ctx.user.full_name} added {sku}, {p.title}",
        target_type="product",
        target_id=str(p.pk),
        details={"label": sku},
    )
    return Status(201, detail(p))


@router.get("/{sku}", response=ProductDetail)
@requires("products:read")
def get_one(request: HttpRequest, sku: str) -> dict:
    return detail(get_product(ctx_of(request), sku))


@router.patch("/{sku}", response=ProductDetail)
@requires("products:write")
def patch_product(request: HttpRequest, sku: str, body: ProductPatch) -> dict:
    ctx = ctx_of(request)
    p = get_product(ctx, sku)
    patch = body.model_dump(exclude_unset=True)
    changed: dict[str, list] = {}
    if "unit_value" in patch:
        value, currency = _money_in(body.unit_value)
        if value != p.unit_value:
            changed["unit_value"] = [str(p.unit_value) if p.unit_value is not None else None, str(value)]
            p.unit_value, p.currency = value, currency
        patch.pop("unit_value")
    for field, value in patch.items():
        if value is not None and getattr(p, field) != value:
            changed[field] = [getattr(p, field), value]
            setattr(p, field, value)
    if changed:
        p.updated_at = clock.now()
        p.save()
        ctx.audit(
            "product.updated",
            f"{ctx.user.full_name} changed {p.sku}",
            target_type="product",
            target_id=str(p.pk),
            details={"label": p.sku, **{k: v for k, v in changed.items() if k != "listing_text"}},
        )
    return detail(p)


@router.delete("/{sku}", response={204: None})
@requires("products:write")
def hide_product(request: HttpRequest, sku: str):
    ctx = ctx_of(request)
    p = get_product(ctx, sku)
    until, _ = binder.keep_until(p)
    p.hidden_at = clock.now()
    p.save(update_fields=["hidden_at"])
    ctx.audit(
        "product.hidden",
        f"{ctx.user.full_name} hid {p.sku}; its record is kept until {until.isoformat()}",
        target_type="product",
        target_id=str(p.pk),
        details={"label": p.sku, "keptUntil": until.isoformat()},
    )
    return Status(204, None)


@router.post("/{sku}/evidence", response={201: EvidenceOut})
@requires("products:write")
def add_evidence(request: HttpRequest, sku: str, file: File[UploadedFile], kind: Form[str] = "", label: Form[str] = ""):
    ctx = ctx_of(request)
    p = get_product(ctx, sku)
    if kind and kind not in ("spec_sheet", "photo", "listing", "supplier_email", "other"):
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "kind", "message": "Unknown kind of evidence."}],
        )
    e = from_upload(p.org, file, kind=kind or None, uploaded_by=ctx.user, product=p, label=label)
    ctx.audit(
        "evidence.added",
        f"{ctx.user.full_name} added {e.label.lower()} {e.file_name} to {p.sku}",
        target_type="product",
        target_id=str(p.pk),
        details={"label": p.sku, "sha256": e.sha256},
    )
    return Status(201, evidence_out(e))


@router.get("/{sku}/binder", response=BinderOut)
@requires("products:read")
def get_binder(request: HttpRequest, sku: str) -> dict:
    ctx = ctx_of(request)
    p = get_product(ctx, sku)
    check = audit.verify(p.org)
    return binder.binder_out(p, chain_ok=check.ok, checked_at=datetime.fromisoformat(check.checked_at))


@router.post("/{sku}/binder/export", response={202: JobAccepted})
@requires("binder:export")
def export_binder(request: HttpRequest, sku: str, body: ExportIn):
    from tariffcompass.catalog.tasks import export_binder as task

    ctx = ctx_of(request)
    p = get_product(ctx, sku)
    job = Job.objects.create(
        org=p.org,
        kind="binder_export",
        created_by=ctx.user,
        params={"product": str(p.pk), "format": body.format},
        message="Putting the binder together…",
    )
    result = task(str(job.pk))
    job.huey_task_id = getattr(result, "id", "") or ""
    job.save(update_fields=["huey_task_id"])
    return Status(202, job_accepted(job))


@exports_router.get("/{export_id}/download")
@requires("binder:export")
def download(request: HttpRequest, export_id: str) -> FileResponse:
    ctx = ctx_of(request)
    job = Job.objects.filter(pk=export_id, org=ctx.org, kind="binder_export").first() if is_uuid(export_id) else None
    if job is None or job.status != "succeeded":
        raise Problem(404, "not_found", "That export isn't ready or doesn't exist.")
    path = Path((job.params or {}).get("path", ""))
    if not path.is_file() or export_root() not in path.resolve().parents:
        raise Problem(404, "not_found", "That export is no longer on file.")
    mime = "application/pdf" if path.suffix == ".pdf" else "application/zip"
    return FileResponse(
        path.open("rb"), as_attachment=True, filename=job.result.get("fileName", path.name), content_type=mime
    )
