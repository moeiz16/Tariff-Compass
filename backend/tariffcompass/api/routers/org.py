"""Organisation: members, invitations, roles, your broker (API_CONTRACT §1.3). Every change is audited."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from ninja.responses import Status

from tariffcompass import clock
from tariffcompass.api.schemas.auth import (
    AcceptInvitationIn,
    EngagementOut,
    InvitationIn,
    InvitationOut,
    Me,
    MemberOut,
    MemberPatch,
    RoleOut,
)
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform import audit, limits, roles
from tariffcompass.platform.context import (
    build_ctx,
    ctx_of,
    enforce_csrf,
    is_uuid,
    requires,
    signed_in,
    start_session,
)
from tariffcompass.platform.models import Engagement, Invitation, Membership, Organisation, User
from tariffcompass.platform.passwords import check_strength
from tariffcompass.platform.present import me_out, member_out

router = WireRouter()
roles_router = WireRouter()
invitations_router = WireRouter()

INVITE_DAYS = 7
COUNTRIES_LABEL = {("CA", "US"): "US and Canadian entries", ("US",): "US entries", ("CA",): "Canadian entries"}


def token_hash(token: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


def _member(org: Organisation, member_id: str) -> Membership:
    m = (
        Membership.objects.filter(org=org, pk=member_id).select_related("user", "engagement__broker_org").first()
        if is_uuid(member_id)
        else None
    )
    if m is None:
        raise Problem(404, "not_found", "We couldn't find that person in this organisation.")
    return m


def _admins(org: Organisation) -> int:
    return Membership.objects.filter(org=org, role="admin").count()


def invitation_out(inv: Invitation, link: str | None = None) -> dict:
    return {
        "id": str(inv.pk),
        "email": inv.email,
        "role": inv.role,
        "role_label": roles.ROLE_LABELS.get(inv.role, inv.role),
        "expires_at": inv.expires_at,
        "invited_by": inv.invited_by.full_name if inv.invited_by else "",
        "link": link,
    }


@router.get("/members", response=list[MemberOut])
@requires("settings:read")
def members(request: HttpRequest) -> list[dict]:
    ctx = ctx_of(request)
    qs = Membership.objects.filter(org=ctx.org).select_related("user", "engagement__broker_org")
    return [member_out(m) for m in qs.order_by("created_at", "id")]


@router.patch("/members/{member_id}", response=MemberOut)
@requires("members:manage")
def patch_member(request: HttpRequest, member_id: str, body: MemberPatch) -> dict:
    ctx = ctx_of(request)
    org = ctx.need_org()
    m = _member(org, member_id)
    changes: dict[str, list[str]] = {}
    with transaction.atomic():
        if body.role is not None and body.role != m.role:
            if m.role == "admin" and _admins(org) <= 1:
                raise Problem(409, "last_admin", "An organisation needs at least one administrator.")
            changes["role"] = [m.role, body.role]
            m.role = body.role
        if body.title is not None and body.title != m.title:
            changes["title"] = [m.title, body.title]
            m.title = body.title[:120]
        if changes:
            m.save()
            ctx.audit(
                "member.changed",
                f"{ctx.user.full_name} changed {m.user.full_name}'s "
                + (f"role to {roles.ROLE_LABELS[m.role]}" if "role" in changes else "title"),
                target_type="member",
                target_id=str(m.pk),
                details=changes,
            )
    return member_out(m)


@router.delete("/members/{member_id}", response={204: None})
@requires("members:manage")
def remove_member(request: HttpRequest, member_id: str):
    ctx = ctx_of(request)
    org = ctx.need_org()
    m = _member(org, member_id)
    if m.role == "admin" and _admins(org) <= 1:
        raise Problem(409, "last_admin", "An organisation needs at least one administrator.")
    name = m.user.full_name
    m.delete()
    ctx.audit("member.removed", f"{ctx.user.full_name} removed {name}", target_type="member", target_id=member_id)
    return Status(204, None)


@router.get("/invitations", response=list[InvitationOut])
@requires("members:manage")
def invitations(request: HttpRequest) -> list[dict]:
    ctx = ctx_of(request)
    qs = Invitation.objects.filter(org=ctx.org, accepted_at__isnull=True, revoked_at__isnull=True)
    return [invitation_out(i) for i in qs.select_related("invited_by")]


@router.post("/invitations", response={201: InvitationOut})
@requires("members:manage")
def invite(request: HttpRequest, body: InvitationIn):
    ctx = ctx_of(request)
    org = ctx.need_org()
    email = body.email.strip().lower()
    if Membership.objects.filter(org=org, user__email=email).exists():
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "email", "message": "This person is already a member."}],
        )
    token = secrets.token_urlsafe(32)
    inv = Invitation.objects.create(
        org=org,
        email=email,
        role=body.role,
        token_hash=token_hash(token),
        expires_at=clock.now() + timedelta(days=INVITE_DAYS),
        invited_by=ctx.user,
    )
    ctx.audit(
        "member.invited",
        f"{ctx.user.full_name} invited {email} as {roles.ROLE_LABELS[body.role]}",
        target_type="invitation",
        target_id=str(inv.pk),
        details={"email": email, "role": body.role},
    )
    link = f"{settings.WEB_ORIGIN.rstrip('/')}/invite/{token}"
    return Status(201, invitation_out(inv, link))


@router.delete("/invitations/{invitation_id}", response={204: None})
@requires("members:manage")
def revoke_invitation(request: HttpRequest, invitation_id: str):
    ctx = ctx_of(request)
    inv = (
        Invitation.objects.filter(org=ctx.org, pk=invitation_id, accepted_at__isnull=True).first()
        if is_uuid(invitation_id)
        else None
    )
    if inv is None:
        raise Problem(404, "not_found", "We couldn't find that invitation.")
    inv.revoked_at = clock.now()
    inv.save(update_fields=["revoked_at"])
    ctx.audit(
        "member.invitation_revoked",
        f"{ctx.user.full_name} withdrew the invitation for {inv.email}",
        target_type="invitation",
        target_id=str(inv.pk),
    )
    return Status(204, None)


@router.get("/brokers", response=list[EngagementOut])
@requires("settings:read")
def brokers(request: HttpRequest) -> list[dict]:
    ctx = ctx_of(request)
    org = ctx.need_org()
    qs = Engagement.objects.filter(active=True).select_related("broker_org", "importer_org")
    qs = qs.filter(importer_org=org) | qs.filter(broker_org=org)
    out = []
    for e in qs.order_by("started_on"):
        people = Membership.objects.filter(engagement=e).select_related("user", "engagement__broker_org")
        countries = sorted(e.countries or [])
        out.append(
            {
                "id": str(e.pk),
                "broker_org": e.broker_org.name,
                "importer_org": e.importer_org.name,
                "countries": countries,
                "countries_label": COUNTRIES_LABEL.get(tuple(countries), "Entries"),
                "started_on": e.started_on,
                "people": [member_out(m) for m in people],
            }
        )
    return out


@roles_router.get("", response=list[RoleOut])
@signed_in
def role_list(request: HttpRequest) -> list[dict]:
    return [
        {
            "role": r,
            "role_label": roles.ROLE_LABELS[r],
            "description": roles.ROLE_DESCRIPTIONS[r],
            "permissions": sorted(roles.permissions_for(r)),
        }
        for r in roles.ROLES
    ]


@invitations_router.post("/{token}/accept", response=Me, auth=None)
def accept(request: HttpRequest, token: str, body: AcceptInvitationIn) -> dict:
    enforce_csrf(request)
    limits.hit(request, "auth")
    inv = Invitation.objects.filter(token_hash=token_hash(token), revoked_at__isnull=True).select_related("org").first()
    if inv is None or inv.accepted_at is not None:
        raise Problem(404, "not_found", "This invitation isn't valid.")
    if inv.expires_at < clock.now():
        raise Problem(410, "expired", "This invitation has expired. Ask for a new one.")
    with transaction.atomic():
        user = User.objects.filter(email=inv.email).first()
        if user is None:
            if not body.full_name or not body.password:
                raise Problem(
                    422,
                    "validation_error",
                    "One or more fields are invalid.",
                    errors=[
                        {"field": "fullName", "message": "Tell us your name."},
                        {"field": "password", "message": "Choose a password."},
                    ],
                )
            check_strength(body.password, email=inv.email, full_name=body.full_name)
            user = User.objects.create_user(inv.email, body.password, full_name=body.full_name.strip())
        Membership.objects.get_or_create(org=inv.org, user=user, defaults={"role": inv.role})
        inv.accepted_at = clock.now()
        inv.save(update_fields=["accepted_at"])
        audit.record(
            inv.org,
            "member.joined",
            f"{user.full_name} joined as {roles.ROLE_LABELS[inv.role]}",
            actor=user,
            actor_role=inv.role,
            target_type="invitation",
            target_id=str(inv.pk),
        )
    start_session(request, user, inv.org)
    ctx = build_ctx(request, user, str(inv.org.pk))
    request.ctx = ctx  # type: ignore[attr-defined]
    return me_out(request, ctx)
