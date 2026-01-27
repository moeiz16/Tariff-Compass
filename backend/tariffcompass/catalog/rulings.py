"""Ruling references as the API shows them: status words, keys and CROSS links, read from the search engine.

Only rulings the corpus knows are ever shown; `exists()` is what the seed and its tests check.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

from tariffcompass import services
from tariffcompass.api import labels


def _dmy(d: date) -> str:
    return f"{d.day} {d.strftime('%b')} {d.year}"


def status_out(kind: str, by_id: str | None = None, on: date | None = None) -> dict[str, Any]:
    word = labels.RULING_STATUSES.get(kind, kind)
    if kind in ("revoked", "modified") and by_id:
        text = f"{word} by {by_id}" + (f", {_dmy(on)}" if on else "")
    elif kind == "contrast":
        text = "Cited for contrast: a different heading"
    else:
        text = word
    return {"kind": kind, "kind_label": word, "text": text, "by_id": by_id, "date": on}


@lru_cache(maxsize=4096)
def _doc(ruling_id: str):
    return services.retriever().ruling(ruling_id)


def exists(ruling_id: str) -> bool:
    return _doc(ruling_id) is not None


def status_of(ruling_id: str) -> dict[str, Any]:
    doc = _doc(ruling_id)
    if doc is None:
        return status_out("in_force")
    return status_out(doc.status, doc.status_by, doc.status_date)


def heading_of(ruling_id: str) -> str:
    doc = _doc(ruling_id)
    return doc.code[:4] if doc else ""


def clear() -> None:
    _doc.cache_clear()
