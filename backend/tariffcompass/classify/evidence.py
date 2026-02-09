"""The evidence the program's modules read, and the text blocks that carry it to the LM.

`build()` gathers, once per product: the first stage's top headings, how the rulings found for the description
vote across headings, the rulings filed under each candidate heading, the tariff lines under each heading (US
and Canada) and the notes that relate candidate headings to each other. The same bundle drives a live answer, a
GEPA training example and an evaluation example; `before` hides rulings issued on or after a date, so an
example never finds itself or anything newer.

The `render_*` functions write the blocks each signature's input fields receive, one item per line with `|`
separated fields; the `parse_*` functions read the modules' outputs back defensively (an LM may answer
loosely). Both sides of this format are tested with the simulator's policies (`adapters/lm_sim.py`).
"""

from __future__ import annotations

import math
import re
from datetime import date

from tariffcompass.contracts import FirstStageResult, ProductQuery, Retriever, Span
from tariffcompass.search.sections import chapter_title

# Notes quoted from the HTSUS (as quoted in CBP rulings) that set one candidate aside in favour of another:
# (excluded heading prefix, chosen heading prefix) → note.
NOTES: tuple[tuple[tuple[str, ...], tuple[str, ...], str, str], ...] = (
    (
        tuple(str(c) for c in range(72, 84)),
        ("96",),
        "Section XV, Note 1(m)",
        "This section does not cover: … (m) Hand sieves, buttons, pens, pencil-holders, pen nibs, monopods, bipods, "
        "tripods and similar articles or other articles of chapter 96 (miscellaneous manufactured articles).",
    ),
    (
        ("86", "87", "88", "89"),
        ("85",),
        "Section XVII, Note 2(f)",
        "The expressions “parts” and “parts and accessories” do not apply to the following articles, whether or not "
        "they are identifiable as for the goods of this section: … (f) Electrical machinery or equipment (chapter 85).",
    ),
)
TARIFF_CANDIDATES = 3  # headings added from a search of the tariff text itself
_EXCLUDING = re.compile(r"(?:other than|excluding|except)\b[^;:]*?heading\s+(\d{2})\.?(\d{2})", re.I)
CITE_RE = re.compile(r"\[(\d+)\]")
WORD = re.compile(r"[a-z][a-z0-9-]+")
STOP_WORDS = (
    "the a an and or of for with to in on by at from as is are be it its this that these those which other than not "
    "no any all each into per such use used thereof parts nesoi kind whether"
)
STOP = frozenset(STOP_WORDS.split())
MAX_CANDIDATES = 6  # from the first stage and the rulings' votes; tariff-text headings come on top


def span(s) -> Span:
    return Span(int(s[0]), int(s[1]))


def words(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 2]


def stem(w: str) -> str:
    """A light stemmer: plurals first (batteries → battery, boxes → box, bicycles → bicycle), then -ing / -ed."""
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith(("ches", "shes", "sses", "xes", "zes")):
        w = w[:-2]
    elif w.endswith("s") and not w.endswith(("ss", "us", "is")) and len(w) > 3:
        w = w[:-1]
    if w.endswith("ing") and len(w) >= 7:
        w = w[:-3]
    elif w.endswith("ed") and len(w) >= 6:
        w = w[:-2]
    return w


def stems(text: str) -> set[str]:
    return {stem(w) for w in words(text)}


def short(text: str, n: int = 80) -> str:
    t = (text or "").split(";")[0].split(":")[0].strip().rstrip(",")
    t = t[0].lower() + t[1:] if t[:1].isupper() and not t[:2].isupper() else t
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


MATERIAL_WORDS = (
    "stainless steel iron aluminum aluminium plastic plastics polypropylene polyethylene polyester nylon cotton "
    "wool silicone rubber glass ceramic wood bamboo leather copper zinc alloy metal"
)
MATERIALS = frozenset(MATERIAL_WORDS.split())


def article_words(text: str) -> str:
    """The words that name the article and what it does, without materials or numbers: what a heading's terms
    are searched with (materials are the first stage's job, and they drown the article in the tariff text)."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]+", text) if w.lower() not in MATERIALS]
    return " ".join(words)


def expand(text: str) -> str:
    """The description plus the tariff words a reader would search for (the simulator's PHRASES and READS)."""
    from tariffcompass.adapters.lm_sim import _RULED_OUT, PHRASES, READS

    extra = [words for pat, words in PHRASES if pat.search(text)]
    if not _RULED_OUT.search(text):
        extra += [v for k, v in READS.items() if k in text.lower()]
    return " ".join([text, *extra])


def product_text(q: ProductQuery) -> str:
    parts = [q.text.strip()]
    if q.spec_sheet_text:
        parts.append("Spec sheet: " + q.spec_sheet_text.strip()[:1500])
    if q.photo_facts:
        parts.append("Photo: " + " ".join(q.photo_facts))
    for k, v in q.confirmed_facts:
        parts.append(f"Confirmed: {k.replace('_', ' ')} is {v}.")
    if q.made_in:
        parts.append(f"Made in {q.made_in}.")
    return "\n".join(parts)


# ── building ────────────────────────────────────────────────────────────────────────────────────────────
def _ruling_dict(h, sim: float, text: str = "") -> dict:
    return {
        "id": h.ruling_id,
        "issued": h.issued.isoformat() if h.issued else "",
        "code": h.code,
        "heading": h.heading,
        "subject": h.subject,
        "holding": h.holding,
        "status": h.status,
        "status_by": h.status_by,
        "status_date": h.status_date.isoformat() if h.status_date else None,
        "score": round(h.rerank, 4),
        "bm25": round(h.bm25, 3),
        "sim": round(sim, 3),
        "passages": [[p[0], [[s.start, s.end] for s in p[1]]] for p in h.passages],
        "text": text,
    }


def build(query: ProductQuery, first: FirstStageResult, retriever: Retriever, *, before: date | None = None) -> dict:
    text = product_text(query)
    probs = {c.code: c.probability for c in first.headings}
    kwargs: dict = {"heading_probs": probs}
    if before is not None:
        kwargs["before"] = before
    try:
        general = retriever.rulings(text, k=10, **kwargs)
    except TypeError:  # a retriever without the optional keywords (the fake)
        general = retriever.rulings(text, k=10)
    us = getattr(retriever, "us", None)
    votes: dict[str, float] = {}
    top_bm = max((h.bm25 for h in general), default=1.0) or 1.0
    for h in general:
        if h.status == "revoked":
            continue
        votes[h.heading] = votes.get(h.heading, 0.0) + h.bm25 / top_bm
    total = sum(votes.values()) or 1.0
    votes = {k: round(v / total, 4) for k, v in votes.items()}

    def known(hd: str) -> bool:
        return us is None or us.line(hd) is not None

    cand = [c.code for i, c in enumerate(first.headings) if known(c.code) and (i < 2 or c.probability >= 0.005)][:5]
    for hd, _ in sorted(votes.items(), key=lambda kv: -kv[1]):
        if len(cand) >= MAX_CANDIDATES - TARIFF_CANDIDATES:
            break
        if hd not in cand and votes[hd] >= 0.15 and known(hd):
            cand.append(hd)
    tariff_rank: dict[str, float] = {}
    if us is not None:
        lead = re.split(r"[.:;]", query.text, maxsplit=1)[0]  # the article itself, before its details
        for q_text in (article_words(expand(query.text[:400])), article_words(expand(lead))):
            found = retriever.tariff(q_text, country="US", k=12, levels=("heading", "subheading"))  # type: ignore[call-arg]
            for i, line in enumerate(found):
                tariff_rank[line.code[:4]] = tariff_rank.get(line.code[:4], 0.0) + 1.0 / (i + 1)
        added = 0
        for hd, _ in sorted(tariff_rank.items(), key=lambda kv: -kv[1]):
            if added >= TARIFF_CANDIDATES or len(cand) >= MAX_CANDIDATES + TARIFF_CANDIDATES:
                break
            if hd not in cand and known(hd):
                cand.append(hd)
                added += 1
    top_t = max(tariff_rank.values(), default=1.0) or 1.0
    e: dict = {
        "first_stage": [
            {"code": c.code, "p": c.probability, "why": [w for w, _ in c.why_terms]} for c in first.headings
        ],
        "chapters": [{"code": c.code, "p": c.probability} for c in first.chapters],
        "votes": votes,
        "candidates": [],
        "rulings": {},
        "general": [_ruling_dict(h, h.bm25 / top_bm) for h in general],
        "us_lines": {},
        "ca_lines": {},
        "us_text": {},
        "ca_text": {},
        "heading_text": {},
        "ca_heading_text": {},
        "notes": {},
        "excludes": {},
        "line_words": {},
    }
    for hd in cand:
        hline = retriever.tariff_line("US", hd)
        htext = hline.text if hline else ""
        e["heading_text"][hd] = htext
        cline = retriever.tariff_line("CA", hd)
        e["ca_heading_text"][hd] = cline.text if cline else htext
        e["candidates"].append(
            {
                "heading": hd,
                "p": round(probs.get(hd, 0.0), 4),
                "votes": votes.get(hd, 0.0),
                "tariff": round(tariff_rank.get(hd, 0.0) / top_t, 3),
                "text": htext,
            }
        )
        try:
            hits = retriever.rulings(text, headings=[hd], k=4, snippets=True, **kwargs)  # type: ignore[call-arg]
        except TypeError:
            hits = [h for h in retriever.rulings(text, headings=[hd], k=4) if h.heading == hd]
        rows = []
        for h in hits:
            doc = retriever.ruling(h.ruling_id)
            body = (doc.text if doc else "")[:1500]
            rows.append(_ruling_dict(h, overlap(query.text, f"{h.subject} {body}"), body))
        e["rulings"][hd] = rows
        if us is not None:
            leaves = us.leaves(hd)
            e["us_lines"][hd] = [[ln.code, ln.full_text] for ln in leaves]
            for n in (6, 8):
                for ln in leaves:
                    anc = us.line(ln.code[:n])
                    if anc is not None:
                        e["us_text"][anc.code] = anc.text
            for ln in leaves:
                e["us_text"][ln.code] = ln.text
            ca = getattr(retriever, "ca", None)
            if ca is not None:
                cl = ca.leaves(hd)
                e["ca_lines"][hd] = [[ln.code, ln.full_text] for ln in cl]
                for ln in cl:
                    e["ca_text"][ln.code] = ln.text
        else:  # the fake retriever: one line per country
            for country, key in (("US", "us_lines"), ("CA", "ca_lines")):
                ln = retriever.tariff(text, country=country, under=hd, k=1)  # type: ignore[arg-type]
                e[key][hd] = [[x.code, x.full_text] for x in ln]
                for x in ln:
                    e["us_text" if country == "US" else "ca_text"][x.code] = x.text
        e["line_words"][hd] = line_words(e["us_lines"].get(hd, []))
        m = _EXCLUDING.findall(htext)
        e["excludes"][hd] = [a + b for a, b in m]
    for hd in cand:
        for excluded, chosen, ref, quote in NOTES:
            if hd[:2] in chosen and any(o[:2] in excluded for o in cand if o != hd):
                e["notes"].setdefault(hd, []).append({"ref": ref, "quote": quote, "excludes": list(excluded)})
    p = [c["p"] for c in e["candidates"]]
    ranked = [*sorted(p, reverse=True), 0.0, 0.0]
    e["margin"] = round(ranked[0] - ranked[1], 4)
    return e


# ── blocks the modules read ─────────────────────────────────────────────────────────────────────────────
def line_words(rows: list[list[str]], limit: int = 40) -> str:
    """The words the heading's own lines use below the heading text (what a reader scans for), comma-joined."""
    seen: list[str] = []
    for _, full in rows:
        for seg in full.split(": ")[1:]:
            for w in WORD.findall(seg.lower()):
                w = re.sub(r"[^a-z0-9-]", "", w)
                if len(w) > 3 and w not in STOP and w not in seen and not w.isdigit():
                    seen.append(w)
    return ",".join(seen[:limit])


def render_candidates(e: dict) -> str:
    return "\n".join(
        f"{c['heading']} | p={c['p']:.3f} | precedent={c['votes']:.3f} | tariff_text={c.get('tariff', 0):.3f} | "
        f"lines={e.get('line_words', {}).get(c['heading'], '') or 'none'} | {c['text']}"
        for c in e["candidates"]
    )


def parse_heading_list(text: str, allowed: list[str]) -> list[str]:
    found = [h for h in re.findall(r"\b(\d{4})\b", text or "") if h in allowed]
    out = list(dict.fromkeys(found))
    return out + [h for h in allowed if h not in out]


def number_rulings(e: dict, headings: list[str], per: int = 2) -> list[dict]:
    rows = []
    for h in headings:
        rows.extend(e["rulings"].get(h, [])[:per])
    return rows


def render_rulings(rows: list[dict]) -> str:
    return "\n".join(
        f"[{i + 1}] {r['id']} | {r['heading']} | {r['status']} | {r['issued']} | sim={r.get('sim', 0):.3f} "
        f"| {r['holding'][:300]}"
        for i, r in enumerate(rows)
    )


def render_gri_headings(e: dict, headings: list[str]) -> str:
    lines = []
    for rank, h in enumerate(headings, 1):
        c = next((c for c in e["candidates"] if c["heading"] == h), {"p": 0.0, "votes": 0.0})
        notes = "; ".join(
            f"{n['ref']} excludes chapters {n['excludes'][0]}-{n['excludes'][-1]}" for n in e["notes"].get(h, [])
        )
        excl = ",".join(e["excludes"].get(h, []))
        lines.append(
            f"{h} | rank={rank} | p={c['p']:.3f} | precedent={c['votes']:.3f} | excludes={excl or 'none'} | "
            f"notes={notes or 'none'} | lines={e.get('line_words', {}).get(h, '') or 'none'} | "
            f"{e['heading_text'].get(h, '')}"
        )
    return "\n".join(lines)


def parse_heading(text: str, allowed: list[str]) -> str | None:
    for h in re.findall(r"\b(\d{4})\b", text or ""):
        if h in allowed:
            return h
    return None


def parse_gri(text: str) -> str:
    m = re.search(r"GRI\s*([1-6])\s*(\([abc]\))?", text or "", re.I)
    if not m:
        return "GRI 1"
    g = f"GRI {m.group(1)}"
    if m.group(2):
        g += m.group(2).lower()
    elif m.group(1) in ("2", "3", "5"):
        g += "(a)"
    return g


def render_lines(e: dict, heading: str, country: str, us_code: str = "") -> str:
    rows = e["us_lines" if country == "US" else "ca_lines"].get(heading, [])
    prec = [
        f"precedent: {r['id']} → {r['code']} (sim {r.get('sim', 0):.3f})"
        for r in e["rulings"].get(heading, [])
        if r["status"] != "revoked" and len(r["code"]) >= 8
    ]
    if country == "CA" and us_code:
        prec = [f"us_code: {us_code}"]
    return "\n".join([*prec, *(f"{c} | {t}" for c, t in rows)])


def parse_code(text: str, lines: list[list[str]]) -> str:
    valid = [c for c, _ in lines]
    d = re.sub(r"\D", "", text or "")
    for cand in (d[:10], d[:8] + "00" if len(d) >= 8 else "", d):
        if cand in valid:
            return cand
    pref = [c for c in valid if d and c.startswith(d[:8])] or [c for c in valid if d and c.startswith(d[:6])]
    return (pref or valid or [""])[0]


def parse_set_aside(text: str, chosen: str) -> list[tuple[str, str, str | None]]:
    out = []
    for line in (text or "").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if not parts or not re.fullmatch(r"\d{4}", parts[0]) or parts[0] == chosen:
            continue
        rid = parts[2] if len(parts) > 2 and parts[2].lower() != "none" else None
        out.append((parts[0], parts[1] if len(parts) > 1 else "Set aside", rid))
    return out


def citation_rulings(e: dict, heading: str, others: list[str]) -> list[dict]:
    """Rulings the citation step may use: the chosen heading's first, then the strongest of each neighbour."""
    rows = list(e["rulings"].get(heading, []))
    for h in others[:2]:
        rows.extend(e["rulings"].get(h, [])[:1])
    for r in e["general"]:
        if len(rows) >= 7:
            break
        if r["id"] not in {x["id"] for x in rows}:
            rows.append(r)
    return rows[:7]


def render_decision(heading: str, us_code: str, ca_code: str, gri: str, set_aside: list) -> str:
    aside = ", ".join(h for h, _, _ in set_aside) or "none"
    return (
        f"heading={heading} | us={us_code} | ca={ca_code or 'none'} | gri={gri.strip() or 'GRI 1'} | set_aside={aside}"
    )


def parse_sentences(text: str, n_rulings: int) -> list[tuple[str, tuple[int, ...]]]:
    out = []
    for line in (text or "").splitlines():
        line = line.strip(" -•\t")
        if len(line) < 8:
            continue
        ns = tuple(int(x) for x in CITE_RE.findall(line) if 0 < int(x) <= n_rulings)
        out.append((line, ns))
    return out[:5]


def is_contrast_sentence(text: str) -> bool:
    t = text.lower()
    return t.startswith(("by contrast", "in contrast", "contrast:", "unlike")) or "for contrast" in t


def strip_cites(text: str) -> str:
    return " ".join(CITE_RE.sub("", text).split()).replace(" .", ".")


def deciding_status(product: str, heading: str, runner: str | None) -> str:
    """Whether the fact that separates the chosen heading from its runner-up is stated, and which way it points."""
    from tariffcompass.classify import facts as facts_mod

    if not runner:
        return "none"
    d = facts_mod.DISTINCTIONS.get(frozenset({heading, runner}))
    if d is None:
        return "none"
    f = next((f for f in facts_mod.extract(product) if f.key == d.key), None)
    if f is None:
        return "unknown"
    if f.source == "read":
        return "read"
    lead = d.leads.get(f.value)
    if lead is None:
        return "unclear"
    return "stated_for" if lead == heading else "stated_against"


def runner_up(heading: str, set_aside: list) -> str | None:
    """The neighbour the answer turns on: one with a known deciding fact if any, else the first set aside."""
    from tariffcompass.classify.facts import DISTINCTIONS

    for h, _, _ in set_aside:
        if frozenset({heading, h}) in DISTINCTIONS:
            return h
    return set_aside[0][0] if set_aside else None


def overlap(product: str, text: str) -> float:
    """How alike the product's words and the ruling's letter are: shared words over the geometric mean of the
    two vocabularies (1.0 when identical)."""
    p, r = stems(product), stems(text)
    return round(len(p & r) / math.sqrt(len(p) * len(r)), 3) if p and r else 0.0


def render_agreement(
    e: dict, heading: str, cited: list[dict], sentences, runner: str | None = None, product: str = ""
) -> str:
    support = {n for s, ns in sentences for n in ns if not is_contrast_sentence(s)}
    sup_rows = [cited[n - 1] for n in support if 0 < n <= len(cited)]
    agreeing = sum(1 for r in sup_rows if r["heading"] == heading)
    p = {c["heading"]: c["p"] for c in e["candidates"]}
    ranked = sorted(p.items(), key=lambda kv: -kv[1])
    second = runner or next((h for h, _ in ranked if h != heading), "none")
    top_p = p.get(heading, 0.0)
    margin = top_p - p.get(second, 0.0) if second != "none" else top_p
    return (
        f"agreeing={agreeing} | cited={len(sup_rows)} | first_stage_p={top_p:.3f} | margin={margin:.3f} | "
        f"precedent={e['votes'].get(heading, 0.0):.3f} | runner_up={second} | "
        f"deciding={deciding_status(product, heading, None if second == 'none' else second)}"
    )


# ── words for the path ──────────────────────────────────────────────────────────────────────────────────
def heading_why(e: dict, heading: str, gri: str) -> str:
    text = e["heading_text"].get(heading, "")
    if gri.startswith("GRI 1"):
        return f"The terms of heading {heading} (“{short(text, 120)}”) describe the product (GRI 1)."
    return f"GRI 1 alone does not decide between the candidate headings; {gri} places it in heading {heading}."


def level_why(level: str, text: str, model_why: str) -> str:
    if level == "suffix" and model_why and model_why.lower() != "none":
        return model_why[:240]
    return f"At this level only lines of the same rank are compared (GRI 6); “{short(text, 100)}” fits."


def siblings(e: dict, heading: str, part: str) -> list[tuple[str, str]]:
    n = len(part)
    seen: dict[str, str] = {}
    for code, _ in e["us_lines"].get(heading, []):
        if code[: n - 2] == part[: n - 2] and code[:n] != part and code[:n] not in seen:
            txt = e["us_text"].get(code[:n]) or e["us_text"].get(code, "")
            if txt:
                seen[code[:n]] = txt
    return list(seen.items())


def best_line_for(e: dict, heading: str, text: str) -> str:
    """The line under a heading a GRI 6 walk reaches for the description (the same walk the subheading step
    takes offline), used for the alternative code and the deciding question's options."""
    from tariffcompass.adapters.lm_sim import _subheading

    rows = e["us_lines"].get(heading, [])
    if not rows:
        return ""
    lines = "\n".join(f"{c} | {t}" for c, t in rows)
    return _subheading({"product": text, "lines": lines}, "").get("code") or rows[0][0]


def chapter_words(ch: str) -> str:
    return chapter_title(ch)
