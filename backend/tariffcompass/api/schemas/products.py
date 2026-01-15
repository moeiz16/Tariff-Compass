"""Products and the reasonable-care binder (API_CONTRACT §1.9)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from tariffcompass.api.schemas.classify import EvidenceOut
from tariffcompass.api.schemas.common import Money, PersonRef
from tariffcompass.core.wire import Wire

Category = Literal["outdoor", "electronics", "apparel", "kitchen", "bags", "other"]
Standing = Literal["proposed", "in_review", "approved", "needs_recheck", "withdrawn"]
VersionKind = Literal["proposed", "question_answered", "approved", "corrected", "re_approved", "withdrawn"]


class ProductSummary(Wire):
    id: str
    sku: str  # "NB-KT-0412"
    title: str
    category: Category
    category_label: str
    made_in: str
    made_in_label: str
    us_code: str | None
    ca_code: str | None
    standing: Standing
    standing_label: str
    versions: int
    last_decided_at: datetime | None
    in_review: bool


class ProductIn(Wire):
    sku: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=2, max_length=200)
    category: Category
    made_in: str = Field(pattern=r"^[A-Z]{2}$")
    listing_text: str = Field(default="", max_length=8000)
    unit_value: Money | None = None


class ProductPatch(Wire):
    title: str | None = None
    category: Category | None = None
    made_in: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    listing_text: str | None = None
    unit_value: Money | None = None


class ProductDetail(ProductSummary):
    listing_text: str
    unit_value: Money | None
    evidence: list[EvidenceOut]
    latest_answer_id: str | None


class RulingRef(Wire):
    id: str
    key: str
    status_label: str


class DecidingFactCell(Wire):
    label: str  # "Between the walls"
    value: str  # "A vacuum"
    source_note: str  # "read from 'insulated'" → "confirmed by the supplier"


class BinderVersion(Wire):
    """One column of the revision matrix. `changed` lists the rows that differ from the previous version."""

    n: int
    kind: VersionKind
    kind_label: str  # "Proposed" | "Question answered" | "Approved" | "Corrected" | "Re-approved"
    at: datetime
    us_code: str | None
    ca_code: str | None
    standing: Standing
    standing_label: str
    deciding_fact: DecidingFactCell | None
    evidence: list[str]  # labels ("Spec sheet v3", "Supplier email 14 Jan")
    rulings_relied: list[RulingRef]
    decided_by: PersonRef | None
    why: str
    fingerprint: str  # short audit fingerprint ("3f9a·c1d2·7be0")
    current: bool
    changed: list[
        Literal["usCode", "caCode", "standing", "decidingFact", "evidence", "rulingsRelied", "decidedBy", "why"]
    ]


class EntryOut(Wire):
    entry_number: str
    country: Literal["US", "CA"]
    entered_on: date
    code: str
    duty_paid: Money


class RecordOut(Wire):
    chain_verified: bool
    checked_at: datetime
    events: int
    fingerprint: str


class ApprovalStamp(Wire):
    by: PersonRef
    at: datetime
    version: int
    sentence: str  # "Approved by Dana Whitlock, licensed customs broker, Driftwood · 17 Feb 2026, 10:12 PT · version 4"


class BinderOut(Wire):
    product: ProductSummary
    opened_on: date
    kept_until: date  # five years after the latest entry (19 CFR 163.4)
    retention_note: str
    versions: list[BinderVersion]  # oldest first (matrix columns)
    approval: ApprovalStamp | None
    evidence: list[EvidenceOut]
    entries: list[EntryOut]
    record: RecordOut
    advance_ruling: str | None  # "Draft a CBSA advance ruling request (Memorandum D11-11-3)…"


class ExportIn(Wire):
    format: Literal["pdf", "zip"]


class ExportResult(Wire):
    download_url: str
    file_name: str
    bytes: int
    pages: int | None
    fingerprint: str  # sha256 of the file, short form; also printed on every PDF page
    record_fingerprint: str  # the audit-chain head at export time
