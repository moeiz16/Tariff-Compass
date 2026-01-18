# ADR 0004: Tantivy as the search engine, Huey on SQLite for background jobs

**Status:** accepted

## Context

The product is a search engine for customs law: every answer cites rulings and tariff texts, the Rulings and
Tariff text scopes are searches, and the citation drawers quote passages. It must run in process on a laptop,
offline, without a separate server. Long work (training rounds, index builds, watch scans, binder exports) must not
block requests and must report progress.

## Decision

1. **Tantivy (Rust, Python bindings) with BM25.** Two indexes under `data/index/`: rulings (number, date, heading,
   codes, status, subject, holding and body with an English stemmer) and tariff text (country, code with prefixes,
   level, indent, text, full text, notes). Queries are restricted to the first stage's candidate headings plus
   contrast candidates; results are reranked by heading agreement, recency and status; a revoked ruling is never
   returned as support. Snippets come from Tantivy's snippet generator; marked spans are character offsets.
   Embeddings are an optional reranking signal through a cloud adapter (Jina or Cohere free tiers), with a
   deterministic hashing fake by default. ChromaDB and local embedding models are out of scope.
2. **Huey with SQLite storage.** One worker process (`manage.py run_huey`, one thread) consumes `data/huey.db`.
   Each user-visible task has a `Job` row the web app follows by polling or SSE. Tasks live in each app's
   `tasks.py`. Tests and the single-process demo run tasks inline (`HUEY_IMMEDIATE`).

## Consequences

- No extra server and no Docker; the index is memory-mapped and cheap to rebuild (`make build-index`).
- Tantivy's Python API is lower level than a search server's; the reranker and snippet logic are ours and tested.
- One worker thread means heavy jobs queue rather than compete for memory, which suits an 8 GB laptop.
- SQLite in WAL mode serves the API and the worker concurrently; Postgres is a settings change (`DATABASE_URL`).
