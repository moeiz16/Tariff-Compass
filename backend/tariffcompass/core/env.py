"""Environment helpers for settings: typed reads, a tiny `.env` loader and DATABASE_URL parsing.

Kept dependency-free on purpose. Secrets only ever come from the environment.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

_TRUE = {"1", "true", "yes", "on"}


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overriding variables that are already set."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in _TRUE


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def env_list(name: str, default: str = "") -> list[str]:
    return [p.strip() for p in os.environ.get(name, default).split(",") if p.strip()]


def database_from_url(url: str, base_dir: Path) -> dict:
    """Translate `sqlite:///relative/path.db`, `sqlite:////abs/path.db` or `postgres://…` into DATABASES['default']."""
    parsed = urlparse(url)
    if parsed.scheme == "sqlite":
        raw = unquote(parsed.path)
        # sqlite:///data/x.db -> "/data/x.db" (relative to repo root); sqlite:////abs/x.db -> "//abs/x.db"
        name = raw[1:] if raw.startswith("//") else raw.lstrip("/")
        path = Path(name) if Path(name).is_absolute() else (base_dir / name)
        if name != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:" if name == ":memory:" else str(path),
            # WAL lets the API read while the worker writes; IMMEDIATE avoids upgrade deadlocks on writes.
            "OPTIONS": {
                "transaction_mode": "IMMEDIATE",
                "timeout": 20,
                "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;",
            },
        }
    if parsed.scheme in {"postgres", "postgresql"}:
        query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
            "CONN_MAX_AGE": 60,
            "OPTIONS": query,
        }
    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme!r}")
