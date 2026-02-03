"""The rulings corpus, cleaned: labels re-derived from each letter's own holding, numbers checked, statuses linked.

The mirror of CROSS (docs/DATA.md) carries CBP's letters with a ruling number, a date and a tariff number, but
the three don't always belong to the same letter. This module reads every letter on its own terms:

- **Holding.** The classification sentence ("The applicable subheading for … will be 9617.00.1000"; HQ:
  "classified in heading 9617, specifically subheading 9617.00.10") gives the codes the letter actually holds.
- **Number.** HQ letters print their own number in the reference line ("OT:RR:CTF:CPMM H303684 CKG"); when it
  disagrees with the mirror the letterhead wins, unless another letter already holds that number. NY letters
  don't print their number, so a NY ruling is trusted only when its holding agrees with the mirror's tariff
  number at the heading (and, when present, with the chapter in its file reference "CLA-2-73:…").
- **Status.** HQ letters titled "Revocation of …" / "Modification of …" revoke or modify the rulings they name.
  When the corpus letter filed under a revoked number is plainly a different letter (its heading appears
  nowhere in the revoking letter), it is dropped and the revoked ruling is kept as a *noted* record that quotes
  the revoking letter's description, so it can be shown as revoked without pretending we hold its text.
- **Description.** The classifier's input is the product as the letter describes it, *before* any legal
  analysis: the subject line plus the facts, cut at the first sentence that names a heading, a tariff number,
  the HTSUS or a rule, with every tariff number removed. The holding never reaches the classifier.

Labelled examples are rulings whose holdings share one six-digit subheading, agree with the mirror at the
heading and carry a trusted number. Everything else stays searchable evidence (unless its number is wrong) but
never becomes a label. `CleanReport` records every count.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

HOLDING_NY = re.compile(
    r"(?:applicable|appropriate)\s+(?:tariff\s+)?(?:classification\s+)?(?:sub)?heading\s+for\s+.{0,500}?"
    r"\s+(?:will|would|is)\s+be\s+(\d{4}\.\d{2}\.\d{2,4}(?:\.\d{2})?)",
    re.S | re.I,
)
HOLDING_HQ = re.compile(
    r"(?:is|are)\s+(?:properly\s+)?(?:classified|classifiable)\s+(?:in|under)\s+"
    r"(?:heading\s+\d{4},?\s+(?:HTSUS,?\s+)?(?:and\s+)?(?:specifically\s+)?(?:in\s+|under\s+)?)?"
    r"subheading\s+(\d{4}\.\d{2}(?:\.\d{2,4})?)",
    re.S | re.I,
)
HOLDING_SECTION = re.compile(r"\bHOLDINGS?:?\s", re.S)
FILE_REF_CH = re.compile(r"^\s*(?:[A-Z]{3}-\d)?\s*CLA-2-(\d{2})\b")
HQ_OFFICE = re.compile(r"OT:RR:(?:CTF|BSTC|RDL)")
STATUS_RE = re.compile(r"RE:\s*(?:Proposed\s+)?(Revocation|Modification)s?\s+of\s+(.{0,400}?)(?:;|Dear\b)", re.S | re.I)
RULING_REF = re.compile(r"\b(NY|HQ)\s+([A-Z]?\d{5,6})\b")
CODE_ANY = re.compile(r"\b\d{4}\.\d{2}(?:\.\d{2,4}){0,2}\b|\b\d{4}\.\d{2}\b")
SUBJECT_RE = re.compile(r"\bRE:\s*(.{6,300}?)(?:\.\s|\s+Dear\b)", re.S)
DEAR_RE = re.compile(r"\bDear\s+[^:]{1,80}:\s*", re.S)
LEGAL_TURN = re.compile(
    r"\b(?:sub)?headings?\b|\bHTSUS\b|Harmonized Tariff|\bGRIs?\b|General Rules? of Interpretation|"
    r"Explanatory Notes?|\bENs?\b|\bclassif(?:y|ied|ication|iable)\b(?! ruling)|\bNY [A-Z]?\d{5,6}|\bHQ [A-Z]?\d{5,6}|"
    r"\bchapter \d{1,2}\b|\bsection [XVI]+\b|\bnote \d",
    re.I,
)
REQUEST_SENTENCE = re.compile(
    r"(?:requested|request|requesting)\s+(?:a\s+)?(?:binding\s+)?(?:tariff\s+)?(?:classification|ruling)|"
    r"^In your (?:letter|request|electronic)|on behalf of|submitted (?:for|with) (?:our|your) (?:review|request)|"
    r"(?:samples?|photographs?|illustrations?|literature|information) (?:was|were) (?:submitted|provided|received)",
    re.I,
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"(])")
FROM_COUNTRY = re.compile(r"\s+from\s+[A-Z][A-Za-z ,.'-]{1,60}$")
SUBJECT_PREFIX = re.compile(
    r"^(?:The\s+)?(?:tariff\s+)?classification\s+(?:and\s+[a-z ]+\s+)?of\s+(?:an?\s+|the\s+)?", re.I
)
FACTS_HQ = re.compile(r"\bFACTS:?\s*(.*?)(?:\bISSUES?:|\bLAW AND ANALYSIS:?)", re.S)
MAX_DESCRIPTION = 1400


@dataclass
class CleanRuling:
    id: str  # "NY N321134" (from the letterhead when the mirror disagrees)
    issued: str  # ISO date
    collection: str  # NY | HQ
    mirror_id: str
    mirror_code: str
    code: str  # the code the letter holds (first holding), digits; mirror code when there is no holding
    held: list[str]  # every code the letter holds, digits, in order
    heading: str
    subject: str
    description: str  # classifier input: product facts only, no tariff numbers or legal analysis
    holding: str  # the holding sentence, quoted
    text: str
    status: str = "in_force"  # in_force | modified | revoked
    status_by: str | None = None
    status_date: str | None = None
    related: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    labelled: bool = False  # becomes a labelled example (training / validation / test)
    citable: bool = True  # number trusted: may be cited as support
    noted: bool = False  # a revoked ruling known only from the letter that revoked it
    sha256: str = ""
    category: str = "Classification"


@dataclass
class CleanReport:
    read: int = 0
    duplicates: int = 0
    with_holding: int = 0
    no_holding: int = 0
    holding_agrees_heading: int = 0
    holding_agrees_six: int = 0
    holding_agrees_ten: int = 0
    disagree_heading: int = 0
    multi_subheading: int = 0
    file_ref_chapter_disagrees: int = 0
    rekeyed_from_letterhead: int = 0
    collection_mismatch: int = 0
    letterhead_differs: int = 0
    letterhead_conflicts: int = 0
    wrong_letter_under_number: int = 0
    noted_records: int = 0
    revoked: int = 0
    modified: int = 0
    short_description: int = 0
    labelled: int = 0
    citable: int = 0
    kept_searchable: int = 0
    examples: dict[str, list[str]] = field(default_factory=dict)

    def note(self, key: str, rid: str) -> None:
        bucket = self.examples.setdefault(key, [])
        if len(bucket) < 5:
            bucket.append(rid)


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def holdings(text: str) -> tuple[list[str], str]:
    """Codes the letter holds (digits, in order of appearance) and the first holding sentence."""
    found = [(m.start(), m.end(), m.group(1)) for m in HOLDING_NY.finditer(text)]
    if not found:
        sec = HOLDING_SECTION.search(text)
        tail = text[sec.start() :] if sec else text
        offset = sec.start() if sec else 0
        found = [(m.start() + offset, m.end() + offset, m.group(1)) for m in HOLDING_HQ.finditer(tail)]
    codes: list[str] = []
    for _, _, c in found:
        d = digits(c)
        if len(d) >= 6 and d not in codes:
            codes.append(d)
    sentence = ""
    if found:
        start, end, _ = found[0]
        s0 = max(text.rfind(". ", 0, start) + 2, 0)
        e0 = text.find(". ", end)
        sentence = " ".join(text[s0 : e0 + 1 if e0 != -1 else len(text)].split())[:600]
    return codes, sentence


def subject_of(text: str) -> str:
    m = SUBJECT_RE.search(text[:2000])
    return " ".join(m.group(1).split()).rstrip(" .;") if m else ""


def product_phrase(subject: str) -> str:
    """'The tariff classification of stainless steel bottles from China' → 'stainless steel bottles'."""
    s = SUBJECT_PREFIX.sub("", subject)
    s = FROM_COUNTRY.sub("", s)
    return s.strip(" .;")


def describe(text: str, subject: str, collection: str) -> str:
    """The product as described before any legal analysis, without tariff numbers or ruling numbers."""
    body = ""
    if collection == "HQ":
        m = FACTS_HQ.search(text)
        if m:
            body = m.group(1)
    if not body:
        dear = DEAR_RE.search(text[:3000])
        body = text[dear.end() :] if dear else text
    kept: list[str] = []
    for sentence in SENTENCE_SPLIT.split(body):
        if LEGAL_TURN.search(sentence) or CODE_ANY.search(sentence):
            if kept:
                break
            continue  # an opening sentence that only frames the request
        if REQUEST_SENTENCE.search(sentence):
            continue
        kept.append(sentence)
        if sum(len(k) for k in kept) > MAX_DESCRIPTION:
            break
    phrase = product_phrase(subject)
    out = " ".join([phrase + "." if phrase else "", *kept])
    out = RULING_REF.sub("", CODE_ANY.sub("", out))
    return " ".join(out.split())[: MAX_DESCRIPTION + 200]


def iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def _letterhead_number(text: str) -> str | None:
    m = re.search(r"\b(H\d{6})\b", text[:160])
    return m.group(1) if m else None


def clean(rows: Iterable[dict]) -> tuple[list[CleanRuling], CleanReport]:
    rep = CleanReport()
    by_id: dict[str, CleanRuling] = {}
    for r in rows:
        rep.read += 1
        rid = " ".join(str(r["id"]).split())
        if rid in by_id:
            rep.duplicates += 1
            continue
        text = r["text"]
        held, sentence = holdings(text)
        subject = r.get("subject") or subject_of(text)
        mirror_code = digits(r.get("code", ""))
        code = held[0] if held else mirror_code
        cr = CleanRuling(
            id=rid,
            issued=r["issued"],
            collection=rid[:2],
            mirror_id=rid,
            mirror_code=mirror_code,
            code=code,
            held=held,
            heading=code[:4],
            subject=subject,
            description=describe(text, subject, rid[:2]),
            holding=sentence,
            text=text,
            sha256=r.get("sha256") or hashlib.sha256(text.encode()).hexdigest(),
        )
        if held:
            rep.with_holding += 1
            rep.holding_agrees_heading += held[0][:4] == mirror_code[:4]
            rep.holding_agrees_six += held[0][:6] == mirror_code[:6]
            rep.holding_agrees_ten += len(held[0]) == 10 and held[0] == mirror_code[:10]
            if held[0][:4] != mirror_code[:4]:
                cr.flags.append("holding_disagrees_with_mirror")
                cr.citable = False
                rep.disagree_heading += 1
                rep.note("holding_disagrees_with_mirror", rid)
            if len({h[:6] for h in held}) > 1:
                cr.flags.append("several_subheadings")
                rep.multi_subheading += 1
        else:
            rep.no_holding += 1
            cr.flags.append("no_holding")
            cr.category = _category(text, subject)
        ref = FILE_REF_CH.search(text[:120])
        if ref and held and ref.group(1) != held[0][:2]:
            cr.flags.append("file_reference_chapter_differs")
            rep.file_ref_chapter_disagrees += 1
        by_id[rid] = cr

    # Numbers from the letterhead. HQ letters print their own number; NY letters print only a file reference.
    for cr in list(by_id.values()):
        head = _letterhead_number(cr.text)
        hq_letter = bool(HQ_OFFICE.search(cr.text[:160]))
        ny_letter = "OT:RR:NC" in cr.text[:160]
        if cr.collection == "HQ" and ny_letter:
            cr.flags.append("collection_differs_from_letter")
            cr.citable = False
            rep.collection_mismatch += 1
            rep.note("collection_differs_from_letter", cr.id)
            continue
        if not head or not hq_letter or f"HQ {head}" == cr.id:
            continue
        if cr.collection == "HQ":  # two HQ numbers disagree (often a transposed digit): trust neither for citing
            cr.flags.append("letterhead_number_differs")
            cr.citable = False
            rep.letterhead_differs += 1
            rep.note("letterhead_number_differs", f"{cr.id} (letterhead {head})")
            continue
        true_id = f"HQ {head}"  # an HQ letter filed under an NY number: the letterhead wins
        holder = by_id.get(true_id)
        if holder is not None and _letterhead_number(holder.text) == head and HQ_OFFICE.search(holder.text[:160]):
            cr.flags.append("letterhead_conflict")
            cr.citable = False
            rep.letterhead_conflicts += 1
            continue
        if holder is not None:  # the letter filed under the true number is some other letter
            del by_id[true_id]
            holder.id = f"{holder.collection} ?{holder.mirror_id.split()[-1]}"
            if "number_unverified" not in holder.flags:
                holder.flags.append("number_unverified")
            holder.citable = False
            by_id[holder.id] = holder
        del by_id[cr.id]
        cr.id = true_id
        cr.collection = "HQ"
        cr.flags.append("rekeyed_from_letterhead")
        rep.rekeyed_from_letterhead += 1
        rep.note("rekeyed_from_letterhead", f"{cr.mirror_id} → {true_id}")
        by_id[true_id] = cr

    # Revocations and modifications.
    noted: dict[str, CleanRuling] = {}
    for cr in sorted(by_id.values(), key=lambda c: c.issued):
        m = STATUS_RE.search(cr.text[:2000])
        if not m or cr.collection != "HQ":
            continue
        kind = "revoked" if m.group(1).lower().startswith("revoc") else "modified"
        mentioned = {digits(c)[:4] for c in CODE_ANY.findall(cr.text)}
        for col, num in RULING_REF.findall(m.group(2)):
            target_id = f"{col} {num}"
            cr.related.append(target_id)
            target = by_id.get(target_id)
            if target is not None and target.heading not in mentioned and target.heading:
                # the corpus letter under this number is a different letter: drop it, keep a noted record
                rep.wrong_letter_under_number += 1
                rep.note("wrong_letter_under_number", f"{target_id} (filed letter: {target.subject[:60]})")
                del by_id[target_id]
                target.id = f"{target.collection} ?{target_id.split()[-1]}"  # kept as evidence, number unknown
                target.flags.append("number_unverified")
                target.citable = False
                by_id[target.id] = target
                target = None
            if target is None:
                rec = noted.get(target_id) or _noted_record(target_id, cr)
                noted[target_id] = rec
                target = rec
            if target.status == "in_force" or kind == "revoked":
                target.status = kind
                target.status_by = cr.id
                target.status_date = cr.issued
            target.related.append(cr.id)
    for rid, rec in noted.items():
        if rid not in by_id:
            by_id[rid] = rec
            rep.noted_records += 1

    out = sorted(by_id.values(), key=lambda c: (c.issued, c.id))
    for cr in out:
        rep.revoked += cr.status == "revoked"
        rep.modified += cr.status == "modified"
        if cr.noted:
            continue
        rep.kept_searchable += 1
        ok = (
            bool(cr.held)
            and cr.citable
            and "several_subheadings" not in cr.flags
            and "file_reference_chapter_differs" not in cr.flags
            and "letterhead_conflict" not in cr.flags
        )
        if ok and len(cr.description) < 40:
            cr.flags.append("description_too_short")
            rep.short_description += 1
            ok = False
        cr.labelled = ok
        rep.labelled += ok
        rep.citable += cr.citable
    return out, rep


def _category(text: str, subject: str) -> str:
    s = f"{subject} {text[:600]}".lower()
    if "country of origin" in s or "marking" in s:
        return "Country of origin or marking"
    if "valuation" in s or "transaction value" in s:
        return "Valuation"
    if "coastwise" in s or "vessel" in s:
        return "Vessels"
    if "drawback" in s:
        return "Drawback"
    return "Other"


def _noted_record(target_id: str, revoking: CleanRuling) -> CleanRuling:
    """A revoked ruling we know only from the letter that revoked it (quoted, never invented)."""
    num = target_id.split()[-1]
    text = revoking.text
    i = text.find(f"in {target_id}")
    if i == -1:
        i = text.find(target_id, 400)
    excerpt = " ".join(text[max(i, 0) : max(i, 0) + 900].split()) if i != -1 else ""
    prior = re.search(
        rf"{re.escape(target_id)}[^.]{{0,300}}?(?:subheading|heading)\s+(\d{{4}}(?:\.\d{{2}}(?:\.\d{{2,4}})?)?)", text
    )
    code = digits(prior.group(1)) if prior else ""
    return CleanRuling(
        id=target_id,
        issued="",
        collection=target_id[:2],
        mirror_id=target_id,
        mirror_code="",
        code=code,
        held=[code] if code else [],
        heading=code[:4],
        subject=f"Ruling {num}, as described in {revoking.id}",
        description="",
        holding="",
        text=(
            f"The letter for {target_id} is not in the corpus. {revoking.id} ({revoking.issued}) describes it: "
            f"{excerpt}"
        ),
        flags=["noted_from_revoking_letter"],
        citable=False,
        noted=True,
        sha256=hashlib.sha256(f"{target_id}:{revoking.sha256}".encode()).hexdigest(),
        category="Classification",
    )


def save(rulings: list[CleanRuling], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rulings:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def load(path: Path) -> list[CleanRuling]:
    return [CleanRuling(**row) for row in iter_jsonl(path)]


def issued(r: CleanRuling) -> date | None:
    return date.fromisoformat(r.issued) if r.issued else None


def snapshot_hash(rulings: Iterable[CleanRuling]) -> str:
    h = hashlib.sha256()
    for r in sorted(rulings, key=lambda r: r.id):
        h.update(f"{r.id}\t{r.sha256}\n".encode())
    return h.hexdigest()


def counts(rulings: list[CleanRuling]) -> Counter:
    return Counter(r.heading[:2] for r in rulings if r.labelled)
