"""The search engine (Retriever): Tantivy BM25 over rulings and tariff text, then a reranker.

Index layout (data/index/, rebuilt by `manage.py build_index`):
- `rulings`: ruling_id (raw), issued (date, fast), heading (raw, fast), code (raw), status (raw), subject,
  holding and body (en_stem, stored), plus a positions-enabled body for passage snippets.
- `tariff`: country (raw), code (raw, prefix-searchable via a `code_prefixes` multi-value field), level,
  indent, text and full_text (en_stem, stored), notes.
Reranking: BM25 × heading agreement with the first stage × recency × status (revoked rulings never cited as
support). Offline the committed sample fixtures (search/fixtures) are indexed when data/ is empty.
"""

from __future__ import annotations

from tariffcompass.contracts import Retriever


def build_retriever() -> Retriever:
    raise NotImplementedError("search engine not built yet")
