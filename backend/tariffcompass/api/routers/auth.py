"""Auth and session (API_CONTRACT §1.2). `GET /auth/session` is always 200.

Cookie sessions (`tc_session`) with CSRF (`tc_csrf` echoed in `X-CSRFToken`). Sign-in failures are generic and
counted per email; five in 15 minutes pause that email (`423`). Demo sign-in by role exists only while the
sample organisation is seeded and `DEMO_SIGN_IN` is on.
"""

from __future__ import annotations

from functools import cache

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.sessions.models import Session
from django.db import transaction
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.utils.text import slugify
from ninja.responses import Status

from tariffcompass import clock
from tariffcompass.api.schemas.auth import (
    DemoSignInIn,
    LoginIn,
    Me,
    PasswordIn,
    SessionOut,
    SessionTimes,
    SignupIn,
    SwitchOrgIn,
)
from tariffcompass.api.schemas.common import ClockOut
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform import audit, limits, roles
from tariffcompass.platform.context import (
    SESSION_ORG,
    SESSION_USER,
    build_ctx,
    client_ip,
    ctx_of,
    default_org,
    end_session,
    enforce_csrf,
    is_uuid,
    resolve,
    session_times,
    start_session,
    touch,
)
from tariffcompass.platform.models import Membership, Organisation, User
from tariffcompass.platform.passwords import check_strength
from tariffcompass.platform.present import me_out
from tariffcompass.seed.people import DEMO_PEOPLE, SAMPLE_IMPORTER_SLUG

router = WireRouter()


@cache
def _dummy_hash() -> str:
    """Hash checked when the email is unknown, so a miss costs the same time as a wrong password."""
    return make_password("not-a-real-password-tariff-compass")


def _demo_on() -> bool:
    return (
        bool(settings.TARIFF_COMPASS["DEMO_SIGN_IN"])
        and Organisation.objects.filter(slug=SAMPLE_IMPORTER_SLUG, is_sample=True).exists()
    )


def _signed_in(request: HttpRequest, user: User, *, org: Organisation | None = None) -> dict:
    org = org or default_org(user)
    start_session(request, user, org)
    ctx = build_ctx(request, user, str(org.pk) if org else None)
    request.ctx = ctx  # type: ignore[attr-defined]
    ctx.audit("auth.login", f"{user.full_name} signed in", target_type="user", target_id=str(user.pk))
    return me_out(request, ctx)


@router.get("/csrf", response={204: None}, auth=None)
def csrf(request: HttpRequest):
    get_token(request)
    return Status(204, None)


@router.get("/session", response=SessionOut, auth=None)
def session(request: HttpRequest) -> dict:
    me = None
    try:
        ctx = resolve(request)
    except Problem:
        ctx = None  # ended session: the visitor view (always 200)
    if ctx is not None:
        me = me_out(request, ctx)
    demo = _demo_on()
    people = []
    if demo:
        orgs = {o.slug: o for o in Organisation.objects.filter(is_sample=True)}
        for role, p in DEMO_PEOPLE.items():
            o = orgs.get(p["org_slug"])
            if o and User.objects.filter(email=p["email"]).exists():
                people.append(
                    {
                        "role": role,
                        "role_label": roles.ROLE_LABELS[role],
                        "full_name": p["full_name"],
                        "title": p["title"],
                        "org_name": o.name,
                    }
                )
    return {"me": me, "clock": ClockOut(**clock.describe()), "demo_sign_in": demo, "demo_people": people}


@router.post("/login", response=Me, auth=None)
def login(request: HttpRequest, body: LoginIn) -> dict:
    enforce_csrf(request)
    limits.hit(request, "auth")
    email = body.email.strip().lower()
    limits.check_paused(email)
    user = User.objects.filter(email=email, is_active=True).first()
    ok = check_password(body.password, user.password if user else _dummy_hash())
    if not (user and ok):
        left = limits.record_failure(email, client_ip(request))
        if user is not None:
            org = default_org(user)
            audit.record(
                org,
                "auth.login_failed",
                "A sign-in with a wrong password",
                actor=user,
                target_type="user",
                target_id=str(user.pk),
                ip=client_ip(request),
            )
        if left == 0:
            limits.check_paused(email)
        raise Problem(
            401,
            "invalid_credentials",
            f"That email and password didn't match. {left} tries left before we pause sign-in for this email "
            f"for {limits.PAUSE_MINUTES} minutes.",
            tries_left=left,
        )
    limits.clear_failures(email)
    return _signed_in(request, user)


@router.post("/demo", response=Me, auth=None)
def demo(request: HttpRequest, body: DemoSignInIn) -> dict:
    enforce_csrf(request)
    limits.hit(request, "auth")
    if not _demo_on():
        raise Problem(404, "not_found", "Demo sign-in isn't available here.")
    person = DEMO_PEOPLE[body.role]
    user = User.objects.filter(email=person["email"], is_active=True).first()
    if user is None:
        raise Problem(404, "not_found", "Demo sign-in isn't available here.")
    return _signed_in(request, user)


@router.post("/signup", response={201: Me}, auth=None)
def signup(request: HttpRequest, body: SignupIn):
    enforce_csrf(request)
    limits.hit(request, "auth")
    email = body.email.strip().lower()
    check_strength(body.password, email=email, full_name=body.full_name)
    if User.objects.filter(email=email).exists():
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "email", "message": "An account with this email already exists. Sign in instead."}],
        )
    with transaction.atomic():
        user = User.objects.create_user(email, body.password, full_name=body.full_name.strip())
        base = slugify(body.org_name)[:60] or "org"
        slug, i = base, 1
        while Organisation.objects.filter(slug=slug).exists():
            i += 1
            slug = f"{base}-{i}"
        org = Organisation.objects.create(name=body.org_name.strip(), slug=slug, kind=body.kind)
        Membership.objects.create(org=org, user=user, role="admin", title="Administrator")
        audit.record(
            org,
            "org.created",
            f"{user.full_name} created {org.name}",
            actor=user,
            actor_role="admin",
            target_type="org",
            target_id=str(org.pk),
        )
    return Status(201, _signed_in(request, user, org=org))


@router.post("/logout", response={204: None})
def logout(request: HttpRequest):
    ctx = ctx_of(request)
    ctx.audit("auth.logout", f"{ctx.user.full_name} signed out", target_type="user", target_id=str(ctx.user.pk))
    end_session(request)
    return Status(204, None)


@router.post("/refresh", response=SessionTimes)
def refresh(request: HttpRequest) -> dict:
    touch(request, force=True)
    return session_times(request)


@router.post("/switch-org", response=Me)
def switch_org(request: HttpRequest, body: SwitchOrgIn) -> dict:
    ctx = ctx_of(request)
    m = (
        Membership.objects.filter(user=ctx.user, org_id=body.org_id).select_related("org", "engagement").first()
        if is_uuid(body.org_id)
        else None
    )
    if m is None or (m.engagement is not None and not m.engagement.active):
        raise Problem(404, "not_found", "You aren't a member of that organisation.")
    request.session[SESSION_ORG] = str(m.org.pk)
    new = build_ctx(request, ctx.user, str(m.org.pk))
    request.ctx = new  # type: ignore[attr-defined]
    new.audit(
        "auth.org_switched",
        f"{ctx.user.full_name} switched to {m.org.name}",
        target_type="org",
        target_id=str(m.org.pk),
    )
    return me_out(request, new)


@router.post("/password", response={204: None})
def password(request: HttpRequest, body: PasswordIn):
    ctx = ctx_of(request)
    if not ctx.user.check_password(body.current_password):
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "currentPassword", "message": "That isn't your current password."}],
        )
    check_strength(body.new_password, email=ctx.user.email, full_name=ctx.user.full_name, field="newPassword")
    ctx.user.set_password(body.new_password)
    ctx.user.save(update_fields=["password"])
    current = request.session.session_key
    uid = str(ctx.user.pk)
    for s in Session.objects.exclude(session_key=current).iterator():
        if s.get_decoded().get(SESSION_USER) == uid:
            s.delete()
    ctx.audit(
        "auth.password_changed", f"{ctx.user.full_name} changed their password", target_type="user", target_id=uid
    )
    return Status(204, None)
