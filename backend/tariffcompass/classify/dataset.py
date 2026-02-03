"""Labelled examples and the leakage-safe splits by ruling date (ADR 0006).

Examples are the rulings `search.corpus` marks `labelled`. The split is by issue date:

    train       issued before VAL_FROM            (the first stage and the program's examples learn from these)
    validation  VAL_FROM ≤ issued < TEST_FROM     (tuning, calibration, GEPA's validation set)
    test        issued on or after TEST_FROM       (the newest rulings: "rulings it hasn't seen")

The test set is frozen in `classify/artifacts/splits.json` (ids plus a SHA-256 over ids and letter hashes) before
any model is tuned, and `load_splits()` refuses to run if the corpus no longer reproduces that hash. Broker
corrections join training only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.conf import settings

from tariffcompass.search import corpus as corpus_mod

VAL_FROM = date(2024, 4, 1)
TEST_FROM = date(2025, 1, 1)
SPLITS_FILE = "splits.json"


@dataclass(frozen=True)
class Example:
    id: str
    issued: date
    text: str  # the product as the letter describes it (no tariff numbers, no legal analysis)
    heading: str
    code: str  # primary held code (digits, 6–10)
    codes: tuple[str, ...]  # every code the letter holds (same six-digit subheading)
    made_in: str = ""
    source: str = "ruling"  # ruling | correction
    lesson: str = ""

    @property
    def chapter(self) -> str:
        return self.heading[:2]

    @property
    def six(self) -> str:
        return self.code[:6]

    @property
    def tens(self) -> tuple[str, ...]:
        return tuple(c for c in self.codes if len(c) == 10)


@dataclass
class Splits:
    train: list[Example]
    val: list[Example]
    test: list[Example]
    meta: dict = field(default_factory=dict)

    def all(self) -> list[Example]:
        return self.train + self.val + self.test


def artifact_dir() -> Path:
    return Path(str(settings.TARIFF_COMPASS["ARTIFACT_DIR"]))


def examples_from(rulings: list[corpus_mod.CleanRuling]) -> list[Example]:
    out = []
    for r in rulings:
        if not r.labelled or not r.issued:
            continue
        out.append(
            Example(
                id=r.id,
                issued=date.fromisoformat(r.issued),
                text=r.description,
                heading=r.code[:4],
                code=r.code,
                codes=tuple(r.held),
                made_in=_origin(r.subject),
            )
        )
    out.sort(key=lambda e: (e.issued, e.id))
    return out


def _origin(subject: str) -> str:
    s = subject.lower()
    for name, iso in (
        ("china", "CN"),
        ("vietnam", "VN"),
        ("viet nam", "VN"),
        ("mexico", "MX"),
        ("canada", "CA"),
        ("germany", "DE"),
        ("italy", "IT"),
        ("india", "IN"),
        ("taiwan", "TW"),
    ):
        if f"from {name}" in s:
            return iso
    return ""


def split_hash(examples: list[Example], texts: dict[str, str]) -> str:
    h = hashlib.sha256()
    for e in sorted(examples, key=lambda e: e.id):
        h.update(f"{e.id}\t{e.issued.isoformat()}\t{e.code}\t{texts.get(e.id, '')}\n".encode())
    return h.hexdigest()


def make_splits(rulings: list[corpus_mod.CleanRuling]) -> Splits:
    ex = examples_from(rulings)
    train = [e for e in ex if e.issued < VAL_FROM]
    val = [e for e in ex if VAL_FROM <= e.issued < TEST_FROM]
    test = [e for e in ex if e.issued >= TEST_FROM]
    return Splits(train, val, test)


def freeze(splits: Splits, rulings: list[corpus_mod.CleanRuling], path: Path | None = None) -> dict:
    """Record the split (and the test set's hash) once, before any tuning. Never overwrites."""
    path = path or artifact_dir() / SPLITS_FILE
    if path.exists():
        return json.loads(path.read_text())
    sha = {r.id: r.sha256 for r in rulings}
    meta = {
        "rule": f"train < {VAL_FROM} ≤ validation < {TEST_FROM} ≤ test (by ruling issue date)",
        "valFrom": VAL_FROM.isoformat(),
        "testFrom": TEST_FROM.isoformat(),
        "counts": {"train": len(splits.train), "val": len(splits.val), "test": len(splits.test)},
        "testWindow": [splits.test[0].issued.isoformat(), splits.test[-1].issued.isoformat()] if splits.test else [],
        "hashes": {
            "train": split_hash(splits.train, sha),
            "val": split_hash(splits.val, sha),
            "test": split_hash(splits.test, sha),
        },
        "corpusSnapshot": corpus_mod.snapshot_hash(rulings),
        "ids": {
            "train": [e.id for e in splits.train],
            "val": [e.id for e in splits.val],
            "test": [e.id for e in splits.test],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=0) + "\n")
    return meta


def load_splits(rulings: list[corpus_mod.CleanRuling], path: Path | None = None, *, strict: bool = True) -> Splits:
    """The frozen split, re-materialised from the corpus; `strict` checks the recorded test hash."""
    path = path or artifact_dir() / SPLITS_FILE
    meta = json.loads(path.read_text())
    by_id = {e.id: e for e in examples_from(rulings)}
    parts = {k: [by_id[i] for i in meta["ids"][k] if i in by_id] for k in ("train", "val", "test")}
    sp = Splits(parts["train"], parts["val"], parts["test"], meta)
    if strict:
        sha = {r.id: r.sha256 for r in rulings}
        got = split_hash(sp.test, sha)
        if got != meta["hashes"]["test"]:
            raise RuntimeError(f"frozen test set no longer reproduces: {got[:12]} ≠ {meta['hashes']['test'][:12]}")
    return sp


def correction_examples(corrections: tuple[dict, ...] | list[dict]) -> list[Example]:
    """Broker corrections (review.TrainingExample, the format agreed with the platform) as training examples."""
    out = []
    for c in corrections:
        code = c.get("us_code") or ""
        if len(code) < 6:
            continue
        decided = c.get("decided_on") or "2026-01-01"
        out.append(
            Example(
                id=f"correction:{c.get('id', '')}",
                issued=date.fromisoformat(decided[:10]),
                text=c.get("text", ""),
                heading=code[:4],
                code=code,
                codes=(code,),
                made_in=c.get("made_in", ""),
                source="correction",
                lesson=c.get("lesson", ""),
            )
        )
    return out
