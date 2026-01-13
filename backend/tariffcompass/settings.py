"""Tariff Compass settings. Everything environment-specific comes from env vars (see `.env.example`)."""

from __future__ import annotations

import sys
from pathlib import Path

from tariffcompass.core.env import database_from_url, env_bool, env_int, env_list, env_str, load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
load_dotenv(REPO_DIR / ".env")

TESTING = "pytest" in sys.modules
ENV = env_str("DJANGO_ENV", "test" if TESTING else "dev")  # dev | test | prod
IS_PROD = ENV == "prod"
DEBUG = env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env_str("SECRET_KEY")
if not SECRET_KEY:
    if IS_PROD:
        raise RuntimeError("SECRET_KEY must be set when DJANGO_ENV=prod")
    SECRET_KEY = "dev-only-insecure-key-change-me-tariff-compass-0123456789"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
WEB_ORIGIN = env_str("WEB_ORIGIN", "http://localhost:3050")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:3050,http://127.0.0.1:3050")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "huey.contrib.djhuey",
    # platform and product records
    "tariffcompass.platform",
    "tariffcompass.catalog",
    "tariffcompass.review",
    "tariffcompass.watch",
    "tariffcompass.lab",
    "tariffcompass.seed",
    # classification core
    "tariffcompass.search",
    "tariffcompass.classify",
    "tariffcompass.duties",
]

MIDDLEWARE = [
    "tariffcompass.core.middleware.RequestContextMiddleware",
    "tariffcompass.core.middleware.ClockHeaderMiddleware",
    "tariffcompass.core.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tariffcompass.urls"
ASGI_APPLICATION = "tariffcompass.asgi.application"
WSGI_APPLICATION = "tariffcompass.wsgi.application"
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BACKEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]

DATA_DIR = Path(env_str("DATA_DIR", str(REPO_DIR / "data")))
DATABASES = {"default": database_from_url(env_str("DATABASE_URL", "sqlite:///data/tariffcompass.db"), REPO_DIR)}
if TESTING:
    DATABASES["default"]["TEST"] = {"NAME": ":memory:"}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "platform.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
]

# ── Sessions and CSRF: cookie auth for the same-origin web app (docs/API_CONTRACT.md §1.2) ──
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "tc_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = IS_PROD
SESSION_IDLE_MINUTES = env_int("SESSION_IDLE_MINUTES", 30)
SESSION_ABSOLUTE_HOURS = env_int("SESSION_ABSOLUTE_HOURS", 12)
SESSION_COOKIE_AGE = SESSION_IDLE_MINUTES * 60
CSRF_COOKIE_NAME = "tc_csrf"
CSRF_COOKIE_HTTPONLY = False  # the web app reads it and echoes it in X-CSRFToken
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = IS_PROD
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_FAILURE_VIEW = "tariffcompass.core.errors.csrf_failure"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("BEHIND_PROXY") else None

MAX_UPLOAD_MB = env_int("MAX_UPLOAD_MB", 10)  # spec sheets and photos
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_MB * 1024 * 1024
MEDIA_ROOT = DATA_DIR / "uploads"  # evidence files; never served publicly

LANGUAGE_CODE = "en-us"
TIME_ZONE = env_str("TIME_ZONE", "America/Vancouver")  # Northbound's home zone; the API speaks UTC
USE_I18N = False
USE_TZ = True

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "tariffcompass"}}

NINJA_PAGINATION_PER_PAGE = 25
NINJA_MAX_PER_PAGE_SIZE = 100

# ── Background jobs: Huey on SQLite (ADR 0004). Tests and the single-process demo run tasks inline. ──
HUEY = {
    "huey_class": "huey.SqliteHuey",
    "name": "tariffcompass",
    "filename": env_str("HUEY_DB", str(DATA_DIR / "huey.db")),
    "immediate": TESTING or env_bool("HUEY_IMMEDIATE", default=False),
    "results": True,
    "utc": True,
    "consumer": {"workers": env_int("HUEY_WORKERS", 1), "worker_type": "thread", "periodic": True},
}

# ── Logging ──
LOG_LEVEL = env_str("LOG_LEVEL", "WARNING" if TESTING else "INFO")
LOG_JSON = env_bool("LOG_JSON", default=IS_PROD)
LOGGING_CONFIG = None
from tariffcompass.core.logging import configure_logging

configure_logging(LOG_LEVEL, json_logs=LOG_JSON)

# ── Tariff Compass domain settings (docs/ARCHITECTURE.md, docs/DATA.md) ──
TARIFF_COMPASS = {
    # demo clock (tariffcompass/clock.py)
    "DEMO_TODAY": "2026-02-19" if TESTING else env_str("TARIFF_COMPASS_DEMO_TODAY", "2026-02-19"),
    "DEMO_TIME": "10:30"
    if TESTING
    else env_str("TARIFF_COMPASS_DEMO_TIME", ""),  # "HH:MM" pins the time of day, e.g. 10:30
    "CLOCK_ANCHOR": None if TESTING else DATA_DIR / "demo-clock.json",
    # data (docs/DATA.md); the committed fixtures make everything work offline
    "RULINGS_PATH": env_str("RULINGS_PATH", str(DATA_DIR / "rulings" / "rulings.jsonl")),
    "RULINGS_SAMPLE": BACKEND_DIR / "tariffcompass" / "search" / "fixtures" / "rulings_sample.jsonl",
    "HTS_PATH": env_str("HTS_PATH", str(DATA_DIR / "hts" / "hts_2026_rev3.jsonl")),
    "CA_TARIFF_PATH": env_str("CA_TARIFF_PATH", str(DATA_DIR / "ca" / "customs_tariff_t2026.jsonl")),
    "TARIFF_SAMPLE_DIR": BACKEND_DIR / "tariffcompass" / "search" / "fixtures",
    "DUTY_LAYERS_PATH": BACKEND_DIR / "tariffcompass" / "duties" / "data" / "layers.json",
    "INDEX_DIR": env_str("INDEX_DIR", str(DATA_DIR / "index")),
    "ARTIFACT_DIR": env_str("ARTIFACT_DIR", str(BACKEND_DIR / "tariffcompass" / "classify" / "artifacts")),
    "MLFLOW_TRACKING_URI": env_str("MLFLOW_TRACKING_URI", f"sqlite:///{REPO_DIR / 'mlruns' / 'mlflow.db'}"),
    "MLFLOW_ARTIFACT_ROOT": env_str("MLFLOW_ARTIFACT_ROOT", str(REPO_DIR / "mlruns" / "artifacts")),
    # the classifier program's LM (ADR 0003). Offline simulator unless LLM_FAKE=false and a key is set.
    "LLM_FAKE": env_bool("LLM_FAKE", default=True),
    "LITELLM_MODEL": env_str("LITELLM_MODEL", "groq/llama-3.3-70b-versatile"),
    "LITELLM_REFLECTION_MODEL": env_str("LITELLM_REFLECTION_MODEL", "gemini/gemini-2.5-flash"),
    "LLM_TIMEOUT_SECONDS": env_int("LLM_TIMEOUT_SECONDS", 20),
    # photos and embeddings go through adapters too (fakes by default)
    "VISION_FAKE": env_bool("VISION_FAKE", default=True),
    "VISION_MODEL": env_str("VISION_MODEL", "gemini/gemini-2.5-flash"),
    "EMBEDDINGS": env_str("EMBEDDINGS", "fake"),  # fake | jina | cohere
    "EMBEDDINGS_MODEL": env_str("EMBEDDINGS_MODEL", "jina-embeddings-v3"),
    # product rules
    "ALWAYS_REVIEW_VALUE_USD": env_int("ALWAYS_REVIEW_VALUE_USD", 25_000),
    "RETENTION_YEARS": env_int("RETENTION_YEARS", 5),
    # jobs and events
    "SSE_POLL_SECONDS": float(env_str("SSE_POLL_SECONDS", "0.5")),
    "SSE_HEARTBEAT_SECONDS": env_int("SSE_HEARTBEAT_SECONDS", 15),
    "SSE_MAX_SECONDS": env_int("SSE_MAX_SECONDS", 300),
    "RATE_LIMIT_AUTH": env_str("RATE_LIMIT_AUTH", "10/min"),
    "RATE_LIMIT_CLASSIFY": env_str("RATE_LIMIT_CLASSIFY", "30/min"),
    "RATE_LIMIT_API": env_str("RATE_LIMIT_API", "300/min"),
    "DEMO_SIGN_IN": env_bool("DEMO_SIGN_IN", default=not IS_PROD),
}
