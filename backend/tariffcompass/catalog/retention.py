"""How long a product's record is kept.

- United States: five years from the date of entry (19 CFR 163.4(a)), for records of the entry and its
  classification (reasonable care, 19 U.S.C. 1484).
- Canada: six years following the importation of the goods (CBSA Memorandum D17-1-21, paragraph 2).

A binder is kept until the later of the two for its latest entries. A product with no entries yet is kept from
its latest decision (five years, or six when it is imported into Canada). Deleting a product only hides it.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

US_YEARS = 5
CA_YEARS = 6
US_RULE = "19 CFR 163.4"
CA_RULE = "CBSA Memorandum D17-1-21"


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28)


def kept_until(*, entries: Iterable[tuple[str, date]], last_decision: date, into: Iterable[str]) -> tuple[date, str]:
    """(date, the rule that sets it). `entries` are (country, entered_on)."""
    candidates: list[tuple[date, str]] = []
    rows = list(entries)
    for country, entered in rows:
        if country == "CA":
            candidates.append((add_years(entered, CA_YEARS), CA_RULE))
        else:
            candidates.append((add_years(entered, US_YEARS), US_RULE))
    if not rows:
        candidates.append((add_years(last_decision, US_YEARS), US_RULE))
        if "CA" in set(into):
            candidates.append((add_years(last_decision, CA_YEARS), CA_RULE))
    return max(candidates)


def note(until: date, rule: str) -> str:
    words = (
        "five years after the latest US entry (19 CFR 163.4)"
        if rule == US_RULE
        else "six years after the latest Canadian import (CBSA Memorandum D17-1-21)"
    )
    return (
        f"Kept until {until.day} {until.strftime('%b')} {until.year}: {words}, whichever rule runs longer. "
        "Deleting the product hides it; the record stays until then."
    )


def policy_sentence() -> str:
    return (
        "US entry records are kept five years from the date of entry (19 CFR 163.4); Canadian import records six "
        "years (CBSA Memorandum D17-1-21). Each binder keeps the longer of the two that applies to it."
    )
