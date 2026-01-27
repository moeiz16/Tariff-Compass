"""The NinjaAPI instance. Routers are mounted here; every error is RFC 7807 (core.errors).

Signed-in is the default (`platform.context.session_auth`, which also enforces CSRF on unsafe methods);
public endpoints say `auth=None`. Each view declares its permission with `@requires(...)`.
"""

from __future__ import annotations

from ninja import NinjaAPI

from tariffcompass import __version__
from tariffcompass.api.routers import (
    audit,
    auth,
    classify,
    jobs,
    meta,
    org,
    products,
    review,
    rulings,
    settings,
    tariff,
)
from tariffcompass.core import errors
from tariffcompass.platform.context import session_auth

api = NinjaAPI(
    title="Tariff Compass API",
    version=__version__,
    description="Tariff classification for US and Canadian imports. Contract: docs/API_CONTRACT.md.",
    urls_namespace="api",
    docs_url="/docs",
    auth=session_auth,
)
errors.install(api)

api.add_router("", meta.router, tags=["meta"])
api.add_router("/auth", auth.router, tags=["auth"])
api.add_router("/org", org.router, tags=["organisation"])
api.add_router("/roles", org.roles_router, tags=["organisation"])
api.add_router("/invitations", org.invitations_router, tags=["organisation"])
api.add_router("/settings", settings.router, tags=["settings"])
api.add_router("/audit", audit.router, tags=["activity"])
api.add_router("/jobs", jobs.router, tags=["jobs"])
api.add_router("/classify", classify.router, tags=["classify"])
api.add_router("/answers", classify.answers_router, tags=["classify"])
api.add_router("/evidence", classify.evidence_router, tags=["classify"])
api.add_router("/public", classify.public_router, tags=["public"])
api.add_router("/rulings", rulings.router, tags=["rulings"])
api.add_router("/tariff", tariff.router, tags=["tariff"])
api.add_router("/landed-cost", tariff.landed_router, tags=["landed cost"])
api.add_router("/duty-layers", tariff.layers_router, tags=["landed cost"])
api.add_router("/products", products.router, tags=["products"])
api.add_router("/exports", products.exports_router, tags=["products"])
api.add_router("/review", review.router, tags=["review"])
api.add_router("/rules", review.rules_router, tags=["review"])
