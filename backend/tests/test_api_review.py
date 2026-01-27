"""The broker's docket: approve, correct (with the lesson and the training example), ask and answer, rules."""

from __future__ import annotations

import pytest

from tariffcompass.platform import audit
from tariffcompass.platform.models import AuditEvent
from tariffcompass.review import lessons
from tariffcompass.review.models import AlwaysReviewRule, ReviewItem, TrainingExample
from tariffcompass.review.service import open_item

pytestmark = pytest.mark.django_db


@pytest.fixture
def item(world, catalogue):
    p = catalogue["tumbler"]
    p.listing_text = "20 oz double-wall stainless steel tumbler, air-insulated, sliding lid."
    p.save()
    start = p.listing_text.find("air-insulated")
    ri = open_item(
        p,
        None,
        kind="differs",
        detail="Proposed 9617.00.10.00; the last approved code was 7323.",
        proposed_us="9617001000",
        proposed_ca="9617000000",
    )
    ri.deciding_phrases = [{"source": "listing", "start": start, "end": start + len("air-insulated")}]
    ri.assigned_to = world.broker
    ri.save()
    return ri


def test_docket_counts_rows_and_labels(world, item):
    d = world.api("broker").get("review").json()
    assert d["counts"]["all"] == 1 and d["counts"]["differs"] == 1 and d["total"] == 1
    row = d["items"][0]
    assert row["kindLabel"] == "Differs from last code" and row["proposedUs"]["code"] == "9617.00.10.00"
    assert row["withName"] == "Dana Whitlock" and row["waitingLabel"] == "today" and row["intoLabel"]
    assert d["nextRound"] == {"round": 1, "correctionsWaiting": 0}
    assert world.api("broker").get("review", filter="unsure").json()["total"] == 0
    assert world.api("broker").get("review", filter="nonsense").status_code == 422


def test_docket_is_tenant_scoped(world, item):
    assert world.api("outsider").get("review").json()["total"] == 0
    assert world.api("outsider").get(f"review/{item.pk}").status_code == 404
    assert world.api("outsider").post(f"review/{item.pk}/approve", {"note": ""}).status_code in (403, 404)


def test_decision_record_marks_the_deciding_phrase(world, item):
    rec = world.api("broker").get(f"review/{item.pk}").json()
    span = rec["decidingPhrases"][0]["span"]
    assert rec["listing"][span["start"] : span["end"]] == "air-insulated"
    assert rec["row"]["id"] == str(item.pk)


@pytest.mark.parametrize("who", ["importer", "compliance", "admin"])
def test_only_brokers_decide(world, item, who):
    api = world.api(who)
    assert api.post(f"review/{item.pk}/approve", {"note": ""}).status_code == 403
    assert api.post(f"review/{item.pk}/lesson", {"reasonKind": "other", "reason": "x"}).status_code == 403


def test_approve_appends_a_binder_version_and_audits_with_licence(world, item):
    res = world.api("broker").post(f"review/{item.pk}/approve", {"note": "Vacuum-sealed per the supplier."})
    assert res.status_code == 200, res.content
    out = res.json()
    assert out["item"]["status"] == "approved" and out["binderVersion"] == 2
    assert out["toast"].startswith("Approved · NB-KT-0412")
    ev = AuditEvent.objects.get(action="review.approved")
    assert "34812" in ev.summary and ev.actor_name == "Dana Whitlock"
    assert item.product.versions.get(n=2).kind == "approved"
    assert audit.verify(world.north).ok


def test_second_decision_is_409_already_decided(world, item):
    world.api("broker").post(f"review/{item.pk}/approve", {"note": ""})
    late = world.api("broker2").post(f"review/{item.pk}/approve", {"note": ""})
    assert late.status_code == 409 and late.json()["code"] == "already_decided"
    assert late.json()["current"]["status"] == "approved"


def test_lesson_preview_has_no_side_effects(world, item):
    res = world.api("broker").post(
        f"review/{item.pk}/lesson",
        {
            "usCode": "9617.00.30.00",
            "reasonKind": "facts_differ",
            "reason": "Holds 1.2 litres, so the vessel exceeds one litre",
        },
    )
    body = res.json()
    assert "air-insulated" in body["lesson"] and "9617.00.30.00, not 9617.00.10.00" in body["lesson"]
    changed = [c["index"] for c in body["redline"] if c["changed"]]
    assert changed == [6] and len(body["redline"]) == 10
    assert not TrainingExample.objects.exists() and ReviewItem.objects.get(pk=item.pk).status == "waiting"


def test_correct_records_the_training_example_in_the_agreed_format(world, item):
    res = world.api("broker").post(
        f"review/{item.pk}/correct",
        {
            "usCode": "9617003000",
            "reasonKind": "facts_differ",
            "reason": "Holds 1.2 litres, so the vessel exceeds one litre",
            "rulingRelied": "ny-n321134",
        },
    )
    assert res.status_code == 200, res.content
    out = res.json()
    assert out["toast"] == "Corrected · NB-KT-0412 → 9617.00.30.00 · binder v2"
    assert out["lesson"]
    ex = TrainingExample.objects.get()
    p = ex.payload
    assert set(p) == {
        "id",
        "product_sku",
        "text",
        "made_in",
        "into",
        "proposed_us",
        "proposed_ca",
        "us_code",
        "ca_code",
        "heading",
        "reason_kind",
        "reason",
        "lesson",
        "ruling_relied",
        "deciding_fact",
        "decided_by",
        "decided_on",
    }
    assert p["us_code"] == "9617003000" and p["proposed_us"] == "9617001000" and p["heading"] == "9617"
    assert p["ruling_relied"] == "NY N321134" and p["decided_by"] == "Dana Whitlock" and p["decided_on"] == "2026-02-19"
    assert p["id"] == str(ex.pk) and ex.used_in_round is None
    v = item.product.versions.get(n=2)
    assert v.kind == "corrected" and v.us_code == "9617003000" and v.rulings_relied == ["NY N321134"]
    docket = world.api("broker").get("review").json()
    assert docket["week"]["corrected"] == 1 and docket["nextRound"]["correctionsWaiting"] == 1


def test_correct_rejects_codes_not_in_the_tariff_and_short_reasons(world, item):
    api = world.api("broker")
    bad = api.post(
        f"review/{item.pk}/correct",
        {"usCode": "1234.56.78.90", "reasonKind": "other", "reason": "Because it is different"},
    )
    assert bad.status_code == 422 and bad.json()["code"] == "unknown_code"
    short = api.post(f"review/{item.pk}/correct", {"usCode": "9617003000", "reasonKind": "other", "reason": "no"})
    assert short.status_code == 422 and short.json()["errors"][0]["field"] == "reason"
    unknown_ruling = api.post(
        f"review/{item.pk}/correct",
        {"usCode": "9617003000", "reasonKind": "other", "reason": "Because it is different", "rulingRelied": "NY X1"},
    )
    assert unknown_ruling.status_code == 422
    assert ReviewItem.objects.get(pk=item.pk).status == "waiting"


def test_ask_then_importer_answers(world, item):
    asked = world.api("broker").post(
        f"review/{item.pk}/ask", {"question": "Is the space between the walls a vacuum?", "options": ["Vacuum", "Air"]}
    )
    assert asked.json()["item"]["status"] == "asked"
    assert world.api("broker").post(f"review/{item.pk}/answer", {"answer": "x"}).status_code == 403
    ans = world.api("importer").post(f"review/{item.pk}/answer", {"answer": "Air: it is not vacuum-sealed."})
    assert ans.status_code == 200 and ans.json()["item"]["status"] == "answered"
    v = item.product.versions.order_by("-n").first()
    assert v.kind == "question_answered" and v.deciding_fact["source_note"] == "answered by Jordan Tse"
    rec = world.api("broker").get(f"review/{item.pk}").json()
    assert rec["questions"][0]["answer"].startswith("Air") and rec["questions"][0]["answeredBy"] == "Jordan Tse"
    again = world.api("importer").post(f"review/{item.pk}/answer", {"answer": "again"})
    assert again.status_code == 409
    # the broker can then decide
    assert world.api("broker").post(f"review/{item.pk}/approve", {"note": ""}).status_code == 200


def test_lessons_are_deterministic_sentences():
    a = lessons.lesson(
        reason_kind="facts_differ",
        reason="Air between the walls, not a vacuum.",
        proposed_us="9617001000",
        final_us="7323930080",
        phrase="Double-wall",
    )
    assert a == lessons.lesson(
        reason_kind="facts_differ",
        reason="Air between the walls, not a vacuum.",
        proposed_us="9617001000",
        final_us="7323930080",
        phrase="Double-wall",
    )
    assert a.startswith("“Double-wall” on its own doesn't decide it.") and "heading 7323, not 9617" in a
    assert lessons.lesson(
        reason_kind="ruling_elsewhere",
        reason="Same article",
        ruling_relied="NY N297165",
        proposed_us="9617001000",
        final_us="7323930080",
    ).startswith("Follow NY N297165")
    assert len(lessons.lesson(reason_kind="other", reason="x" * 600)) <= lessons.MAX_LESSON


def test_rules_crud_rbac_and_matches(world, catalogue):
    broker = world.api("broker")
    res = broker.post("rules", {"kind": "chapter", "value": "96", "label": "Everything in chapter 96"})
    assert res.status_code == 201 and res.json()["matches"] == 1 and res.json()["kindLabel"] == "Chapter"
    rid = res.json()["id"]
    assert world.api("importer").post("rules", {"kind": "keyword", "value": "x", "label": "abc"}).status_code == 403
    assert world.api("importer").get("rules").status_code == 200
    bad = broker.post("rules", {"kind": "value_over", "value": "lots", "label": "Big entries"})
    assert bad.status_code == 422
    paused = world.api("compliance").patch(f"rules/{rid}", {"active": False})
    assert paused.json()["active"] is False and paused.json()["matches"] == 0
    assert world.api("outsider").patch(f"rules/{rid}", {"active": True}).status_code in (403, 404)
    assert broker.delete(f"rules/{rid}").status_code == 204
    assert {"rule.created", "rule.changed", "rule.removed"} <= set(AuditEvent.objects.values_list("action", flat=True))
    assert not AlwaysReviewRule.objects.exists()
