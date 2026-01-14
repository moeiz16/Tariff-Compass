"""Plain-words labels for every code the UI shows (API_CONTRACT Part 5). The web app never maps codes itself.

Words follow frontend/DESIGN.md: "the classifier", "word matching", "training round", "rulings it hasn't seen".
"""

from __future__ import annotations

SCOPES = {
    "answer": "Answer",
    "rulings": "Rulings",
    "tariff": "Tariff text",
    "products": "My products",
    "review": "Review",
    "watch": "Watch",
    "lab": "Lab",
}

ORIGINS = {
    "CN": "China",
    "VN": "Vietnam",
    "MX": "Mexico",
    "DE": "Germany",
    "IT": "Italy",
    "FR": "France",
    "PT": "Portugal",
    "US": "United States",
    "CA": "Canada",
}

COUNTRIES = {"US": "United States", "CA": "Canada"}
VERDICTS = {"strong": "Strong match", "broker": "Needs a broker"}
FACT_SOURCES = {"stated": "Stated", "read": "Read from the text", "assumed": "Assumed", "unknown": "Not stated"}
RULING_STATUSES = {
    "in_force": "In force",
    "modified": "Modified",
    "revoked": "Revoked",
    "contrast": "Cited for contrast",
}
MATCHES = {"same": "Same", "close": "Close", "differs": "Differs"}
RULING_MATCH = {
    "same_heading": "Same heading",
    "same_subheading": "Same subheading",
    "different_heading": "Different heading",
}
LEVELS = {
    "section": "Section",
    "chapter": "Chapter",
    "heading": "Heading",
    "subheading": "Subheading",
    "tariff_item": "Tariff item",
    "suffix": "Statistical suffix",
}
GRI = {
    "GRI 1": "Classify by the terms of the headings and the section and chapter notes.",
    "GRI 2(a)": "Incomplete or unassembled articles count as the finished article.",
    "GRI 2(b)": "Mixtures and combinations of materials.",
    "GRI 3(a)": "The most specific description wins.",
    "GRI 3(b)": "Sets and composite goods: the part that gives the essential character.",
    "GRI 3(c)": "Otherwise, the heading that comes last in number.",
    "GRI 4": "Goods with no heading: the most similar goods.",
    "GRI 5(a)": "Cases made for the article go with it.",
    "GRI 5(b)": "Packing goes with the goods.",
    "GRI 6": "Subheadings are compared only with subheadings at the same level.",
}
LAYER_KINDS = {
    "base": "Normal duty",
    "remedy": "Trade remedy",
    "emergency": "Emergency duty",
    "fee": "Fee",
    "tax": "Tax",
    "surtax": "Surtax",
    "preference": "Trade agreement",
}
TRANSPORT = {"ocean": "Ocean freight", "air": "Air freight", "truck": "Truck", "rail": "Rail", "courier": "Courier"}
CATEGORIES = {
    "outdoor": "Outdoor gear",
    "electronics": "Small electronics",
    "apparel": "Apparel",
    "kitchen": "Kitchenware",
    "bags": "Bags",
    "other": "Other",
}
STANDINGS = {
    "proposed": "Proposed",
    "in_review": "With the broker",
    "approved": "Approved",
    "needs_recheck": "Needs a re-check",
    "withdrawn": "Withdrawn",
}
VERSION_KINDS = {
    "proposed": "Proposed",
    "question_answered": "Question answered",
    "approved": "Approved",
    "corrected": "Corrected",
    "re_approved": "Re-approved",
    "withdrawn": "Withdrawn",
}
REVIEW_KINDS = {
    "unsure": "Classifier unsure",
    "differs": "Differs from last code",
    "ruling_changed": "Ruling changed",
    "always_review": "Always reviewed",
    "requested": "Sent for review",
}
REVIEW_STATUSES = {
    "waiting": "Waiting",
    "asked": "Question asked",
    "answered": "Question answered",
    "approved": "Approved",
    "corrected": "Corrected",
    "withdrawn": "Withdrawn",
}
REASON_KINDS = {
    "facts_differ": "The product facts differ",
    "ruling_elsewhere": "A ruling points elsewhere",
    "heading_misread": "A heading was read wrongly",
    "other": "Something else",
}
CHANGE_KINDS = {
    "legal_pending": "Pending decision",
    "duty_layer": "Duty change",
    "ruling_modified": "Ruling modified",
    "ruling_revoked": "Ruling revoked",
    "new_rulings": "New rulings",
    "schedule_revision": "Tariff revision",
}
RECHECK = {"unchanged": "Unchanged", "needs_review": "Needs review", "re_approved": "Re-approved"}
ROUND_STATUSES = {
    "training": "Training",
    "waiting_signoff": "Waiting for sign-off",
    "live": "Live",
    "not_made_live": "Not made live",
    "retired": "Retired",
    "failed": "Didn't finish",
}
JOB_STATUSES = {"queued": "Waiting to start", "running": "Working", "succeeded": "Done", "failed": "Didn't finish"}
JOB_KINDS = {
    "classify": "Classification",
    "training_round": "Training round",
    "index_build": "Search index",
    "watch_scan": "Change check",
    "binder_export": "Binder export",
    "ingest": "Data update",
}

ALL: dict[str, dict[str, str]] = {
    "countries": COUNTRIES,
    "verdicts": VERDICTS,
    "factSources": FACT_SOURCES,
    "rulingStatuses": RULING_STATUSES,
    "matches": MATCHES,
    "rulingMatch": RULING_MATCH,
    "levels": LEVELS,
    "gri": GRI,
    "layerKinds": LAYER_KINDS,
    "transport": TRANSPORT,
    "categories": CATEGORIES,
    "standings": STANDINGS,
    "versionKinds": VERSION_KINDS,
    "reviewKinds": REVIEW_KINDS,
    "reviewStatuses": REVIEW_STATUSES,
    "reasonKinds": REASON_KINDS,
    "changeKinds": CHANGE_KINDS,
    "recheck": RECHECK,
    "roundStatuses": ROUND_STATUSES,
    "jobStatuses": JOB_STATUSES,
    "jobKinds": JOB_KINDS,
}
