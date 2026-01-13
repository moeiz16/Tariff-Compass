"""Prometheus metrics exposed at /metrics (text format). Domain modules add their own here."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter("tc_http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram(
    "tc_http_request_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.15, 0.25, 0.5, 1.0, 2.5, 6.0, 10.0),
)
CLASSIFY_STAGE = Histogram(
    "tc_classify_stage_seconds",
    "Time per classification stage (first_stage, retrieve, program, duties)",
    ["stage", "lm"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.15, 0.25, 0.5, 1.0, 2.5, 6.0, 10.0),
)
JOBS = Counter("tc_jobs_total", "Background jobs by kind and outcome", ["kind", "status"])
