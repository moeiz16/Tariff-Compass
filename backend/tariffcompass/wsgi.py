"""WSGI entry point (kept for hosts without ASGI; SSE needs ASGI)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tariffcompass.settings")
application = get_wsgi_application()
