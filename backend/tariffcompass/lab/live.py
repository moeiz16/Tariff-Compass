"""Which training round the classifier answers with: only a round that passed all five checks and was signed by
two different people with `lab:sign`. Otherwise none, and word matching (the classical first stage) is in use.

This is the single source of truth for the classification core (`classify.program.load_program()` reads it
through `live_round()`); nothing else decides it.
"""

from __future__ import annotations

from django.db.models import Count, Q

from tariffcompass.lab.models import TrainingRound
from tariffcompass.platform.models import Organisation

REQUIRED_SIGNATURES = 2


def signed_live(org: Organisation | None = None) -> TrainingRound | None:
    qs = (
        TrainingRound.objects.filter(status="live")
        .annotate(signers=Count("signoffs__user", distinct=True, filter=Q(signoffs__isnull=False)))
        .filter(signers__gte=REQUIRED_SIGNATURES)
    )
    if org is not None:
        qs = qs.filter(org=org)
    else:
        sample = qs.filter(org__is_sample=True)
        qs = sample if sample.exists() else qs
    for r in qs.order_by("-live_from", "-n"):
        gates = (r.report or {}).get("gates") or []
        if gates and all(g.get("passed") for g in gates):
            return r
    return None


def live_round(org: Organisation | None = None) -> int | None:
    """The signed-off live round's number, or None when word matching is in use."""
    try:
        r = signed_live(org)
    except Exception:  # no database (offline tooling): nothing is signed off
        return None
    return r.n if r else None
