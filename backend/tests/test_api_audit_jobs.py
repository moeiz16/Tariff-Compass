"""The activity record (list, verify, CSV) and job progress (polling, SSE), with tenancy."""

from __future__ import annotations

import pytest

from tariffcompass.platform import audit
from tariffcompass.platform.models import AuditEvent, Job

pytestmark = pytest.mark.django_db


def test_audit_lists_newest_first_with_labels_and_fingerprints(world):
    audit.record(
        world.north,
        "product.created",
        "Added NB-KT-0412",
        actor=world.importer,
        actor_role="importer",
        target_type="product",
        target_id="x",
        details={"label": "NB-KT-0412"},
    )
    audit.record(world.other, "product.created", "Someone else's", actor=world.outsider)
    page = world.api("compliance").get("audit").json()
    assert page["total"] == 1 and page["items"][0]["actionLabel"] == "Added a product"
    item = page["items"][0]
    assert item["targetLabel"] == "NB-KT-0412" and len(item["fingerprint"]) == 14
    assert item["actorRoleLabel"] == "Importer"


@pytest.mark.parametrize(("who", "status"), [("compliance", 200), ("admin", 200), ("importer", 403), ("broker", 403)])
def test_audit_needs_audit_read(world, who, status):
    assert world.api(who).get("audit").status_code == status


def test_audit_filters(world):
    for i in range(3):
        audit.record(world.north, "review.approved", f"Approved {i}", target_type="product", target_id=str(i))
    audit.record(world.north, "settings.changed", "Changed settings")
    api = world.api("compliance")
    assert api.get("audit", action="review.approved").json()["total"] == 3
    assert api.get("audit", targetId="1").json()["total"] == 1
    assert api.get("audit", **{"from": "2026-02-19", "to": "2026-02-19"}).json()["total"] == 4
    assert api.get("audit", **{"from": "2026-02-20"}).json()["total"] == 0
    assert api.get("audit", **{"from": "not-a-date"}).status_code == 422
    assert api.get("audit", pageSize=2).json()["totalPages"] == 2


def test_verify_detects_tampering(world):
    for i in range(3):
        audit.record(world.north, "x.y", f"event {i}")
    api = world.api("compliance")
    ok = api.get("audit/verify").json()
    assert ok["ok"] and ok["events"] == 3 and ok["sentence"] == "Chain verified 19 Feb, 10:30"
    second = AuditEvent.objects.filter(org=world.north).order_by("id")[1]
    AuditEvent.objects.filter(pk=second.pk).update(summary="rewritten")
    bad = api.get("audit/verify").json()
    assert not bad["ok"] and bad["brokenAt"] == second.pk


def test_every_write_extends_the_chain(world):
    api = world.api("compliance")
    api.patch("settings", {"madeIn": "VN"})
    api.patch("settings", {"madeIn": "MX"})
    assert audit.verify(world.north).ok and audit.verify(world.north).events == 2


def test_csv_export(world):
    audit.record(world.north, "review.corrected", "=HYPERLINK(evil)", actor=world.broker, actor_role="broker")
    res = world.api("admin").get("audit/export.csv")
    assert res.status_code == 200 and res["Content-Type"].startswith("text/csv")
    text = res.content.decode()
    assert text.splitlines()[0].startswith("id,at,actor") and "'=HYPERLINK" in text
    assert "attachment" in res["Content-Disposition"]


def test_job_polling_and_tenancy(world):
    job = Job.objects.create(
        org=world.north, kind="watch_scan", status="running", progress=0.5, message="Checking 120 binders…"
    )
    body = world.api("importer").get(f"jobs/{job.pk}").json()
    assert body["statusLabel"] == "Working" and body["kindLabel"] == "Change check" and body["progress"] == 0.5
    assert world.api("outsider").get(f"jobs/{job.pk}").status_code == 404
    assert world.api("importer").get("jobs/not-a-uuid").status_code == 404


@pytest.mark.filterwarnings("ignore:StreamingHttpResponse must consume")
def test_job_sse_streams_done(world):
    job = Job.objects.create(
        org=world.north, kind="binder_export", status="succeeded", progress=1.0, result={"fileName": "x.pdf"}
    )
    res = world.api("importer").get(f"jobs/{job.pk}/events")
    assert res.status_code == 200 and res["Content-Type"] == "text/event-stream"
    body = b"".join(res).decode()
    assert "event: done" in body and '"fileName": "x.pdf"' in body and "id: 1" in body
    assert world.api("outsider").get(f"jobs/{job.pk}/events").status_code == 404
