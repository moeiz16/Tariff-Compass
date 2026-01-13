from __future__ import annotations

import json
from datetime import date

import pytest
from django.utils import timezone

from tariffcompass import clock


@pytest.fixture
def restore_clock(settings):
    yield
    cfg = settings.TARIFF_COMPASS
    clock.install(cfg["DEMO_TODAY"], cfg["DEMO_TIME"] or None, anchor_file=None)


def test_tests_run_on_the_demo_morning():
    assert clock.today() == date(2026, 2, 19)
    assert clock.local(clock.now()).strftime("%H:%M") in {"10:30", "10:31"}
    assert clock.describe()["demo"] is True


def test_django_now_is_shifted_too():
    assert abs((timezone.now() - clock.now()).total_seconds()) < 1


def test_day_shift_keeps_the_time_of_day_moving(restore_clock):
    clock.install("2026-01-12")
    assert clock.today() == date(2026, 1, 12)
    assert clock.describe()["demoTime"] is None


def test_time_pin_is_shared_through_the_anchor_file(tmp_path, restore_clock):
    anchor = tmp_path / "demo-clock.json"
    clock.install("2026-02-19", "10:30", anchor_file=anchor)
    first = clock.offset()
    saved = json.loads(anchor.read_text())
    assert saved["demoToday"] == "2026-02-19" and saved["demoTime"] == "10:30"
    clock.install("2026-02-19", "10:30", anchor_file=anchor)  # a second process reads the same anchor
    assert abs((clock.offset() - first).total_seconds()) < 0.001


def test_real_turns_the_demo_clock_off(restore_clock):
    clock.install("real")
    assert clock.describe()["demo"] is False
    assert clock.offset().total_seconds() == 0
