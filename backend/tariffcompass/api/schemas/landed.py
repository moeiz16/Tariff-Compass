"""Landed cost and duty layers (API_CONTRACT §1.8). The UI refuses to render a row without a source and date."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from tariffcompass.api.schemas.common import CountryCode, Money
from tariffcompass.core.wire import Wire

LayerKind = Literal["base", "remedy", "emergency", "fee", "tax", "surtax", "preference"]


class LandedCostIn(Wire):
    country: CountryCode
    code: str = Field(pattern=r"^[0-9.]{4,13}$")  # dots optional
    made_in: str = Field(pattern=r"^[A-Z]{2}$")
    value: Money
    quantity: int = Field(default=1, ge=1, le=10_000_000)
    transport: Literal["ocean", "air", "truck", "rail", "courier"] = "ocean"
    usmca_answers: dict[str, bool] = {}  # keys from LandedCostOut.questions
    metal_content_value: Money | None = None  # Section 232 derivatives


class LayerLineOut(Wire):
    letter: str  # a, b, c…
    layer_id: str
    kind: LayerKind
    kind_label: str  # "Normal duty" | "Trade remedy" | "Emergency duty" | "Fee" | "Tax" | "Surtax" | "Preference"
    name: str
    rate: str  # as printed: "7.2%", "10%", "0.3464% (min $33.58, max $651.50)"
    amount: Money
    plain: str  # why it applies, one sentence
    source: str  # "EO 14357 · 90 FR 50725"
    source_url: str
    chapter99: str | None  # "9903.01.24"
    effective_from: date
    effective_to: date | None
    legal_status: str | None  # "Pending at the Supreme Court (argued 5 Nov 2025)"
    legal_status_open: bool  # draws the hatched segment and the ⚠ mark


class NotAppliedOut(Wire):
    name: str
    why: str  # "De minimis ended for every country on 29 Aug 2025 (EO 14324)."


class OriginQuestionOut(Wire):
    key: str
    question: str
    answer: bool | None


class WhatCouldChangeOut(Wire):
    label: str  # "If the pending emergency duties end"
    landed_total: Money
    charges_total: Money


class LandedCostOut(Wire):
    country: CountryCode
    country_label: str
    code: str  # formatted
    made_in: str
    made_in_label: str
    value: Money
    quantity: int
    transport: str
    transport_label: str
    lines: list[LayerLineOut]
    not_applied: list[NotAppliedOut]
    charges_total: Money
    landed_total: Money
    per_unit: Money
    effective_rate: str  # "+27.2%"
    questions: list[OriginQuestionOut]
    what_could_change: list[WhatCouldChangeOut]
    tariffs_as_of: date
    snapshot_label: str


class DutyLayerOut(Wire):
    id: str
    country: CountryCode
    kind: LayerKind
    kind_label: str
    name: str
    authority: str
    chapter99: list[str]
    scope: str
    rate: str
    effective_from: date
    effective_to: date | None
    legal_status: str | None
    legal_status_open: bool
    sources: list[str]
