"""Auth and session (API_CONTRACT §1.2). `GET /auth/session` is always 200.

Sign-in, demo sign-in, sign-out, refresh, switch-org and password change are completed by the platform
workstream; the session endpoint is here first so the web shell can render public pages.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest

from tariffcompass import clock
from tariffcompass.api.schemas.auth import SessionOut
from tariffcompass.api.schemas.common import ClockOut
from tariffcompass.core.wire import WireRouter

router = WireRouter()


@router.get("/session", response=SessionOut, auth=None)
def session(request: HttpRequest) -> dict:
    return {
        "me": None,
        "clock": ClockOut(**clock.describe()),
        "demo_sign_in": bool(settings.TARIFF_COMPASS["DEMO_SIGN_IN"]),
        "demo_people": [],
    }
