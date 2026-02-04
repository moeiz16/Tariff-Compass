"""The classifier program: a DSPy module whose instructions GEPA optimises (ADR 0003).

Five modules, run in order on the first stage's candidates and the search engine's rulings:
1. CandidateHeadings  - which headings could hold the product (from the first stage's top-k and the tariff text)
2. GriReasoning       - apply GRI 1 (headings and notes) and, only when needed, GRI 2-5; say why each
                        neighbour is set aside
3. ChooseSubheading   - GRI 6 down to the 10-digit line, US and Canada separately
4. SelectCitations    - pick the rulings that support each sentence; never cite a revoked ruling as support
5. Confidence         - "strong" or "broker", the deciding fact and the question that would settle it
The signatures below are the contract between the program and the offline simulator's policies
(`adapters/lm_sim.py`); the text blocks each module reads are rendered by `classify/evidence.py`.

`build_evidence()` gathers everything the modules read (first-stage candidates, ruling votes, rulings per
candidate heading, the tariff lines under each heading), so the same evidence drives a live answer, a GEPA
training example and an evaluation example. `assemble()` turns the modules' outputs into the `ProgramAnswer`
the API shows: holding band, facts, issue, the path with the GRI and the neighbours set aside at each step,
numbered citations with a fact-by-fact comparison, and the tariff authorities relied on.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import dspy
from django.conf import settings

from tariffcompass import codes
from tariffcompass.classify import evidence as ev
from tariffcompass.classify import facts as facts_mod
from tariffcompass.contracts import (
    Citation,
    Claim,
    ClassifierProgram,
    CodeChoice,
    DecidingQuestion,
    FirstStageResult,
    NotNeighbour,
    PathStep,
    ProductQuery,
    ProgramAnswer,
    Retriever,
    RulingHit,
    TariffAuthority,
)
from tariffcompass.search.sections import chapter_title, section_of


class CandidateHeadings(dspy.Signature):
    """Given a product description and candidate tariff headings with their texts, list the headings that could
    classify the product, most likely first, with one plain sentence each."""

    product: str = dspy.InputField(desc="description, spec sheet text and photo facts")
    candidates: str = dspy.InputField(desc="candidate headings with their official texts")
    headings: str = dspy.OutputField(desc="comma-separated four-digit headings, most likely first")
    rationale: str = dspy.OutputField(desc="one sentence per heading")


class GriReasoning(dspy.Signature):
    """Apply the General Rules of Interpretation in order. Use GRI 1 (heading texts and section and chapter
    notes) first; go to GRI 2-5 only when GRI 1 cannot decide. Explain why each neighbouring heading is set aside."""

    product: str = dspy.InputField()
    headings: str = dspy.InputField(desc="candidate headings with texts and relevant notes")
    rulings: str = dspy.InputField(desc="numbered rulings with their holdings")
    heading: str = dspy.OutputField(desc="the chosen four-digit heading")
    gri: str = dspy.OutputField(desc="the rule that decides it, e.g. GRI 1")
    set_aside: str = dspy.OutputField(desc="one line per neighbour: code | reason | ruling number or none")
    facts: str = dspy.OutputField(desc="one line per fact: key | value | stated, read, assumed or unknown")


class ChooseSubheading(dspy.Signature):
    """Within the chosen heading, compare subheadings at the same level only (GRI 6) and pick the ten-digit line."""

    product: str = dspy.InputField()
    lines: str = dspy.InputField(desc="the heading's indented lines with codes")
    country: str = dspy.InputField(desc="US or CA")
    code: str = dspy.OutputField(desc="ten digits, no dots")
    why: str = dspy.OutputField()


class SelectCitations(dspy.Signature):
    """Write the answer in three or four plain sentences and cite, for each sentence, the rulings that support it.
    A revoked ruling may only be cited for contrast."""

    product: str = dspy.InputField()
    decision: str = dspy.InputField(desc="chosen codes, path and set-aside neighbours")
    rulings: str = dspy.InputField(desc="numbered rulings with holdings and status")
    sentences: str = dspy.OutputField(desc="one sentence per line ending with citation numbers like [1][2]")


class Confidence(dspy.Signature):
    """Decide whether the answer is a strong match or needs a broker. If it needs a broker, name the single fact
    that would decide it and ask it as a question with two answers."""

    product: str = dspy.InputField()
    decision: str = dspy.InputField()
    agreement: str = dspy.InputField(desc="how many cited rulings reach the same heading")
    verdict: str = dspy.OutputField(desc="strong or broker")
    deciding_fact: str = dspy.OutputField(desc="fact key, or none")
    question: str = dspy.OutputField(desc="the question that would settle it, or none")


PROGRAM_VERSION = "program-5m-1"


class TariffProgram(dspy.Module):
    """The five modules over one evidence bundle (JSON, from `build_evidence`)."""

    def __init__(self) -> None:
        super().__init__()
        self.candidates = dspy.Predict(CandidateHeadings)
        self.gri = dspy.Predict(GriReasoning)
        self.subheading = dspy.Predict(ChooseSubheading)
        self.cite = dspy.Predict(SelectCitations)
        self.confidence = dspy.Predict(Confidence)

    def forward(self, product: str, evidence: str) -> dspy.Prediction:
        e = json.loads(evidence)
        cands = [c["heading"] for c in e["candidates"]]
        out1 = self.candidates(product=product, candidates=ev.render_candidates(e))
        order = ev.parse_heading_list(out1.headings, cands)
        top = order
        numbered = ev.number_rulings(e, top)
        out2 = self.gri(product=product, headings=ev.render_gri_headings(e, top), rulings=ev.render_rulings(numbered))
        heading = ev.parse_heading(out2.heading, top) or top[0]
        us_lines = e["us_lines"].get(heading, [])
        out3 = self.subheading(product=product, lines=ev.render_lines(e, heading, "US"), country="US")
        us_code = ev.parse_code(out3.code, us_lines)
        ca_lines = e["ca_lines"].get(heading, [])
        ca_code = ""
        ca_why = ""
        if ca_lines:
            out3c = self.subheading(
                product=product, lines=ev.render_lines(e, heading, "CA", us_code=us_code), country="CA"
            )
            ca_code = ev.parse_code(out3c.code, ca_lines)
            ca_why = out3c.why
        set_aside = ev.parse_set_aside(out2.set_aside, heading)
        cite_list = ev.citation_rulings(e, heading, [s[0] for s in set_aside])
        decision = ev.render_decision(heading, us_code, ca_code, out2.gri, set_aside)
        out4 = self.cite(product=product, decision=decision, rulings=ev.render_rulings(cite_list))
        sentences = ev.parse_sentences(out4.sentences, len(cite_list))
        runner = ev.runner_up(heading, set_aside)
        agreement = ev.render_agreement(e, heading, cite_list, sentences, runner, product)
        out5 = self.confidence(product=product, decision=decision, agreement=agreement)
        verdict = "broker" if "broker" in (out5.verdict or "").lower() else "strong"
        support = sorted({n for _, ns in sentences for n in ns if not ev.is_contrast_sentence(_)})
        return dspy.Prediction(
            order=order,
            heading=heading,
            gri=ev.parse_gri(out2.gri),
            set_aside=set_aside,
            facts=out2.facts,
            us_code=us_code,
            us_why=out3.why,
            ca_code=ca_code,
            ca_why=ca_why,
            cited=cite_list,
            sentences=sentences,
            support_ids=[cite_list[n - 1]["id"] for n in support if 0 < n <= len(cite_list)],
            verdict=verdict,
            deciding_fact=(out5.deciding_fact or "none").strip(),
            question=(out5.question or "none").strip(),
        )


# ── evidence ────────────────────────────────────────────────────────────────────────────────────────────
def build_evidence(query: ProductQuery, first: FirstStageResult, retriever: Retriever, *, before=None) -> dict:
    return ev.build(query, first, retriever, before=before)


# ── the answer the API shows ────────────────────────────────────────────────────────────────────────────
def _hit(c: dict) -> RulingHit:
    from datetime import date

    return RulingHit(
        ruling_id=c["id"],
        issued=date.fromisoformat(c["issued"]) if c.get("issued") else date(1970, 1, 1),
        code=c["code"],
        heading=c["heading"],
        subject=c["subject"],
        holding=c["holding"],
        status=c["status"],
        status_by=c.get("status_by"),
        status_date=date.fromisoformat(c["status_date"]) if c.get("status_date") else None,
        bm25=c.get("bm25", 0.0),
        rerank=c.get("score", 0.0),
        passages=tuple((p[0], tuple(ev.span(s) for s in p[1])) for p in c.get("passages", [])),
    )


def assemble(
    query: ProductQuery, e: dict, pred: dspy.Prediction, *, lm_label: str, version: str, timings: dict
) -> ProgramAnswer:
    heading = pred.heading
    us_line = e["us_text"].get(pred.us_code) or ""
    head_text = e["heading_text"].get(heading, "")
    us = CodeChoice("US", pred.us_code, us_line or head_text, head_text) if pred.us_code else None
    ca = None
    if pred.ca_code:
        ca = CodeChoice(
            "CA", pred.ca_code, e["ca_text"].get(pred.ca_code, head_text), e["ca_heading_text"].get(heading, head_text)
        )
    facts = facts_mod.extract(
        query.text + " " + query.spec_sheet_text + " " + " ".join(query.photo_facts), query.confirmed_facts
    )
    runner = ev.runner_up(heading, pred.set_aside) or next((h for h in pred.order if h != heading), None)
    dist = facts_mod.distinction(heading, runner, head_text, e["heading_text"].get(runner, "")) if runner else None
    if dist is not None and pred.verdict == "broker":
        facts = [
            f if f.key != dist.key else f.__class__(f.key, f.label, f.value, f.source, f.source_note, True)
            for f in facts
        ]
        if not any(f.key == dist.key for f in facts):
            facts.append(facts_mod.Fact(dist.key, dist.label, "Not stated", "unknown", "not stated", True))
    cited = pred.cited
    numbered = {i + 1: c for i, c in enumerate(cited)}
    used = sorted({n for _, ns in pred.sentences for n in ns if n in numbered})
    renumber = {old: i + 1 for i, old in enumerate(used)}
    claims = []
    for text, ns in pred.sentences:
        nn = tuple(renumber[n] for n in ns if n in renumber)
        claims.append(Claim(ev.strip_cites(text), nn))
    citations = []
    for old in used:
        c = numbered[old]
        same_h = c["heading"] == heading
        match = (
            ("same_heading", "same_subheading")
            if same_h and pred.us_code[:6] == c["code"][:6]
            else (("same_heading",) if same_h else ("different_heading",))
        )
        hit = _hit(c)
        if not same_h and hit.status == "in_force":
            hit = hit.__class__(**{**hit.__dict__, "status": "contrast"})
        supports = tuple(i for i, cl in enumerate(claims) if renumber[old] in cl.cites)
        citations.append(
            Citation(renumber[old], hit, match, tuple(facts_mod.compare(facts, c.get("text", c["holding"]))), supports)
        )
    agreeing = sum(1 for c in citations if "same_heading" in c.match)
    path = _path(e, pred, heading, citations, renumber)
    authorities = _authorities(e, heading, runner, pred)
    alt = None
    dq = None
    stake = None
    if pred.verdict == "broker" and runner:
        alt_code = (e["us_lines"].get(runner) or [[""]])[0][0]
        best_alt = ev.best_line_for(e, runner, query.text)
        alt_code = best_alt or alt_code
        if alt_code:
            alt = CodeChoice("US", alt_code, e["us_text"].get(alt_code, ""), e["heading_text"].get(runner, ""))
        if dist is not None:
            opts = tuple(
                (k, label, ev.best_line_for(e, h, query.text) or (e["us_lines"].get(h) or [[h]])[0][0])
                for k, label, h in dist.options
            )
            dq = DecidingQuestion(dist.key, dist.question if pred.question in ("", "none") else pred.question, opts)
        stake = "depends on the duty layers of each line"
    verdict_sentence = (
        f"{agreeing} of {len(citations)} cited rulings reach heading {heading}, and the deciding facts are stated."
        if pred.verdict == "strong"
        else "The answer turns on a fact the description doesn't settle; a broker should confirm it."
    )
    subject = _subject(query.text)
    holding = f"{subject} is classified in subheading {codes.fmt(pred.us_code)}, HTSUS" + (
        f", and tariff item {codes.fmt(pred.ca_code)} of Canada's Customs Tariff." if pred.ca_code else "."
    )
    issue = (
        f"Is {subject.lower() if subject.startswith('The ') else subject} {ev.short(head_text)} "
        f"of heading {heading}, or "
        f"{ev.short(e['heading_text'].get(runner, ''))} of heading {runner}?"
        if runner
        else f"Which heading's terms describe {subject.lower()}?"
    )
    return ProgramAnswer(
        us=us,
        ca=ca,
        verdict=pred.verdict,
        verdict_sentence=verdict_sentence,
        agreeing_rulings=agreeing,
        cited_rulings=len(citations),
        holding_sentence=holding,
        issue=issue,
        facts=tuple(facts),
        reason=tuple(claims),
        path=path,
        citations=tuple(citations),
        tariff_authorities=authorities,
        alternative=alt,
        duty_at_stake=stake,
        deciding_question=dq,
        lm_label=lm_label,
        program_version=version,
        timings_ms=timings,
    )


def _subject(text: str) -> str:
    words = text.strip().rstrip(".").split()
    if 0 < len(words) <= 10:
        t = " ".join(words)
        return "The " + (t[0].lower() + t[1:] if t[:1].isupper() and not t[:2].isupper() else t)
    return "The product"


def _path(e: dict, pred, heading: str, citations: list[Citation], renumber: dict[int, int]) -> tuple[PathStep, ...]:
    ch = heading[:2]
    roman, sec_title = section_of(ch)
    other_chapters = [h[:2] for h in pred.order if h[:2] != ch]
    by_heading_cites = tuple(c.n for c in citations if c.ruling.heading == heading)[:3]
    steps = [
        PathStep(
            "section",
            roman,
            sec_title,
            "GRI 1",
            f"Chapter {ch} sits in Section {roman}; section titles are for reference only (GRI 1).",
        ),
        PathStep(
            "chapter",
            ch,
            chapter_title(ch),
            "GRI 1",
            f"Chapter {ch} covers {chapter_title(ch).lower()}.",
            (),
            tuple(
                NotNeighbour(c, chapter_title(c), "Set aside: its headings don't describe the product as well")
                for c in dict.fromkeys(other_chapters[:2])
            ),
        ),
    ]
    nn = []
    for code, reason, rid in pred.set_aside:
        cite = next((c.n for c in citations if c.ruling.ruling_id == rid), None)
        nn.append(NotNeighbour(code, e["heading_text"].get(code, ""), reason, cite))
    steps.append(
        PathStep(
            "heading",
            heading,
            e["heading_text"].get(heading, ""),
            pred.gri,
            ev.heading_why(e, heading, pred.gri),
            by_heading_cites,
            tuple(nn),
        )
    )
    code = pred.us_code
    for n, level in ((6, "subheading"), (8, "tariff_item"), (10, "suffix")):
        if len(code) < n:
            break
        part = code[:n]
        text = e["us_text"].get(part) or e["us_text"].get(code, "") if n == 10 else e["us_text"].get(part, "")
        sibs = ev.siblings(e, heading, part)
        steps.append(
            PathStep(
                level,  # type: ignore[arg-type]
                part,
                text or e["us_text"].get(code, ""),
                "GRI 6",
                ev.level_why(level, text, pred.us_why),
                (),
                tuple(
                    NotNeighbour(s, t, "Set aside at the same level (GRI 6): its terms don't fit the product")
                    for s, t in sibs[:2]
                ),
                country_note=(
                    f"Canada: tariff item {codes.fmt(pred.ca_code)}"
                    + (f" ({e['ca_text'].get(pred.ca_code, '')})" if pred.ca_code else "")
                )
                if n == 10 and pred.ca_code
                else None,
            )
        )
    return tuple(steps)


def _authorities(e: dict, heading: str, runner: str | None, pred) -> tuple[TariffAuthority, ...]:
    out = [TariffAuthority(f"Heading {heading}", e["heading_text"].get(heading, ""))]
    for quote in e.get("notes", {}).get(heading, []) + (e.get("notes", {}).get(runner, []) if runner else []):
        out.append(TariffAuthority(quote["ref"], quote["quote"]))
    if runner:
        out.append(TariffAuthority(f"Heading {runner}", e["heading_text"].get(runner, "")))
    out.append(
        TariffAuthority(
            "GRI 1",
            "Classification shall be determined according to the terms of the headings and any relative section or "
            "chapter notes.",
        )
    )
    out.append(
        TariffAuthority(
            "GRI 6",
            "Classification in the subheadings of a heading shall be determined according to the terms of those "
            "subheadings and any related subheading notes, mutatis mutandis, to the above rules, on the understanding "
            "that only subheadings at the same level are comparable.",
        )
    )
    return tuple(out)


# ── the live program ────────────────────────────────────────────────────────────────────────────────────
def artifact_dir() -> Path:
    return Path(str(settings.TARIFF_COMPASS["ARTIFACT_DIR"]))


def live_program_path() -> Path | None:
    """The optimised program JSON of the live round (classify/artifacts/rounds/live.json names it)."""
    rounds = artifact_dir() / "rounds"
    marker = rounds / "live.json"
    if marker.exists():
        p = rounds / json.loads(marker.read_text())["program"]
        return p if p.exists() else None
    found = sorted(rounds.glob("round-*.program.json")) if rounds.exists() else []
    return found[-1] if found else None


class DSPyClassifier:
    """ClassifierProgram: evidence → five modules → ProgramAnswer."""

    def __init__(self, program: TariffProgram, lm, lm_label: str, version: str) -> None:
        self.program, self.lm, self.lm_label = program, lm, lm_label
        self.version = version

    def classify(self, query: ProductQuery, first_stage: FirstStageResult, retriever: Retriever) -> ProgramAnswer:
        t0 = time.perf_counter()
        e = build_evidence(query, first_stage, retriever)
        t1 = time.perf_counter()
        product = ev.product_text(query)
        with dspy.context(lm=self.lm, adapter=dspy.ChatAdapter()):
            pred = self.program(product=product, evidence=json.dumps(e))
        t2 = time.perf_counter()
        timings = {"evidence": (t1 - t0) * 1000, "program": (t2 - t1) * 1000}
        return assemble(query, e, pred, lm_label=self.lm_label, version=self.version, timings=timings)


def make_program(path: Path | None = None) -> TariffProgram:
    prog = TariffProgram()
    if path is not None and path.exists():
        prog.load(str(path))
    return prog


def load_program() -> ClassifierProgram:
    from tariffcompass.adapters import lm as lm_adapter

    path = live_program_path()
    prog = make_program(path)
    version = f"{PROGRAM_VERSION}:{path.stem if path else 'unoptimised'}"
    return DSPyClassifier(prog, lm_adapter.task_lm(), lm_adapter.lm_label("task"), version)


def set_live(round_n: int | None) -> None:
    """Record which round's optimised program the classifier uses (called when a round is signed live)."""
    rounds = artifact_dir() / "rounds"
    marker = rounds / "live.json"
    if round_n is None:
        marker.unlink(missing_ok=True)
        return
    name = f"round-{round_n}.program.json"
    if not (rounds / name).exists():
        raise FileNotFoundError(name)
    marker.write_text(json.dumps({"round": round_n, "program": name}) + "\n")
