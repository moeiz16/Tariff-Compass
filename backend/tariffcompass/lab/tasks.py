"""Lab background jobs (autodiscovered by `manage.py run_huey`): one training round at a time.

The optimiser (classification core) does the work and returns a RoundReport; this task stores it, marks the
corrections it used, and leaves the round waiting for two signatures. Training never makes a round live.
"""

from __future__ import annotations

from typing import Any

from huey.contrib.djhuey import db_task

from tariffcompass import clock, services
from tariffcompass.contracts import RoundRequest
from tariffcompass.jobs import Progress, run_job
from tariffcompass.lab import reports
from tariffcompass.lab.models import TrainingRound
from tariffcompass.platform import audit
from tariffcompass.platform.models import Job
from tariffcompass.review.models import TrainingExample


@db_task()
def run_round(job_id: str) -> dict[str, Any]:
    job = Job.objects.get(pk=job_id)
    r = TrainingRound.objects.get(org=job.org, n=job.params["round"])

    def work(progress: Progress) -> dict[str, Any]:
        examples = list(TrainingExample.objects.filter(org=job.org, used_in_round__isnull=True, signal="correction"))
        progress(0.05, "data", f"Gathering rulings and {len(examples)} broker corrections…")
        request = RoundRequest(
            round_n=r.n,
            seed=r.seed,
            train_ids=(),
            val_ids=(),
            test_ids=(),
            corrections=tuple(e.payload for e in examples),
        )
        report = services.optimizer().run(request, progress)
        data = reports.dump(report)
        r.report = data
        r.status = "waiting_signoff"
        r.trained_on = clock.today()
        r.lm_label, r.reflection_lm_label = report.lm_label, report.reflection_lm_label
        r.data_snapshot, r.program_path = report.data_snapshot, report.program_path
        r.corrections_used = len(examples)
        r.save()
        TrainingExample.objects.filter(pk__in=[e.pk for e in examples]).update(used_in_round=r.n)
        audit.record(
            job.org,
            "lab.round_finished",
            f"Training round {r.n} finished and is waiting for sign-off",
            target_type="round",
            target_id=str(r.n),
            details={"round": r.n, "corrections": len(examples)},
        )
        return {"round": r.n, "status": r.status}

    try:
        return run_job(job_id, work)
    except Exception:
        TrainingRound.objects.filter(pk=r.pk).update(status="failed")
        raise
