"""The classifier program: a DSPy module whose instructions GEPA optimises (ADR 0003).

Five modules, run in order on the first stage's candidates and the search engine's rulings:
1. CandidateHeadings  - which headings could hold the product (from the first stage's top-k and the tariff text)
2. GriReasoning       - apply GRI 1 (headings and notes) and, only when needed, GRI 2-5; say why each
                        neighbour is set aside
3. ChooseSubheading   - GRI 6 down to the 10-digit line, US and Canada separately
4. SelectCitations    - pick the rulings that support each sentence; never cite a revoked ruling as support
5. Confidence         - "strong" or "broker", the deciding fact and the question that would settle it
The signatures below are the contract between the program and the offline simulator's policies.
"""

from __future__ import annotations

import dspy

from tariffcompass.contracts import ClassifierProgram


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


def load_program() -> ClassifierProgram:
    raise NotImplementedError("classifier program not built yet")
