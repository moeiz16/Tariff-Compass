"""Who is asking, for which organisation, with which permissions: session auth, CSRF, RBAC and tenancy.

Every signed-in request gets a `Ctx` (`request.ctx`) holding the user, the active organisation and the
membership in it. Views declare the permission they need with `@requires("products:write")`; permissions
come from `platform.roles`, never role names. Tenancy: every domain query filters on `ctx.org`, and an id from
another organisation is a 404, never a 403.

Sessions are server-side Django sessions in the `tc_session` cookie. They end after 30 idle minutes or 12
hours, on the real wall clock (not the demo clock). Unsafe methods need the `X-CSRFToken` header.
"""

from __future__ import annotations

import inspect
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any, TypeVar

from django.conf import settings
from django.http import HttpRequest
from django.middleware.csrf import CsrfViewMiddleware

from tariffcompass.core.errors import Problem
from tariffcompass.platform import audit, limits, roles
from tariffcompass.platform.models import AuditEvent, Membership, Organisation, User

SESSION_USER = "_tc_user"
SESSION_ORG = "_tc_org"
SESSION_STARTED = "_tc_started"  # real epoch seconds
SESSION_SEEN = "_tc_seen"
SESSION_TOUCH_SECONDS = 60  # don't write the session row more than once a minute

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class Ctx:
    user: User
    org: Organisation | None
    membership: Membership | None
    permissions: frozenset[str] = field(default_factory=frozenset)
    ip: str = ""

    @property
    def role(self) -> str:
        return self.membership.role if self.membership else ""

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def need_org(self) -> Organisation:
        if self.org is None:
            raise Problem(403, "no_active_org", "Choose an organisation first.")
        return self.org

    def audit(
        self,
        action: str,
        summary: str,
        *,
        target_type: str = "",
        target_id: str = "",
        details: dict[str, Any] | None = None,
        org: Organisation | None = None,
    ) -> AuditEvent:
        return audit.record(
            org or self.org,
            action,
            summary,
            actor=self.user,
            actor_role=self.role,
            target_type=target_type,
            target_id=str(target_id),
            details=details,
            ip=self.ip,
        )


def client_ip(request: HttpRequest) -> str:
    return str(request.META.get("REMOTE_ADDR", ""))[:64]


def _no_view(request: HttpRequest) -> Any:
    return None


def enforce_csrf(request: HttpRequest) -> None:
    """Django's own CSRF check (Ninja views are exempt from the middleware): header must match the cookie."""
    if request.method not in UNSAFE:
        return
    mw = CsrfViewMiddleware(_no_view)
    request.csrf_processing_done = False  # type: ignore[attr-defined]
    mw.process_request(request)
    if mw.process_view(request, _no_view, (), {}) is not None:
        raise Problem(403, "csrf_failed", "Refresh the page and try again.")


# ── Session lifetime (real wall clock) ───────────────────────────────────────────────────────────────────
def idle_seconds() -> int:
    return int(settings.SESSION_IDLE_MINUTES) * 60


def absolute_seconds() -> int:
    return int(settings.SESSION_ABSOLUTE_HOURS) * 3600


def session_times(request: HttpRequest) -> dict[str, datetime]:
    started = float(request.session.get(SESSION_STARTED, time.time()))
    seen = float(request.session.get(SESSION_SEEN, time.time()))
    absolute = started + absolute_seconds()
    expires = min(seen + idle_seconds(), absolute)
    return {
        "expires_at": datetime.fromtimestamp(expires, UTC),
        "absolute_expires_at": datetime.fromtimestamp(absolute, UTC),
    }


def start_session(request: HttpRequest, user: User, org: Organisation | None) -> None:
    request.session.cycle_key()
    now = time.time()
    request.session[SESSION_USER] = str(user.pk)
    request.session[SESSION_ORG] = str(org.pk) if org else None
    request.session[SESSION_STARTED] = now
    request.session[SESSION_SEEN] = now
    request.session.set_expiry(idle_seconds())


def end_session(request: HttpRequest) -> None:
    request.session.flush()


def touch(request: HttpRequest, *, force: bool = False) -> None:
    now = time.time()
    if force or now - float(request.session.get(SESSION_SEEN, 0)) > SESSION_TOUCH_SECONDS:
        request.session[SESSION_SEEN] = now
        request.session.set_expiry(idle_seconds())


# ── Memberships ──────────────────────────────────────────────────────────────────────────────────────────
def memberships_of(user: User) -> list[Membership]:
    return list(
        Membership.objects.filter(user=user)
        .select_related("org", "engagement__broker_org")
        .order_by("created_at", "id")
    )


def default_org(user: User) -> Organisation | None:
    """Brokers land in their first client (where the docket lives); everyone else in their own organisation."""
    ms = memberships_of(user)
    if not ms:
        return None
    clients = [m for m in ms if m.engagement_id is not None]
    return (clients or ms)[0].org


def build_ctx(request: HttpRequest, user: User, org_id: str | None) -> Ctx:
    membership = None
    org = None
    if org_id and is_uuid(org_id):
        membership = (
            Membership.objects.filter(user=user, org__pk=uuid.UUID(org_id))
            .select_related("org", "engagement__broker_org")
            .first()
        )
        if membership is not None and (membership.engagement is None or membership.engagement.active):
            org = membership.org
        else:
            membership = None
    perms = roles.permissions_for(membership.role) if membership else frozenset()
    return Ctx(user=user, org=org, membership=membership, permissions=perms, ip=client_ip(request))


def resolve(request: HttpRequest) -> Ctx | None:
    """The signed-in context, or None for visitors. Raises `session_expired` for an ended session."""
    uid = request.session.get(SESSION_USER)
    if not uid:
        return None
    now = time.time()
    started = float(request.session.get(SESSION_STARTED, 0))
    seen = float(request.session.get(SESSION_SEEN, 0))
    if now - seen > idle_seconds() or now - started > absolute_seconds():
        end_session(request)
        raise Problem(401, "session_expired", "Your session ended. Sign in again to continue.")
    user = User.objects.filter(pk=uid, is_active=True).first()
    if user is None:
        end_session(request)
        return None
    ctx = build_ctx(request, user, request.session.get(SESSION_ORG))
    request.ctx = ctx  # type: ignore[attr-defined]
    return ctx


class SessionAuth:
    """Ninja auth callback: the session's user, with CSRF enforced on unsafe methods."""

    def __call__(self, request: HttpRequest) -> User | None:
        ctx = resolve(request)
        if ctx is None:
            return None
        enforce_csrf(request)
        limits.hit(request, "api")
        touch(request)
        return ctx.user


session_auth = SessionAuth()


def ctx_of(request: HttpRequest) -> Ctx:
    ctx = getattr(request, "ctx", None)
    if ctx is None:
        raise Problem(401, "not_authenticated", "Sign in to continue.")
    return ctx


def requires(permission: str, *, org: bool = True) -> Callable[[F], F]:
    """Check one permission (and an active organisation) before the view runs."""

    def deco(fn: F) -> F:
        @wraps(fn)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            ctx = ctx_of(request)
            if org:
                ctx.need_org()
            if not ctx.can(permission):
                raise Problem(403, "forbidden", "Your role doesn't allow this.")
            return fn(request, *args, **kwargs)

        return _keep_signature(wrapper, fn)

    return deco


def signed_in[F: Callable[..., Any]](fn: F) -> F:
    @wraps(fn)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        ctx_of(request)
        return fn(request, *args, **kwargs)

    return _keep_signature(wrapper, fn)


def _keep_signature[F: Callable[..., Any]](wrapper: Callable[..., Any], fn: F) -> F:
    """Ninja reads the view's parameters; resolve them in the view's own module, not this one."""
    wrapper.__signature__ = inspect.signature(fn, eval_str=True)  # type: ignore[attr-defined]
    return wrapper  # type: ignore[return-value]


def is_uuid(value: object) -> bool:
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True
