"""URL map: the JSON API under /api/v1, health and metrics at the root."""

from __future__ import annotations

from django.urls import path

from tariffcompass.api.app import api
from tariffcompass.api.health import health, metrics, ready

urlpatterns = [
    path("health", health),
    path("health/ready", ready),
    path("metrics", metrics),
    path("api/v1/", api.urls),
]

handler404 = "tariffcompass.core.errors.handler404"
handler500 = "tariffcompass.core.errors.handler500"
