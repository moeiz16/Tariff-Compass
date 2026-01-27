"""Watch background jobs (autodiscovered by `manage.py run_huey`): re-check binders against the changes."""

from __future__ import annotations

from typing import Any

from huey.contrib.djhuey import db_task

from tariffcompass.jobs import Progress, run_job
from tariffcompass.platform import audit
from tariffcompass.platform.models import Job


@db_task()
def watch_scan(job_id: str) -> dict[str, Any]:
    def work(progress: Progress) -> dict[str, Any]:
        from tariffcompass.watch.scan import scan

        job = Job.objects.select_related("org", "created_by").get(pk=job_id)
        assert job.org is not None
        result = scan(job.org, progress)
        flagged = sum(result["affected"].values())
        role = ""
        if job.created_by:
            role = job.created_by.memberships.filter(org=job.org).values_list("role", flat=True).first() or ""
        audit.record(
            job.org,
            "watch.scanned",
            f"Checked {result['products']} binders against {result['changes']} changes ({flagged} flags)",
            actor=job.created_by,
            actor_role=role,
            target_type="watch",
            details=result,
        )
        return result

    return run_job(job_id, work)
