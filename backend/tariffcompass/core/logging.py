"""Structured logging (structlog) with a per-request id carried in a context variable."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

import structlog

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def _add_request_id(_logger: object, _name: str, event: dict) -> dict:
    rid = request_id_ctx.get()
    if rid and "request_id" not in event:
        event["request_id"] = rid
    return event


def configure_logging(level: str = "INFO", *, json_logs: bool = False) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=lvl, force=True)
    for noisy in ("django.server", "django.request", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    processors: list = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer())
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(lvl),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
