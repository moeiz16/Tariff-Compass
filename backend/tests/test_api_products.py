"""Products, the binder (revision matrix, retention, record) and exports: RBAC, tenancy and the audit chain."""

from __future__ import annotations

import io
import zipfile
from datetime import date

import pytest

from tariffcompass.catalog import binder, retention
from tariffcompass.catalog.models import Entry, Product
from tariffcompass.platform import audit
from tariffcompass.platform.models import AuditEvent, Job

pytestmark = pytest.mark.django_db


def _pdf() -> bytes:
    from tariffcompass.seed import documents

    return documents.spec_sheet("NB-KT-0412")[1]


PDF = _pdf()


def test_list_is_tenant_scoped_paged_and_filtered(world, catalogue):
    api = world.api("importer")
    page = api.get("products").json()
    assert page["total"] == 1 and page["items"][0]["sku"] == "NB-KT-0412"
    item = page["items"][0]
    assert item["usCode"] == "9617.00.10.00" and item["standingLabel"] == "Proposed" and item["versions"] == 1
    assert api.get("products", q="tumbler").json()["total"] == 1
    assert api.get("products", q="9617").json()["total"] == 1
    assert api.get("products", category="apparel").json()["total"] == 0
    assert world.api("outsider").get("products").json()["items"][0]["sku"] == "HH-0001"


def test_foreign_product_is_404_everywhere(world, catalogue):
    api = world.api("compliance")
    for path in ("products/HH-0001", "products/HH-0001/binder", f"products/{catalogue['foreign'].pk}"):
        assert api.get(path).status_code == 404, path
    assert api.patch("products/HH-0001", {"title": "x"}).status_code == 404
    assert api.delete("products/HH-0001").status_code == 404
    assert api.post("products/HH-0001/binder/export", {"format": "pdf"}).status_code == 404


@pytest.mark.parametrize(("who", "status"), [("importer", 201), ("compliance", 201), ("broker", 403), ("admin", 403)])
def test_create_needs_products_write(world, catalogue, who, status):
    res = world.api(who).post(
        "products", {"sku": f"nb-x-{who}", "title": "Trail mug", "category": "kitchen", "madeIn": "VN"}
    )
    assert res.status_code == status
    if status == 201:
        assert res.json()["sku"] == f"NB-X-{who.upper()}"
        assert AuditEvent.objects.filter(action="product.created").exists()


def test_duplicate_sku_and_validation(world, catalogue):
    api = world.api("importer")
    dup = api.post("products", {"sku": "NB-KT-0412", "title": "Again", "category": "kitchen", "madeIn": "CN"})
    assert dup.status_code == 422 and dup.json()["errors"][0]["field"] == "sku"
    bad = api.post("products", {"sku": "X1", "title": "Y", "category": "spaceships", "madeIn": "CN"})
    assert bad.status_code == 422 and bad.json()["code"] == "validation_error"


def test_patch_and_hide_keep_the_record(world, catalogue):
    api = world.api("importer")
    res = api.patch(
        "products/NB-KT-0412", {"title": "20 oz tumbler", "unitValue": {"amount": "12.5", "currency": "USD"}}
    )
    assert res.json()["title"] == "20 oz tumbler" and res.json()["unitValue"]["amount"] == "12.50"
    assert api.delete("products/NB-KT-0412").status_code == 204
    assert api.get("products/NB-KT-0412").status_code == 404
    assert Product.objects.filter(sku="NB-KT-0412").exists()  # hidden, not deleted
    ev = AuditEvent.objects.get(action="product.hidden")
    assert "kept until" in ev.summary and ev.details["keptUntil"] >= "2031-02-19"


def test_binder_matrix_marks_changes_and_ditto(world, catalogue):
    p = catalogue["tumbler"]
    binder.append(
        p,
        "question_answered",
        actor=world.importer,
        actor_role="importer",
        deciding_fact={
            "key": "between_walls",
            "label": "Between the walls",
            "value": "A vacuum",
            "source_note": "confirmed by the supplier",
        },
        why="Supplier confirmed.",
    )
    binder.append(p, "approved", actor=world.broker, actor_role="broker", standing="approved", why="Vacuum-sealed.")
    b = world.api("importer").get("products/NB-KT-0412/binder").json()
    v1, v2, v3 = b["versions"]
    assert v1["changed"] == [] and not v1["current"] and v3["current"]
    assert "decidingFact" in v2["changed"] and "usCode" not in v2["changed"]
    assert set(v3["changed"]) >= {"standing", "decidedBy"}
    assert v3["decidedBy"]["fullName"] == "Dana Whitlock" and v3["decidedBy"]["roleLabel"] == "Licensed customs broker"
    assert b["approval"]["version"] == 3 and "Approved by Dana Whitlock" in b["approval"]["sentence"]
    assert "Driftwood" in b["approval"]["sentence"]
    assert all(len(v["fingerprint"]) == 14 for v in b["versions"])
    assert b["record"]["chainVerified"] and b["record"]["events"] == 3
    assert b["advanceRuling"] and "D11-11-3" in b["advanceRuling"]


def test_binder_versions_link_to_the_audit_chain(world, catalogue):
    p = catalogue["tumbler"]
    v = p.versions.get(n=1)
    assert v.audit_event is not None and v.audit_event.target_id == str(p.pk)
    assert audit.verify(world.north).ok


def test_retention_takes_the_longer_rule():
    assert retention.kept_until(
        entries=[("US", date(2026, 2, 16))], last_decision=date(2026, 2, 17), into=["US", "CA"]
    ) == (date(2031, 2, 16), retention.US_RULE)
    until, rule = retention.kept_until(
        entries=[("US", date(2026, 2, 16)), ("CA", date(2026, 2, 10))],
        last_decision=date(2026, 2, 17),
        into=["US", "CA"],
    )
    assert (until, rule) == (date(2032, 2, 10), retention.CA_RULE)
    assert retention.kept_until(entries=[], last_decision=date(2026, 2, 19), into=["US"])[0] == date(2031, 2, 19)
    assert retention.kept_until(entries=[], last_decision=date(2026, 2, 19), into=["US", "CA"])[0] == date(2032, 2, 19)
    assert retention.add_years(date(2028, 2, 29), 5) == date(2033, 2, 28)


def test_binder_shows_entries_and_both_retention_rules(world, catalogue):
    p = catalogue["tumbler"]
    Entry.objects.create(
        org=world.north,
        product=p,
        entry_number="DW3-0412871-4",
        country="US",
        entered_on=date(2026, 2, 2),
        code="9617001000",
        duty_paid="3458.93",
    )
    Entry.objects.create(
        org=world.north,
        product=p,
        entry_number="13952-0412",
        country="CA",
        entered_on=date(2026, 2, 10),
        code="9617000000",
        duty_paid="1284.38",
        currency="CAD",
    )
    b = world.api("importer").get("products/NB-KT-0412/binder").json()
    assert b["keptUntil"] == "2032-02-10" and "D17-1-21" in b["retentionNote"]
    assert {e["country"] for e in b["entries"]} == {"US", "CA"}
    assert b["entries"][0]["dutyPaid"]["currency"] in {"USD", "CAD"}


def test_evidence_upload_checks_type_and_size(world, catalogue, settings):
    api = world.api("importer")
    url = "/api/v1/products/NB-KT-0412/evidence"
    ok = api.c.post(url, {"file": io.BytesIO(PDF), "kind": "spec_sheet"}, HTTP_X_CSRFTOKEN=api.csrf)
    assert ok.status_code == 201, ok.content
    assert ok.json()["kindLabel"] == "Spec sheet" and len(ok.json()["sha256"]) == 64
    exe = io.BytesIO(b"MZ\x90\x00not a pdf")
    exe.name = "tool.pdf"
    bad = api.c.post(url, {"file": exe}, HTTP_X_CSRFTOKEN=api.csrf)
    assert bad.status_code == 415 and bad.json()["code"] == "unsupported_media_type"
    settings.MAX_UPLOAD_MB = 0
    big = api.c.post(url, {"file": io.BytesIO(PDF)}, HTTP_X_CSRFTOKEN=api.csrf)
    assert big.status_code == 413
    assert world.api("broker").c.post(url, {"file": io.BytesIO(PDF)}, HTTP_X_CSRFTOKEN=api.csrf).status_code in (
        401,
        403,
    )


@pytest.mark.parametrize("fmt", ["pdf", "zip"])
def test_export_job_produces_a_file_with_the_record_fingerprint(world, catalogue, fmt):
    api = world.api("importer")
    res = api.post("products/NB-KT-0412/binder/export", {"format": fmt})
    assert res.status_code == 202
    accepted = res.json()
    job = api.get(accepted["statusUrl"]).json()
    assert job["status"] == "succeeded", job
    result = job["result"]
    assert result["fileName"].endswith(f".{fmt}") and "path" not in result
    assert len(result["recordFingerprint"]) == 14
    dl = api.get(result["downloadUrl"])
    assert dl.status_code == 200
    body = b"".join(dl.streaming_content)
    if fmt == "pdf":
        assert body.startswith(b"%PDF") and result["pages"] >= 1
    else:
        names = zipfile.ZipFile(io.BytesIO(body)).namelist()
        assert "MANIFEST.txt" in names and "activity.csv" in names and any(n.endswith(".pdf") for n in names)
    assert AuditEvent.objects.filter(action="binder.exported").exists()
    assert audit.verify(world.north).ok


def test_export_download_is_tenant_scoped(world, catalogue):
    api = world.api("importer")
    job_id = api.post("products/NB-KT-0412/binder/export", {"format": "pdf"}).json()["jobId"]
    from tariffcompass.platform.models import User
    from tests.platform_fixtures import Api

    kim = User.objects.get(email="kim@hh.example")  # compliance in the other importer: has binder:export
    assert Api().sign_in(kim, world.other).get(f"exports/{job_id}/download").status_code == 404
    assert world.api("admin").get(f"exports/{job_id}/download").status_code == 403  # no binder:export
    pending = Job.objects.create(org=world.north, kind="binder_export", status="running")
    assert api.get(f"exports/{pending.pk}/download").status_code == 404
