"""Optimisation lab: training rounds, accuracy, calibration, drift, two-person sign-off (API_CONTRACT §1.12).

All numbers come from RoundReport (contracts.py), computed on rulings the classifier hasn't seen.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from tariffcompass.core.wire import Wire

RoundStatus = Literal["training", "waiting_signoff", "live", "not_made_live", "retired", "failed"]


class RoundStrip(Wire):
    n: int
    status: RoundStatus
    status_label: str  # "Live since 30 Jan" | "Waiting for sign-off" | "Not made live" | "Retired"
    trained_on: date | None
    note: str  # "worse on knitted apparel, so round 4 stayed"


class InUseOut(Wire):
    """What answers today: a signed-off round, or word matching when no round has passed and been signed."""

    kind: Literal["word_matching", "round"]
    round: int | None
    label: str  # "Word matching" | "Round 6"
    full_code: float | None  # 0..100 on rulings it hasn't seen
    heading: float | None
    sentence: str


class LabOut(Wire):
    rounds: list[RoundStrip]
    live: int | None  # only a round that passed all five checks and was signed by two people
    candidate: int | None
    corrections_waiting: int
    in_use: InUseOut


class DepthRow(Wire):
    level: Literal["chapter", "heading", "subheading", "full_code"]
    level_label: str  # "Chapter" | "Heading" | "Subheading" | "Full code"
    word_matching: float  # 0..100, the classical yardstick
    live: float | None  # the live round
    candidate: float  # this round
    unoptimised: float | None = None  # the program before optimisation (shown in the table view)


class ConfidenceCell(Wire):
    said: int  # times it said this word
    right: int  # strong: right; broker: first guess wrong
    per100: int
    sentence: str  # "When it said Strong match (812 times): right 97 times in 100"


class ChapterRow(Wire):
    chapter: str
    title: str
    tested: int
    before: float
    after: float
    change: float
    change_label: str  # "▲ 6" | "▼ 2"
    new_rulings: int
    moving: bool  # new rulings since the live round > 25


class CheckOut(Wire):
    key: str
    label: str  # "Full-code accuracy at least the live round's"
    passed: bool
    value: str
    threshold: str


class Signature(Wire):
    name: str
    role: str
    role_label: str
    signed_at: datetime
    statement: str


class SignOffOut(Wire):
    required: int  # 2
    signatures: list[Signature]
    can_sign: bool  # the viewer has lab:sign and hasn't signed yet
    will_promote: bool  # the viewer's signature would be the second
    note: str  # "Round 6 stays one click away. Answers already approved keep their codes; nothing is re-filed."


class RoundOut(Wire):
    n: int
    status: RoundStatus
    status_label: str
    trained_on: date | None
    test_count: int
    test_from: date
    test_to: date
    snapshot: str  # data snapshot hash, short
    rerun_note: str  # "Same rulings, seed 7 and budget give the same round."
    # "Round 7 gets the full ten-digit code right for 71 in 100 rulings it hasn't seen, up from 58.
    #  Word matching alone gets 44."
    lede: str
    by_depth: list[DepthRow]
    confidence: dict[Literal["strong", "broker"], ConfidenceCell]
    by_chapter: list[ChapterRow]
    learned: list[str]
    drift: dict[str, str | int | float]  # {"newRulings": 212, "mostMoved": "85", "psi": 0.14, "sentence": "…"}
    checks: list[CheckOut]
    sign_off: SignOffOut
    run_by: str  # "offline simulator" or the cloud LM: shown only here, labelled "Answers written by"


class StartRoundIn(Wire):
    note: str = Field(default="", max_length=500)


class SignIn(Wire):
    statement: str = Field(min_length=3, max_length=200)  # the signer types their name
