"""Shared fixtures. Tests run on an in-memory database, inline Huey tasks and the demo clock pinned to
Thu 19 Feb 2026, 10:30 America/Vancouver (settings.TESTING)."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.fixture
def client() -> Client:
    return Client(enforce_csrf_checks=True)
