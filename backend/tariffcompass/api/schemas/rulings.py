"""Rulings search, ruling detail, two-pane compare, tariff text (API_CONTRACT §1.6–1.7)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from tariffcompass.api.schemas.classify import FactCompareOut, RulingStatusOut
from tariffcompass.api.schemas.common import CountryCode, Span
from tariffcompass.core.wire import Wire


class RulingSummary(Wire):
    id: str
    key: str
    issued: date
    subject: str
    code: str  # formatted 10-digit ("9617.00.10.00"); `codeAsQuoted` keeps CBP's "9617.00.1000"
    code_as_quoted: str
    heading: str
    status: RulingStatusOut
    holding: str
    snippet: str  # plain text; marks in `snippetMarks`
    snippet_marks: list[Span]


class RelatedRuling(Wire):
    id: str
    key: str
    relation: Literal["modifies", "modified_by", "revokes", "revoked_by", "cites", "cited_by"]
    relation_label: str


class AlsoCitedIn(Wire):
    product_id: str
    sku: str
    title: str


class RulingDetail(RulingSummary):
    category: str
    codes: list[str]  # every tariff number in the letter, formatted
    text: str  # the letter
    paragraphs: list[Span]  # paragraph boundaries in `text`
    related: list[RelatedRuling]
    also_cited_in: list[AlsoCitedIn]
    source_url: str


class EvidencePane(Wire):
    kind: str
    label: str  # "Listing", "Spec sheet v3", "Supplier email"
    text: str
    marked: list[Span]


class CompareOut(Wire):
    """GET /rulings/{key}/compare?answerId=…: your product against the ruling (19 CFR 177.9(b)(1))."""

    ruling: RulingDetail
    cited_as: int | None
    product_title: str
    made_in_label: str
    rule_quote: str  # the 19 CFR 177.9(b)(1) sentence
    alignment: list[FactCompareOut]
    evidence: list[EvidencePane]
    ruling_marked: list[Span]  # supporting passages inside ruling.text, in reading order


class TariffLineOut(Wire):
    country: CountryCode
    code: str  # formatted
    digits: str
    level: str
    level_label: str
    indent: int
    text: str
    full_text: str
    unit: str
    general_rate: str
    special: str
    has_children: bool


class TariffOutline(Wire):
    line: TariffLineOut
    ancestors: list[TariffLineOut]
    children: list[TariffLineOut]
    notes: list[str]  # section and chapter notes that bear on this line
    edition_label: str  # "HTSUS 2026 Revision 3 (in force from 12 Feb 2026)" | "Customs Tariff T2026 (from 1 Jan 2026)"


class ChapterTile(Wire):
    chapter: str  # "01".."97"
    title: str
    reserved: bool  # chapter 77


class SectionOut(Wire):
    section: str  # "I".."XXI"
    title: str
    chapters: list[ChapterTile]
