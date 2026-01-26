"""Typed access to the `TARIFF_COMPASS` settings block (settings.py builds it as a plain dict)."""

from __future__ import annotations

from typing import Any, cast

from django.conf import settings


def tc() -> dict[str, Any]:
    return cast(dict[str, Any], settings.TARIFF_COMPASS)
