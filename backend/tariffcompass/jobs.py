"""Background jobs on Huey with SQLite storage (ADR 0004).

The worker is `manage.py run_huey` (one thread worker; heavy jobs such as training rounds run one at a time).
Every user-visible job has a platform.Job row: the API returns `JobAccepted`, the web app follows
`GET /jobs/{id}` (polling) or `GET /jobs/{id}/events` (SSE). `run_job` wraps a task so status, progress,
errors and timings land on that row whatever the task does. In tests and with HUEY_IMMEDIATE=true the
tasks run inline. Tasks live in each app's `tasks.py` (the worker autodiscovers them there).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from huey.contrib.djhuey import HUEY

from tariffcompass import clock
from tariffcompass.core.metrics import JOBS
from tariffcompass.platform.models import Job

log = structlog.get_logger("tariffcompass.jobs")


class Progress:
    """Passed to long tasks so they can report a stage, a fraction and a plain-words message."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id

    def __call__(self, fraction: float, stage: str = "", message: str = "") -> None:
        Job.objects.filter(id=self.job_id).update(
            progress=max(0.0, min(1.0, fraction)), stage=stage[:60], message=message[:300]
        )


def run_job(job_id: str, fn: Callable[[Progress], dict[str, Any]]) -> dict[str, Any]:
    job = Job.objects.get(id=job_id)
    Job.objects.filter(id=job_id).update(status="running", started_at=clock.now())
    try:
        result = fn(Progress(job_id)) or {}
    except Exception as exc:
        log.exception("job_failed", job=job_id, kind=job.kind)
        Job.objects.filter(id=job_id).update(status="failed", error=str(exc)[:500], finished_at=clock.now())
        JOBS.labels(job.kind, "failed").inc()
        raise
    Job.objects.filter(id=job_id).update(status="succeeded", progress=1.0, result=result, finished_at=clock.now())
    JOBS.labels(job.kind, "succeeded").inc()
    return result


huey = HUEY

__all__ = ["Progress", "huey", "run_job"]
