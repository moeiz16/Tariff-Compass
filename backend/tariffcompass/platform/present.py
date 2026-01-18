"""Platform rows → wire dicts (users, organisations, memberships, `Me`). Labels come from `platform.roles`."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from tariffcompass.platform import roles
from tariffcompass.platform.context import Ctx, memberships_of, session_times
from tariffcompass.platform.models import Membership, Organisation, User

ORG_KIND_LABELS = dict(Organisation.KINDS)


def user_out(user: User) -> dict[str, Any]:
    return {
        "id": str(user.pk),
        "email": user.email,
        "full_name": user.full_name,
        "licence": user.licence,
        "avatar_color": user.avatar_color,
    }


def person_ref(user: User | None, role: str = "") -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": str(user.pk),
        "full_name": user.full_name,
        "role": role,
        "role_label": roles.ROLE_LABELS.get(role, ""),
        "licence": user.licence,
    }


def org_out(org: Organisation) -> dict[str, Any]:
    return {
        "id": str(org.pk),
        "name": org.name,
        "slug": org.slug,
        "kind": org.kind,
        "kind_label": ORG_KIND_LABELS.get(org.kind, org.kind),
        "locations": list(org.locations or []),
        "timezone": org.timezone,
        "is_sample": org.is_sample,
    }


def via_broker(m: Membership) -> str | None:
    return m.engagement.broker_org.name if m.engagement_id and m.engagement else None


def membership_out(m: Membership) -> dict[str, Any]:
    return {
        "role": m.role,
        "role_label": roles.ROLE_LABELS.get(m.role, m.role),
        "title": m.title,
        "permissions": sorted(roles.permissions_for(m.role)),
    }


def me_out(request: HttpRequest, ctx: Ctx) -> dict[str, Any]:
    orgs = [
        {
            "id": str(m.org.pk),
            "name": m.org.name,
            "kind": m.org.kind,
            "role": m.role,
            "role_label": roles.ROLE_LABELS.get(m.role, m.role),
            "via_broker": via_broker(m),
            "is_sample": m.org.is_sample,
        }
        for m in memberships_of(ctx.user)
        if m.engagement is None or m.engagement.active
    ]
    return {
        "user": user_out(ctx.user),
        "active_org": org_out(ctx.org) if ctx.org else None,
        "membership": membership_out(ctx.membership) if ctx.membership else None,
        "orgs": orgs,
        "session": session_times(request),
    }


def member_out(m: Membership) -> dict[str, Any]:
    return {
        "id": str(m.pk),
        "user": user_out(m.user),
        "role": m.role,
        "role_label": roles.ROLE_LABELS.get(m.role, m.role),
        "title": m.title,
        "via_broker": via_broker(m),
        "joined_at": m.created_at,
    }
