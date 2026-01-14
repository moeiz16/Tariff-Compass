from __future__ import annotations

import pytest

from tariffcompass.jobs import huey
from tariffcompass.platform.models import Job
from tariffcompass.platform.tasks import ping

pytestmark = pytest.mark.django_db


def test_huey_runs_inline_in_tests_and_updates_the_job_row():
    assert huey.immediate
    job = Job.objects.create(kind="ingest")
    result = ping(str(job.id))()
    job.refresh_from_db()
    assert job.status == "succeeded" and job.progress == 1.0
    assert result["pong"].startswith("2026-02-19")
