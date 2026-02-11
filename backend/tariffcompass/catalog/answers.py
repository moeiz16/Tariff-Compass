"""Classification answers: run the core through `services`, map its value objects to the wire, store them.

`classify()` runs first stage → program (which reads the search engine) → duty engine, then maps
`ProgramAnswer` + `LandedCost` to `AnswerOut` (API_CONTRACT §1.5) and stores the answer immutably with the
versions that produced it. Mapping lives here so the routers, the seed and the public samples share it.
"""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal
from typing import Any

import structlog

from tariffcompass import codes, services
from tariffcompass.api import labels
from tariffcompass.contracts import (
    Citation,
    CodeChoice,
    LandedCost,
    LandedCostQuery,
    ProductQuery,
    ProgramAnswer,
)
from tariffcompass.core.metrics import CLASSIFY_STAGE

log = structlog.get_logger("tariffcompass.answers")

SNAPSHOT_DATE = date(2026, 2, 19)
SNAPSHOT_LABEL = "HTSUS 2026 Revision 3 · Customs Tariff T2026"
CENT = Decimal("0.01")


def money(amount: Decimal, currency: str) -> dict[str, str]:
    return {"amount": str(Decimal(amount).quantize(CENT)), "currency": currency}


def code_out(choice: CodeChoice | None, *, leaning: bool = False) -> dict[str, Any] | None:
    if choice is None:
        return None
    d = codes.digits(choice.code)
    return {
        "country": choice.country,
        "country_label": labels.COUNTRIES[choice.country],
        "code": codes.fmt(d),
        "digits": d,
        "heading_digits": d[:4],
        "text": choice.text,
        "heading_text": choice.heading_text,
        "leaning": leaning,
    }


def code_out_from_digits(country: str, digits: str, *, leaning: bool = False) -> dict[str, Any] | None:
    """A code card for a stored code, with texts from the tariff (empty when the line isn't known)."""
    if not digits:
        return None
    retr = services.retriever()
    line = retr.tariff_line(country, digits)  # type: ignore[arg-type]
    heading = retr.tariff_line(country, digits[:4])  # type: ignore[arg-type]
    return {
        "country": country,
        "country_label": labels.COUNTRIES.get(country, country),
        "code": codes.fmt(digits),
        "digits": digits,
        "heading_digits": digits[:4],
        "text": line.full_text if line else "",
        "heading_text": heading.text if heading else (line.text if line else ""),
        "leaning": leaning,
    }


def _path_code(level: str, code: str) -> str:
    if level == "section":
        return code
    return codes.fmt(code) if len(codes.digits(code)) > 4 else codes.digits(code)


def _status(c: Citation) -> dict[str, Any]:
    from tariffcompass.catalog.rulings import status_out

    h = c.ruling
    return status_out(h.status, h.status_by, h.status_date)


def _marked(c: Citation) -> list[dict[str, int]]:
    h = c.ruling
    for text, spans in h.passages:
        if text == h.holding:
            return [{"start": s.start, "end": s.end} for s in spans]
    out = []
    needle = h.heading
    start = h.holding.find(needle) if needle else -1
    if start >= 0:
        end = start
        while end < len(h.holding) and (h.holding[end].isdigit() or h.holding[end] == "."):
            end += 1
        out.append({"start": start, "end": end})
    return out


def _bar_kind(c: Citation) -> str:
    if c.ruling.status == "contrast":
        return "contrast"
    return "same" if "different_heading" not in c.match else "differs"


def cited_ruling(c: Citation) -> dict[str, Any]:
    h = c.ruling
    return {
        "n": c.n,
        "id": h.ruling_id,
        "key": h.ruling_id.lower().replace(" ", "-"),
        "date": h.issued,
        "subject": h.subject,
        "status": _status(c),
        "holding": h.holding,
        "marked_spans": _marked(c),
        "match": list(c.match),
        "match_labels": [labels.RULING_MATCH.get(m, m) for m in c.match],
        "fact_compare": [
            {
                "fact": f.fact,
                "yours": f.yours,
                "theirs": f.theirs,
                "match": f.match,
                "match_label": labels.MATCHES.get(f.match, f.match),
            }
            for f in c.fact_compare
        ],
        "supports": list(c.supports),
        "url": f"https://rulings.cbp.gov/ruling/{h.ruling_id.split()[-1]}",
    }


def landed_out(lc: LandedCost) -> dict[str, Any]:
    q = lc.query
    cur = q.currency
    value = q.customs_value
    return {
        "country": q.country,
        "country_label": labels.COUNTRIES[q.country],
        "code": codes.fmt(q.code),
        "made_in": q.made_in,
        "made_in_label": labels.ORIGINS.get(q.made_in, q.made_in),
        "value": money(value, cur),
        "quantity": q.quantity,
        "transport": q.transport,
        "transport_label": labels.TRANSPORT.get(q.transport, q.transport),
        "lines": [
            {
                "letter": ln.letter,
                "layer_id": ln.layer_id,
                "kind": ln.kind,
                "kind_label": labels.LAYER_KINDS.get(ln.kind, ln.kind),
                "name": ln.name,
                "rate": ln.rate,
                "amount": money(ln.amount, cur),
                "plain": ln.plain,
                "source": ln.source,
                "source_url": ln.source_url,
                "chapter99": ln.chapter99,
                "effective_from": ln.effective_from,
                "effective_to": ln.effective_to,
                "legal_status": ln.legal_status,
                "legal_status_open": legal_open(ln.legal_status),
            }
            for ln in lc.lines
        ],
        "not_applied": [{"name": n.name, "why": n.why} for n in lc.not_applied],
        "charges_total": money(lc.charges_total, cur),
        "landed_total": money(lc.landed_total, cur),
        "per_unit": money(lc.per_unit, cur),
        "effective_rate": f"+{(Decimal(lc.effective_rate) * 100).quantize(Decimal('0.1'))}%",
        "questions": [{"key": oq.key, "question": oq.question, "answer": oq.answer} for oq in lc.questions],
        "what_could_change": [
            {"label": label, "landed_total": money(total, cur), "charges_total": money(total - value, cur)}
            for label, total in lc.what_could_change
        ],
        "tariffs_as_of": lc.tariffs_as_of,
        "snapshot_label": lc.snapshot or SNAPSHOT_LABEL,
    }


DEPTH_LABELS = {"heading": "Heading", "full_code": "Full code"}


def verdict_depths(ans: Any) -> list[dict[str, str]]:
    """`ProgramAnswer.verdict_by_depth` on the wire (empty when the core doesn't say)."""
    out = []
    for level, word in getattr(ans, "verdict_by_depth", ()) or ():
        if level in DEPTH_LABELS and word in labels.VERDICTS:
            out.append(
                {"level": level, "level_label": DEPTH_LABELS[level], "word": word, "word_label": labels.VERDICTS[word]}
            )
    return out


def legal_open(status: str | None) -> bool:
    return bool(status) and "pending" in str(status).lower()


def landed_cost(
    country: str,
    code: str,
    made_in: str,
    shipment: dict[str, Any],
    usmca: dict[str, bool] | None = None,
    as_of: date | None = None,
) -> LandedCost:
    value = Decimal(str(shipment.get("value_cad" if country == "CA" else "value") or shipment.get("value") or 0))
    currency = "CAD" if country == "CA" and shipment.get("value_cad") else shipment.get("currency", "USD")
    return services.duties().landed_cost(
        LandedCostQuery(
            country=country,  # type: ignore[arg-type]
            code=codes.digits(code),
            made_in=made_in,
            customs_value=value,
            currency=currency,
            quantity=int(shipment.get("quantity") or 1),
            transport=shipment.get("transport") or "ocean",
            usmca_answers=tuple(sorted((usmca or {}).items())),
            as_of=as_of or SNAPSHOT_DATE,
        )
    )


def broker_short_name(org) -> str:
    from tariffcompass.platform.models import Engagement

    e = Engagement.objects.filter(importer_org=org, active=True).select_related("broker_org").first() if org else None
    return e.broker_org.name.split()[0] if e else "your broker"


def payload(
    q: dict[str, Any],
    ans: ProgramAnswer,
    landed: list[LandedCost],
    *,
    timings: dict[str, float],
    classifier_round: int | None,
    first_stage_version: str,
    search_version: str,
    broker: str,
) -> dict[str, Any]:
    leaning = ans.verdict == "broker"
    deciding = None
    if ans.deciding_question is not None:
        dq = ans.deciding_question
        deciding = {
            "fact_key": dq.fact_key,
            "question": dq.question,
            "options": [{"key": k, "label": lbl, "leads_to": codes.fmt(c) if c else None} for k, lbl, c in dq.options],
            "not_sure_label": f"Not sure: send to {broker}",
        }
    alternative = None
    if ans.alternative is not None:
        alt = ans.alternative
        condition = ""
        if ans.deciding_question is not None:
            for _k, lbl, c in ans.deciding_question.options:
                if c and codes.digits(c) == codes.digits(alt.code):
                    condition = f"if {lbl[:1].lower()}{lbl[1:]}"
        alternative = {
            "code": code_out(alt, leaning=True),
            "condition": condition or "if the deciding fact differs",
            "duty_at_stake": ans.duty_at_stake,
        }
    cites = list(ans.citations)
    return {
        "query": q,
        "made_in_label": labels.ORIGINS.get(q["made_in"], q["made_in"]),
        "tariffs_as_of": SNAPSHOT_DATE,
        "snapshot_label": SNAPSHOT_LABEL,
        "us": code_out(ans.us, leaning=leaning) if "US" in q["into"] else None,
        "ca": code_out(ans.ca, leaning=leaning) if "CA" in q["into"] else None,
        "verdict": {
            "word": ans.verdict,
            "word_label": labels.VERDICTS[ans.verdict],
            "sentence": ans.verdict_sentence,
            "agreeing": ans.agreeing_rulings,
            "cited": ans.cited_rulings,
            "in_force": sum(1 for c in cites if c.ruling.status == "in_force"),
            "agreement_bar": [{"n": c.n, "kind": _bar_kind(c)} for c in cites],
            "by_depth": verdict_depths(ans),
        },
        "alternative": alternative,
        "deciding_question": deciding,
        "holding_sentence": ans.holding_sentence,
        "issue": ans.issue,
        "facts": [
            {
                "key": f.key,
                "label": f.label,
                "value": f.value,
                "source": f.source,
                "source_label": labels.FACT_SOURCES.get(f.source, f.source),
                "source_note": f.source_note,
                "decides": f.decides,
            }
            for f in ans.facts
        ],
        "reason": [
            {"text": c.text, "cites": list(c.cites), "marked": [{"start": s.start, "end": s.end} for s in c.marked]}
            for c in ans.reason
        ],
        "path": [
            {
                "level": s.level,
                "level_label": labels.LEVELS.get(s.level, s.level),
                "code": _path_code(s.level, s.code),
                "text": s.text,
                "gri": s.gri,
                "gri_label": labels.GRI.get(s.gri, ""),
                "why": s.why,
                "cites": list(s.cites),
                "not_neighbours": [
                    {"code": _path_code("heading", n.code), "text": n.text, "reason": n.reason, "cite": n.cite}
                    for n in s.not_neighbours
                ],
                "country_note": s.country_note,
            }
            for s in ans.path
        ],
        "rulings": [cited_ruling(c) for c in cites],
        "tariff_authorities": [{"ref": t.ref, "quote": t.quote} for t in ans.tariff_authorities],
        "landed": [landed_out(lc) for lc in landed],
        "provenance": {
            "classifier_round": classifier_round,
            "first_stage_version": first_stage_version,
            "search_version": search_version,
            "lm_label": ans.lm_label,
        },
        "timings": timings,
    }


def run_core(
    q: dict[str, Any],
    *,
    spec_text: str = "",
    photo_facts: tuple[str, ...] = (),
    product_id: str | None = None,
    shipment: dict[str, Any] | None = None,
    classifier_round: int | None = None,
    broker: str = "your broker",
) -> tuple[ProgramAnswer, dict[str, Any]]:
    """Run the classification core on a ClassifyIn-shaped dict; returns the program answer and the payload."""
    query = ProductQuery(
        text=q["text"],
        made_in=q["made_in"],
        into=tuple(q["into"]),
        spec_sheet_text=spec_text,
        photo_facts=photo_facts,
        confirmed_facts=tuple((f["key"], f["answer"]) for f in q.get("confirmed_facts", [])),
        product_id=product_id,
    )
    t0 = time.perf_counter()
    fs = services.first_stage().predict(query, k=5)
    t1 = time.perf_counter()
    retr = services.retriever()
    ans = services.program().classify(query, fs, retr)
    t2 = time.perf_counter()
    landed: list[LandedCost] = []
    if shipment and Decimal(str(shipment.get("value") or 0)) > 0:
        for country, choice in (("US", ans.us), ("CA", ans.ca)):
            if country in q["into"] and choice is not None:
                try:
                    landed.append(landed_cost(country, choice.code, q["made_in"], shipment))
                except Exception as exc:  # an answer never fails over a duty line the engine can't price
                    log.warning("landed_cost_skipped", country=country, code=choice.code, reason=str(exc))
    t3 = time.perf_counter()
    lm = ans.lm_label or "offline simulator"
    CLASSIFY_STAGE.labels("first_stage", lm).observe(t1 - t0)
    CLASSIFY_STAGE.labels("program", lm).observe(t2 - t1)
    CLASSIFY_STAGE.labels("duties", lm).observe(t3 - t2)
    tm = dict(ans.timings_ms or {})
    timings = {
        "firstStageMs": round(fs.elapsed_ms or (t1 - t0) * 1000, 2),
        "searchMs": round(float(tm.get("search", tm.get("retrieve", 0.0))), 2),
        "programMs": round((t2 - t1) * 1000, 2),
        "dutiesMs": round((t3 - t2) * 1000, 2),
        "totalMs": round((t3 - t0) * 1000, 2),
    }
    return ans, payload(
        q,
        ans,
        landed,
        timings=timings,
        classifier_round=classifier_round,
        first_stage_version=fs.model_version,
        search_version=getattr(retr, "version", ""),
        broker=broker,
    )


def jsonable(data: Any) -> Any:
    """Dates and decimals as JSON strings (stored payloads; the wire schemas parse them back)."""
    import json

    from django.core.serializers.json import DjangoJSONEncoder

    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))
