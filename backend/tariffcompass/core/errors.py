"""RFC 7807 problem details for every error (docs/API_CONTRACT.md §1.1 Errors).

Views raise `Problem(...)` (or one of the helpers); `install(api)` maps Ninja/Django exceptions to the same
shape so the web app handles exactly one error format: `application/problem+json` with a stable `code`.
"""

from __future__ import annotations

from typing import Any

import structlog
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, JsonResponse
from ninja.errors import AuthenticationError, HttpError, ValidationError
from ninja.errors import Throttled as NinjaThrottled
from pydantic.alias_generators import to_camel

log = structlog.get_logger("tariffcompass.errors")

PROBLEM_BASE = "https://tariffcompass.dev/problems/"
CONTENT_TYPE = "application/problem+json"

TITLES: dict[str, str] = {
    "bad_request": "Bad request",
    "not_authenticated": "Sign in to continue",
    "session_expired": "Your session ended",
    "invalid_credentials": "That email and password didn't match",
    "sign_in_paused": "Sign-in is paused for this email",
    "forbidden": "You don't have access to this",
    "csrf_failed": "Security check failed",
    "no_active_org": "Choose an organisation first",
    "not_found": "Not found",
    "not_in_demo": "The public demo only knows the sample products",
    "last_admin": "An organisation needs at least one administrator",
    "conflict": "That changed while you were looking",
    "already_decided": "Someone already decided this item",
    "stale_version": "This record has a newer version",
    "needs_second_signature": "A second person must sign",
    "same_person": "The second signature must come from someone else",
    "gates_failed": "This training round didn't pass its checks",
    "expired": "This link has expired",
    "payload_too_large": "That file is too large",
    "unsupported_media_type": "That file type isn't supported",
    "validation_error": "Some fields need attention",
    "weak_password": "Choose a stronger password",
    "unknown_code": "That code isn't in the tariff",
    "rate_limited": "Too many requests",
    "not_implemented": "Not available yet",
    "internal_error": "Something went wrong on our side",
    "unavailable": "A service we depend on is unavailable",
}


class Problem(Exception):
    """Raise from any view: becomes an RFC 7807 response with a stable `code`."""

    def __init__(
        self,
        status: int,
        code: str,
        detail: str = "",
        *,
        title: str | None = None,
        errors: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(detail or code)
        self.status, self.code, self.detail = status, code, detail
        self.title = title or TITLES.get(code, code.replace("_", " ").capitalize())
        self.errors, self.headers, self.extra = errors, headers or {}, extra


def not_found(detail: str = "We couldn't find that.") -> Problem:
    return Problem(404, "not_found", detail)


def forbidden(detail: str = "Your role doesn't allow this.") -> Problem:
    return Problem(403, "forbidden", detail)


def conflict(code: str, detail: str) -> Problem:
    return Problem(409, code, detail)


def problem_response(request: HttpRequest | None, p: Problem) -> JsonResponse:
    body: dict[str, Any] = {
        "type": PROBLEM_BASE + p.code,
        "title": p.title,
        "status": p.status,
        "code": p.code,
        "detail": p.detail,
    }
    if p.errors:
        body["errors"] = p.errors
    body.update({to_camel(k): v for k, v in p.extra.items()})
    if request is not None and getattr(request, "request_id", None):
        body["requestId"] = request.request_id  # type: ignore[attr-defined]
    resp = JsonResponse(body, status=p.status, content_type=CONTENT_TYPE)
    for k, v in p.headers.items():
        resp[k] = v
    return resp


def _field_errors(exc: ValidationError) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for err in exc.errors:
        loc = [str(x) for x in err.get("loc", ()) if x not in ("body", "query", "path", "form", "payload")]
        out.append({"field": ".".join(to_camel(x) for x in loc) or "body", "message": str(err.get("msg", "Invalid"))})
    return out


def install(api: Any) -> None:
    """Register the problem handlers on a NinjaAPI instance."""

    @api.exception_handler(Problem)
    def _problem(request: HttpRequest, exc: Problem) -> JsonResponse:
        return problem_response(request, exc)

    @api.exception_handler(ValidationError)
    def _validation(request: HttpRequest, exc: ValidationError) -> JsonResponse:
        return problem_response(
            request, Problem(422, "validation_error", "One or more fields are invalid.", errors=_field_errors(exc))
        )

    @api.exception_handler(AuthenticationError)
    def _auth(request: HttpRequest, exc: AuthenticationError) -> JsonResponse:
        return problem_response(request, Problem(401, "not_authenticated", "Sign in to continue."))

    @api.exception_handler(NinjaThrottled)
    def _throttled(request: HttpRequest, exc: NinjaThrottled) -> JsonResponse:
        wait = int(getattr(exc, "wait", 0) or 60)
        return problem_response(
            request, Problem(429, "rate_limited", "Slow down a little.", headers={"Retry-After": str(wait)})
        )

    @api.exception_handler(Http404)
    def _404(request: HttpRequest, exc: Http404) -> JsonResponse:
        return problem_response(request, not_found())

    @api.exception_handler(PermissionDenied)
    def _403(request: HttpRequest, exc: PermissionDenied) -> JsonResponse:
        return problem_response(request, forbidden())

    @api.exception_handler(HttpError)
    def _http(request: HttpRequest, exc: HttpError) -> JsonResponse:
        code = {
            400: "bad_request",
            401: "not_authenticated",
            403: "forbidden",
            404: "not_found",
            405: "bad_request",
            409: "conflict",
            413: "payload_too_large",
            415: "unsupported_media_type",
            429: "rate_limited",
            501: "not_implemented",
        }.get(exc.status_code, "bad_request")
        return problem_response(request, Problem(exc.status_code, code, str(exc)))

    @api.exception_handler(Exception)
    def _500(request: HttpRequest, exc: Exception) -> JsonResponse:
        log.exception("unhandled_error", path=request.path)
        return problem_response(request, Problem(500, "internal_error", "We logged it with this request id."))


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    return problem_response(request, Problem(403, "csrf_failed", "Refresh the page and try again."))


def handler404(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return problem_response(request, not_found())


def handler500(request: HttpRequest) -> JsonResponse:
    return problem_response(request, Problem(500, "internal_error", "We logged it with this request id."))
