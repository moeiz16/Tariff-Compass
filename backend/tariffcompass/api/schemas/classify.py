"""Classify, answers, evidence uploads (API_CONTRACT §1.5). Mirrors frontend/DESIGN.md §13 data contracts."""

from __future__ import annotations

import datetime as dt
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from tariffcompass.api.schemas.common import CodeOut, CountryCode, Money, Span
from tariffcompass.api.schemas.landed import LandedCostOut
from tariffcompass.core.wire import Wire

VerdictWord = Literal["strong", "broker"]
FactSource = Literal["stated", "read", "assumed", "unknown"]
RulingStatusKind = Literal["in_force", "modified", "revoked", "contrast"]
MatchWord = Literal["same", "close", "differs"]
Level = Literal["section", "chapter", "heading", "subheading", "tariff_item", "suffix"]


class ShipmentIn(Wire):
    value: Money
    quantity: int = Field(default=1, ge=1, le=10_000_000)
    transport: Literal["ocean", "air", "truck", "rail", "courier"] = "ocean"


class ClassifyIn(Wire):
    text: str = Field(min_length=3, max_length=8000)  # description, listing or pasted text
    made_in: str = Field(default="CN", pattern=r"^[A-Z]{2}$")
    into: list[CountryCode] = ["US", "CA"]
    product_id: str | None = None  # classify an existing product (its evidence is used too)
    evidence_ids: list[str] = []  # spec sheets / photos uploaded through POST /evidence
    confirmed_facts: list[ConfirmedFact] = []
    shipment: ShipmentIn | None = None  # for ¶4; else the product's last shipment; else omitted


class ConfirmedFact(Wire):
    key: str
    answer: str  # an option key from decidingQuestion.options, or free text for ¶1 confirm boxes


class EvidenceOut(Wire):
    id: str
    kind: Literal["spec_sheet", "photo", "listing", "supplier_email", "other"]
    kind_label: str
    file_name: str
    pages: int | None = None
    extracted_text: str = ""  # spec sheet text (first 4,000 characters)
    photo_facts: list[str] = []  # from the photo reader
    certain: bool = True  # False: the reader could not see product details
    sha256: str
    uploaded_by: str
    uploaded_at: datetime


class AgreementSegment(Wire):
    n: int
    kind: Literal["same", "contrast", "differs"]


class VerdictOut(Wire):
    word: VerdictWord
    word_label: str  # "Strong match" | "Needs a broker"
    sentence: str
    agreeing: int  # rulings reaching the same heading ("5 of 6")
    cited: int
    in_force: int  # "still in force 5 of 6"
    agreement_bar: list[AgreementSegment]


class AlternativeOut(Wire):
    code: CodeOut
    condition: str  # "if the torch use is real"
    duty_at_stake: str | None = None  # "about 10 points"


class QuestionOption(Wire):
    key: str
    label: str
    leads_to: str | None = None  # formatted code


class DecidingQuestionOut(Wire):
    fact_key: str
    question: str
    options: list[QuestionOption]
    not_sure_label: str  # "Not sure: send to Driftwood"


class FactOut(Wire):
    key: str
    label: str
    value: str
    source: FactSource
    source_label: str  # "Stated" | "Read from the text" | "Assumed" | "Not stated"
    source_note: str  # "read from 'insulated'"
    decides: bool = False


class ClaimOut(Wire):
    text: str
    cites: list[int]
    marked: list[Span] = []


class NotNeighbourOut(Wire):
    code: str
    text: str
    reason: str
    cite: int | None = None


class PathStepOut(Wire):
    level: Level
    level_label: str  # "Section" | "Chapter" | "Heading" | "Subheading" | "Statistical suffix"
    code: str  # formatted for its level ("XX", "96", "9617", "9617.00", "9617.00.10.00")
    text: str
    gri: str  # "GRI 1"
    gri_label: str  # the rule in plain words, for the tooltip
    why: str
    cites: list[int] = []
    not_neighbours: list[NotNeighbourOut] = []
    country_note: str | None = None


class RulingStatusOut(Wire):
    kind: RulingStatusKind
    kind_label: str  # "In force" | "Modified" | "Revoked" | "Cited for contrast"
    text: str  # "Revoked by HQ H303684, 7 Jul 2021"
    by_id: str | None = None
    date: dt.date | None = None


class FactCompareOut(Wire):
    fact: str
    yours: str
    theirs: str
    match: MatchWord
    match_label: str  # "Same" | "Close" | "Differs"


class CitedRulingOut(Wire):
    n: int
    id: str  # "NY N321134"
    key: str  # "ny-n338211" (path segment)
    date: dt.date
    subject: str
    status: RulingStatusOut
    holding: str
    marked_spans: list[Span]  # inside `holding`
    match: list[Literal["same_heading", "same_subheading", "different_heading"]]
    match_labels: list[str]
    fact_compare: list[FactCompareOut]
    supports: list[int]  # indexes into `reason`
    url: str  # CBP CROSS


class TariffAuthorityOut(Wire):
    ref: str
    quote: str


class Provenance(Wire):
    """Which versions produced the answer. Shown only in the binder export and the Lab, in plain words."""

    classifier_round: int | None
    first_stage_version: str
    search_version: str
    lm_label: str  # "offline simulator" or the cloud LM id; never rendered in the product UI


class AnswerOut(Wire):
    id: str
    query: ClassifyIn
    made_in_label: str
    created_at: datetime
    created_by: str | None
    tariffs_as_of: date
    snapshot_label: str  # "HTSUS 2026 Revision 3 · Customs Tariff 2026"
    sample: bool = False  # public sample answer (landing banner)
    us: CodeOut | None
    ca: CodeOut | None
    verdict: VerdictOut
    alternative: AlternativeOut | None = None
    deciding_question: DecidingQuestionOut | None = None
    holding_sentence: str
    issue: str
    facts: list[FactOut]
    reason: list[ClaimOut]  # ¶0 In short
    path: list[PathStepOut]  # ¶3 Law and analysis
    rulings: list[CitedRulingOut]  # numbered citations [1]…[n]
    tariff_authorities: list[TariffAuthorityOut]  # ¶5
    landed: list[LandedCostOut] = []  # ¶4, one per country in `into`, when a shipment is known
    product_id: str | None = None
    review_item_id: str | None = None
    provenance: Provenance
    timings: dict[str, float]  # {"firstStageMs": 3.1, "totalMs": 212.0}


class AnswerSummary(Wire):
    id: str
    query_text: str
    us_code: str | None
    ca_code: str | None
    verdict: VerdictWord
    verdict_label: str
    created_at: datetime
    created_by: str


class SaveToBinderIn(Wire):
    product_id: str | None = None  # existing product
    new_product: NewProductIn | None = None


class NewProductIn(Wire):
    sku: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=2, max_length=200)
    category: Literal["outdoor", "electronics", "apparel", "kitchen", "bags", "other"]
    made_in: str = Field(pattern=r"^[A-Z]{2}$")
    unit_value: Money | None = None


class SendToBrokerIn(Wire):
    note: str = Field(default="", max_length=1000)


class CitationFeedbackIn(Wire):
    reason: str = Field(min_length=3, max_length=500)  # "This ruling doesn't apply"


ClassifyIn.model_rebuild()
SaveToBinderIn.model_rebuild()


class PublicClassifyIn(Wire):
    text: str = Field(min_length=3, max_length=8000)


class SampleOut(Wire):
    key: str  # "tumbler"
    title: str
    made_in: str
    query: str
