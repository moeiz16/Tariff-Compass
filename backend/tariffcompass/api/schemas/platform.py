"""Meta, settings, activity, jobs (API_CONTRACT §1.4, §1.13–1.16)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from tariffcompass.api.schemas.common import ClockOut, CountryCode, Labelled
from tariffcompass.core.wire import Wire


class SnapshotOut(Wire):
    us_hts: str  # "HTSUS 2026 Revision 3"
    us_hts_in_force: tuple[date, date | None]  # (2026-02-12, None): no end date was published on the demo day
    ca_tariff: str  # "Customs Tariff T2026"
    ca_tariff_from: date
    duty_layers_as_of: date
    rulings_count: int
    rulings_newest: date | None
    label: str  # "Tariffs as of Thu 19 Feb 2026"


class MetaOut(Wire):
    product: str
    version: str
    clock: ClockOut
    snapshot: SnapshotOut
    scopes: list[Labelled]
    labels: dict[str, dict[str, str]]  # static dictionaries: verdicts, factSources, rulingStatuses, …
    origins: list[Labelled]  # CN China, VN Vietnam, MX Mexico, DE Germany, IT Italy…


class ScopeCounts(Wire):
    rulings: int
    products: int
    review: int
    watch: int


class OrgSettingsOut(Wire):
    into: list[CountryCode]
    made_in: str
    ports: list[str]  # "Seattle (3001)", "Vancouver (809)"
    always_send_to_broker: bool
    retention_years: int  # US: five years from the date of entry (19 CFR 163.4)
    retention_years_ca: int = 6  # Canada: six years following importation (CBSA Memorandum D17-1-21)
    retention_note: str = ""  # both rules in one sentence
    deleting_note: str  # "Deleting hides a record; it is kept until its retention date."
    broker_name: str | None


class OrgSettingsPatch(Wire):
    into: list[CountryCode] | None = None
    made_in: str | None = None
    ports: list[str] | None = None
    always_send_to_broker: bool | None = None


class AuditRow(Wire):
    id: int
    at: datetime
    actor_name: str
    actor_role: str
    actor_role_label: str
    action: str
    action_label: str  # "Corrected a code"
    summary: str
    target_type: str
    target_id: str
    target_label: str
    fingerprint: str


class ChainOut(Wire):
    ok: bool
    events: int
    broken_at: int | None
    checked_at: datetime
    sentence: str  # "Chain verified 19 Feb, 10:30"


class JobOut(Wire):
    id: str
    kind: Literal["classify", "training_round", "index_build", "watch_scan", "binder_export", "ingest"]
    kind_label: str
    status: Literal["queued", "running", "succeeded", "failed"]
    status_label: str
    progress: float
    stage: str
    message: str  # "Reading the heading texts and section notes, then checking 214 rulings…"
    result: dict[str, Any]
    error: str
    created_at: datetime
    finished_at: datetime | None


class JobAccepted(Wire):
    job_id: str
    status_url: str  # /api/v1/jobs/{id}
    events_url: str  # /api/v1/jobs/{id}/events (SSE)


class HealthOut(Wire):
    status: Literal["ok", "degraded"]
    version: str
    now: str
    checks: dict[str, str]
