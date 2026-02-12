"""In-process interfaces between the classification core and the platform (docs/API_CONTRACT.md Part 3).

The API layer only ever talks to these five protocols, obtained through `tariffcompass.services`:

    Retriever          search engine over rulings and tariff text (Tantivy BM25 + reranker)
    FirstStage         classical chapter/heading classifier (TF-IDF linear models + LightGBM)
    ClassifierProgram  the DSPy program (candidate headings → GRI reasoning → subheading → citations → confidence)
    DutyEngine         landed cost from dated duty layers
    Optimizer          one training round: GEPA over rulings + broker corrections, evaluated on newer rulings

Value objects are frozen dataclasses with snake_case fields; the API maps them to camelCase wire schemas
(`tariffcompass.api.schemas`). Deterministic fakes for all five live in `tariffcompass.fakes`.
Codes are always digits only here (`9617001000`); formatting (`9617.00.10.00`) happens at the edge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

Country = Literal["US", "CA"]
Level = Literal["section", "chapter", "heading", "subheading", "tariff_item", "suffix"]
Verdict = Literal["strong", "broker"]
FactSource = Literal["stated", "read", "assumed", "unknown"]
RulingStatusKind = Literal["in_force", "modified", "revoked", "contrast"]
Match = Literal["same", "close", "differs"]
Gri = Literal[
    "GRI 1", "GRI 2(a)", "GRI 2(b)", "GRI 3(a)", "GRI 3(b)", "GRI 3(c)", "GRI 4", "GRI 5(a)", "GRI 5(b)", "GRI 6"
]
LayerKind = Literal["base", "remedy", "emergency", "fee", "tax", "surtax", "preference"]
Transport = Literal["ocean", "air", "truck", "rail", "courier"]


# ── Inputs ──────────────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ProductQuery:
    """Everything known about the product when it is classified."""

    text: str  # the description or listing the user typed or pasted
    made_in: str = "CN"  # ISO 3166 alpha-2 (CN, VN, MX, DE, IT…)
    into: tuple[Country, ...] = ("US", "CA")
    spec_sheet_text: str = ""  # extracted from a PDF (pypdf)
    photo_facts: tuple[str, ...] = ()  # sentences from the vision adapter
    confirmed_facts: tuple[tuple[str, str], ...] = ()  # (fact key, answer) from "the fact that decides it"
    product_id: str | None = None


# ── Search engine ───────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Span:
    start: int  # character offsets into the passage or letter
    end: int


@dataclass(frozen=True)
class RulingHit:
    ruling_id: str  # "NY N321134", "HQ H303684"
    issued: date
    code: str  # digits as stated in the ruling (10 when available)
    heading: str  # first 4 digits
    subject: str  # one line ("The tariff classification of a vacuum-insulated tumbler from China")
    holding: str  # the classification sentence from the letter
    status: RulingStatusKind
    status_by: str | None = None  # ruling id that modified or revoked it
    status_date: date | None = None
    bm25: float = 0.0
    rerank: float = 0.0
    passages: tuple[tuple[str, tuple[Span, ...]], ...] = ()  # (passage text, marked spans)


@dataclass(frozen=True)
class RulingDoc:
    ruling_id: str
    issued: date
    category: str  # "Classification"
    code: str
    codes: tuple[str, ...]  # every tariff number the ruling mentions
    subject: str
    text: str  # the full letter
    status: RulingStatusKind
    status_by: str | None = None
    status_date: date | None = None
    related: tuple[str, ...] = ()
    source_url: str = ""  # https://rulings.cbp.gov/ruling/N321134


@dataclass(frozen=True)
class TariffLine:
    country: Country
    code: str  # digits; 4 = heading, 6 = subheading, 8/10 = tariff item / statistical
    level: Level
    indent: int
    text: str  # the article description as printed
    full_text: str  # the description with its superior lines joined ("Vacuum flasks…: Vessels: Having a capacity…")
    unit: str = ""
    general_rate: str = ""  # US column 1 General / CA MFN, as printed ("7.2%", "Free")
    special: str = ""  # US special programs / CA preferential treatments, as printed
    notes: tuple[str, ...] = ()  # section/chapter notes relevant to this line


@runtime_checkable
class Retriever(Protocol):
    version: str

    def rulings(self, text: str, *, headings: list[str] | None = None, k: int = 20) -> list[RulingHit]: ...

    def ruling(self, ruling_id: str) -> RulingDoc | None: ...

    def tariff(self, text: str, *, country: Country, under: str | None = None, k: int = 20) -> list[TariffLine]: ...

    def tariff_line(self, country: Country, code: str) -> TariffLine | None: ...

    def tariff_children(self, country: Country, code: str) -> list[TariffLine]: ...


# ── First stage ─────────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Candidate:
    code: str  # 2-digit chapter or 4-digit heading
    level: Level
    probability: float  # calibrated
    why_terms: tuple[tuple[str, float], ...] = ()  # top contributing words (coefficients / LightGBM contributions)


@dataclass(frozen=True)
class FirstStageResult:
    chapters: tuple[Candidate, ...]  # sorted, top-k
    headings: tuple[Candidate, ...]
    model_version: str
    elapsed_ms: float


@runtime_checkable
class FirstStage(Protocol):
    version: str

    def predict(self, query: ProductQuery, k: int = 5) -> FirstStageResult: ...


# ── The program ─────────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CodeChoice:
    country: Country
    code: str  # 10 digits
    text: str  # the line's description (full_text)
    heading_text: str  # the 4-digit heading's text, quoted in the holding band


@dataclass(frozen=True)
class Fact:
    key: str  # "between_walls"
    label: str  # "Between the walls"
    value: str  # "A vacuum"
    source: FactSource
    source_note: str  # "read from 'insulated'" / "your description" / "not stated"
    decides: bool = False  # the fact that decides it (needs a broker)


@dataclass(frozen=True)
class DecidingQuestion:
    fact_key: str
    question: str  # "Is it made only to ride on the bike, or does it also work as a hand torch?"
    options: tuple[tuple[str, str, str], ...]  # (answer key, label, code it leads to)


@dataclass(frozen=True)
class Claim:
    text: str  # one plain sentence
    cites: tuple[int, ...]  # citation numbers [1], [2]
    marked: tuple[Span, ...] = ()  # words briefly marked when its citation lands


@dataclass(frozen=True)
class NotNeighbour:
    code: str
    text: str
    reason: str  # "Set aside: excluded by Section XV, Note 1"
    cite: int | None = None


@dataclass(frozen=True)
class PathStep:
    level: Level
    code: str  # "XX", "96", "9617", "9617.00", "9617.00.10", "9617.00.10.00" as digits
    text: str
    gri: Gri
    why: str  # the reasoning in plain words
    cites: tuple[int, ...] = ()
    not_neighbours: tuple[NotNeighbour, ...] = ()
    country_note: str | None = None  # "Canada: 9617.00.00 is one tariff item for every capacity"


@dataclass(frozen=True)
class FactCompare:
    fact: str
    yours: str
    theirs: str
    match: Match


@dataclass(frozen=True)
class Citation:
    n: int
    ruling: RulingHit
    match: tuple[str, ...]  # ("same_heading", "same_subheading") or ("different_heading",)
    fact_compare: tuple[FactCompare, ...]
    supports: tuple[int, ...]  # indexes of the claims (In short) that cite it


@dataclass(frozen=True)
class TariffAuthority:
    ref: str  # "Heading 9617", "Section XV, Note 1", "GRI 1", "GRI 6"
    quote: str


@dataclass(frozen=True)
class ProgramAnswer:
    us: CodeChoice | None
    ca: CodeChoice | None
    verdict: Verdict
    verdict_sentence: str
    agreeing_rulings: int  # rulings that reach the same heading
    cited_rulings: int
    holding_sentence: str
    issue: str
    facts: tuple[Fact, ...]
    reason: tuple[Claim, ...]  # "In short"
    path: tuple[PathStep, ...]  # US path; CA divergence in country_note
    citations: tuple[Citation, ...]
    tariff_authorities: tuple[TariffAuthority, ...]
    alternative: CodeChoice | None = None  # "Also possible…"
    duty_at_stake: str | None = None  # "about 10 points"
    deciding_question: DecidingQuestion | None = None
    # the confidence word per depth, each calibrated on validation: (("heading", "strong"), ("full_code", "broker"));
    # `verdict` is the full-code word. Empty when no per-depth calibration exists.
    verdict_by_depth: tuple[tuple[str, Verdict], ...] = ()
    lm_label: str = "offline simulator"  # which LM produced it: shown in the Lab and stored on the answer
    program_version: str = ""
    timings_ms: dict[str, float] = field(default_factory=dict)


@runtime_checkable
class ClassifierProgram(Protocol):
    version: str

    def classify(self, query: ProductQuery, first_stage: FirstStageResult, retriever: Retriever) -> ProgramAnswer: ...


# ── Landed cost ─────────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DutyLayer:
    """One dated layer from duties/data/layers.json (every rate has a source and an effective date)."""

    id: str
    country: Country
    kind: LayerKind
    name: str
    authority: str
    chapter99: tuple[str, ...]
    effective_from: date
    effective_to: date | None
    legal_status: str | None  # "Pending at the Supreme Court (argued 5 Nov 2025)"
    sources: tuple[str, ...]


@dataclass(frozen=True)
class LandedCostQuery:
    country: Country
    code: str  # 10 digits
    made_in: str
    customs_value: Decimal
    currency: str = "USD"
    quantity: int = 1
    transport: Transport = "ocean"
    usmca_answers: tuple[tuple[str, bool], ...] = ()
    metal_content_value: Decimal | None = None  # Section 232 derivatives pay on the metal content
    as_of: date | None = None  # defaults to clock.today()


@dataclass(frozen=True)
class LayerLine:
    letter: str  # a, b, c… (the receipt's lettering)
    layer_id: str
    kind: LayerKind
    name: str
    rate: str  # "7.2%", "25%", "0.3464% (min $33.58, max $651.50)"
    amount: Decimal
    plain: str  # why it applies, in one sentence
    source: str  # "HTSUS 2026 Rev. 3, heading 9617" / "EO 14357; 90 FR 50725"
    source_url: str
    chapter99: str | None
    effective_from: date
    effective_to: date | None
    legal_status: str | None


@dataclass(frozen=True)
class NotApplied:
    name: str
    why: str


@dataclass(frozen=True)
class OriginQuestion:
    key: str
    question: str
    answer: bool | None


@dataclass(frozen=True)
class LandedCost:
    query: LandedCostQuery
    lines: tuple[LayerLine, ...]
    not_applied: tuple[NotApplied, ...]
    charges_total: Decimal
    landed_total: Decimal
    per_unit: Decimal
    effective_rate: Decimal  # charges / value, as a fraction
    questions: tuple[OriginQuestion, ...]  # USMCA / CUSMA origin questions when they matter
    what_could_change: tuple[tuple[str, Decimal], ...]  # ("If the pending emergency duties end", 1881.25)
    tariffs_as_of: date
    snapshot: str  # "HTSUS 2026 Revision 3 · Customs Tariff T2026 · duty layers as of 19 Feb 2026"


@runtime_checkable
class DutyEngine(Protocol):
    version: str

    def landed_cost(self, query: LandedCostQuery) -> LandedCost: ...

    def layers_in_force(self, country: Country, as_of: date) -> list[DutyLayer]: ...


# ── Optimisation (training rounds) ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RoundRequest:
    round_n: int
    seed: int
    train_ids: tuple[str, ...]
    val_ids: tuple[str, ...]
    test_ids: tuple[str, ...]  # newest rulings: never seen in training
    corrections: tuple[dict, ...] = ()  # broker corrections (review.TrainingExample) as extra labelled examples
    budget_metric_calls: int = 600
    lm_label: str = "offline simulator"
    reflection_lm_label: str = "offline simulator"


@dataclass(frozen=True)
class DepthAccuracy:
    system: Literal["word_matching", "unoptimised", "optimised", "live"]
    chapter: float
    heading: float
    subheading: float  # 6 digits
    full_code: float  # 10 digits
    n: int


@dataclass(frozen=True)
class RoundReport:
    round_n: int
    data_snapshot: str  # sha256 over the sorted train/val/test ids and the ruling texts' hashes
    test_window: tuple[date, date]
    by_depth: tuple[DepthAccuracy, ...]
    by_chapter: tuple[dict, ...]  # {chapter, tested, before, after, newRulings, moving}
    calibration: dict  # {strong: {said, right}, broker: {said, firstGuessWrong}}
    citation_precision: float
    latency_ms: dict  # {firstStageP95, answerP95}
    drift_psi: dict  # chapter-mix PSI, train vs newest rulings
    learned: tuple[str, ...]  # sentences from broker corrections
    gates: tuple[dict, ...]  # {name, passed, value, threshold, plain}
    program_path: str  # optimised program JSON (committed for the demo round)
    lm_label: str
    reflection_lm_label: str
    seed: int


@runtime_checkable
class Optimizer(Protocol):
    def run(self, request: RoundRequest, progress: object | None = None) -> RoundReport: ...
