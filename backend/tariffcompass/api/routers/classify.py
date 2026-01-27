"""Classify, answers, evidence and the public samples (API_CONTRACT §1.5).

A classification produces an immutable answer. It never files anything: always-review rules and the verdict
decide whether a review item opens for the broker.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from django.http import HttpRequest
from ninja import File, Form, UploadedFile
from ninja.responses import Status

from tariffcompass import clock, codes
from tariffcompass.api.routers.common import paginate
from tariffcompass.api.schemas.classify import (
    AnswerOut,
    AnswerSummary,
    CitationFeedbackIn,
    ClassifyIn,
    ConfirmedFact,
    EvidenceOut,
    PublicClassifyIn,
    SampleOut,
    SaveToBinderIn,
    SendToBrokerIn,
)
from tariffcompass.api.schemas.common import Page
from tariffcompass.api.schemas.products import BinderVersion as BinderVersionOut
from tariffcompass.api.schemas.review import ReviewRow
from tariffcompass.catalog import answers as core
from tariffcompass.catalog import binder, samples
from tariffcompass.catalog.evidence import evidence_out, from_upload
from tariffcompass.catalog.models import Answer, Evidence, Product
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform import limits
from tariffcompass.platform.context import Ctx, ctx_of, enforce_csrf, is_uuid, requires
from tariffcompass.review import service as review
from tariffcompass.review.models import OPEN_STATUSES, ReviewItem, TrainingExample

router = WireRouter()  # /classify
answers_router = WireRouter()  # /answers
evidence_router = WireRouter()  # /evidence
public_router = WireRouter()  # /public


# ── Helpers ─────────────────────────────────────────────────────────────────────────────────────────────
def shipment_of(body_shipment: Any, product: Product | None) -> dict[str, Any] | None:
    if body_shipment is not None:
        return {
            "value": body_shipment.value.amount,
            "currency": body_shipment.value.currency,
            "quantity": body_shipment.quantity,
            "transport": body_shipment.transport,
        }
    if product is not None and product.shipment:
        return dict(product.shipment)
    return None


def live_round(org) -> int | None:
    from tariffcompass.lab.models import TrainingRound

    return TrainingRound.objects.filter(org=org, status="live").values_list("n", flat=True).first()


def answer_out(a: Answer) -> dict[str, Any]:
    item = None
    if a.product_id:
        item = (
            ReviewItem.objects.filter(product_id=a.product_id, status__in=OPEN_STATUSES)
            .values_list("id", flat=True)
            .first()
        )
    return {
        **a.payload,
        "id": str(a.pk),
        "created_at": a.created_at,
        "created_by": a.created_by.full_name if a.created_by else None,
        "sample": False,
        "product_id": str(a.product_id) if a.product_id else None,
        "review_item_id": str(item) if item else None,
    }


def get_answer(ctx: Ctx, answer_id: str) -> Answer:
    a = (
        Answer.objects.filter(org=ctx.need_org(), pk=answer_id).select_related("product", "created_by").first()
        if is_uuid(answer_id)
        else None
    )
    if a is None:
        raise Problem(404, "not_found", "We couldn't find that answer.")
    return a


def classify_for(
    ctx: Ctx,
    q: dict[str, Any],
    *,
    product: Product | None,
    evidence: list[Evidence],
    shipment: dict[str, Any] | None,
    parent: Answer | None = None,
) -> Answer:
    org = ctx.need_org()
    spec = " ".join(e.extracted_text for e in evidence if e.extracted_text)
    facts = tuple(f for e in evidence for f in (e.photo_facts or []))
    ans, payload = core.run_core(
        q,
        spec_text=spec,
        photo_facts=facts,
        product_id=str(product.pk) if product else None,
        shipment=shipment,
        classifier_round=live_round(org),
        broker=core.broker_short_name(org),
    )
    a = Answer.objects.create(
        org=org,
        product=product,
        created_by=ctx.user,
        query_text=q["text"],
        made_in=q["made_in"],
        us_code=codes.digits(ans.us.code) if ans.us else "",
        ca_code=codes.digits(ans.ca.code) if ans.ca else "",
        verdict=ans.verdict,
        payload=core.jsonable(payload),
        lm_label=ans.lm_label,
        program_version=ans.program_version,
        first_stage_version=payload["provenance"]["first_stage_version"],
        search_version=payload["provenance"]["search_version"],
        classifier_round=payload["provenance"]["classifier_round"],
        parent=parent,
    )
    ctx.audit(
        "answer.created",
        f"{ctx.user.full_name} classified {product.sku if product else 'a product'}: "
        f"{codes.fmt(a.us_code) if a.us_code else codes.fmt(a.ca_code)} ({a.payload['verdict']['word_label']})",
        target_type="product" if product else "answer",
        target_id=str(product.pk if product else a.pk),
        details={"label": product.sku if product else "", "answer": str(a.pk), "verdict": a.verdict},
    )
    if product is not None:
        review.route(product, a, verdict=ans.verdict, us_code=a.us_code, ca_code=a.ca_code, text=q["text"], ctx=ctx)
    return a


def _evidence(ctx: Ctx, ids: list[str], product: Product | None) -> list[Evidence]:
    ids = [i for i in ids if is_uuid(i)]
    qs = Evidence.objects.filter(org=ctx.org, pk__in=ids)
    found = list(qs)
    if len(found) != len(set(ids)):
        raise Problem(404, "not_found", "We couldn't find one of those files.")
    if product is not None:
        found += [e for e in product.evidence.all() if e.pk not in {f.pk for f in found}]
    return found


# ── Classify ────────────────────────────────────────────────────────────────────────────────────────────
@router.post("", response=AnswerOut)
@requires("classify:run")
def classify(request: HttpRequest, body: ClassifyIn) -> dict:
    ctx = ctx_of(request)
    limits.hit(request, "classify")
    product = None
    if body.product_id:
        from tariffcompass.api.routers.products import get_product

        product = get_product(ctx, body.product_id)
    q = body.model_dump()
    q["into"] = sorted(set(q["into"]), key=["US", "CA"].index) or ["US", "CA"]
    a = classify_for(
        ctx,
        q,
        product=product,
        evidence=_evidence(ctx, body.evidence_ids, product),
        shipment=shipment_of(body.shipment, product),
    )
    return answer_out(a)


@answers_router.get("", response=Page[AnswerSummary])
@requires("classify:read")
def list_answers(request: HttpRequest, mine: bool = False, page: int = 1, pageSize: int = 25) -> dict:
    ctx = ctx_of(request)
    qs = Answer.objects.filter(org=ctx.org).select_related("created_by").order_by("-created_at")
    if mine:
        qs = qs.filter(created_by=ctx.user)
    out = paginate(qs, page, pageSize)
    out["items"] = [summary(a) for a in out["items"]]
    return out


def summary(a: Answer) -> dict[str, Any]:
    return {
        "id": str(a.pk),
        "query_text": a.query_text,
        "us_code": codes.fmt(a.us_code) if a.us_code else None,
        "ca_code": codes.fmt(a.ca_code) if a.ca_code else None,
        "verdict": a.verdict,
        "verdict_label": a.payload["verdict"]["word_label"],
        "created_at": a.created_at,
        "created_by": a.created_by.full_name if a.created_by else "Tariff Compass",
    }


@answers_router.get("/{answer_id}", response=AnswerOut)
@requires("classify:read")
def get_one(request: HttpRequest, answer_id: str) -> dict:
    return answer_out(get_answer(ctx_of(request), answer_id))


@answers_router.post("/{answer_id}/facts", response=AnswerOut)
@requires("classify:run")
def confirm_fact(request: HttpRequest, answer_id: str, body: ConfirmedFact) -> dict:
    ctx = ctx_of(request)
    limits.hit(request, "classify")
    prev = get_answer(ctx, answer_id)
    q = dict(prev.payload["query"])
    facts = [f for f in q.get("confirmed_facts", []) if f["key"] != body.key]
    facts.append({"key": body.key, "answer": body.answer})
    q["confirmed_facts"] = facts
    product = prev.product
    a = classify_for(
        ctx,
        q,
        product=product,
        evidence=_evidence(ctx, q.get("evidence_ids", []), product),
        shipment=shipment_from_query(q, product),
        parent=prev,
    )
    fact = next((f for f in prev.payload.get("facts", []) if f["key"] == body.key), None)
    question = (prev.payload.get("deciding_question") or {}).get("question", "")
    ctx.audit(
        "answer.fact_confirmed",
        f"{ctx.user.full_name} answered: {question or body.key} → {body.answer}",
        target_type="product" if product else "answer",
        target_id=str(product.pk if product else a.pk),
        details={"label": product.sku if product else "", "key": body.key, "answer": body.answer},
    )
    if product is not None and product.versions.exists():
        binder.append_from_ctx(
            product,
            "question_answered",
            ctx,
            us_code=a.us_code,
            ca_code=a.ca_code,
            standing="proposed",
            deciding_fact={
                "key": body.key,
                "label": fact["label"] if fact else body.key,
                "value": body.answer,
                "source_note": f"confirmed by {ctx.user.full_name}",
            },
            why=question or "A fact was confirmed.",
            answer=a,
            action="answer.fact_confirmed",
        )
    return answer_out(a)


def shipment_from_query(q: dict[str, Any], product: Product | None) -> dict[str, Any] | None:
    s = q.get("shipment")
    if s:
        return {
            "value": s["value"]["amount"],
            "currency": s["value"]["currency"],
            "quantity": s.get("quantity", 1),
            "transport": s.get("transport", "ocean"),
        }
    return dict(product.shipment) if product is not None and product.shipment else None


@answers_router.post("/{answer_id}/save", response=BinderVersionOut)
@requires("products:write")
def save(request: HttpRequest, answer_id: str, body: SaveToBinderIn) -> dict:
    from tariffcompass.api.routers.products import get_product

    ctx = ctx_of(request)
    a = get_answer(ctx, answer_id)
    if body.product_id:
        product = get_product(ctx, body.product_id)
    elif body.new_product is not None:
        np = body.new_product
        sku = np.sku.strip().upper()
        if Product.objects.filter(org=ctx.org, sku=sku).exists():
            raise Problem(
                422,
                "validation_error",
                "One or more fields are invalid.",
                errors=[{"field": "newProduct.sku", "message": "A product with this SKU already exists."}],
            )
        product = Product.objects.create(
            org=ctx.need_org(),
            sku=sku,
            title=np.title,
            category=np.category,
            made_in=np.made_in,
            into=list(a.payload["query"]["into"]),
            listing_text=a.query_text,
            created_by=ctx.user,
            unit_value=np.unit_value.amount if np.unit_value else None,
            currency=np.unit_value.currency if np.unit_value else "USD",
        )
        ctx.audit(
            "product.created",
            f"{ctx.user.full_name} added {sku}, {np.title}",
            target_type="product",
            target_id=str(product.pk),
            details={"label": sku},
        )
    elif a.product is not None:
        product = a.product
    else:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "productId", "message": "Choose a product or create one."}],
        )
    if a.product_id != product.pk:
        Answer.objects.filter(pk=a.pk).update(product=product)
    deciding = next((f for f in a.payload.get("facts", []) if f.get("decides")), None) or next(
        (f for f in a.payload.get("facts", []) if f.get("source") in ("read", "stated")), None
    )
    relied = [
        r["id"]
        for r in a.payload.get("rulings", [])
        if r["status"]["kind"] == "in_force" and "different_heading" not in r.get("match", [])
    ]
    ev = [
        e.label
        for e in Evidence.objects.filter(
            pk__in=[i for i in a.payload["query"].get("evidence_ids", []) if is_uuid(i)], org=ctx.org
        )
    ]
    v = binder.append_from_ctx(
        product,
        "proposed",
        ctx,
        us_code=a.us_code,
        ca_code=a.ca_code,
        standing="proposed",
        deciding_fact={
            "key": deciding["key"],
            "label": deciding["label"],
            "value": deciding["value"],
            "source_note": deciding["source_note"],
        }
        if deciding
        else None,
        evidence=ev or None,
        rulings_relied=relied,
        why=a.payload.get("holding_sentence", ""),
        answer=a,
        action="answer.saved",
        summary=f"{ctx.user.full_name} saved the answer to the {product.sku} binder",
    )
    review.route(product, a, verdict=a.verdict, us_code=a.us_code, ca_code=a.ca_code, text=a.query_text, ctx=ctx)
    v.refresh_from_db()
    prev = product.versions.filter(n=v.n - 1).first()
    return binder.version_out(v, prev, True)


@answers_router.post("/{answer_id}/send-to-broker", response=ReviewRow)
@requires("review:submit")
def send_to_broker(request: HttpRequest, answer_id: str, body: SendToBrokerIn) -> dict:
    ctx = ctx_of(request)
    a = get_answer(ctx, answer_id)
    if a.product is None:
        raise Problem(
            422,
            "validation_error",
            "Save the answer to a product binder first.",
            errors=[{"field": "productId", "message": "Save it to a product first."}],
        )
    item = review.open_item(
        a.product,
        a,
        kind="requested",
        detail=body.note or "Sent for review by the importer.",
        proposed_us=a.us_code,
        proposed_ca=a.ca_code,
        note=body.note,
        ctx=None,
        leaning=a.verdict == "broker",
    )
    ctx.audit(
        "answer.sent_to_broker",
        f"{ctx.user.full_name} sent {a.product.sku} to {core.broker_short_name(ctx.org)}",
        target_type="product",
        target_id=str(a.product.pk),
        details={"label": a.product.sku, "note": body.note},
    )
    return review.row_out(item)


@answers_router.post("/{answer_id}/citations/{n}/feedback", response={204: None})
@requires("review:decide")
def citation_feedback(request: HttpRequest, answer_id: str, n: int, body: CitationFeedbackIn):
    ctx = ctx_of(request)
    a = get_answer(ctx, answer_id)
    cited = next((r for r in a.payload.get("rulings", []) if r["n"] == n), None)
    if cited is None:
        raise Problem(404, "not_found", "That answer has no such citation.")
    payload = {
        "signal": "citation",
        "answer_id": str(a.pk),
        "ruling_id": cited["id"],
        "reason": body.reason,
        "text": a.query_text,
        "made_in": a.made_in,
        "us_code": a.us_code or None,
        "heading": a.us_code[:4],
        "decided_by": ctx.user.full_name,
        "decided_on": clock.today().isoformat(),
    }
    lesson = f"{cited['id']} doesn't apply to this product: {body.reason.strip().rstrip('.')}."
    TrainingExample.objects.create(
        org=ctx.need_org(), product=a.product, signal="citation", payload=payload, lesson=lesson
    )
    ctx.audit(
        "answer.citation_flagged",
        f"{ctx.user.full_name} flagged {cited['id']} as not applying",
        target_type="answer",
        target_id=str(a.pk),
        details={"ruling": cited["id"], "reason": body.reason},
    )
    return Status(204, None)


# ── Evidence ────────────────────────────────────────────────────────────────────────────────────────────
@evidence_router.post("", response={201: EvidenceOut})
@requires("classify:run")
def upload(request: HttpRequest, file: File[UploadedFile], kind: Form[str] = ""):
    ctx = ctx_of(request)
    e = from_upload(ctx.need_org(), file, kind=kind or None, uploaded_by=ctx.user)
    ctx.audit(
        "evidence.added",
        f"{ctx.user.full_name} uploaded {e.file_name}",
        target_type="evidence",
        target_id=str(e.pk),
        details={"sha256": e.sha256},
    )
    return Status(201, evidence_out(e))


# ── Public samples ──────────────────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=8)
def _sample_payload(key: str) -> dict[str, Any]:
    s = samples.SAMPLES[key]
    _, payload = core.run_core(samples.classify_in(key), shipment=s["shipment"], broker="Driftwood")
    return core.jsonable(payload)


def sample_out(key: str) -> dict[str, Any]:
    return {
        **_sample_payload(key),
        "id": f"sample-{key}",
        "created_at": clock.now(),
        "created_by": None,
        "sample": True,
        "product_id": None,
        "review_item_id": None,
    }


@public_router.get("/samples", response=list[SampleOut], auth=None)
def list_samples(request: HttpRequest) -> list[dict[str, Any]]:
    limits.hit(request, "public")
    return [
        {"key": k, "title": s["title"], "made_in": s["made_in"], "query": s["query"]}
        for k, s in samples.SAMPLES.items()
    ]


@public_router.get("/samples/{key}", response=AnswerOut, auth=None)
def get_sample(request: HttpRequest, key: str) -> dict:
    limits.hit(request, "public")
    if key not in samples.SAMPLES:
        raise Problem(404, "not_found", "There's no sample by that name.")
    return sample_out(key)


@public_router.post("/classify", response=AnswerOut, auth=None)
def public_classify(request: HttpRequest, body: PublicClassifyIn) -> dict:
    enforce_csrf(request)
    limits.hit(request, "public")
    text = body.text
    key = samples.match(text)
    if key is None:
        raise Problem(
            404, "not_in_demo", "The public demo knows the sample products only. Sign in to classify your own."
        )
    return sample_out(key)
