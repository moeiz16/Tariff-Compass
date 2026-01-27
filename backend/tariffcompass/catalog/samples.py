"""The public demo's sample products (the landing's "Try a sample"). Anyone can classify these without an
account; any other text gets `404 not_in_demo`. Answers are computed by the real classification core."""

from __future__ import annotations

import re
from typing import Any

SAMPLES: dict[str, dict[str, Any]] = {
    "tumbler": {
        "title": "20 oz vacuum tumbler",
        "made_in": "CN",
        "into": ["US", "CA"],
        "query": "20 oz double-wall stainless steel tumbler, vacuum insulated, with a sliding lid. Holds 591 ml.",
        "shipment": {"value": "12500.00", "currency": "USD", "quantity": 1000, "transport": "ocean"},
    },
    "bike-light": {
        "title": "Rechargeable bicycle headlight",
        "made_in": "CN",
        "into": ["US", "CA"],
        "query": "Rechargeable LED bicycle headlight, 800 lumens, USB-C, mounts on the handlebar with a rubber strap.",
        "shipment": {"value": "8400.00", "currency": "USD", "quantity": 600, "transport": "ocean"},
    },
    "pullover": {
        "title": "Knitted cotton pullover",
        "made_in": "VN",
        "into": ["US", "CA"],
        "query": "Women's crew-neck pullover, knitted, 100% cotton, ribbed cuffs and hem.",
        "shipment": {"value": "9600.00", "currency": "USD", "quantity": 800, "transport": "ocean"},
    },
}

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"a", "an", "the", "with", "and", "of", "on", "in", "for", "to", "it", "oz", "ml"}


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


def match(text: str) -> str | None:
    """The sample this text describes, if it clearly is one (most of the sample's words, or its title)."""
    words = _tokens(text)
    if not words:
        return None
    best, best_share = None, 0.0
    for key, s in SAMPLES.items():
        title = _tokens(s["title"])
        query = _tokens(s["query"])
        share = len(words & query) / len(query)
        if title <= words:
            share = max(share, 0.9)
        if share > best_share:
            best, best_share = key, share
    return best if best_share >= 0.6 else None


def classify_in(key: str) -> dict[str, Any]:
    s = SAMPLES[key]
    return {
        "text": s["query"],
        "made_in": s["made_in"],
        "into": list(s["into"]),
        "product_id": None,
        "evidence_ids": [],
        "confirmed_facts": [],
        "shipment": {
            "value": {"amount": s["shipment"]["value"], "currency": "USD"},
            "quantity": s["shipment"]["quantity"],
            "transport": s["shipment"]["transport"],
        },
    }
