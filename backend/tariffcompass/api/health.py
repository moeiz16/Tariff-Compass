"""Liveness, readiness and Prometheus metrics (outside /api/v1, no auth, quiet in the access log)."""

from __future__ import annotations

from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from tariffcompass import __version__, clock


def _db_ok() -> bool:
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        return False


def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok", "version": __version__, "now": clock.now_iso(), "checks": {}})


def ready(request: HttpRequest) -> JsonResponse:
    db = _db_ok()
    body = {
        "status": "ok" if db else "degraded",
        "version": __version__,
        "now": clock.now_iso(),
        "checks": {"database": "ok" if db else "unreachable"},
    }
    return JsonResponse(body, status=200 if db else 503)


def metrics(request: HttpRequest) -> HttpResponse:
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
