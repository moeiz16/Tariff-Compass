"""What the next training round will learn from a broker's correction, and the training example itself.

The lesson is one plain sentence built from the broker's reason, the phrase that decided it and the codes, so a
broker sees exactly what will be fed back before saving. The training example is the dict the optimiser reads
(`RoundRequest.corrections`), in the format agreed with the classification core:

    {id, product_sku, text, made_in, into, proposed_us, proposed_ca, us_code, ca_code, heading, reason_kind,
     reason, lesson, ruling_relied, deciding_fact, decided_by, decided_on}

Codes are bare digits. Corrections only ever join the training side, never the rulings it is tested on.
"""

from __future__ import annotations

import re
from typing import Any

from tariffcompass import codes

LEADS = {
    "facts_differ": "Read the product facts before the words",
    "ruling_elsewhere": "Follow the ruling",
    "heading_misread": "Read the heading text closely",
    "other": "Broker's correction",
}
MAX_LESSON = 300


def _clean(reason: str) -> str:
    text = " ".join(reason.split()).strip().rstrip(".")
    return text[:1].lower() + text[1:] if text[:2] != text[:2].upper() else text


def change_words(proposed: str, final: str) -> str:
    p, f = codes.digits(proposed), codes.digits(final)
    if not f or p == f:
        return ""
    if p[:4] != f[:4]:
        return f"heading {f[:4]}, not {p[:4]}" if p else f"heading {f[:4]}"
    return f"{codes.fmt(f)}, not {codes.fmt(p)}"


def lesson(
    *,
    reason_kind: str,
    reason: str,
    proposed_us: str = "",
    final_us: str = "",
    proposed_ca: str = "",
    final_ca: str = "",
    phrase: str = "",
    ruling_relied: str = "",
) -> str:
    """One sentence, deterministic: same inputs, same lesson."""
    parts: list[str] = []
    if phrase:
        parts.append(f"“{phrase}” on its own doesn't decide it.")
    lead = LEADS.get(reason_kind, LEADS["other"])
    if reason_kind == "ruling_elsewhere" and ruling_relied:
        lead = f"Follow {ruling_relied}"
    change = change_words(proposed_us, final_us) or change_words(proposed_ca, final_ca)
    body = _clean(reason) if reason.strip() else "the broker's code stands"
    sentence = f"{lead}: {body}"
    if change:
        sentence += f" ({change})"
    parts.append(sentence + ".")
    out = " ".join(parts)
    return out if len(out) <= MAX_LESSON else out[: MAX_LESSON - 1].rstrip() + "…"


def redline(proposed: str, yours: str) -> list[dict[str, Any]]:
    p, y = codes.digits(proposed).ljust(10)[:10], codes.digits(yours).ljust(10)[:10]
    return [{"index": i, "proposed": p[i].strip(), "yours": y[i].strip(), "changed": p[i] != y[i]} for i in range(10)]


def deciding_phrase(listing: str, spec: str, phrases: list[dict[str, Any]]) -> str:
    for ph in phrases or []:
        text = listing if ph.get("source", "listing") == "listing" else spec
        start, end = int(ph.get("start", 0)), int(ph.get("end", 0))
        if 0 <= start < end <= len(text):
            return text[start:end]
    return ""


def example_payload(
    *,
    example_id: str,
    sku: str,
    text: str,
    made_in: str,
    into: list[str],
    proposed_us: str,
    proposed_ca: str,
    us_code: str,
    ca_code: str,
    reason_kind: str,
    reason: str,
    lesson_text: str,
    ruling_relied: str | None,
    deciding_fact: dict[str, str] | None,
    decided_by: str,
    decided_on: str,
) -> dict[str, Any]:
    us = codes.digits(us_code)
    return {
        "id": example_id,
        "product_sku": sku,
        "text": text,
        "made_in": made_in,
        "into": list(into),
        "proposed_us": codes.digits(proposed_us) or None,
        "proposed_ca": codes.digits(proposed_ca) or None,
        "us_code": us or None,
        "ca_code": codes.digits(ca_code) or None,
        "heading": (us or codes.digits(ca_code))[:4],
        "reason_kind": reason_kind,
        "reason": reason,
        "lesson": lesson_text,
        "ruling_relied": ruling_relied or None,
        "deciding_fact": deciding_fact,
        "decided_by": decided_by,
        "decided_on": decided_on,
    }


_WORD = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))
