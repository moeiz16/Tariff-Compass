"""Build the small committed fixtures (backend/tariffcompass/search/fixtures) from data/ after fetch_data.py.

The fixtures let tests, CI and the offline demo run without downloading anything: a deterministic sample of
rulings from the chapters Northbound imports (every 9617 ruling included), and the tariff lines of those
chapters for the US and Canada. Letters are trimmed to keep the repository small.
"""

from __future__ import annotations

import hashlib
import json
import re
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
# Rulings the seed, the docket, Watch and the samples cite (by their cleaned ids), always kept.
FORCE = (
    "NY N321134", "HQ H303684", "NY N297165", "NY N321985", "NY N297760", "NY N298117", "NY N265787",
    "NY N343672", "NY N341481", "NY N342804", "NY N344429", "NY N333596", "NY N331973", "NY N334131",
    "NY N309424", "NY N320207", "NY N350116", "NY N347094", "NY N346959", "NY N340388", "NY N341281",
    "NY N349433", "NY N343619", "NY N329546", "NY N341977", "NY N342008", "NY N338957", "NY N344038",
    "NY N337096", "NY N326613", "NY N329004", "NY N322548", "NY N343677", "NY N304023", "NY N249601",
    "NY N326879", "NY N266733", "NY N325197", "NY N339129", "HQ H268599", "NY N341339", "NY N325073",
    "NY N347592", "NY N343667", "NY N335445",
    # real status links in the product set's headings (revoked or modified by a corpus HQ letter)
    "NY N249247", "HQ H265674", "NY N284187", "HQ H289250", "NY N279310", "HQ H282945",
)  # fmt: skip


def _rank(rid: str) -> str:
    return hashlib.sha256(rid.encode()).hexdigest()


def _trim(text: str) -> str:
    """Keep the opening (facts) and the holding sentence, so the sample still states its classification."""
    if len(text) <= MAX_TEXT:
        return text
    m = re.search(r"(?:applicable|appropriate)\s+(?:tariff\s+)?(?:sub)?heading\s+for|HOLDINGS?:", text, re.I)
    head = text[:1600].rsplit(" ", 1)[0]
    if m and m.start() > 1600:
        tail = text[max(m.start() - 200, 1600) : m.start() + 600].split(" ", 1)[-1].rsplit(" ", 1)[0]
        return f"{head} […] {tail} […]"
    return text[:MAX_TEXT].rsplit(" ", 1)[0] + " […]"


def _mirror_ids() -> set[str]:
    """Mirror ids of the forced rulings (the cleaned corpus maps letterhead ids back to the mirror's)."""
    clean = DATA / "rulings" / "rulings_clean.jsonl"
    if not clean.exists():
        return set(FORCE)
    out = set()
    for line in clean.open(encoding="utf-8"):
        r = json.loads(line)
        if r["id"] in FORCE:
            out.add(r["mirror_id"])
    return out


def rulings() -> int:
    rows = [json.loads(line) for line in (DATA / "rulings" / "rulings.jsonl").open(encoding="utf-8")]
    keep: dict[str, dict] = {}
    forced = _mirror_ids()
    for r in rows:
        if r["id"] in forced:
            keep[r["id"]] = r
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
    final += [r for r in keep.values() if r["id"] in forced and r not in final]
    final.sort(key=lambda r: (r["issued"], r["id"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "rulings_sample.jsonl").open("w", encoding="utf-8") as fh:
        for r in final:
            text = _trim(r["text"])
            fh.write(json.dumps({**r, "text": text, "trimmed": len(r["text"]) > MAX_TEXT}, ensure_ascii=False) + "\n")
    return len(final)


def _heading_of(code: str) -> str:
    return "".join(ch for ch in code if ch.isdigit())[:4]


def tariff() -> tuple[int, int]:
    n_us = n_ca = 0
    src_us, src_ca = DATA / "hts" / "hts_2026_rev3.jsonl", DATA / "ca" / "customs_tariff_t2026.jsonl"
    if not src_us.exists():
        src_us = DATA / "hts" / "hts_current.jsonl"
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
