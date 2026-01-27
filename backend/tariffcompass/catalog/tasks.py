"""Catalog background jobs (autodiscovered by `manage.py run_huey`): binder exports."""

from __future__ import annotations

from typing import Any

from huey.contrib.djhuey import db_task

from tariffcompass.jobs import Progress, run_job
from tariffcompass.platform.models import Job


@db_task()
def export_binder(job_id: str) -> dict[str, Any]:
    def work(progress: Progress) -> dict[str, Any]:
        from tariffcompass.catalog.export import export
        from tariffcompass.catalog.models import Product
        from tariffcompass.platform import audit

        job = Job.objects.get(pk=job_id)
        product = Product.objects.select_related("org").get(pk=job.params["product"], org=job.org)
        fmt = job.params.get("format", "pdf")
        progress(0.2, "binder", "Putting the binder together…")
        result = export(product, fmt, job_id)
        path = result.pop("path")
        Job.objects.filter(pk=job_id).update(params={**job.params, "path": path})
        progress(0.9, "record", "Recording the export in the activity record…")
        audit.record(
            product.org,
            "binder.exported",
            f"Exported the {product.sku} binder as {fmt.upper()} (fingerprint {result['fingerprint']})",
            actor=job.created_by,
            actor_role=job.created_by.memberships.filter(org=product.org).values_list("role", flat=True).first() or ""
            if job.created_by
            else "",
            target_type="product",
            target_id=str(product.pk),
            details={"label": product.sku, "format": fmt, "sha256Short": result["fingerprint"]},
        )
        return result

    return run_job(job_id, work)
