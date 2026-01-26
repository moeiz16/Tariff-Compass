"""GET /health and GET /meta: the clock, the data snapshot and the static label dictionaries."""

from __future__ import annotations

from datetime import date
from functools import cache

from django.http import HttpRequest

from tariffcompass import __version__, clock, services
from tariffcompass.api import labels
from tariffcompass.api.schemas.common import ClockOut, Labelled
from tariffcompass.api.schemas.platform import HealthOut, MetaOut, SnapshotOut
from tariffcompass.core.wire import WireRouter

router = WireRouter()

# The editions in force on the demo day (docs/DATA.md). The duty engine overrides `rulings_*` once indexed.
SNAPSHOT_DATE = date(2026, 2, 19)
SNAPSHOT: dict[str, object] = {
    "us_hts": "HTSUS 2026 Revision 3",
    "us_hts_in_force": (date(2026, 2, 12), date(2026, 2, 25)),
    "ca_tariff": "Customs Tariff T2026",
    "ca_tariff_from": date(2026, 1, 1),
    "duty_layers_as_of": SNAPSHOT_DATE,
}


@router.get("/health", response=HealthOut, auth=None)
def api_health(request: HttpRequest) -> dict:
    return {"status": "ok", "version": __version__, "now": clock.now_iso(), "checks": {}}


@cache
def corpus_stats() -> tuple[int, date | None]:
    """How many rulings the search engine holds and the newest one's date (0 and None when it can't say)."""
    browse = getattr(services.retriever(), "browse", None)
    if not callable(browse):
        return 0, None
    try:
        hits, total = browse("", sort="newest", limit=1)
    except Exception:  # the count is informative only; never fail /meta over it
        return 0, None
    return int(total), (hits[0].issued if hits else None)


@router.get("/meta", response=MetaOut, auth=None)
def meta(request: HttpRequest) -> dict:
    as_of: date = SNAPSHOT_DATE
    count, newest = corpus_stats()
    return {
        "product": "Tariff Compass",
        "version": __version__,
        "clock": ClockOut.model_validate(clock.describe()),
        "snapshot": SnapshotOut.model_validate(
            {
                **SNAPSHOT,
                "rulings_count": count,
                "rulings_newest": newest,
                "label": f"Tariffs as of {as_of.strftime('%a')} {as_of.day} {as_of.strftime('%b %Y')}",
            }
        ),
        "scopes": [Labelled(key=k, label=v) for k, v in labels.SCOPES.items()],
        "labels": labels.ALL,
        "origins": [Labelled(key=k, label=v) for k, v in labels.ORIGINS.items()],
    }
