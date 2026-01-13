"""Request context (request id, access log, metrics), the demo-clock header and security headers.

All middlewares are sync+async capable so SSE streaming responses under ASGI are not buffered.
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.http import HttpRequest, HttpResponseBase

from tariffcompass import clock
from tariffcompass.core.logging import request_id_ctx
from tariffcompass.core.metrics import HTTP_LATENCY, HTTP_REQUESTS

log = structlog.get_logger("tariffcompass.access")

NOW_HEADER = "X-Tariff-Compass-Now"
_RID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_ID_RE = re.compile(r"/[0-9a-fA-F-]{32,36}(?=/|$)")
_SKU_RE = re.compile(r"/(products|rulings|review|jobs)/[^/]+")
_QUIET = ("/health", "/health/ready", "/metrics")

Handler = Callable[[HttpRequest], HttpResponseBase] | Callable[[HttpRequest], Awaitable[HttpResponseBase]]


def route_label(path: str) -> str:
    """Low-cardinality route label for metrics (ids, SKUs and ruling numbers collapsed)."""
    return _SKU_RE.sub(r"/\1/{id}", _ID_RE.sub("/{id}", path))


class _Hybrid:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response: Handler) -> None:
        self.get_response = get_response
        self._async = iscoroutinefunction(get_response)
        if self._async:
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest):  # a response, or a coroutine under ASGI
        if self._async:
            return self._acall(request)
        self.before(request)
        response = self.get_response(request)
        return self.after(request, response)  # type: ignore[arg-type]

    async def _acall(self, request: HttpRequest) -> HttpResponseBase:
        self.before(request)
        response = await self.get_response(request)  # type: ignore[misc]
        return self.after(request, response)

    def before(self, request: HttpRequest) -> None: ...

    def after(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        return response


class RequestContextMiddleware(_Hybrid):
    """Assigns or propagates `X-Request-ID`, binds it to logs, records metrics and one access-log line."""

    def before(self, request: HttpRequest) -> None:
        incoming = request.headers.get("X-Request-ID", "")
        rid = incoming if _RID_RE.match(incoming) else uuid.uuid4().hex
        request.request_id = rid  # type: ignore[attr-defined]
        request._rid_token = request_id_ctx.set(rid)  # type: ignore[attr-defined]
        request._started = time.perf_counter()  # type: ignore[attr-defined]

    def after(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        response["X-Request-ID"] = request.request_id  # type: ignore[attr-defined]
        elapsed = time.perf_counter() - request._started  # type: ignore[attr-defined]
        label = route_label(request.path)
        HTTP_REQUESTS.labels(request.method, label, str(response.status_code)).inc()
        HTTP_LATENCY.labels(request.method, label).observe(elapsed)
        if not request.path.endswith(_QUIET):
            log.info(
                "request", method=request.method, path=label, status=response.status_code, ms=round(elapsed * 1000, 1)
            )
        request_id_ctx.reset(request._rid_token)  # type: ignore[attr-defined]
        return response


class ClockHeaderMiddleware(_Hybrid):
    """Every response says what time the server thinks it is (the demo clock), as ISO-8601 UTC."""

    def after(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        response[NOW_HEADER] = clock.now_iso()
        return response


_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# Printable binder pages: inline styles only, no scripts.
_DOC_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'self'"


class SecurityHeadersMiddleware(_Hybrid):
    """Strict headers on every response; API JSON is never cached unless a view sets Cache-Control."""

    def after(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        is_doc = response.get("Content-Type", "").startswith("text/html")
        response.setdefault("Content-Security-Policy", _DOC_CSP if is_doc else _API_CSP)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "same-origin")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        response.setdefault("X-Frame-Options", "SAMEORIGIN" if is_doc else "DENY")
        if getattr(settings, "IS_PROD", False):
            response.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.path.startswith("/api/") and "Cache-Control" not in response:
            response["Cache-Control"] = "no-store"
        return response
