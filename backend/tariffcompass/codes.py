"""Tariff codes: digits inside, the official grouping at the edge.

US HTSUS ten digits display 4.2.2.2 (`9617.00.10.00`); CBP rulings quote 4.2.4 (`9617.00.1000`), kept only
as quoted text. Canada's Customs Tariff tariff items are 8 digits (4.2.2) plus a 2-digit statistical suffix:
`9617.00.00.00`.
"""

from __future__ import annotations

import re

_DIGITS = re.compile(r"\D")


def digits(code: str) -> str:
    return _DIGITS.sub("", code)


def heading(code: str) -> str:
    return digits(code)[:4]


def chapter(code: str) -> str:
    return digits(code)[:2]


def fmt(code: str) -> str:
    """Format any 2–10 digit code in the 4.2.2.2 grouping used by both schedules' ten-digit numbers."""
    d = digits(code)
    if len(d) <= 4:
        return d
    parts = [d[:4], d[4:6], d[6:8], d[8:10]]
    return ".".join(p for p in parts if p)


def fmt_as_quoted_by_cbp(code: str) -> str:
    """CBP CROSS style: 9617.00.1000."""
    d = digits(code)
    return f"{d[:4]}.{d[4:6]}.{d[6:10]}" if len(d) == 10 else fmt(d)


def is_valid_length(code: str) -> bool:
    return len(digits(code)) in (2, 4, 6, 8, 10)
