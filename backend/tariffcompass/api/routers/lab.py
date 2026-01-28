"""Optimisation lab: training rounds, their report and the two-person sign-off (API_CONTRACT §1.12)."""

from __future__ import annotations

from django.db.models import Max
from django.http import HttpRequest
from ninja.responses import Status

from tariffcompass.api.routers.common import job_accepted
from tariffcompass.api.schemas.lab import LabOut, RoundOut, SignIn, StartRoundIn
from tariffcompass.api.schemas.platform import JobAccepted
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.lab import service
from tariffcompass.lab.models import TrainingRound
from tariffcompass.platform.context import ctx_of, requires
from tariffcompass.platform.models import Job

router = WireRouter()


@router.get("", response=LabOut)
@requires("lab:read")
def lab(request: HttpRequest) -> dict:
    return service.lab_out(ctx_of(request).need_org())


@router.get("/rounds/{n}", response=RoundOut)
@requires("lab:read")
def get_round(request: HttpRequest, n: int) -> dict:
    ctx = ctx_of(request)
    return service.round_out(service.get_round(ctx.need_org(), n), ctx)


@router.post("/rounds", response={202: JobAccepted})
@requires("lab:run")
def start_round(request: HttpRequest, body: StartRoundIn):
    from tariffcompass.lab.tasks import run_round

    ctx = ctx_of(request)
    org = ctx.need_org()
    if TrainingRound.objects.filter(org=org, status="training").exists():
        raise Problem(409, "conflict", "A training round is already running. One at a time.")
    n = (TrainingRound.objects.filter(org=org).aggregate(m=Max("n"))["m"] or 0) + 1
    job = Job.objects.create(
        org=org,
        kind="training_round",
        created_by=ctx.user,
        params={"round": n},
        message="Getting the rulings it hasn't seen ready…",
    )
    TrainingRound.objects.create(org=org, n=n, status="training", note=body.note, job=job, started_by=ctx.user)
    ctx.audit(
        "lab.round_started",
        f"{ctx.user.full_name} started training round {n}",
        target_type="round",
        target_id=str(n),
        details={"round": n, "note": body.note},
    )
    run_round(str(job.pk))
    return Status(202, job_accepted(job))


@router.post("/rounds/{n}/sign", response=RoundOut)
@requires("lab:sign")
def sign(request: HttpRequest, n: int, body: SignIn) -> dict:
    ctx = ctx_of(request)
    r = service.sign(ctx, service.get_round(ctx.need_org(), n), body.statement)
    return service.round_out(r, ctx)
