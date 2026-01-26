"""Organisation settings (API_CONTRACT §1.13): defaults for new questions and the records policy."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from tariffcompass.api.schemas.platform import OrgSettingsOut, OrgSettingsPatch
from tariffcompass.catalog.retention import CA_YEARS, US_YEARS, policy_sentence
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform.config import tc
from tariffcompass.platform.context import ctx_of, requires
from tariffcompass.platform.models import Engagement, Organisation

router = WireRouter()

DEFAULTS: dict[str, Any] = {"into": ["US", "CA"], "made_in": "CN", "ports": [], "always_send_to_broker": False}


def org_settings(org: Organisation) -> dict[str, Any]:
    return {**DEFAULTS, **(org.settings or {})}


def broker_name(org: Organisation) -> str | None:
    e = Engagement.objects.filter(importer_org=org, active=True).select_related("broker_org").first()
    return e.broker_org.name if e else None


def settings_out(org: Organisation) -> dict[str, Any]:
    s = org_settings(org)
    return {
        "into": s["into"],
        "made_in": s["made_in"],
        "ports": s["ports"],
        "always_send_to_broker": bool(s["always_send_to_broker"]),
        "retention_years": int(tc().get("RETENTION_YEARS", US_YEARS)),
        "retention_years_ca": CA_YEARS,
        "retention_note": policy_sentence(),
        "deleting_note": "Deleting hides a record; it is kept until its retention date, never destroyed early.",
        "broker_name": broker_name(org),
    }


@router.get("", response=OrgSettingsOut)
@requires("settings:read")
def get_settings(request: HttpRequest) -> dict:
    return settings_out(ctx_of(request).need_org())


@router.patch("", response=OrgSettingsOut)
@requires("settings:manage")
def patch_settings(request: HttpRequest, body: OrgSettingsPatch) -> dict:
    ctx = ctx_of(request)
    org = ctx.need_org()
    current = org_settings(org)
    patch = body.model_dump(exclude_none=True)
    if "made_in" in patch and not (len(patch["made_in"]) == 2 and patch["made_in"].isalpha()):
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "madeIn", "message": "Use a two-letter country code."}],
        )
    if "into" in patch and not patch["into"]:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "into", "message": "Choose at least one country."}],
        )
    changed = {k: [current.get(k), v] for k, v in patch.items() if current.get(k) != v}
    if changed:
        org.settings = {**(org.settings or {}), **patch}
        org.save(update_fields=["settings", "updated_at"])
        ctx.audit(
            "settings.changed",
            f"{ctx.user.full_name} changed {', '.join(_words(k) for k in changed)}",
            target_type="org",
            target_id=str(org.pk),
            details=changed,
        )
    return settings_out(org)


def _words(key: str) -> str:
    return {
        "into": "where it imports into",
        "made_in": "the usual origin",
        "ports": "the ports",
        "always_send_to_broker": "always sending to the broker",
    }.get(key, key)
