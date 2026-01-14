"""Platform tasks (autodiscovered by `manage.py run_huey`). Each app keeps its own Huey tasks in `tasks.py`."""

from __future__ import annotations

from typing import Any

from huey.contrib.djhuey import db_task

from tariffcompass import clock
from tariffcompass.jobs import run_job


@db_task()
def ping(job_id: str) -> dict[str, Any]:
    """A no-op job: proves the worker, the queue and the Job row work end to end."""
    return run_job(job_id, lambda progress: {"pong": clock.now_iso()})
