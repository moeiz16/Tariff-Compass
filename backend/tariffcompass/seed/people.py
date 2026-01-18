"""The sample organisations' people (docs/DATA.md). Emails use reserved `.example` domains."""

from __future__ import annotations

SAMPLE_IMPORTER_SLUG = "northbound-goods"
SAMPLE_BROKER_SLUG = "driftwood-customs"
SAMPLE_PASSWORD = "compass-sample-2026"  # sample accounts only; printed by `make seed`

# role → the person demo sign-in uses (API_CONTRACT §1.2)
DEMO_PEOPLE: dict[str, dict[str, str]] = {
    "importer": {
        "email": "jordan.tse@northbound.example",
        "full_name": "Jordan Tse",
        "title": "Operations lead, Seattle",
        "org_slug": SAMPLE_IMPORTER_SLUG,
    },
    "broker": {
        "email": "dana.whitlock@driftwood.example",
        "full_name": "Dana Whitlock",
        "title": "Licensed customs broker, US entries",
        "org_slug": SAMPLE_BROKER_SLUG,
    },
    "compliance": {
        "email": "maya.lindqvist@northbound.example",
        "full_name": "Maya Lindqvist",
        "title": "Trade compliance lead",
        "org_slug": SAMPLE_IMPORTER_SLUG,
    },
    "admin": {
        "email": "priscilla.mensah@northbound.example",
        "full_name": "Priscilla Mensah",
        "title": "Administrator",
        "org_slug": SAMPLE_IMPORTER_SLUG,
    },
}
