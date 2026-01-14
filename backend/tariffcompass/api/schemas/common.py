"""Shared wire shapes: money, clock, pages, codes with labels."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, TypeVar

from tariffcompass.core.wire import Wire

T = TypeVar("T")
CountryCode = Literal["US", "CA"]


class Money(Wire):
    amount: str  # decimal string, two places ("3400.00"); never a float
    currency: Literal["USD", "CAD"]


class ClockOut(Wire):
    now: str  # ISO-8601 UTC, same as the X-Tariff-Compass-Now header
    today: date
    timezone: str
    demo: bool
    demo_today: str | None = None
    demo_time: str | None = None


class Labelled(Wire):
    """Any code the UI shows travels with its words."""

    key: str
    label: str


class Page[T](Wire):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int


class Span(Wire):
    start: int
    end: int


class CodeOut(Wire):
    country: CountryCode
    country_label: str  # "United States" | "Canada"
    code: str  # formatted: "9617.00.10.00" (US 4.2.2.2), "9617.00.00.00" (CA 4.2.2 + 2)
    digits: str  # "9617001000"
    heading_digits: str  # "9617": drawn on the highlighter
    text: str  # the line's article description (with superior lines joined)
    heading_text: str  # the heading's text, quoted in serif
    leaning: bool = False  # needs a broker: dashed underline instead of the highlighter


class PersonRef(Wire):
    id: str
    full_name: str
    role: str
    role_label: str
    licence: str = ""


class Ack(Wire):
    ok: bool = True
    message: str = ""  # a toast slip, e.g. "Corrected · NB-KT-0388 → 7323.93.00.80 · binder v3"


class Timestamped(Wire):
    created_at: datetime
