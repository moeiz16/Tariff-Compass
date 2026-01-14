from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def test_health_is_ok_and_carries_the_demo_now(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res["X-Tariff-Compass-Now"].startswith("2026-02-19T18:3")  # 10:30 PT is 18:30 UTC
    assert res["X-Request-ID"]
    assert res["X-Content-Type-Options"] == "nosniff"


def test_ready_checks_the_database(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["checks"]["database"] == "ok"


def test_meta_is_camel_case_with_labels_and_snapshot(client):
    body = client.get("/api/v1/meta").json()
    assert body["clock"]["today"] == "2026-02-19"
    assert body["clock"]["demoToday"] == "2026-02-19"
    assert body["snapshot"]["usHts"] == "HTSUS 2026 Revision 3"
    assert body["snapshot"]["label"] == "Tariffs as of Thu 19 Feb 2026"
    assert body["labels"]["verdicts"]["broker"] == "Needs a broker"
    assert {s["key"] for s in body["scopes"]} >= {"answer", "rulings", "review", "watch", "lab"}


def test_session_is_always_200_for_visitors(client):
    res = client.get("/api/v1/auth/session")
    assert res.status_code == 200
    body = res.json()
    assert body["me"] is None
    assert body["clock"]["timezone"] == "America/Vancouver"
    assert res["Cache-Control"] == "no-store"


def test_unknown_api_path_is_a_problem_document(client):
    res = client.get("/api/v1/nowhere")
    assert res.status_code == 404
    assert res["Content-Type"] == "application/problem+json"
    assert res.json()["code"] == "not_found"
    assert res["X-Tariff-Compass-Now"]


def test_metrics_exposes_prometheus_text(client):
    client.get("/health")
    res = client.get("/metrics")
    assert res.status_code == 200
    assert b"tc_http_requests_total" in res.content
