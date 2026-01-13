"""ASGI entry point (uvicorn tariffcompass.asgi:application --port 8050)."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tariffcompass.settings")
application = get_asgi_application()
