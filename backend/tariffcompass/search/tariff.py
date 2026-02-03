"""The two tariff schedules in memory: US HTSUS (2026 Revision 3 reading) and Canada's Customs Tariff (T2026).

Both are loaded from the JSONL files written by `scripts/fetch_data.py` (or the committed samples) into
`TariffLine` objects keyed by digits. A US line inherits its column 1 General rate from the nearest numbered
ancestor that prints one (the HTSUS prints the rate once, on the eight-digit line); `full_text` joins the line
with every superior line above it, so "Having a capacity not exceeding 1 liter" reads as
"Vacuum flasks …: Vessels: Having a capacity not exceeding 1 liter".
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path

from tariffcompass.contracts import Country, Level, TariffLine

_DIGITS = re.compile(r"\D")


def _level(n_digits: int) -> Level:
    levels: dict[int, Level] = {2: "chapter", 4: "heading", 6: "subheading", 8: "tariff_item"}
    return levels.get(n_digits, "suffix")


@dataclass
class Schedule:
    country: Country
    edition: str
    lines: dict[str, TariffLine] = field(default_factory=dict)  # digits → line
    order: list[str] = field(default_factory=list)  # digits in schedule order
    children: dict[str, list[str]] = field(default_factory=dict)  # parent digits → child digits (numbered)
    superiors: dict[str, list[str]] = field(default_factory=dict)  # digits → unnumbered superior texts above it

    def line(self, code: str) -> TariffLine | None:
        d = _DIGITS.sub("", code)
        if d in self.lines:
            return self.lines[d]
        if len(d) == 10 and d.endswith("00") and d[:8] in self.lines:  # an eight-digit line without suffixes
            return replace(self.lines[d[:8]], code=d, level="suffix")
        return None

    def kids(self, code: str) -> list[TariffLine]:
        return [self.lines[c] for c in self.children.get(_DIGITS.sub("", code), [])]

    def leaves(self, heading: str) -> list[TariffLine]:
        """Every ten-digit line (or eight-digit line without suffixes, as ten digits) under a heading."""
        out: list[TariffLine] = []
        for d in self.order:
            if not d.startswith(heading) or len(d) < 8:
                continue
            if len(d) == 10:
                out.append(self.lines[d])
            elif not self.children.get(d):
                out.append(replace(self.lines[d], code=d + "00", level="suffix"))
        return out

    def headings(self) -> list[TariffLine]:
        return [self.lines[d] for d in self.order if len(d) == 4]

    def ancestors(self, code: str) -> list[TariffLine]:
        d = _DIGITS.sub("", code)
        return [self.lines[d[:n]] for n in (4, 6, 8) if n < len(d) and d[:n] in self.lines]


def _add(s: Schedule, line: TariffLine, parent: str | None) -> None:
    s.lines[line.code] = line
    s.order.append(line.code)
    if parent:
        s.children.setdefault(parent, []).append(line.code)


def load_us(rows: Iterable[dict], edition: str = "HTSUS 2026 Revision 3") -> Schedule:
    s = Schedule("US", edition)
    stack: list[tuple[int, str, str]] = []  # (indent, digits or "", description)
    heading_text: dict[str, str] = {}
    for row in rows:
        indent = int(row.get("indent") or 0)
        text = " ".join(str(row.get("description") or "").split())
        code = _DIGITS.sub("", row.get("htsno") or "")
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if code and len(code) == 4:
            heading_text[code] = text.rstrip(":")
        if code and len(code) > 4 and code[:4] not in s.lines:
            # some headings print only as their single subheading (9617.00) or line (9618.00.00.00)
            own = text.rstrip(":")
            heading_text[code[:4]] = own
            _add(s, TariffLine("US", code[:4], "heading", 0, own, own), None)
        if code and len(code) in (4, 6, 8, 10):
            parent = next((d for _, d, _ in reversed(stack) if d and code.startswith(d) and d != code), None)
            if parent is None and len(code) > 4 and code[:4] in s.lines:
                parent = code[:4]
            sup = [t.rstrip(":") for _, d, t in stack if t]
            if len(code) > 4 and code[:4] in heading_text and (not sup or sup[0] != heading_text[code[:4]]):
                sup = [heading_text[code[:4]], *sup]
            full = ": ".join([*sup, text.rstrip(":")]) if len(code) > 4 else text.rstrip(":")
            general = (row.get("general") or "").strip()
            if not general and parent:
                general = _inherited_rate(s, parent)
            units = row.get("units") or []
            _add(
                s,
                TariffLine(
                    country="US",
                    code=code,
                    level=_level(len(code)),
                    indent=indent,
                    text=text.rstrip(":"),
                    full_text=full,
                    unit=", ".join(units) if isinstance(units, list) else str(units),
                    general_rate=general,
                    special=(row.get("special") or "").strip(),
                    notes=tuple(_footnotes(row)),
                ),
                parent,
            )
            stack.append((indent, code, text))
        else:
            stack.append((indent, "", text))
    return s


def _inherited_rate(s: Schedule, parent: str) -> str:
    d = parent
    while d:
        line = s.lines.get(d)
        if line and line.general_rate:
            return line.general_rate
        d = d[:-2] if len(d) > 4 else ""
    return ""


def _footnotes(row: dict) -> list[str]:
    notes = row.get("footnotes") or []
    out = []
    for n in notes:
        if isinstance(n, dict) and n.get("value"):
            out.append(" ".join(str(n["value"]).split()))
    return out


def load_ca(rows: Iterable[dict], edition: str = "Customs Tariff T2026") -> Schedule:
    """CBSA rows: tariff item (8 digits, or the heading as '96.17') + suffix; descriptions joined by ' - '."""
    s = Schedule("CA", edition)
    for row in rows:
        item = _DIGITS.sub("", row["tariffItem"])
        suffix = _DIGITS.sub("", row.get("suffix") or "")
        desc = " ".join(str(row.get("description") or "").split())
        parts = [p.strip(" .:") for p in desc.split(" - ") if p.strip(" .:")]
        own = parts[-1] if parts else desc
        if len(item) == 4:
            if item not in s.lines:
                _add(s, TariffLine("CA", item, "heading", 0, own, own), None)
            continue
        heading = item[:4]
        if heading not in s.lines:
            _add(
                s, TariffLine("CA", heading, "heading", 0, parts[0] if parts else own, parts[0] if parts else own), None
            )
        code = item + suffix if suffix else item
        if code in s.lines:
            continue
        level: Level = (
            "suffix" if suffix else ("subheading" if item.endswith("00") and len(item) == 6 else "tariff_item")
        )
        if len(item) == 6:
            level = "subheading"
        parent = item if suffix and item in s.lines else heading
        _add(
            s,
            TariffLine(
                country="CA",
                code=code,
                level=level,
                indent=max(len(parts) - 1, 1),
                text=own,
                full_text=": ".join(parts),
                unit=(row.get("unit") or "").strip(),
                general_rate=(row.get("mfn") or "").strip(),
                special=(row.get("preferential") or "").strip(),
            ),
            parent,
        )
    return s


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def ca_ten(item_or_code: str, schedule: Schedule) -> str | None:
    """Canada's ten digits for an eight-digit tariff item: its only suffix, or 00 when it has none printed."""
    d = _DIGITS.sub("", item_or_code)
    if len(d) == 10 and d in schedule.lines:
        return d
    kids = [c for c in schedule.children.get(d[:8], []) if len(c) == 10]
    if kids:
        return kids[0]
    return d[:8] + "00" if d[:8] in schedule.lines else None
