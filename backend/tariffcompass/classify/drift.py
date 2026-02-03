"""Drift: chapter-mix PSI as new rulings arrive, and detection of a tariff revision that moves products' codes.

PSI (population stability index) compares two distributions over the same bins:
    PSI = Σ (p_i − q_i) · ln(p_i / q_i), with a small floor so empty bins don't explode.
Reading, as commonly used: < 0.10 stable, 0.10–0.25 moderate shift, > 0.25 large shift.

`simulate_revision()` builds a revised copy of a schedule (a line split, a line renumbered, a heading's text
changed, a line deleted) and `detect_revision()` compares any two schedules line by line, so the same check
flags products whose code no longer exists, was split, or whose text changed under them.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from tariffcompass.search.tariff import Schedule

PSI_FLOOR = 1e-4
STABLE, MODERATE = 0.10, 0.25


def distribution(values: Iterable[str], bins: Sequence[str]) -> list[float]:
    c = Counter(values)
    n = sum(c[b] for b in bins) or 1
    return [c[b] / n for b in bins]


def psi(expected: Sequence[float], actual: Sequence[float]) -> float:
    total = 0.0
    for p, q in zip(expected, actual, strict=True):
        p, q = max(p, PSI_FLOOR), max(q, PSI_FLOOR)
        total += (q - p) * math.log(q / p)
    return total


def chapter_psi(train_chapters: Iterable[str], new_chapters: Iterable[str], top: int = 30) -> dict:
    """PSI over the training set's most common chapters plus an 'other' bin; the chapters that moved most."""
    tr, nw = list(train_chapters), list(new_chapters)
    common = [c for c, _ in Counter(tr).most_common(top)]

    def binned(xs: list[str]) -> list[str]:
        return [x if x in common else "other" for x in xs]

    bins = [*common, "other"]
    p, q = distribution(binned(tr), bins), distribution(binned(nw), bins)
    moved = sorted(
        (
            {"chapter": b, "train": round(a, 4), "new": round(c, 4), "change": round(c - a, 4)}
            for b, a, c in zip(bins, p, q, strict=True)
        ),
        key=lambda d: -abs(float(d["change"])),  # type: ignore[arg-type]
    )
    value = psi(p, q)
    return {"psi": round(value, 4), "reading": reading(value), "mostMoved": moved[:5], "bins": len(bins)}


def reading(value: float) -> str:
    if value < STABLE:
        return "stable"
    return "moderate shift" if value < MODERATE else "large shift"


@dataclass(frozen=True)
class RevisionChange:
    kind: str  # removed | split | text_changed | added
    code: str
    detail: str
    new_codes: tuple[str, ...] = ()


def simulate_revision(s: Schedule, *, split: str, renumber: tuple[str, str], retext: str, remove: str) -> Schedule:
    """A revised copy: `split` becomes two new ten-digit lines, `renumber` moves a line to a new number,
    `retext` changes a heading's text, `remove` deletes a line. The original is untouched."""
    new = Schedule(s.country, s.edition + " (simulated revision)")
    new.lines = dict(s.lines)
    new.order = list(s.order)
    new.children = {k: list(v) for k, v in s.children.items()}

    def drop(code: str) -> None:
        new.lines.pop(code, None)
        if code in new.order:
            new.order.remove(code)
        for kids in new.children.values():
            if code in kids:
                kids.remove(code)

    def put_after(anchor: str, line) -> None:
        new.lines[line.code] = line
        i = new.order.index(anchor) + 1 if anchor in new.order else len(new.order)
        new.order.insert(i, line.code)

    base = s.line(split)
    if base is not None:
        a = replace(
            base, code=split[:8] + "10", text=base.text + ": insulated", full_text=base.full_text + ": insulated"
        )
        b = replace(base, code=split[:8] + "90", text=base.text + ": other", full_text=base.full_text + ": other")
        anchor = split if split in new.lines else split[:8]
        put_after(anchor, a)
        put_after(a.code, b)
        drop(split)
    old, to = renumber
    line = s.line(old)
    if line is not None:
        put_after(old if old in new.lines else old[:8], replace(line, code=to))
        drop(old)
    h = new.lines.get(retext)
    if h is not None:
        new.lines[retext] = replace(h, text=h.text + " (revised)", full_text=h.full_text + " (revised)")
    drop(remove)
    return new


def detect_revision(old: Schedule, new: Schedule) -> list[RevisionChange]:
    changes: list[RevisionChange] = []
    old_codes, new_codes = set(old.lines), set(new.lines)
    for code in sorted(old_codes - new_codes):
        siblings = tuple(sorted(c for c in new_codes - old_codes if c[:8] == code[:8] and len(c) == len(code)))
        if siblings:
            changes.append(RevisionChange("split", code, f"{code} was split into {', '.join(siblings)}", siblings))
        else:
            changes.append(RevisionChange("removed", code, f"{code} is no longer a line of the schedule"))
    for code in sorted(old_codes & new_codes):
        if old.lines[code].text != new.lines[code].text:
            changes.append(RevisionChange("text_changed", code, f"the text of {code} changed"))
    for code in sorted(new_codes - old_codes):
        if not any(code in ch.new_codes for ch in changes):
            changes.append(RevisionChange("added", code, f"{code} is a new line"))
    return changes


def affected(products: Iterable[tuple[str, str]], changes: list[RevisionChange]) -> dict[str, list[str]]:
    """Products (key, ten-digit code) touched by the changes: their own line, or an ancestor line, changed."""
    out: dict[str, list[str]] = {}
    for key, code in products:
        hits = []
        for ch in changes:
            if ch.kind == "added":
                continue
            c = ch.code
            own_line = code == c
            ancestor_text = len(c) < len(code) and code.startswith(c) and ch.kind == "text_changed"
            same_item = ch.kind in ("removed", "split") and len(c) == 8 and code[:8] == c
            if own_line or ancestor_text or same_item:
                hits.append(ch.detail)
        if hits:
            out[key] = hits
    return out
