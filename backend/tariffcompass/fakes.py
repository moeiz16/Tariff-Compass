"""Deterministic fakes for the five core interfaces (contracts.py).

They let the API, the seed and the web app be built and tested before the real search engine, first stage,
program, duty engine and optimiser land, and they stay as the test doubles afterwards. They know one product
family end to end (the 20 oz vacuum tumbler) plus a keyword table for a few headings; nothing here is a
measured result.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from tariffcompass import clock
from tariffcompass.contracts import (
    Candidate,
    Citation,
    Claim,
    CodeChoice,
    DepthAccuracy,
    DutyLayer,
    Fact,
    FactCompare,
    FirstStageResult,
    LandedCost,
    LandedCostQuery,
    LayerLine,
    NotApplied,
    NotNeighbour,
    PathStep,
    ProductQuery,
    ProgramAnswer,
    RoundReport,
    RoundRequest,
    RulingDoc,
    RulingHit,
    TariffAuthority,
    TariffLine,
)

KEYWORDS: dict[str, tuple[str, str]] = {  # word → (heading, chapter)
    "vacuum": ("9617", "96"),
    "tumbler": ("9617", "96"),
    "flask": ("9617", "96"),
    "bicycle": ("8512", "85"),
    "bike": ("8512", "85"),
    "torch": ("8513", "85"),
    "pullover": ("6110", "61"),
    "sweater": ("6110", "61"),
    "backpack": ("4202", "42"),
    "power bank": ("8507", "85"),
    "lithium": ("8507", "85"),
    "pot": ("7323", "73"),
}

# Real CBP rulings (CROSS), holdings quoted from the letters. HQ H303684 revoked four earlier NY rulings that had
# put insulated stainless containers in 7323 and moved them to 9617; NY N297165 is an earlier 7323 ruling on
# insulated tumblers, cited for contrast.
TUMBLER_RULINGS = (
    RulingHit(
        "NY N321134",
        date(2021, 12, 3),
        "9617001000",
        "9617",
        "The tariff classification of stainless steel bottles from China",
        "The applicable subheading for the stainless steel bottles, style numbers Y27-500 and KL13-500 will be "
        "9617.00.1000, Harmonized Tariff Schedule of the United States (HTSUS).",
        "in_force",
        bm25=14.2,
    ),
    RulingHit(
        "HQ H303684",
        date(2021, 7, 7),
        "9617001000",
        "9617",
        "Revocation of NY N297758, NY N297169, NY N254461 and NY N264760; classification of insulated stainless "
        "steel beverage containers",
        "Pursuant to GRIs 1 and 6, the stainless steel containers at issue are classified in heading 9617, "
        "specifically subheading 9617.00.10, HTSUS.",
        "in_force",
        bm25=12.9,
    ),
    RulingHit(
        "NY N297165",
        date(2018, 6, 11),
        "7323930080",
        "7323",
        "The tariff classification of insulated stainless steel beverage tumblers from China",
        "The applicable subheading for item numbers 01182, 01385, 01386, 01565 and 01730 will be 7323.93.0080, "
        "Harmonized Tariff Schedule of the United States (HTSUS).",
        "contrast",
        bm25=10.4,
    ),
)


class FakeRetriever:
    version = "fake-retriever-1"

    def rulings(self, text: str, *, headings: list[str] | None = None, k: int = 20) -> list[RulingHit]:
        hits = [h for h in TUMBLER_RULINGS if not headings or h.heading in headings or h.status == "contrast"]
        return hits[:k]

    def ruling(self, ruling_id: str) -> RulingDoc | None:
        hit = next((h for h in TUMBLER_RULINGS if h.ruling_id == ruling_id), None)
        if hit is None:
            return None
        return RulingDoc(
            hit.ruling_id,
            hit.issued,
            "Classification",
            hit.code,
            (hit.code,),
            hit.subject,
            f"{hit.subject}.\n\n{hit.holding}",
            hit.status,
            source_url=f"https://rulings.cbp.gov/ruling/{hit.ruling_id.split()[-1]}",
        )

    def tariff(self, text: str, *, country, under: str | None = None, k: int = 20) -> list[TariffLine]:
        line = self.tariff_line(country, "9617001000" if country == "US" else "9617000000")
        return [line] if line else []

    def tariff_line(self, country, code: str) -> TariffLine | None:
        if not code.startswith("9617"):
            return None
        text = "Vacuum flasks and other vacuum vessels, complete; parts thereof other than glass inners"
        if country == "US":
            return TariffLine(
                "US",
                code,
                "suffix",
                2,
                "Having a capacity not exceeding 1 liter",
                f"{text}: Vessels: Having a capacity not exceeding 1 liter",
                "No.",
                "7.2%",
                "",
            )
        return TariffLine("CA", code, "tariff_item", 0, text, text, "", "7.5%", "MXT, CEUT, CPTPT: Free")

    def tariff_children(self, country, code: str) -> list[TariffLine]:
        return []


class FakeFirstStage:
    version = "fake-first-stage-1"

    def predict(self, query: ProductQuery, k: int = 5) -> FirstStageResult:
        t0 = time.perf_counter()
        text = f"{query.text} {query.spec_sheet_text}".lower()
        found = [(w, KEYWORDS[w]) for w in KEYWORDS if w in text] or [("", ("9617", "96"))]
        heading, chapter = found[0][1]
        why = tuple((w, 1.0) for w, _ in found if w)
        return FirstStageResult(
            chapters=(Candidate(chapter, "chapter", 0.9, why),),
            headings=(Candidate(heading, "heading", 0.8, why),),
            model_version=self.version,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        )


class FakeProgram:
    version = "fake-program-1"

    def classify(self, query: ProductQuery, first_stage: FirstStageResult, retriever) -> ProgramAnswer:
        hits = retriever.rulings(query.text, headings=[first_stage.headings[0].code])
        us = CodeChoice(
            "US",
            "9617001000",
            "Vessels: Having a capacity not exceeding 1 liter",
            "Vacuum flasks and other vacuum vessels, complete; parts thereof other than glass inners",
        )
        ca = CodeChoice("CA", "9617000000", us.heading_text, us.heading_text)
        cites = tuple(
            Citation(
                i + 1,
                h,
                ("same_heading", "same_subheading") if h.heading == "9617" else ("different_heading",),
                (
                    FactCompare(
                        "Between the walls",
                        "A vacuum",
                        "A vacuum" if h.heading == "9617" else "Air",
                        "same" if h.heading == "9617" else "differs",
                    ),
                ),
                (0,) if h.heading == "9617" else (1,),
            )
            for i, h in enumerate(hits)
        )
        return ProgramAnswer(
            us=us,
            ca=ca,
            verdict="strong",
            verdict_sentence="Rulings on the same kind of article agree.",
            agreeing_rulings=sum(1 for h in hits if h.heading == "9617"),
            cited_rulings=len(hits),
            holding_sentence="The tumbler is classified in subheading 9617.00.10.00, HTSUS, and tariff item "
            "9617.00.00.00 of Canada's Customs Tariff.",
            issue="Is a double-wall stainless tumbler a vacuum vessel of heading 9617 or a steel household article "
            "of heading 7323?",
            facts=(Fact("between_walls", "Between the walls", "A vacuum", "read", "read from 'vacuum insulated'"),),
            reason=(
                Claim("Heading 9617 names vacuum vessels outright.", (1, 2)),
                Claim("A double-wall tumbler without a vacuum goes to 7323 instead.", (3,)),
            ),
            path=(
                PathStep("section", "XX", "Miscellaneous manufactured articles", "GRI 1", "Named in Section XX."),
                PathStep("chapter", "96", "Miscellaneous manufactured articles", "GRI 1", "Chapter 96 holds it."),
                PathStep(
                    "heading",
                    "9617",
                    us.heading_text,
                    "GRI 1",
                    "The heading names vacuum vessels.",
                    (1, 2),
                    (
                        NotNeighbour(
                            "7323",
                            "Table, kitchen or other household articles of iron or steel",
                            "Set aside: excluded by Section XV, Note 1",
                            3,
                        ),
                    ),
                ),
                PathStep(
                    "suffix",
                    "9617001000",
                    us.text,
                    "GRI 6",
                    "Capacity is 591 ml.",
                    country_note="Canada: 9617.00.00 is one tariff item for every capacity",
                ),
            ),
            citations=cites,
            tariff_authorities=(
                TariffAuthority("Heading 9617", us.heading_text),
                TariffAuthority(
                    "GRI 1",
                    "Classification shall be determined according to the "
                    "terms of the headings and any relative section or chapter notes",
                ),
            ),
            program_version=self.version,
            timings_ms={"program": 1.0},
        )


_MFN = {"US": {"9617001000": Decimal("0.072")}, "CA": {"9617000000": Decimal("0.075")}}


class FakeDutyEngine:
    version = "fake-duties-1"

    def landed_cost(self, query: LandedCostQuery) -> LandedCost:
        as_of = query.as_of or clock.today()
        value = query.customs_value
        rate = _MFN.get(query.country, {}).get(query.code, Decimal("0"))
        cent = Decimal("0.01")
        lines = [
            LayerLine(
                "a",
                f"{query.country}-MFN",
                "base",
                "Normal duty",
                f"{rate * 100:.1f}%",
                (value * rate).quantize(cent, ROUND_HALF_UP),
                "The tariff's own rate for this line.",
                "HTSUS 2026 Revision 3" if query.country == "US" else "Customs Tariff T2026",
                "https://hts.usitc.gov/",
                None,
                date(2026, 1, 1),
                None,
                None,
            )
        ]
        total = sum((ln.amount for ln in lines), Decimal("0"))
        return LandedCost(
            query=replace(query, as_of=as_of),
            lines=tuple(lines),
            not_applied=(NotApplied("De minimis", "De minimis ended for every country on 29 Aug 2025."),),
            charges_total=total,
            landed_total=value + total,
            per_unit=((value + total) / max(query.quantity, 1)).quantize(cent, ROUND_HALF_UP),
            effective_rate=(total / value) if value else Decimal("0"),
            questions=(),
            what_could_change=(),
            tariffs_as_of=as_of,
            snapshot="fake duty table",
        )

    def layers_in_force(self, country, as_of: date) -> list[DutyLayer]:
        return []


class FakeOptimizer:
    def run(self, request: RoundRequest, progress: object | None = None) -> RoundReport:
        return RoundReport(
            round_n=request.round_n,
            data_snapshot="0" * 64,
            test_window=(date(2024, 7, 1), date(2025, 8, 1)),
            by_depth=(
                DepthAccuracy("word_matching", 0.8, 0.6, 0.5, 0.4, 10),
                DepthAccuracy("optimised", 0.9, 0.7, 0.6, 0.5, 10),
            ),
            by_chapter=(),
            calibration={},
            citation_precision=1.0,
            latency_ms={},
            drift_psi={},
            learned=(),
            gates=(),
            program_path="",
            lm_label=request.lm_label,
            reflection_lm_label=request.reflection_lm_label,
            seed=request.seed,
        )
