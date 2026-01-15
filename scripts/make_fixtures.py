"""Build the small committed fixtures (backend/tariffcompass/search/fixtures) from data/ after fetch_data.py.

The fixtures let tests, CI and the offline demo run without downloading anything: a deterministic sample of
rulings from the chapters Northbound imports (every 9617 ruling included), and the tariff lines of those
chapters for the US and Canada. Letters are trimmed to keep the repository small.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
OUT = REPO / "backend" / "tariffcompass" / "search" / "fixtures"
CHAPTERS = ("39", "42", "61", "62", "63", "64", "73", "76", "84", "85", "94", "95", "96")
PER_CHAPTER = 36
ALWAYS = ("9617", "8512", "8513", "8507", "6110", "7323", "4202")
# Headings Northbound imports, plus the neighbours its answers set aside.
HEADINGS = (
    "3923",
    "3924",
    "4202",
    "6101",
    "6102",
    "6109",
    "6110",
    "6115",
    "6116",
    "6201",
    "6202",
    "6210",
    "6306",
    "6602",
    "6912",
    "7013",
    "7321",
    "7323",
    "7326",
    "7615",
    "8211",
    "8504",
    "8507",
    "8512",
    "8513",
    "8516",
    "8518",
    "9404",
    "9405",
    "9506",
    "9617",
)
MAX_TEXT = 2400


def _rank(rid: str) -> str:
    return hashlib.sha256(rid.encode()).hexdigest()


def rulings() -> int:
    rows = [json.loads(line) for line in (DATA / "rulings" / "rulings.jsonl").open(encoding="utf-8")]
    keep: dict[str, dict] = {}
    for r in rows:
        if r["code"][:4] in ALWAYS and len(keep) < 10_000:
            keep.setdefault(r["id"], r)
    for ch in CHAPTERS:
        pool = sorted((r for r in rows if r["code"].startswith(ch)), key=lambda r: _rank(r["id"]))
        for r in pool[:PER_CHAPTER]:
            keep.setdefault(r["id"], r)
    # cap the always-included headings so one heading can't dominate
    by_heading: dict[str, list[dict]] = {}
    for r in sorted(keep.values(), key=lambda r: _rank(r["id"])):
        by_heading.setdefault(r["code"][:4], []).append(r)
    final = [r for group in by_heading.values() for r in group[:40]]
    final.sort(key=lambda r: (r["issued"], r["id"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "rulings_sample.jsonl").open("w", encoding="utf-8") as fh:
        for r in final:
            text = r["text"] if len(r["text"]) <= MAX_TEXT else r["text"][:MAX_TEXT].rsplit(" ", 1)[0] + " […]"
            fh.write(json.dumps({**r, "text": text, "trimmed": len(r["text"]) > MAX_TEXT}, ensure_ascii=False) + "\n")
    return len(final)


def _heading_of(code: str) -> str:
    return "".join(ch for ch in code if ch.isdigit())[:4]


def tariff() -> tuple[int, int]:
    n_us = n_ca = 0
    src_us, src_ca = DATA / "hts" / "hts_current.jsonl", DATA / "ca" / "customs_tariff_t2026.jsonl"
    if src_us.exists():
        with (OUT / "hts_sample.jsonl").open("w", encoding="utf-8") as fh:
            current = ""
            for line in src_us.open(encoding="utf-8"):
                row = json.loads(line)
                if row.get("htsno"):
                    current = _heading_of(row["htsno"])
                if current in HEADINGS:  # numbered lines and the unnumbered superior lines inside the heading
                    fh.write(line)
                    n_us += 1
    if src_ca.exists():
        with (OUT / "ca_tariff_sample.jsonl").open("w", encoding="utf-8") as fh:
            for line in src_ca.open(encoding="utf-8"):
                if _heading_of(json.loads(line)["tariffItem"]) in HEADINGS:
                    fh.write(line)
                    n_ca += 1
    return n_us, n_ca


def main() -> int:
    n = rulings()
    us, ca = tariff()
    print(f"fixtures: {n} rulings, {us} US lines, {ca} Canadian lines → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
