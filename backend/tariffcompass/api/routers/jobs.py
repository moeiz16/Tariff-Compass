"""Job progress (API_CONTRACT §1.15): polling and Server-Sent Events.

The stream sends `progress` whenever the row changes, then `done` or `failed`, with a comment heartbeat every
15 s; it closes after the final event or 300 s (clients reconnect with `Last-Event-ID`). Jobs belong to an
organisation: another organisation's job id is a 404.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, StreamingHttpResponse
from pydantic.alias_generators import to_camel

from tariffcompass.api import labels
from tariffcompass.api.schemas.platform import JobOut
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform.context import Ctx, ctx_of, is_uuid, signed_in
from tariffcompass.platform.models import Job

router = WireRouter()


def job_out(job: Job) -> dict[str, Any]:
    return {
        "id": str(job.pk),
        "kind": job.kind,
        "kind_label": labels.JOB_KINDS.get(job.kind, job.kind),
        "status": job.status,
        "status_label": labels.JOB_STATUSES.get(job.status, job.status),
        "progress": round(float(job.progress), 4),
        "stage": job.stage,
        "message": job.message,
        "result": job.result or {},
        "error": job.error,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
    }


def _wire(job: Job) -> str:
    return json.dumps({to_camel(k): v for k, v in job_out(job).items()}, cls=DjangoJSONEncoder)


def visible_job(ctx: Ctx, job_id: str) -> Job:
    job = Job.objects.filter(pk=job_id).first() if is_uuid(job_id) else None
    if job is None:
        raise Problem(404, "not_found", "We couldn't find that job.")
    if job.org_id is not None:
        if ctx.org is None or job.org_id != ctx.org.pk:
            raise Problem(404, "not_found", "We couldn't find that job.")
    elif job.created_by_id != ctx.user.pk:
        raise Problem(404, "not_found", "We couldn't find that job.")
    return job


@router.get("/{job_id}", response=JobOut)
@signed_in
def get_job(request: HttpRequest, job_id: str) -> dict:
    return job_out(visible_job(ctx_of(request), job_id))


async def _events(job_id: str, last_seen: str) -> AsyncIterator[str]:
    cfg = settings.TARIFF_COMPASS
    poll = float(cfg["SSE_POLL_SECONDS"])
    beat = float(cfg["SSE_HEARTBEAT_SECONDS"])
    limit = float(cfg["SSE_MAX_SECONDS"])
    started = last_beat = time.monotonic()
    seq = int(last_seen) if last_seen.isdigit() else 0
    previous = ""
    yield "retry: 2000\n\n"
    get = sync_to_async(lambda: Job.objects.filter(pk=job_id).first())
    while True:
        job = await get()
        if job is None:
            return
        payload = _wire(job)
        if payload != previous:
            previous = payload
            seq += 1
            kind = {"succeeded": "done", "failed": "failed"}.get(job.status, "progress")
            yield f"id: {seq}\nevent: {kind}\ndata: {payload}\n\n"
            if kind != "progress":
                return
        now = time.monotonic()
        if now - started > limit:
            return
        if now - last_beat >= beat:
            last_beat = now
            yield ": still working\n\n"
        await asyncio.sleep(poll)


@router.get("/{job_id}/events")
@signed_in
def job_events(request: HttpRequest, job_id: str) -> StreamingHttpResponse:
    job = visible_job(ctx_of(request), job_id)
    resp = StreamingHttpResponse(
        _events(str(job.pk), request.headers.get("Last-Event-ID", "")), content_type="text/event-stream"
    )
    resp["Cache-Control"] = "no-cache, no-transform"
    resp["X-Accel-Buffering"] = "no"
    return resp
