"""Download the public data into data/ (git-ignored). Stdlib only; polite (one request at a time, pauses).

    python scripts/fetch_data.py [rulings] [hts] [rev3] [ca] [--since 2014-01-01] [--chapters 39,42,61,...]

- rulings: CBP CROSS rulings (NY and HQ letters) from a public mirror of CROSS on Hugging Face
  (`orlandowhite/hts-cross-rulings`, ~290 MB JSON). CROSS itself has no bulk export and its search API refuses
  scripted clients. We stream-parse the mirror and keep only CBP's own fields: ruling number, date, tariff
  number and the letter text (US government works, public domain). The mirror's generated summaries are
  dropped. Output: data/rulings/rulings.jsonl (one ruling per line), then the download is deleted.
- hts: the USITC HTS JSON export, chapter by chapter (exportList). USITC serves JSON for the current revision
  only; the release name is recorded so the snapshot is explicit (docs/DATA.md explains how the demo pins
  2026 Revision 3). Output: data/hts/hts_current.jsonl + data/hts/release.json.
- rev3: the 2026 HTSUS Revision 3 chapter PDFs (archived revisions are PDF only). Every eight-digit line of the
  current JSON is checked against the Revision 3 text of its chapter: present or not, and whether its column 1
  General rate is printed beside it. Output: data/hts/hts_2026_rev3.jsonl (the current JSON restricted to lines
  present in Revision 3) and data/hts/rev3_check.json (every difference, listed).
- ca: CBSA Customs Tariff T2026 (effective 1 Jan 2026), chapter HTML pages parsed into
  data/ca/customs_tariff_t2026.jsonl (tariff item, suffix, description, unit, MFN, preferential treatments).
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
UA = "TariffCompass-data-fetch/0.1 (+offline demo; polite)"
RULINGS_URL = "https://huggingface.co/datasets/orlandowhite/hts-cross-rulings/resolve/main/cross_rulings.json"
HTS_EXPORT = "https://hts.usitc.gov/reststop/exportList?from={a}&to={b}&format=JSON&styles=false"
HTS_RELEASES = "https://hts.usitc.gov/reststop/releaseList"
CA_CHAPTER = "https://www.cbsa-asfc.gc.ca/trade-commerce/tariff-tarif/2026/html/00/ch{ch:02d}-eng.html"
PAUSE = 1.0
_getaddrinfo = socket.getaddrinfo


def _prefer_ipv4(host, port, family=0, *args, **kwargs):
    """urllib has no happy-eyeballs fallback; some government hosts hang on IPv6, so try IPv4 first."""
    res = _getaddrinfo(host, port, family, *args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET] or res


socket.getaddrinfo = _prefer_ipv4


def get(url: str, dest: Path | None = None, timeout: int = 120, attempts: int = 4) -> bytes:
    for attempt in range(1, attempts + 1):
        try:
            return _get_once(url, dest, timeout)
        except (OSError, urllib.error.URLError) as exc:
            if attempt == attempts:
                raise
            wait = 5 * attempt
            print(f"  retry {attempt}/{attempts - 1} in {wait}s after {exc}", file=sys.stderr)
            time.sleep(wait)
    return b""


def _get_once(url: str, dest: Path | None, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if dest is None:
            return resp.read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as fh:
            while chunk := resp.read(1 << 20):
                fh.write(chunk)
        return b""


def iter_json_array(path: Path, chunk: int = 1 << 20):
    """Yield objects from a huge top-level JSON array without loading it (raw_decode over a rolling buffer)."""
    dec = json.JSONDecoder()
    buf, pos, started = "", 0, False
    with path.open(encoding="utf-8") as fh:
        while True:
            data = fh.read(chunk)
            buf = buf[pos:] + data
            pos = 0
            while True:
                while pos < len(buf) and buf[pos] in " \r\n\t,":
                    pos += 1
                if not started:
                    if pos < len(buf) and buf[pos] == "[":
                        started, pos = True, pos + 1
                        continue
                    break
                if pos < len(buf) and buf[pos] == "]":
                    return
                try:
                    obj, end = dec.raw_decode(buf, pos)
                except json.JSONDecodeError:
                    break  # need more data
                yield obj
                pos = end
            if not data:
                return


DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d")
CODE_RE = re.compile(r"\b(\d{4}\.\d{2}\.\d{2,4}(?:\.\d{2})?)\b")
STATED_RE = re.compile(r"\d{4}\.?\d{2}(?:\.?\d{2}(?:\.?\d{2})?)?")
RE_LINE = re.compile(r"\bRE:\s*(.{10,240}?)(?:\.\s|Dear\b)", re.S)


def parse_date(s: str) -> date | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def fetch_rulings(since: date) -> None:
    out = DATA / "rulings" / "rulings.jsonl"
    raw = DATA / "raw" / "cross_rulings.json"
    if not raw.exists():
        print(f"downloading rulings mirror (~290 MB) → {raw}")
        get(RULINGS_URL, raw, timeout=900)
    kept = skipped = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in iter_json_array(raw):
            issued = parse_date(str(r.get("date", "")))
            text = (r.get("original_ruling_text") or "").strip()
            stated = [re.sub(r"\D", "", c) for c in STATED_RE.findall(str(r.get("hts_code", "")))]
            code = stated[0] if stated else ""
            rid = " ".join(str(r.get("ruling_id", "")).split())
            if not issued or issued < since or len(code) < 6 or len(text) < 200 or rid[:2] not in ("NY", "HQ"):
                skipped += 1
                continue
            subject = RE_LINE.search(text)
            codes = sorted(set(stated) | {re.sub(r"\D", "", c) for c in CODE_RE.findall(text)})
            fh.write(
                json.dumps(
                    {
                        "id": rid,
                        "issued": issued.isoformat(),
                        "collection": rid[:2],
                        "code": code,
                        "codes": codes,
                        "subject": " ".join(subject.group(1).split()) if subject else "",
                        "text": text,
                        "sha256": hashlib.sha256(text.encode()).hexdigest(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            kept += 1
    raw.unlink()
    print(f"rulings: kept {kept} since {since} ({skipped} skipped) → {out}")


def fetch_hts(chapters: list[int]) -> None:
    out = DATA / "hts" / "hts_current.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    releases = json.loads(get(HTS_RELEASES))
    current = next((r for r in releases if r.get("status") == "current"), {})
    (DATA / "hts" / "release.json").write_text(
        json.dumps({"release": current.get("name"), "title": current.get("title")}, indent=1)
    )
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for ch in chapters:
            rows = json.loads(get(HTS_EXPORT.format(a=f"{ch:02d}00", b=f"{ch:02d}99")))
            for row in rows:
                fh.write(
                    json.dumps(
                        {
                            "chapter": f"{ch:02d}",
                            **{
                                k: row.get(k)
                                for k in (
                                    "htsno",
                                    "indent",
                                    "description",
                                    "superior",
                                    "units",
                                    "general",
                                    "special",
                                    "other",
                                    "footnotes",
                                )
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                n += 1
            time.sleep(PAUSE)
    print(f"hts: {n} lines from release {current.get('name')} → {out}")


REV3_PDF = "https://hts.usitc.gov/reststop/file?release=2026HTSRev3&filename=Chapter%20{ch}"
PDF_CODE = re.compile(r"\d*(\d{4}\.\d{2}\.\d{2})")
PDF_RATE = re.compile(r"\d+(?:\.\d+)?%|Free")


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader  # backend dependency; run with the backend venv

    return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)


def check_rev3(chapters: list[int]) -> None:
    """Pin the schedule to 2026 Revision 3: keep the current JSON's lines that Revision 3 prints, list the rest."""
    src = DATA / "hts" / "hts_current.jsonl"
    rows = [json.loads(line) for line in src.open(encoding="utf-8")]
    pdf_dir = DATA / "hts" / "rev3"
    report: dict = {"release": "2026HTSRev3", "chapters": {}, "missingInRev3": [], "onlyInRev3": [], "rateNotSeen": []}
    rev3_codes: dict[str, dict[str, list[str]]] = {}
    for ch in chapters:
        if ch == 77:
            continue
        pdf = pdf_dir / f"chapter-{ch:02d}.pdf"
        if not pdf.exists():
            get(REV3_PDF.format(ch=ch), pdf, timeout=300)
            time.sleep(PAUSE)
        text = _pdf_text(pdf)
        codes: dict[str, list[str]] = {}
        matches = list(PDF_CODE.finditer(text))
        for i, m in enumerate(matches):
            window = text[m.end() : matches[i + 1].start() if i + 1 < len(matches) else m.end() + 400]
            codes.setdefault(m.group(1), []).extend(PDF_RATE.findall(window[:400]))
        rev3_codes[f"{ch:02d}"] = codes
    kept = 0
    seen_current: set[str] = set()
    out = DATA / "hts" / "hts_2026_rev3.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            ch = row["chapter"]
            code = row.get("htsno") or ""
            eight = code[:10] if len(code) >= 10 else ""
            if ch not in rev3_codes:
                continue
            if eight:
                seen_current.add(eight)
                if eight not in rev3_codes[ch]:
                    report["missingInRev3"].append(code)
                    continue
                general = (row.get("general") or "").strip()
                if len(code) == 10 and general and general not in rev3_codes[ch][eight]:
                    report["rateNotSeen"].append({"code": code, "general": general})
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            kept += 1
    for ch, codes in rev3_codes.items():
        only = sorted(c for c in codes if c not in seen_current and c[:2] == ch)
        report["onlyInRev3"].extend(only)
        report["chapters"][ch] = {"rev3EightDigit": len(codes)}
    report["kept"] = kept
    demo = REPO / "eval" / "sets" / "landed_cost_20.json"
    if demo.exists():
        codes = sorted({p["code"] for p in json.loads(demo.read_text())["products"] if p["country"] == "US"})
        report["demoLines"] = check_demo_lines(codes)
    (DATA / "hts" / "rev3_check.json").write_text(json.dumps(report, indent=1))
    print(
        f"rev3: kept {kept} lines; {len(report['missingInRev3'])} current lines not in Rev 3; "
        f"{len(report['onlyInRev3'])} Rev 3 lines not in the current JSON; "
        f"{len(report['rateNotSeen'])} rates not seen beside their line → {out}"
    )


def check_demo_lines(codes: list[str]) -> dict:
    """Each ten-digit line the demo relies on, read in the Revision 3 PDF of its chapter: the eight-digit number,
    then its statistical suffix before the next eight-digit number (a '00' suffix prints glued to the number)."""
    out = {}
    texts: dict[str, str] = {}
    for code in codes:
        d = re.sub(r"\D", "", code)
        ch = d[:2]
        if ch not in texts:
            texts[ch] = _pdf_text(DATA / "hts" / "rev3" / f"chapter-{ch}.pdf")
        t = texts[ch]
        eight = f"{d[:4]}.{d[4:6]}.{d[6:8]}"
        found = False
        for m in re.finditer(re.escape(eight), t):
            nxt = PDF_CODE.search(t, m.end())
            window = t[max(m.start() - 2, 0) : nxt.start() if nxt else m.end() + 3000]
            if (d[8:] == "00" and t[max(m.start() - 2, 0) : m.start()] == "00") or re.search(
                rf"(?<![\d.]){d[8:]}(?![\d.%])", window[len(eight) + 2 :]
            ):
                found = True
            if found:
                break
        out[code] = found
    return out


ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _clean(cell: str) -> str:
    return " ".join(html.unescape(re.sub(r"<br\s*/?>", " | ", re.sub(r"<(?!br)[^>]+>", "", cell))).split())


def fetch_ca(chapters: list[int]) -> None:
    out = DATA / "ca" / "customs_tariff_t2026.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for ch in chapters:
            if ch == 77:
                continue  # reserved
            page = get(CA_CHAPTER.format(ch=ch)).decode("utf-8", "replace")
            for row in ROW_RE.findall(page):
                cells = [_clean(c) for c in CELL_RE.findall(row)]
                if len(cells) < 6 or not re.match(r"^\d{2}\.\d{2}$|^\d{4}\.\d{2}(\.\d{2})?$", cells[0]):
                    continue
                item, suffix, desc, unit, mfn, pref = cells[:6]
                fh.write(
                    json.dumps(
                        {
                            "chapter": f"{ch:02d}",
                            "tariffItem": item,
                            "suffix": suffix.strip("- "),
                            "description": desc,
                            "unit": unit.strip("- "),
                            "mfn": mfn,
                            "preferential": pref,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                n += 1
            time.sleep(PAUSE)
    print(f"ca: {n} lines (T2026) → {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="*", default=["rulings", "hts", "rev3", "ca"])
    ap.add_argument("--since", default="2014-01-01")
    ap.add_argument("--chapters", default="", help="comma-separated chapters (default: all 1–97)")
    a = ap.parse_args()
    chapters = [int(c) for c in a.chapters.split(",") if c] or list(range(1, 98))
    if "rulings" in a.what:
        fetch_rulings(date.fromisoformat(a.since))
    if "hts" in a.what:
        fetch_hts(chapters)
    if "rev3" in a.what:
        check_rev3(chapters)
    if "ca" in a.what:
        fetch_ca(chapters)
    return 0


if __name__ == "__main__":
    sys.exit(main())
