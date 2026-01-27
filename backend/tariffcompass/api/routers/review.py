"""Broker review: the docket, the decision record, decisions, and always-review rules (API_CONTRACT §1.10)."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja.responses import Status

from tariffcompass import clock
from tariffcompass.api.schemas.review import (
    AnswerQuestionIn,
    ApproveIn,
    AskIn,
    CorrectIn,
    DecisionOut,
    DecisionRecord,
    DocketOut,
    LessonIn,
    LessonOut,
    RuleIn,
    RuleOut,
    RulePatch,
)
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform.context import ctx_of, is_uuid, requires
from tariffcompass.review import service
from tariffcompass.review.models import AlwaysReviewRule
from tariffcompass.review.rules import count_matches

router = WireRouter()
rules_router = WireRouter()


@router.get("", response=DocketOut)
@requires("review:read")
def get_docket(
    request: HttpRequest, filter: str = "all", q: str = "", sort: str = "waiting", page: int = 1, pageSize: int = 25
) -> dict:
    ctx = ctx_of(request)
    if filter not in service.FILTERS:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "filter", "message": "Unknown filter."}],
        )
    return service.docket(ctx.need_org(), filter_=filter, q=q, sort=sort, page=page, page_size=pageSize)


@router.get("/{item_id}", response=DecisionRecord)
@requires("review:read")
def get_record(request: HttpRequest, item_id: str) -> dict:
    ctx = ctx_of(request)
    return service.decision_record(service.get_item(ctx.need_org(), item_id))


@router.post("/{item_id}/lesson", response=LessonOut)
@requires("review:decide")
def lesson(request: HttpRequest, item_id: str, body: LessonIn) -> dict:
    ctx = ctx_of(request)
    item = service.get_item(ctx.need_org(), item_id)
    return service.preview(
        item, us_code=body.us_code, ca_code=body.ca_code, reason_kind=body.reason_kind, reason=body.reason
    )


@router.post("/{item_id}/approve", response=DecisionOut)
@requires("review:decide")
def approve(request: HttpRequest, item_id: str, body: ApproveIn) -> dict:
    ctx = ctx_of(request)
    return service.approve(ctx, service.get_item(ctx.need_org(), item_id), body.note)


@router.post("/{item_id}/correct", response=DecisionOut)
@requires("review:decide")
def correct(request: HttpRequest, item_id: str, body: CorrectIn) -> dict:
    ctx = ctx_of(request)
    item = service.get_item(ctx.need_org(), item_id)
    if not body.us_code and not body.ca_code and not body.also_change_ca:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "usCode", "message": "Give the code you're correcting to."}],
        )
    return service.correct(
        ctx,
        item,
        us_code=body.us_code,
        ca_code=body.ca_code,
        reason_kind=body.reason_kind,
        reason=body.reason,
        ruling_relied=body.ruling_relied,
        also_change_ca=body.also_change_ca,
    )


@router.post("/{item_id}/ask", response=DecisionOut)
@requires("review:decide")
def ask(request: HttpRequest, item_id: str, body: AskIn) -> dict:
    ctx = ctx_of(request)
    return service.ask(ctx, service.get_item(ctx.need_org(), item_id), body.question, body.options)


@router.post("/{item_id}/answer", response=DecisionOut)
@requires("review:answer")
def answer(request: HttpRequest, item_id: str, body: AnswerQuestionIn) -> dict:
    ctx = ctx_of(request)
    return service.answer(ctx, service.get_item(ctx.need_org(), item_id), body.answer)


# ── Always-review rules ─────────────────────────────────────────────────────────────────────────────────
def rule_out(r: AlwaysReviewRule) -> dict:
    from tariffcompass.review.models import RULE_KINDS

    return {
        "id": str(r.pk),
        "kind": r.kind,
        "kind_label": dict(RULE_KINDS).get(r.kind, r.kind),
        "value": r.value,
        "label": r.label,
        "active": r.active,
        "created_by": r.created_by.full_name if r.created_by else "Tariff Compass",
        "created_at": r.created_at,
        "matches": count_matches(r),
    }


def _rule(request: HttpRequest, rule_id: str) -> AlwaysReviewRule:
    ctx = ctx_of(request)
    r = AlwaysReviewRule.objects.filter(org=ctx.org, pk=rule_id).first() if is_uuid(rule_id) else None
    if r is None:
        raise Problem(404, "not_found", "We couldn't find that rule.")
    return r


@rules_router.get("", response=list[RuleOut])
@requires("review:read")
def list_rules(request: HttpRequest) -> list[dict]:
    ctx = ctx_of(request)
    return [rule_out(r) for r in AlwaysReviewRule.objects.filter(org=ctx.org).select_related("created_by")]


@rules_router.post("", response={201: RuleOut})
@requires("rules:manage")
def create_rule(request: HttpRequest, body: RuleIn):
    ctx = ctx_of(request)
    if body.kind == "value_over" and not body.value.replace(",", "").replace("$", "").strip().isdigit():
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "value", "message": "Give an amount in US dollars, like 25000."}],
        )
    r = AlwaysReviewRule.objects.create(
        org=ctx.need_org(),
        kind=body.kind,
        value=body.value.strip(),
        label=body.label.strip(),
        created_by=ctx.user,
        created_at=clock.now(),
    )
    ctx.audit(
        "rule.created",
        f"{ctx.user.full_name} added a review rule: {r.label}",
        target_type="rule",
        target_id=str(r.pk),
        details={"kind": r.kind, "value": r.value, "label": r.label},
    )
    return Status(201, rule_out(r))


@rules_router.patch("/{rule_id}", response=RuleOut)
@requires("rules:manage")
def patch_rule(request: HttpRequest, rule_id: str, body: RulePatch) -> dict:
    ctx = ctx_of(request)
    r = _rule(request, rule_id)
    changed: dict[str, list[Any]] = {}
    if body.active is not None and body.active != r.active:
        changed["active"] = [r.active, body.active]
        r.active = body.active
    if body.label and body.label.strip() != r.label:
        changed["label"] = [r.label, body.label.strip()]
        r.label = body.label.strip()
    if changed:
        r.save()
        state = "paused" if changed.get("active") == [True, False] else "changed"
        ctx.audit(
            "rule.changed",
            f"{ctx.user.full_name} {state} the review rule {r.label}",
            target_type="rule",
            target_id=str(r.pk),
            details=changed,
        )
    return rule_out(r)


@rules_router.delete("/{rule_id}", response={204: None})
@requires("rules:manage")
def delete_rule(request: HttpRequest, rule_id: str):
    ctx = ctx_of(request)
    r = _rule(request, rule_id)
    label = r.label
    r.delete()
    ctx.audit(
        "rule.removed",
        f"{ctx.user.full_name} removed the review rule {label}",
        target_type="rule",
        target_id=rule_id,
        details={"label": label},
    )
    return Status(204, None)
