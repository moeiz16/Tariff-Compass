"""Rate limits and the sign-in pause (API_CONTRACT §1.1 Rate limits). Both use the real wall clock.

Limits are a sliding window per minute, per user (or IP when signed out), kept in the process cache:
`auth` 10, `public` 20, `classify` 30, `api` 300. A sign-in pauses one email for 15 minutes after five failures
within 15 minutes (`423 sign_in_paused`), counted in `LoginFailure` so every process agrees.
"""

from __future__ import annotations

import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest

from tariffcompass import clock
from tariffcompass.core.errors import Problem
from tariffcompass.platform.models import LoginFailure

PAUSE_AFTER = 5
PAUSE_MINUTES = 15
_BUCKETS = {"auth": "RATE_LIMIT_AUTH", "classify": "RATE_LIMIT_CLASSIFY", "api": "RATE_LIMIT_API"}
_DEFAULTS = {"auth": 10, "public": 20, "classify": 30, "api": 300}


def _limit(bucket: str) -> int:
    key = _BUCKETS.get(bucket)
    raw = str(settings.TARIFF_COMPASS.get(key, "")) if key else ""
    try:
        return int(raw.split("/")[0]) if raw else _DEFAULTS[bucket]
    except ValueError:
        return _DEFAULTS[bucket]


def _who(request: HttpRequest) -> str:
    ctx = getattr(request, "ctx", None)
    if ctx is not None:
        return f"u:{ctx.user.pk}"
    return f"ip:{request.META.get('REMOTE_ADDR', '')}"


def hit(request: HttpRequest, bucket: str) -> None:
    """Count one request in `bucket`; raise 429 with Retry-After once the minute's allowance is spent."""
    limit = _limit(bucket)
    now = time.time()
    key = f"rl:{bucket}:{_who(request)}"
    stamps = [t for t in (cache.get(key) or []) if now - t < 60]
    if len(stamps) >= limit:
        wait = max(1, int(60 - (now - stamps[0])) + 1)
        raise Problem(429, "rate_limited", "Slow down a little.", headers={"Retry-After": str(wait)})
    stamps.append(now)
    cache.set(key, stamps, 61)


# ── Sign-in pause ───────────────────────────────────────────────────────────────────────────────────────
def _real_now():
    return clock.real_now()


def recent_failures(email: str) -> list[LoginFailure]:
    since = _real_now() - timedelta(minutes=PAUSE_MINUTES)
    return list(LoginFailure.objects.filter(email=email.lower(), created_at__gte=since).order_by("created_at"))


def check_paused(email: str) -> None:
    fails = recent_failures(email)
    if len(fails) >= PAUSE_AFTER:
        resume = fails[-PAUSE_AFTER].created_at + timedelta(minutes=PAUSE_MINUTES)
        wait = max(1, int((resume - _real_now()).total_seconds()))
        raise Problem(
            423,
            "sign_in_paused",
            f"Too many tries. Sign-in for this email is paused for {PAUSE_MINUTES} minutes.",
            retry_after_seconds=wait,
            headers={"Retry-After": str(wait)},
        )


def record_failure(email: str, ip: str) -> int:
    """Store one failure; returns how many tries are left before the pause."""
    LoginFailure.objects.create(email=email.lower(), ip=ip, created_at=_real_now())
    return max(0, PAUSE_AFTER - len(recent_failures(email)))


def clear_failures(email: str) -> None:
    LoginFailure.objects.filter(email=email.lower()).delete()
