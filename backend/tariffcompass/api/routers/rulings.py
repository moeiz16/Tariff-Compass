"""Rulings search, ruling detail and the two-pane compare (API_CONTRACT §1.6), over the search engine.

Only real CBP rulings from the corpus appear; each links to CROSS. Ruling keys are the path form of the
number (`ny-n321134`).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from django.http import HttpRequest

from tariffcompass import codes, services
from tariffcompass.api import labels
from tariffcompass.api.routers.common import page_params
from tariffcompass.api.schemas.common import Page
from tariffcompass.api.schemas.rulings import CompareOut, RulingDetail, RulingSummary
from tariffcompass.catalog.models import BinderVersion, Evidence
from tariffcompass.catalog.rulings import status_out
from tariffcompass.contracts import RulingDoc, RulingHit
from tariffcompass.core.errors import Problem
from tariffcompass.core.wire import WireRouter
from tariffcompass.platform.context import ctx_of, requires

router = WireRouter()

RULE_QUOTE = (
    "19 CFR 177.9(b)(2): Each ruling letter setting forth the proper classification of an article under the "
    "provisions of the Harmonized Tariff Schedule of the United States will be applied only with respect to "
    "transactions involving articles identical to the sample submitted with the ruling request or to articles "
    "whose description is identical to the description set forth in the ruling letter."
)
_HOLDING = re.compile(r"[^.]*\b(?:applicable|proper)\s+(?:sub)?heading[^.]*\.(?:\d{2,4}[^.]*\.)*", re.I)
RELATION_LABELS = {
    "modifies": "Modifies",
    "modified_by": "Modified by",
    "revokes": "Revokes",
    "revoked_by": "Revoked by",
    "cites": "Cites",
    "cited_by": "Cited by",
}


def key_to_id(key: str) -> str:
    raw = key.strip()
    if " " in raw:
        return raw.upper()
    coll, _, num = raw.partition("-")
    return f"{coll.upper()} {num.upper()}"


def id_to_key(ruling_id: str) -> str:
    return ruling_id.lower().replace(" ", "-")


def holding_of(text: str) -> str:
    m = _HOLDING.search(text or "")
    return " ".join(m.group(0).split()) if m else ""


def _snippet(hit: RulingHit) -> tuple[str, list[dict[str, int]]]:
    if hit.passages:
        text, spans = hit.passages[0]
        return text, [{"start": s.start, "end": s.end} for s in spans]
    return hit.holding[:280], []


def summary_from_hit(hit: RulingHit) -> dict[str, Any]:
    snippet, marks = _snippet(hit)
    d = codes.digits(hit.code)
    return {
        "id": hit.ruling_id,
        "key": id_to_key(hit.ruling_id),
        "issued": hit.issued,
        "subject": hit.subject,
        "code": codes.fmt(d),
        "code_as_quoted": codes.fmt_as_quoted_by_cbp(d),
        "heading": hit.heading or d[:4],
        "status": status_out(hit.status, hit.status_by, hit.status_date),
        "holding": hit.holding,
        "snippet": snippet,
        "snippet_marks": marks,
    }


def _paragraphs(text: str) -> list[dict[str, int]]:
    out, pos = [], 0
    for block in re.split(r"\n\s*\n", text):
        start = text.find(block, pos)
        if block.strip():
            out.append({"start": start, "end": start + len(block)})
        pos = start + len(block)
    return out


def detail_from_doc(doc: RulingDoc, org) -> dict[str, Any]:
    d = codes.digits(doc.code)
    holding = holding_of(doc.text)
    related = []
    for rid in doc.related:
        if rid == doc.status_by:
            rel = "revoked_by" if doc.status == "revoked" else "modified_by"
        else:
            other = services.retriever().ruling(rid)
            if other is not None and other.status_by == doc.ruling_id:
                rel = "revokes" if other.status == "revoked" else "modifies"
            else:
                rel = "cites"
        related.append({"id": rid, "key": id_to_key(rid), "relation": rel, "relation_label": RELATION_LABELS[rel]})
    if doc.status_by and doc.status_by not in doc.related:
        rel = "revoked_by" if doc.status == "revoked" else "modified_by"
        related.append(
            {
                "id": doc.status_by,
                "key": id_to_key(doc.status_by),
                "relation": rel,
                "relation_label": RELATION_LABELS[rel],
            }
        )
    also = []
    if org is not None:
        seen = set()
        for v in BinderVersion.objects.filter(org=org, product__hidden_at__isnull=True).select_related("product"):
            if doc.ruling_id in (v.rulings_relied or []) and v.product_id not in seen:
                seen.add(v.product_id)
                also.append({"product_id": str(v.product_id), "sku": v.product.sku, "title": v.product.title})
    return {
        "id": doc.ruling_id,
        "key": id_to_key(doc.ruling_id),
        "issued": doc.issued,
        "subject": doc.subject,
        "code": codes.fmt(d),
        "code_as_quoted": codes.fmt_as_quoted_by_cbp(d),
        "heading": d[:4],
        "status": status_out(doc.status, doc.status_by, doc.status_date),
        "holding": holding,
        "snippet": holding or doc.text[:280],
        "snippet_marks": [],
        "category": doc.category,
        "codes": [codes.fmt(c) for c in doc.codes],
        "text": doc.text,
        "paragraphs": _paragraphs(doc.text),
        "related": related,
        "also_cited_in": also[:20],
        "source_url": doc.source_url or f"https://rulings.cbp.gov/ruling/{doc.ruling_id.split()[-1]}",
    }


def _date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": field, "message": "Use a date like 2025-07-01."}],
        ) from exc


@router.get("", response=Page[RulingSummary])
@requires("rulings:read")
def search(
    request: HttpRequest,
    q: str = "",
    heading: str | None = None,
    status: str | None = None,
    to: str | None = None,
    sort: str = "relevance",
    page: int = 1,
    pageSize: int = 25,
) -> dict:
    page, size = page_params(page, pageSize)
    date_from, date_to = _date(request.GET.get("from"), "from"), _date(to, "to")
    head = codes.digits(heading or "")[:4] or None
    retr = services.retriever()
    browse = getattr(retr, "browse", None)
    if callable(browse):
        hits, total = browse(
            q,
            heading=head,
            status=status,
            date_from=date_from,
            date_to=date_to,
            sort="newest" if sort == "newest" else "relevance",
            offset=(page - 1) * size,
            limit=size,
        )
    else:
        found = retr.rulings(q, headings=[head] if head else None, k=500)
        found = [
            h
            for h in found
            if (not status or h.status == status)
            and (not head or h.heading == head)
            and (not date_from or h.issued >= date_from)
            and (not date_to or h.issued <= date_to)
        ]
        if sort == "newest":
            found.sort(key=lambda h: h.issued, reverse=True)
        total = len(found)
        hits = found[(page - 1) * size : page * size]
    return {
        "items": [summary_from_hit(h) for h in hits],
        "page": page,
        "page_size": size,
        "total": total,
        "total_pages": max(1, -(-total // size)),
    }


@router.get("/{key}", response=RulingDetail)
@requires("rulings:read")
def detail(request: HttpRequest, key: str) -> dict:
    ctx = ctx_of(request)
    doc = services.retriever().ruling(key_to_id(key))
    if doc is None:
        raise Problem(404, "not_found", "We couldn't find that ruling.")
    return detail_from_doc(doc, ctx.org)


def _find_spans(text: str, needles: list[str]) -> list[dict[str, int]]:
    out: list[dict[str, int]] = []
    low = text.lower()
    for n in needles:
        n = n.strip().lower()
        if len(n) < 3:
            continue
        i = low.find(n)
        if i >= 0:
            out.append({"start": i, "end": i + len(n)})
    out.sort(key=lambda s: s["start"])
    merged: list[dict[str, int]] = []
    for s in out:
        if merged and s["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], s["end"])
        else:
            merged.append(s)
    return merged


@router.get("/{key}/compare", response=CompareOut)
@requires("rulings:read")
def compare(request: HttpRequest, key: str, answerId: str, n: int | None = None) -> dict:
    from tariffcompass.api.routers.classify import get_answer

    ctx = ctx_of(request)
    a = get_answer(ctx, answerId)
    rid = key_to_id(key)
    doc = services.retriever().ruling(rid)
    if doc is None:
        raise Problem(404, "not_found", "We couldn't find that ruling.")
    cited = next((r for r in a.payload.get("rulings", []) if r["id"] == rid and (n is None or r["n"] == n)), None)
    alignment = cited["fact_compare"] if cited else []
    yours = [f["yours"] for f in alignment]
    theirs = [f["theirs"] for f in alignment]
    panes = [{"kind": "listing", "label": "Listing", "text": a.query_text, "marked": _find_spans(a.query_text, yours)}]
    ev_ids = list(a.payload["query"].get("evidence_ids", []))
    evidence = list(Evidence.objects.filter(org=ctx.org, pk__in=ev_ids)) if ev_ids else []
    if a.product is not None:
        evidence += [e for e in a.product.evidence.all() if e not in evidence]
    for e in evidence:
        text = e.extracted_text or " ".join(e.photo_facts or [])
        if text:
            panes.append(
                {"kind": e.kind, "label": e.label or e.file_name, "text": text, "marked": _find_spans(text, yours)}
            )
    ruling = detail_from_doc(doc, ctx.org)
    marked = _find_spans(doc.text, [*theirs, ruling["holding"]])
    return {
        "ruling": ruling,
        "cited_as": cited["n"] if cited else None,
        "product_title": a.product.title if a.product else a.query_text[:80],
        "made_in_label": labels.ORIGINS.get(a.made_in, a.made_in),
        "rule_quote": RULE_QUOTE,
        "alignment": alignment,
        "evidence": panes,
        "ruling_marked": marked,
    }
