"""The broker's docket: opening items, presenting them and deciding them (API_CONTRACT §1.10).

Only `review:decide` (licensed brokers) approves, corrects or asks; the importer answers. Every decision is
audited with the broker's name and licence, lands in the binder, and a correction becomes a training example.
Deciding an item someone else already decided is `409 already_decided` (optimistic `version` check).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q

from tariffcompass import clock, codes, services
from tariffcompass.api import labels
from tariffcompass.api.routers.common import ago_words, money
from tariffcompass.catalog import binder
from tariffcompass.catalog.answers import code_out_from_digits
from tariffcompass.catalog.models import Answer, Product
from tariffcompass.catalog.rulings import status_out
from tariffcompass.core.errors import Problem
from tariffcompass.platform.context import Ctx
from tariffcompass.platform.models import Organisation
from tariffcompass.review import lessons
from tariffcompass.review.models import (
    OPEN_STATUSES,
    AlwaysReviewRule,
    Decision,
    Question,
    ReviewItem,
    TrainingExample,
)
from tariffcompass.review.rules import first_match, shipment_value

INTO_LABELS = {"US": "United States", "CA": "Canada", "both": "US and Canada"}
FILTERS = {
    "all": Q(),
    "unsure": Q(kind="unsure"),
    "differs": Q(kind="differs"),
    "ruling_changed": Q(kind="ruling_changed"),
    "always": Q(kind="always_review"),
    "ca": Q(into="CA"),
}


def into_of(into: list[str]) -> str:
    s = set(into or [])
    return "both" if s >= {"US", "CA"} else ("CA" if s == {"CA"} else "US")


# ── Opening items ───────────────────────────────────────────────────────────────────────────────────────
def open_item(
    product: Product,
    answer: Answer | None,
    *,
    kind: str,
    detail: str,
    proposed_us: str = "",
    proposed_ca: str = "",
    rule: AlwaysReviewRule | None = None,
    note: str = "",
    ctx: Ctx | None = None,
    leaning: bool = False,
) -> ReviewItem:
    existing = ReviewItem.objects.filter(product=product, status__in=OPEN_STATUSES).first()
    if existing is not None:
        return existing
    last_approved = product.versions.filter(kind__in=binder.DECIDED_KINDS).order_by("-n").first()
    item = ReviewItem.objects.create(
        org=product.org,
        product=product,
        answer=answer,
        kind=kind,
        detail=detail[:300],
        into=into_of(product.into),
        proposed_us=codes.digits(proposed_us),
        proposed_ca=codes.digits(proposed_ca),
        previous_us=last_approved.us_code if last_approved else "",
        value=shipment_value(product),
        rule=rule,
        note=note,
        leaning=leaning,
    )
    if product.standing != "approved" or kind != "always_review":
        Product.objects.filter(pk=product.pk).update(standing="in_review")
    if ctx is not None:
        ctx.audit(
            "review.opened",
            f"{product.sku} went to the broker: {labels.REVIEW_KINDS[kind].lower()}",
            target_type="product",
            target_id=str(product.pk),
            details={"label": product.sku, "kind": kind},
        )
    return item


def route(
    product: Product, answer: Answer, *, verdict: str, us_code: str, ca_code: str, text: str, ctx: Ctx | None
) -> ReviewItem | None:
    """Unsure answers, codes that differ from the last approved one and always-review rules open an item."""
    last = product.versions.filter(kind__in=binder.DECIDED_KINDS).order_by("-n").first()
    if verdict == "broker":
        return open_item(
            product,
            answer,
            kind="unsure",
            detail="The classifier wasn't sure; one fact decides it.",
            proposed_us=us_code,
            proposed_ca=ca_code,
            ctx=ctx,
            leaning=True,
        )
    if last is not None and last.us_code and codes.digits(us_code)[:10] != last.us_code:
        return open_item(
            product,
            answer,
            kind="differs",
            detail=f"Proposed {codes.fmt(us_code)}; the last approved code was {codes.fmt(last.us_code)}.",
            proposed_us=us_code,
            proposed_ca=ca_code,
            ctx=ctx,
        )
    rule = first_match(product, us_code=us_code, text=text)
    if rule is not None:
        return open_item(
            product,
            answer,
            kind="always_review",
            detail=f"Always reviewed: {rule.label}.",
            proposed_us=us_code,
            proposed_ca=ca_code,
            rule=rule,
            ctx=ctx,
        )
    if (product.org.settings or {}).get("always_send_to_broker"):
        return open_item(
            product,
            answer,
            kind="requested",
            detail="Every new code goes to the broker.",
            proposed_us=us_code,
            proposed_ca=ca_code,
            ctx=ctx,
        )
    return None


# ── Presentation ────────────────────────────────────────────────────────────────────────────────────────
def row_out(item: ReviewItem) -> dict[str, Any]:
    p = item.product
    return {
        "id": str(item.pk),
        "product_id": str(p.pk),
        "sku": p.sku,
        "product_title": p.title,
        "waiting_since": item.created_at,
        "waiting_label": ago_words(item.created_at),
        "into": item.into,
        "into_label": INTO_LABELS.get(item.into, item.into),
        "proposed_us": code_out_from_digits("US", item.proposed_us, leaning=item.leaning),
        "proposed_ca": code_out_from_digits("CA", item.proposed_ca, leaning=item.leaning),
        "kind": item.kind,
        "kind_label": labels.REVIEW_KINDS.get(item.kind, item.kind),
        "detail": item.detail,
        "value": money(item.value, item.currency),
        "with_name": item.assigned_to.full_name if item.assigned_to else None,
        "status": item.status,
        "status_label": labels.REVIEW_STATUSES.get(item.status, item.status),
    }


def question_out(q: Question) -> dict[str, Any]:
    return {
        "id": str(q.pk),
        "asked_by": q.asked_by.full_name if q.asked_by else "",
        "asked_at": q.asked_at,
        "text": q.text,
        "options": list(q.options or []),
        "answer": q.answer or None,
        "answered_by": q.answered_by.full_name if q.answered_by else None,
        "answered_at": q.answered_at,
    }


def _spec(product: Product):
    return product.evidence.filter(kind="spec_sheet").select_related("uploaded_by").order_by("-uploaded_at").first()


def decision_record(item: ReviewItem) -> dict[str, Any]:
    p = item.product
    spec = _spec(p)
    current = p.versions.order_by("-n").first()
    relied = list(current.rulings_relied) if current else []
    return {
        "row": row_out(item),
        "listing": p.listing_text,
        "spec_sheet": spec.extracted_text if spec else "",
        "spec_sheet_file": spec.file_name if spec else None,
        "uploaded_by": spec.uploaded_by.full_name if spec and spec.uploaded_by else None,
        "uploaded_at": spec.uploaded_at if spec else None,
        "deciding_phrases": [
            {"source": ph.get("source", "listing"), "span": {"start": ph["start"], "end": ph["end"]}}
            for ph in (item.deciding_phrases or [])
        ],
        "misread": item.misread or None,
        "previous_us": codes.fmt(item.previous_us) if item.previous_us else None,
        "rulings_relied": [{"id": r, "key": binder.ruling_key(r), "status_label": status_label(r)} for r in relied],
        "ruling_change": status_out(
            item.ruling_change["kind"], item.ruling_change.get("by_id"), _date(item.ruling_change.get("date"))
        )
        if item.ruling_change
        else None,
        "rule": item.rule.label if item.rule else None,
        "answer_id": str(item.answer_id) if item.answer_id else "",
        "questions": [question_out(q) for q in item.questions.select_related("asked_by", "answered_by")],
    }


def status_label(ruling_id: str) -> str:
    from tariffcompass.catalog.rulings import status_of

    return status_of(ruling_id)["kind_label"]


def _date(value: Any):
    from datetime import date

    if value in (None, ""):
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def docket(
    org: Organisation, *, filter_: str = "all", q: str = "", sort: str = "waiting", page: int = 1, page_size: int = 25
) -> dict[str, Any]:
    from tariffcompass.lab.models import TrainingRound

    base = ReviewItem.objects.filter(org=org, status__in=OPEN_STATUSES).select_related("product", "assigned_to")
    counts = {k: base.filter(cond).count() for k, cond in FILTERS.items()}
    qs = base.filter(FILTERS.get(filter_, Q()))
    if q.strip():
        qs = qs.filter(Q(product__sku__icontains=q.strip()) | Q(product__title__icontains=q.strip()))
    qs = qs.order_by({"value": "-value", "product": "product__sku"}.get(sort, "created_at"), "created_at")
    total = qs.count()
    page, page_size = max(1, page), max(1, min(100, page_size))
    items = list(qs[(page - 1) * page_size : page * page_size])
    oldest = base.order_by("created_at").first()
    week_start = clock.now() - timedelta(days=7)
    week = Decision.objects.filter(org=org, created_at__gte=week_start)
    last_round = TrainingRound.objects.filter(org=org).order_by("-n").values_list("n", flat=True).first() or 0
    waiting = TrainingExample.objects.filter(org=org, used_in_round__isnull=True).count()
    broker = binder_broker_name(org)
    return {
        "counts": {
            "all": counts["all"],
            "unsure": counts["unsure"],
            "differs": counts["differs"],
            "ruling_changed": counts["ruling_changed"],
            "always": counts["always"],
            "ca": counts["ca"],
        },
        "oldest_label": f"oldest {ago_words(oldest.created_at)}" if oldest else "",
        "items": [row_out(i) for i in items],
        "total": total,
        "week": {
            "approved": week.filter(action="approve").count(),
            "corrected": week.filter(action="correct").count(),
            "questions": week.filter(action="ask").count(),
        },
        "next_round": {"round": last_round + 1, "correctionsWaiting": waiting},
        "empty_message": f"Nothing waiting for {broker}. New answers that need a broker will appear here.",
    }


def binder_broker_name(org: Organisation) -> str:
    from tariffcompass.catalog.answers import broker_short_name

    return broker_short_name(org)


# ── Decisions ───────────────────────────────────────────────────────────────────────────────────────────
def get_item(org: Organisation, item_id: str) -> ReviewItem:
    from tariffcompass.platform.context import is_uuid

    item = (
        ReviewItem.objects.filter(org=org, pk=item_id).select_related("product__org", "assigned_to", "rule").first()
        if is_uuid(item_id)
        else None
    )
    if item is None:
        raise Problem(404, "not_found", "We couldn't find that review item.")
    return item


def _claim(item: ReviewItem, allowed: tuple[str, ...], status: str) -> None:
    """Move the item to `status` only if nobody else moved it first."""
    n = ReviewItem.objects.filter(pk=item.pk, version=item.version, status__in=allowed).update(
        status=status,
        version=item.version + 1,
        decided_at=clock.now() if status in ("approved", "corrected") else None,
    )
    if n == 0:
        item.refresh_from_db()
        raise Problem(409, "already_decided", "Someone already decided this item.", current=_jsonable(row_out(item)))
    item.refresh_from_db()


def _jsonable(data: Any) -> Any:
    from pydantic.alias_generators import to_camel

    from tariffcompass.catalog.answers import jsonable

    def camel(x: Any) -> Any:
        if isinstance(x, dict):
            return {to_camel(k): camel(v) for k, v in x.items()}
        if isinstance(x, list):
            return [camel(v) for v in x]
        return x

    return camel(jsonable(data))


def _licence_words(ctx: Ctx) -> str:
    return f" ({ctx.user.licence})" if ctx.user.licence else ""


def approve(ctx: Ctx, item: ReviewItem, note: str) -> dict[str, Any]:
    product = item.product
    with transaction.atomic():
        _claim(item, OPEN_STATUSES, "approved")
        prior = product.versions.filter(kind__in=binder.DECIDED_KINDS).exists()
        same = product.us_code == item.proposed_us
        kind = "re_approved" if prior and same else "approved"
        relied = _relied_from_answer(item)
        v = binder.append_from_ctx(
            product,
            kind,
            ctx,
            us_code=item.proposed_us or product.us_code,
            ca_code=item.proposed_ca or product.ca_code,
            standing="approved",
            rulings_relied=relied,
            why=note or "Approved as proposed.",
            answer=item.answer,
            action="review.approved",
            summary=f"{ctx.user.full_name}{_licence_words(ctx)} approved {product.sku} as "
            f"{codes.fmt(item.proposed_us or product.us_code)}",
        )
        Decision.objects.create(
            org=item.org,
            item=item,
            action="approve",
            final_us=v.us_code,
            final_ca=v.ca_code,
            reason=note,
            decided_by=ctx.user,
            licence=ctx.user.licence,
            binder_version=v.n,
        )
    return {
        "item": row_out(item),
        "binder_version": v.n,
        "lesson": None,
        "toast": f"Approved · {product.sku} · {codes.fmt(v.us_code)} · binder v{v.n}",
    }


def _relied_from_answer(item: ReviewItem) -> list[str] | None:
    if item.answer is None:
        return None
    cited = [
        r
        for r in item.answer.payload.get("rulings", [])
        if r.get("status", {}).get("kind") == "in_force" and "different_heading" not in r.get("match", [])
    ]
    return [r["id"] for r in cited] or None


def check_code(country: str, digits: str, field: str) -> str:
    d = codes.digits(digits)
    if len(d) != 10 or services.retriever().tariff_line(country, d) is None:  # type: ignore[arg-type]
        raise Problem(
            422,
            "unknown_code",
            f"{codes.fmt(d) or digits} isn't a line of the tariff in force.",
            errors=[{"field": field, "message": "That code isn't a line of the tariff in force."}],
        )
    return d


def canadian_for(us_digits: str) -> str:
    retr = services.retriever()
    for line in retr.tariff("", country="CA", under=us_digits[:6], k=10):
        if len(line.code) == 10:
            return line.code
    return ""


def preview(
    item: ReviewItem, *, us_code: str | None, ca_code: str | None, reason_kind: str, reason: str
) -> dict[str, Any]:
    product = item.product
    spec = _spec(product)
    phrase = lessons.deciding_phrase(product.listing_text, spec.extracted_text if spec else "", item.deciding_phrases)
    final_us = codes.digits(us_code or "") or item.proposed_us
    text = lessons.lesson(
        reason_kind=reason_kind,
        reason=reason,
        proposed_us=item.proposed_us,
        final_us=final_us,
        proposed_ca=item.proposed_ca,
        final_ca=codes.digits(ca_code or ""),
        phrase=phrase,
    )
    return {"lesson": text, "redline": lessons.redline(item.proposed_us, final_us)}


def correct(
    ctx: Ctx,
    item: ReviewItem,
    *,
    us_code: str | None,
    ca_code: str | None,
    reason_kind: str,
    reason: str,
    ruling_relied: str | None,
    also_change_ca: bool,
) -> dict[str, Any]:
    product = item.product
    final_us = check_code("US", us_code, "usCode") if us_code else (item.proposed_us or product.us_code)
    if ca_code:
        final_ca = check_code("CA", ca_code, "caCode")
    elif also_change_ca:
        final_ca = canadian_for(final_us) or item.proposed_ca or product.ca_code
    else:
        final_ca = item.proposed_ca or product.ca_code
    relied_id = None
    if ruling_relied:
        from tariffcompass.catalog import rulings

        relied_id = _ruling_id(ruling_relied)
        if not rulings.exists(relied_id):
            raise Problem(
                422,
                "validation_error",
                "One or more fields are invalid.",
                errors=[{"field": "rulingRelied", "message": "We don't know that ruling."}],
            )
    spec = _spec(product)
    phrase = lessons.deciding_phrase(product.listing_text, spec.extracted_text if spec else "", item.deciding_phrases)
    lesson_text = lessons.lesson(
        reason_kind=reason_kind,
        reason=reason,
        proposed_us=item.proposed_us,
        final_us=final_us,
        proposed_ca=item.proposed_ca,
        final_ca=final_ca,
        phrase=phrase,
        ruling_relied=relied_id or "",
    )
    with transaction.atomic():
        _claim(item, OPEN_STATUSES, "corrected")
        v = binder.append_from_ctx(
            product,
            "corrected",
            ctx,
            us_code=final_us,
            ca_code=final_ca,
            standing="approved",
            rulings_relied=[relied_id] if relied_id else None,
            why=reason,
            answer=item.answer,
            action="review.corrected",
            summary=f"{ctx.user.full_name}{_licence_words(ctx)} corrected {product.sku} from "
            f"{codes.fmt(item.proposed_us)} to {codes.fmt(final_us)}",
        )
        decision = Decision.objects.create(
            org=item.org,
            item=item,
            action="correct",
            final_us=final_us,
            final_ca=final_ca,
            reason_kind=reason_kind,
            reason=reason,
            ruling_relied=relied_id or "",
            lesson=lesson_text,
            decided_by=ctx.user,
            licence=ctx.user.licence,
            binder_version=v.n,
        )
        example = TrainingExample(org=item.org, product=product, decision=decision, lesson=lesson_text, payload={})
        example.payload = lessons.example_payload(
            example_id=str(example.pk),
            sku=product.sku,
            text=f"{product.listing_text}\n\n{spec.extracted_text if spec else ''}".strip(),
            made_in=product.made_in,
            into=list(product.into or []),
            proposed_us=item.proposed_us,
            proposed_ca=item.proposed_ca,
            us_code=final_us,
            ca_code=final_ca,
            reason_kind=reason_kind,
            reason=reason,
            lesson_text=lesson_text,
            ruling_relied=relied_id,
            deciding_fact=_deciding_fact(product),
            decided_by=ctx.user.full_name,
            decided_on=clock.today().isoformat(),
        )
        example.save()
    return {
        "item": row_out(item),
        "binder_version": v.n,
        "lesson": lesson_text,
        "toast": f"Corrected · {product.sku} → {codes.fmt(final_us)} · binder v{v.n}",
    }


def _ruling_id(key_or_id: str) -> str:
    raw = key_or_id.strip()
    if "-" in raw and " " not in raw:
        coll, num = raw.split("-", 1)
        return f"{coll.upper()} {num.upper()}"
    return raw.upper()


def _deciding_fact(product: Product) -> dict[str, str] | None:
    v = product.versions.order_by("-n").first()
    if v and v.deciding_fact:
        return {k: v.deciding_fact.get(k, "") for k in ("key", "label", "value")}
    return None


def ask(ctx: Ctx, item: ReviewItem, question: str, options: list[str]) -> dict[str, Any]:
    with transaction.atomic():
        _claim(item, OPEN_STATUSES, "asked")
        Question.objects.create(
            org=item.org, item=item, asked_by=ctx.user, text=question, options=[o for o in options if o.strip()][:6]
        )
        Decision.objects.create(
            org=item.org, item=item, action="ask", reason=question, decided_by=ctx.user, licence=ctx.user.licence
        )
        ctx.audit(
            "review.asked",
            f"{ctx.user.full_name} asked {item.org.name} about {item.product.sku}",
            target_type="product",
            target_id=str(item.product.pk),
            details={"label": item.product.sku, "question": question},
        )
    return {
        "item": row_out(item),
        "binder_version": None,
        "lesson": None,
        "toast": f"Asked · {item.product.sku} · waiting for {item.org.name.split()[0]}",
    }


def answer(ctx: Ctx, item: ReviewItem, text: str) -> dict[str, Any]:
    q = item.questions.filter(answered_at__isnull=True).order_by("-asked_at").first()
    if item.status != "asked" or q is None:
        raise Problem(
            409, "already_decided", "There's no open question on this item.", current=_jsonable(row_out(item))
        )
    product = item.product
    with transaction.atomic():
        _claim(item, ("asked",), "answered")
        q.answer, q.answered_by, q.answered_at = text, ctx.user, clock.now()
        q.save(update_fields=["answer", "answered_by", "answered_at"])
        Decision.objects.create(org=item.org, item=item, action="answer", reason=text, decided_by=ctx.user)
        prev = product.versions.order_by("-n").first()
        fact = dict(prev.deciding_fact) if prev and prev.deciding_fact else {"key": "question", "label": q.text[:80]}
        fact.update(value=text[:200], source_note=f"answered by {ctx.user.full_name}")
        v = binder.append_from_ctx(
            product,
            "question_answered",
            ctx,
            standing="in_review",
            deciding_fact=fact,
            why=f"{q.asked_by.full_name if q.asked_by else 'The broker'} asked: {q.text}",
            action="review.answered",
            summary=f"{ctx.user.full_name} answered the broker's question on {product.sku}",
        )
    return {
        "item": row_out(item),
        "binder_version": v.n,
        "lesson": None,
        "toast": f"Answered · {product.sku} · back with the broker",
    }
