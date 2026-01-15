"""Broker review docket, decisions, questions and always-review rules (API_CONTRACT §1.10)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from tariffcompass.api.schemas.classify import RulingStatusOut
from tariffcompass.api.schemas.common import CodeOut, Money, Span
from tariffcompass.api.schemas.products import RulingRef
from tariffcompass.core.wire import Wire

ReviewKind = Literal["unsure", "differs", "ruling_changed", "always_review", "requested"]
ReviewStatus = Literal["waiting", "asked", "answered", "approved", "corrected", "withdrawn"]
ReasonKind = Literal["facts_differ", "ruling_elsewhere", "heading_misread", "other"]
Filter = Literal["all", "unsure", "differs", "ruling_changed", "always", "ca"]


class ReviewRow(Wire):
    id: str
    product_id: str
    sku: str
    product_title: str
    waiting_since: datetime
    waiting_label: str  # "3 days"
    into: Literal["US", "CA", "both"]
    into_label: str
    proposed_us: CodeOut | None
    proposed_ca: CodeOut | None
    kind: ReviewKind
    # "Classifier unsure" | "Differs from last code" | "Ruling changed" | "Always reviewed" | "Sent for review"
    kind_label: str
    detail: str  # one line
    value: Money | None
    with_name: str | None  # who has it
    status: ReviewStatus
    status_label: str


class DocketCounts(Wire):
    all: int
    unsure: int
    differs: int
    ruling_changed: int
    always: int
    ca: int


class DocketOut(Wire):
    counts: DocketCounts
    oldest_label: str  # "oldest 3 days"
    items: list[ReviewRow]
    total: int
    week: dict[str, int]  # {"approved": 31, "corrected": 9, "questions": 4}
    next_round: dict[str, int]  # {"round": 8, "correctionsWaiting": 23}
    empty_message: str  # "Nothing waiting for Driftwood. Northbound's next shipment books on Monday."


class DecidingPhrase(Wire):
    source: Literal["listing", "spec_sheet"]
    span: Span


class DecisionRecord(Wire):
    row: ReviewRow
    listing: str
    spec_sheet: str
    spec_sheet_file: str | None
    uploaded_by: str | None
    uploaded_at: datetime | None
    deciding_phrases: list[DecidingPhrase]
    misread: str | None  # one sentence on what the classifier misread
    previous_us: str | None  # "your last code"
    rulings_relied: list[RulingRef]
    ruling_change: RulingStatusOut | None
    rule: str | None  # the always-review rule that put it here
    answer_id: str
    questions: list[QuestionOut]


class QuestionOut(Wire):
    id: str
    asked_by: str
    asked_at: datetime
    text: str
    options: list[str]
    answer: str | None
    answered_by: str | None
    answered_at: datetime | None


class ApproveIn(Wire):
    note: str = Field(default="", max_length=1000)


class CorrectIn(Wire):
    us_code: str | None = Field(default=None, pattern=r"^[0-9.]{10,13}$")
    ca_code: str | None = Field(default=None, pattern=r"^[0-9.]{10,13}$")
    reason_kind: ReasonKind
    reason: str = Field(min_length=10, max_length=2000)
    ruling_relied: str | None = None  # ruling key
    also_change_ca: bool = False


class LessonIn(Wire):
    us_code: str | None = None
    ca_code: str | None = None
    reason_kind: ReasonKind
    reason: str = Field(default="", max_length=2000)


class LessonOut(Wire):
    lesson: (
        str  # "'Double-wall' on its own doesn't mean vacuum: look for 'vacuum-sealed' or 'only air between the walls'."
    )
    redline: list[RedlineCell]


class RedlineCell(Wire):
    index: int  # 0..9
    proposed: str
    yours: str
    changed: bool


class AskIn(Wire):
    question: str = Field(min_length=5, max_length=1000)
    options: list[str] = []


class AnswerQuestionIn(Wire):
    answer: str = Field(min_length=1, max_length=1000)


class DecisionOut(Wire):
    item: ReviewRow
    binder_version: int | None
    lesson: str | None
    toast: str  # "Corrected · NB-KT-0388 → 7323.93.00.80 · binder v3"


class RuleOut(Wire):
    id: str
    kind: Literal["heading", "chapter", "material", "value_over", "origin", "keyword"]
    kind_label: str
    value: str
    label: str  # "Anything with lithium cells", "Steel or aluminium content", "Entries over $25,000"
    active: bool
    created_by: str
    created_at: datetime
    matches: int  # products it currently routes to review


class RuleIn(Wire):
    kind: Literal["heading", "chapter", "material", "value_over", "origin", "keyword"]
    value: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=3, max_length=200)


class RulePatch(Wire):
    active: bool | None = None
    label: str | None = None


DecisionRecord.model_rebuild()
LessonOut.model_rebuild()
