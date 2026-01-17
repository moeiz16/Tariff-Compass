"""The NinjaAPI instance. Routers are mounted here; every error is RFC 7807 (core.errors)."""

from __future__ import annotations

from ninja import NinjaAPI

from tariffcompass import __version__
from tariffcompass.api.routers import auth, meta
from tariffcompass.core import errors

api = NinjaAPI(
    title="Tariff Compass API",
    version=__version__,
    description="Tariff classification for US and Canadian imports. Contract: docs/API_CONTRACT.md.",
    urls_namespace="api",
    docs_url="/docs",
)
errors.install(api)

api.add_router("", meta.router, tags=["meta"])
api.add_router("/auth", auth.router, tags=["auth"])
# Mounted by the platform layer as each area lands (API_CONTRACT Part 1):
#   /org, /roles, /classify, /evidence, /answers, /public, /rulings, /tariff, /landed-cost, /duty-layers,
#   /products, /review, /rules, /watch, /home, /lab, /settings, /audit, /jobs
