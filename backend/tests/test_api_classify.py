"""Classify through services (fakes here), answers, facts, save, send to the broker, citations, public samples,
rulings, tariff text and landed cost."""

from __future__ import annotations

import io

import pytest

from tariffcompass.catalog.models import Answer, Product
from tariffcompass.platform.models import AuditEvent
from tariffcompass.review.models import ReviewItem, TrainingExample
from tests.platform_fixtures import Api

pytestmark = pytest.mark.django_db

TEXT = "20 oz double-wall stainless steel tumbler, vacuum insulated, sliding lid"


def classify(api: Api, **extra):
    body = {
        "text": TEXT,
        "madeIn": "CN",
        "into": ["US", "CA"],
        "shipment": {"value": {"amount": "12500.00", "currency": "USD"}, "quantity": 1000, "transport": "ocean"},
        **extra,
    }
    return api.post("classify", body)


def test_classify_returns_the_answer_shape(world, fake_core):
    res = classify(world.api("importer"))
    assert res.status_code == 200, res.content
    a = res.json()
    assert a["us"]["code"] == "9617.00.10.00" and a["us"]["headingDigits"] == "9617"
    assert a["ca"]["code"] == "9617.00.00.00" and a["verdict"]["wordLabel"] == "Strong match"
    assert [r["id"] for r in a["rulings"]] == ["NY N321134", "HQ H303684", "NY N297165"]
    assert a["rulings"][0]["url"] == "https://rulings.cbp.gov/ruling/N321134" and a["rulings"][0]["key"] == "ny-n321134"
    assert a["verdict"]["agreementBar"][2]["kind"] == "contrast"
    assert a["path"][0]["code"] == "XX" and a["path"][-1]["code"] == "9617.00.10.00"
    assert a["path"][-1]["levelLabel"] == "Statistical suffix" and a["path"][0]["griLabel"]
    assert a["landed"][0]["country"] == "US" and a["landed"][0]["lines"][0]["amount"]["amount"] == "900.00"
    assert a["landed"][0]["effectiveRate"] == "+7.2%" and a["landed"][1]["country"] == "CA"
    assert set(a["timings"]) == {"firstStageMs", "searchMs", "programMs", "dutiesMs", "totalMs"}
    assert a["provenance"]["lmLabel"] == "offline simulator"
    assert Answer.objects.get(pk=a["id"]).verdict == "strong"
    assert AuditEvent.objects.filter(action="answer.created").exists()
    assert "%" not in a["verdict"]["sentence"]


@pytest.mark.parametrize(("who", "status"), [("importer", 200), ("broker", 200), ("compliance", 200), ("admin", 403)])
def test_classify_rbac(world, fake_core, who, status):
    assert classify(world.api(who)).status_code == status


def test_classify_validation_and_rate_limit(world, fake_core, settings):
    api = world.api("importer")
    assert api.post("classify", {"text": "x"}).status_code == 422
    settings.TARIFF_COMPASS = {**settings.TARIFF_COMPASS, "RATE_LIMIT_CLASSIFY": "2/min"}
    codes = [classify(api).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_answers_are_tenant_scoped(world, fake_core):
    aid = classify(world.api("importer")).json()["id"]
    assert world.api("compliance").get(f"answers/{aid}").status_code == 200
    assert world.api("outsider").get(f"answers/{aid}").status_code == 404
    page = world.api("importer").get("answers", mine="true").json()
    assert page["total"] == 1 and page["items"][0]["usCode"] == "9617.00.10.00"
    assert world.api("compliance").get("answers", mine="true").json()["total"] == 0


def test_save_to_a_new_product_then_send_to_broker(world, fake_core):
    api = world.api("importer")
    aid = classify(api).json()["id"]
    v = api.post(
        f"answers/{aid}/save",
        {"newProduct": {"sku": "nb-kt-9001", "title": "Sample tumbler", "category": "kitchen", "madeIn": "CN"}},
    )
    assert v.status_code == 200, v.content
    assert v.json()["n"] == 1 and v.json()["kind"] == "proposed" and v.json()["usCode"] == "9617.00.10.00"
    assert [r["id"] for r in v.json()["rulingsRelied"]] == ["NY N321134", "HQ H303684"]  # not the contrast one
    product = Product.objects.get(sku="NB-KT-9001")
    sent = api.post(f"answers/{aid}/send-to-broker", {"note": "Please check before the first entry"})
    assert sent.status_code == 200 and sent.json()["kind"] == "requested"
    assert ReviewItem.objects.get(product=product).note.startswith("Please check")
    assert api.get(f"answers/{aid}").json()["reviewItemId"] == sent.json()["id"]


def test_send_to_broker_needs_a_product(world, fake_core):
    api = world.api("importer")
    aid = classify(api).json()["id"]
    assert api.post(f"answers/{aid}/send-to-broker", {"note": ""}).status_code == 422


def test_classifying_a_product_routes_always_review_rules(world, catalogue):
    world.api("broker").post("rules", {"kind": "material", "value": "stainless", "label": "Steel content"})
    p = catalogue["tumbler"]
    from tariffcompass.catalog import binder

    binder.append(p, "approved", actor=world.broker, actor_role="broker", standing="approved")
    a = classify(world.api("importer"), productId="NB-KT-0412").json()
    item = ReviewItem.objects.get(product=p)
    assert item.kind == "always_review" and a["reviewItemId"] == str(item.pk)


def test_confirming_a_fact_reruns_and_records_it(world, catalogue):
    api = world.api("importer")
    aid = classify(api, productId="NB-KT-0412").json()["id"]
    res = api.post(f"answers/{aid}/facts", {"key": "between_walls", "answer": "vacuum"})
    assert res.status_code == 200 and res.json()["id"] != aid
    assert res.json()["query"]["confirmedFacts"] == [{"key": "between_walls", "answer": "vacuum"}]
    v = catalogue["tumbler"].versions.order_by("-n").first()
    assert v.kind == "question_answered" and v.deciding_fact["source_note"] == "confirmed by Jordan Tse"


def test_citation_feedback_is_a_broker_signal(world, fake_core):
    aid = classify(world.api("importer")).json()["id"]
    assert (
        world.api("importer").post(f"answers/{aid}/citations/3/feedback", {"reason": "Different article"}).status_code
        == 403
    )
    res = world.api("broker").post(f"answers/{aid}/citations/3/feedback", {"reason": "A different article"})
    assert res.status_code == 204
    ex = TrainingExample.objects.get()
    assert ex.signal == "citation" and ex.payload["ruling_id"] == "NY N297165"
    assert world.api("broker").post(f"answers/{aid}/citations/9/feedback", {"reason": "abc"}).status_code == 404


def test_evidence_upload_reads_spec_sheet_text(world, fake_core):
    from tariffcompass.seed import documents

    api = world.api("importer")
    _, pdf = documents.spec_sheet("NB-KT-0412")
    res = api.c.post("/api/v1/evidence", {"file": io.BytesIO(pdf)}, HTTP_X_CSRFTOKEN=api.csrf)
    assert res.status_code == 201, res.content
    assert "double-wall 18/8 stainless steel" in res.json()["extractedText"] and res.json()["pages"] == 1
    photo = io.BytesIO(documents.photo("NB-KT-0412"))
    photo.name = "tumbler.png"
    seen = api.c.post("/api/v1/evidence", {"file": photo}, HTTP_X_CSRFTOKEN=api.csrf).json()
    assert seen["kind"] == "photo" and seen["certain"] and "tumbler" in seen["photoFacts"][0]
    other = io.BytesIO(documents._png("something else"))
    other.name = "x.png"
    unknown = api.c.post("/api/v1/evidence", {"file": other}, HTTP_X_CSRFTOKEN=api.csrf).json()
    assert unknown["certain"] is False


def test_public_samples_need_no_account(db, fake_core):
    api = Api()
    samples = api.get("public/samples").json()
    assert {s["key"] for s in samples} == {"tumbler", "bike-light", "pullover"} and samples[0]["madeIn"]
    one = api.get("public/samples/tumbler").json()
    assert one["sample"] is True and one["id"] == "sample-tumbler"
    hit = api.post("public/classify", {"text": "a 20 oz vacuum tumbler"})
    assert hit.status_code == 200 and hit.json()["sample"]
    miss = api.post("public/classify", {"text": "an industrial gas turbine for aircraft"})
    assert miss.status_code == 404 and miss.json()["code"] == "not_in_demo"
    assert api.get("public/samples/nope").status_code == 404


def test_rulings_detail_compare_and_search(world, fake_core):
    api = world.api("importer")
    d = api.get("rulings/ny-n321134").json()
    assert d["id"] == "NY N321134" and d["codeAsQuoted"] == "9617.00.1000" and d["sourceUrl"].endswith("N321134")
    assert api.get("rulings/ny-n000000").status_code == 404
    page = api.get("rulings", q="tumbler").json()
    assert page["total"] >= 1 and page["items"][0]["key"]
    aid = classify(api).json()["id"]
    cmp = api.get("rulings/ny-n321134/compare", answerId=aid).json()
    assert cmp["citedAs"] == 1 and "177.9(b)(2)" in cmp["ruleQuote"] and cmp["alignment"]
    assert world.api("outsider").get("rulings/ny-n321134/compare", answerId=aid).status_code == 404


def test_tariff_sections_and_lines(world, fake_core):
    sections = Api().get("tariff/sections").json()
    assert len(sections) == 21 and sum(len(s["chapters"]) for s in sections) == 97
    assert any(c["reserved"] for s in sections for c in s["chapters"] if c["chapter"] == "77")
    api = world.api("importer")
    line = api.get("tariff/US/lines/9617.00.10.00").json()
    assert line["line"]["generalRate"] == "7.2%" and "Revision 3" in line["editionLabel"]
    assert api.get("tariff/US/lines/0101210000").status_code == 404
    assert api.get("tariff/XX/lines/9617").status_code == 404


def test_landed_cost_and_duty_layers(world, fake_core):
    api = world.api("importer")
    res = api.post(
        "landed-cost",
        {
            "country": "US",
            "code": "9617.00.10.00",
            "madeIn": "CN",
            "value": {"amount": "12500", "currency": "USD"},
            "quantity": 1000,
        },
    )
    assert res.status_code == 200 and res.json()["chargesTotal"]["amount"] == "900.00"
    assert res.json()["lines"][0]["source"] and res.json()["lines"][0]["effectiveFrom"]
    assert (
        api.post(
            "landed-cost", {"country": "US", "code": "96", "madeIn": "CN", "value": {"amount": "1", "currency": "USD"}}
        ).status_code
        == 422
    )
    assert api.get("duty-layers", country="US").status_code == 200


def test_verdict_by_depth_maps_onto_the_wire():
    from types import SimpleNamespace

    from tariffcompass.catalog.answers import verdict_depths

    ans = SimpleNamespace(verdict_by_depth=(("heading", "strong"), ("full_code", "broker"), ("chapter", "strong")))
    assert verdict_depths(ans) == [
        {"level": "heading", "level_label": "Heading", "word": "strong", "word_label": "Strong match"},
        {"level": "full_code", "level_label": "Full code", "word": "broker", "word_label": "Needs a broker"},
    ]
    assert verdict_depths(SimpleNamespace()) == []
