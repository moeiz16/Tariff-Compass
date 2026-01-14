"""GET /health and GET /meta: the clock, the data snapshot and the static label dictionaries."""

from __future__ import annotations

from datetime import date

from django.http import HttpRequest

from tariffcompass import __version__, clock
from tariffcompass.api import labels
from tariffcompass.api.schemas.common import ClockOut, Labelled
from tariffcompass.api.schemas.platform import HealthOut, MetaOut, SnapshotOut
from tariffcompass.core.wire import WireRouter

router = WireRouter()

# The editions in force on the demo day (docs/DATA.md). The duty engine overrides `rulings_*` once indexed.
SNAPSHOT = {
    "us_hts": "HTSUS 2026 Revision 3",
    "us_hts_in_force": (date(2026, 2, 12), date(2026, 2, 25)),
    "ca_tariff": "Customs Tariff T2026",
    "ca_tariff_from": date(2026, 1, 1),
    "duty_layers_as_of": date(2026, 2, 19),
}


@router.get("/health", response=HealthOut, auth=None)
def api_health(request: HttpRequest) -> dict:
    return {"status": "ok", "version": __version__, "now": clock.now_iso(), "checks": {}}


@router.get("/meta", response=MetaOut, auth=None)
def meta(request: HttpRequest) -> dict:
    as_of = SNAPSHOT["duty_layers_as_of"]
    return {
        "product": "Tariff Compass",
        "version": __version__,
        "clock": ClockOut(**clock.describe()),
        "snapshot": SnapshotOut(
            **SNAPSHOT,
            rulings_count=0,
            rulings_newest=None,
            label=f"Tariffs as of {as_of.strftime('%a')} {as_of.day} {as_of.strftime('%b %Y')}",
        ),
        "scopes": [Labelled(key=k, label=v) for k, v in labels.SCOPES.items()],
        "labels": labels.ALL,
        "origins": [Labelled(key=k, label=v) for k, v in labels.ORIGINS.items()],
    }
