"""The demo clock: every "now" and "today" in Tariff Compass comes from here.

`TARIFF_COMPASS_DEMO_TODAY` (default `2026-02-19`) moves the server's idea of today to that date, so seeded
records, ages ("waiting 3 days"), retention dates, "tariffs as of" and the activity log read as of the demo
day. Set it to `real` to run on the wall clock.

- Without a time pin the shift is a whole number of days: the time of day still advances normally.
- `TARIFF_COMPASS_DEMO_TIME=10:30` also pins the time of day (in `TIME_ZONE`, America/Vancouver) at the moment
  the clock is first anchored; from then on it ticks. The anchor lives in `data/demo-clock.json`, so the API,
  the Huey worker and management commands all read the same "now". `make reset` re-anchors it.

Business code calls `clock.now()` / `clock.today()` (or Django's `timezone.now()`, which `install()` shifts too,
so `auto_now` fields agree). Session expiry and rate limits deliberately use the real wall clock (`time.time()`).
Every HTTP response carries `X-Tariff-Compass-Now` (see core.middleware).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.utils import timezone

DEFAULT_DEMO_TODAY = "2026-02-19"
DEFAULT_ZONE = "America/Vancouver"

_real_now: Callable[[], datetime] | None = None
_offset = timedelta(0)
_state: dict[str, str | bool | None] = {"demo": False, "demoToday": None, "demoTime": None}


def _zone() -> ZoneInfo:
    try:
        from django.conf import settings

        return ZoneInfo(getattr(settings, "TIME_ZONE", DEFAULT_ZONE))
    except Exception:  # settings not configured (scripts)
        return ZoneInfo(DEFAULT_ZONE)


def real_now() -> datetime:
    """The wall clock, never shifted (sessions, rate limits, anchors)."""
    return (_real_now or timezone.now)()


def now() -> datetime:
    """Current time as an aware UTC datetime (shifted when the demo clock is installed)."""
    return real_now() + _offset


def now_iso() -> str:
    return now().astimezone(UTC).isoformat(timespec="seconds")


def today() -> date:
    """Today's date in the configured zone (America/Vancouver by default)."""
    return now().astimezone(_zone()).date()


def local(dt: datetime) -> datetime:
    return dt.astimezone(_zone())


def offset() -> timedelta:
    return _offset


def describe() -> dict[str, str | bool | None]:
    """The clock block returned by /meta and /auth/session."""
    return {
        "now": now_iso(),
        "today": today().isoformat(),
        "timezone": str(_zone()),
        "demo": bool(_state["demo"]),
        "demoToday": _state["demoToday"],
        "demoTime": _state["demoTime"],
    }


def _anchor(path: Path | None, demo_today: date, demo_time: time, zone: ZoneInfo) -> timedelta:
    """Offset that makes the pinned demo moment line up with a real instant shared by every process."""
    target = datetime.combine(demo_today, demo_time, zone)
    key = {"demoToday": demo_today.isoformat(), "demoTime": demo_time.strftime("%H:%M")}
    if path is not None and path.is_file():
        try:
            saved = json.loads(path.read_text())
            if {k: saved.get(k) for k in key} == key:
                return datetime.fromisoformat(saved["demoAnchor"]) - datetime.fromisoformat(saved["realAnchor"])
        except (ValueError, KeyError, OSError):
            pass
    real = real_now()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({**key, "realAnchor": real.isoformat(), "demoAnchor": target.isoformat()}))
        os.replace(tmp, path)
    return target - real


def install(demo_today: date | str | None, demo_time: str | None = None, anchor_file: Path | None = None) -> timedelta:
    """Shift `timezone.now()` so that `today()` is `demo_today` (optionally at `demo_time`). Idempotent."""
    global _real_now, _offset
    uninstall()
    if not demo_today or str(demo_today).lower() in {"real", "off", "none"}:
        return timedelta(0)
    target = date.fromisoformat(demo_today) if isinstance(demo_today, str) else demo_today
    zone = _zone()
    real = timezone.now
    _real_now = real
    if demo_time:
        hh, mm = (int(x) for x in demo_time.split(":", 1))
        _offset = _anchor(anchor_file, target, time(hh, mm), zone)
    else:
        _offset = timedelta(days=(target - real().astimezone(zone).date()).days)
    shift = _offset

    def shifted_now() -> datetime:
        return real() + shift

    timezone.now = shifted_now
    _state.update(demo=True, demoToday=target.isoformat(), demoTime=demo_time or None)
    return _offset


def uninstall() -> None:
    """Back to real time (tests)."""
    global _real_now, _offset
    if _real_now is not None:
        timezone.now = _real_now
    _real_now, _offset = None, timedelta(0)
    _state.update(demo=False, demoToday=None, demoTime=None)
