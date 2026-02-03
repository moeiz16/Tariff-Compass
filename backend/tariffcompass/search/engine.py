"""The search engine (Retriever): Tantivy BM25 over rulings and tariff text, then a reranker.

Index layout (data/index/<version>/, rebuilt by `manage.py build_index`):
- `rulings`: id, issued (days since epoch, fast), heading and chapter (raw), status, citable, collection,
  subject, description (the product facts) and body (en_stem, stored), holding (stored).
- `tariff`: country, code, heading (raw), level, text and full_text (en_stem, stored).

Rulings are retrieved by BM25 (description and subject boosted over the body), optionally restricted to a set of
headings and to rulings issued before a cutoff (evaluation uses the test window's start, so a ruling is never
found by its own text). The reranker then combines cross-features, each documented in `rerank()`:
heading agreement with the first stage, recency, the kind of ruling (HQ over NY), status (revoked rulings
sink and are marked, never support) and, optionally, an embedding similarity through the embeddings adapter.

Without `data/` the committed fixtures (search/fixtures) are indexed into a temporary directory on first use.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import structlog
import tantivy
from django.conf import settings

from tariffcompass.contracts import Country, RulingDoc, RulingHit, Span, TariffLine
from tariffcompass.search import corpus as corpus_mod
from tariffcompass.search import tariff as tariff_mod

log = structlog.get_logger("tariffcompass.search")

VERSION = "tantivy-bm25-rerank-1"
_EPOCH = date(1970, 1, 1)
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]{1,}")
STOP = frozenset(
    [
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "for",
        "with",
        "to",
        "in",
        "on",
        "by",
        "at",
        "from",
        "as",
        "is",
        "are",
        "be",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "which",
        "other",
        "than",
        "not",
        "no",
        "any",
        "all",
        "each",
        "into",
        "per",
        "such",
        "use",
        "used",
    ]
)
# Reranker weights (documented, fixed; the eval measures the result rather than tuning these on the test set)
W_BM25, W_HEADING, W_RECENCY, W_HQ, W_REVOKED, W_EMBED = 1.0, 0.9, 0.15, 0.1, -1.5, 0.3
RECENCY_HALF_LIFE_YEARS = 6.0


def days(d: date) -> int:
    return (d - _EPOCH).days


def query_terms(text: str, limit: int = 48) -> list[str]:
    """Words safe for Tantivy's query parser (no syntax characters), deduplicated, in order."""
    seen: list[str] = []
    for w in _WORD.findall(text.lower()):
        w = re.sub(r"[^a-z0-9]", "", w)
        if len(w) > 1 and w not in STOP and w not in seen:
            seen.append(w)
        if len(seen) >= limit:
            break
    return seen


@dataclass(frozen=True)
class RulingMeta:
    id: str
    issued: date | None
    heading: str
    code: str
    subject: str
    holding: str
    status: str
    status_by: str | None
    status_date: date | None
    collection: str
    citable: bool
    labelled: bool
    noted: bool


def _ruling_schema() -> tantivy.Schema:
    sb = tantivy.SchemaBuilder()
    sb.add_text_field("id", stored=True, tokenizer_name="raw")
    sb.add_integer_field("issued", stored=True, indexed=True, fast=True)
    sb.add_text_field("heading", stored=True, tokenizer_name="raw")
    sb.add_text_field("chapter", stored=False, tokenizer_name="raw")
    sb.add_text_field("status", stored=True, tokenizer_name="raw")
    sb.add_text_field("citable", stored=False, tokenizer_name="raw")
    sb.add_text_field("collection", stored=False, tokenizer_name="raw")
    sb.add_text_field("subject", stored=True, tokenizer_name="en_stem")
    sb.add_text_field("description", stored=True, tokenizer_name="en_stem")
    sb.add_text_field("body", stored=True, tokenizer_name="en_stem")
    return sb.build()


def _tariff_schema() -> tantivy.Schema:
    sb = tantivy.SchemaBuilder()
    sb.add_text_field("country", stored=True, tokenizer_name="raw")
    sb.add_text_field("code", stored=True, tokenizer_name="raw")
    sb.add_text_field("heading", stored=False, tokenizer_name="raw")
    sb.add_text_field("level", stored=False, tokenizer_name="raw")
    sb.add_text_field("text", stored=False, tokenizer_name="en_stem")
    sb.add_text_field("full_text", stored=False, tokenizer_name="en_stem")
    return sb.build()


def build_indexes(
    rulings: list[corpus_mod.CleanRuling],
    us: tariff_mod.Schedule,
    ca: tariff_mod.Schedule,
    out_dir: Path,
    heap: int = 64_000_000,
) -> dict:
    """Write both Tantivy indexes and the rulings metadata sidecar; returns counts."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "rulings").mkdir(parents=True)
    (out_dir / "tariff").mkdir(parents=True)
    rs = _ruling_schema()
    idx = tantivy.Index(rs, path=str(out_dir / "rulings"))
    w = idx.writer(heap_size=heap, num_threads=1)
    meta = []
    n = 0
    for r in rulings:
        d = corpus_mod.issued(r)
        w.add_document(
            tantivy.Document(
                id=r.id,
                issued=days(d) if d else 0,
                heading=r.heading or "none",
                chapter=(r.heading or "00")[:2],
                status=r.status,
                citable="1" if r.citable else "0",
                collection=r.collection,
                subject=r.subject,
                description=r.description,
                body=r.text,
            )
        )
        meta.append(
            [
                r.id,
                r.issued,
                r.heading,
                r.code,
                r.subject,
                r.holding,
                r.status,
                r.status_by,
                r.status_date,
                r.collection,
                r.citable,
                r.labelled,
                r.noted,
            ]
        )
        n += 1
    w.commit()
    w.wait_merging_threads()
    ts = _tariff_schema()
    tidx = tantivy.Index(ts, path=str(out_dir / "tariff"))
    tw = tidx.writer(heap_size=heap // 2, num_threads=1)
    nt = 0
    for sched in (us, ca):
        for code in sched.order:
            line = sched.lines[code]
            tw.add_document(
                tantivy.Document(
                    country=line.country,
                    code=line.code,
                    heading=line.code[:4],
                    level=line.level,
                    text=line.text,
                    full_text=line.full_text,
                )
            )
            nt += 1
    tw.commit()
    tw.wait_merging_threads()
    (out_dir / "rulings_meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    info = {"version": VERSION, "rulings": n, "tariffLines": nt}
    (out_dir / "info.json").write_text(json.dumps(info))
    return info


class TantivyRetriever:
    """Retriever over a built index directory; thread-safe for reads."""

    version = VERSION

    def __init__(
        self,
        index_dir: Path,
        us: tariff_mod.Schedule,
        ca: tariff_mod.Schedule,
        *,
        cutoff: date | None = None,
        embeddings: object | None = None,
    ) -> None:
        self.index_dir = index_dir
        self.us, self.ca = us, ca
        self.cutoff = cutoff
        self.embeddings = embeddings
        self._ri = tantivy.Index.open(str(index_dir / "rulings"))
        self._ti = tantivy.Index.open(str(index_dir / "tariff"))
        self._rs = self._ri.schema
        self._ts = self._ti.schema
        self._lock = threading.Lock()
        self.meta: dict[str, RulingMeta] = {}
        for row in json.loads((index_dir / "rulings_meta.json").read_text()):
            rid, iss, head, code, subj, hold, status, by, sdate, coll, citable, labelled, noted = row
            self.meta[rid] = RulingMeta(
                rid,
                date.fromisoformat(iss) if iss else None,
                head,
                code,
                subj,
                hold,
                status,
                by,
                date.fromisoformat(sdate) if sdate else None,
                coll,
                bool(citable),
                bool(labelled),
                bool(noted),
            )
        self.newest = max((m.issued for m in self.meta.values() if m.issued), default=None)

    # ── variants ────────────────────────────────────────────────────────────────────────────────────────
    def with_cutoff(self, cutoff: date | None) -> TantivyRetriever:
        """The same index seen as of a date: rulings issued on or after `cutoff` are invisible."""
        other = object.__new__(TantivyRetriever)
        other.__dict__.update(self.__dict__)
        other.cutoff = cutoff
        return other

    def schedule(self, country: Country) -> tariff_mod.Schedule:
        return self.us if country == "US" else self.ca

    # ── rulings ─────────────────────────────────────────────────────────────────────────────────────────
    def _ruling_query(
        self,
        text: str,
        *,
        headings: list[str] | None,
        before: date | None,
        citable_only: bool,
        status: str | None = None,
        date_from: date | None = None,
    ) -> tantivy.Query:
        must: list[tuple[tantivy.Occur, tantivy.Query]] = []
        terms = query_terms(text)
        if terms:
            q = self._ri.parse_query(
                " ".join(terms),
                ["description", "subject", "body"],
                field_boosts={"description": 2.0, "subject": 2.5, "body": 0.6},
            )
            must.append((tantivy.Occur.Must, q))
        if headings:
            must.append((tantivy.Occur.Must, tantivy.Query.term_set_query(self._rs, "heading", list(headings))))
        cut = min(x for x in (before, self.cutoff) if x) if (before or self.cutoff) else None
        if cut or date_from:
            must.append(
                (
                    tantivy.Occur.Must,
                    tantivy.Query.range_query(
                        self._rs,
                        "issued",
                        tantivy.FieldType.Integer,
                        days(date_from) if date_from else 1,
                        days(cut) - 1 if cut else days(date(2100, 1, 1)),
                    ),
                )
            )
        if citable_only:
            must.append((tantivy.Occur.Must, tantivy.Query.term_query(self._rs, "citable", "1")))
        if status:
            must.append((tantivy.Occur.Must, tantivy.Query.term_query(self._rs, "status", status)))
        if not must:
            return tantivy.Query.all_query()
        if len(must) == 1 and must[0][0] == tantivy.Occur.Must and terms:
            return must[0][1]
        if not terms:
            must.append((tantivy.Occur.Must, tantivy.Query.all_query()))
        return tantivy.Query.boolean_query(must)

    def _hit(self, meta: RulingMeta, bm25: float, rerank: float, passages=()) -> RulingHit:
        return RulingHit(
            ruling_id=meta.id,
            issued=meta.issued or _EPOCH,
            code=meta.code,
            heading=meta.heading,
            subject=meta.subject,
            holding=meta.holding,
            status=meta.status,  # type: ignore[arg-type]
            status_by=meta.status_by,
            status_date=meta.status_date,
            bm25=round(bm25, 4),
            rerank=round(rerank, 4),
            passages=passages,
        )

    def search_raw(
        self,
        text: str,
        *,
        headings: list[str] | None = None,
        k: int = 50,
        before: date | None = None,
        citable_only: bool = True,
    ) -> list[tuple[float, RulingMeta, tantivy.DocAddress]]:
        q = self._ruling_query(text, headings=headings, before=before, citable_only=citable_only)
        with self._lock:
            searcher = self._ri.searcher()
            res = searcher.search(q, k, count=False)
            out = []
            for score, addr in res.hits:
                rid = searcher.doc(addr)["id"][0]
                m = self.meta.get(rid)
                if m is not None:
                    out.append((float(score), m, addr))
        return out

    def rerank(
        self,
        text: str,
        raw: list[tuple[float, RulingMeta, tantivy.DocAddress]],
        heading_probs: dict[str, float] | None = None,
        as_of: date | None = None,
    ) -> list[tuple[float, float, RulingMeta, tantivy.DocAddress]]:
        """Cross-features over the BM25 candidates; returns (rerank, bm25, meta, addr), best first.

        - BM25, normalised by the best candidate's score (W_BM25);
        - heading agreement: the first stage's probability for the ruling's heading (W_HEADING);
        - recency: 0.5 ** (age / 6 years) (W_RECENCY), newer rulings reflect the current reading;
        - kind of ruling: HQ decisions are headquarters' considered view (W_HQ);
        - status: revoked rulings sink (W_REVOKED); they stay visible for contrast, never as support;
        - embedding similarity through the embeddings adapter, when one is configured (W_EMBED).
        """
        if not raw:
            return []
        top = max(s for s, _, _ in raw) or 1.0
        ref = as_of or self.cutoff or self.newest or date.today()
        emb_scores: dict[str, float] = {}
        if self.embeddings is not None:
            from tariffcompass.adapters.embeddings import cosine

            vecs = self.embeddings.embed([text] + [f"{m.subject}. {m.holding}" for _, m, _ in raw])  # type: ignore[attr-defined]
            emb_scores = {m.id: cosine(vecs[0], v) for (_, m, _), v in zip(raw, vecs[1:], strict=True)}
        out = []
        for s, m, addr in raw:
            age = max((ref - m.issued).days / 365.25, 0.0) if m.issued else 10.0
            score = (
                W_BM25 * (s / top)
                + W_HEADING * (heading_probs or {}).get(m.heading, 0.0)
                + W_RECENCY * math.pow(0.5, age / RECENCY_HALF_LIFE_YEARS)
                + W_HQ * (m.collection == "HQ")
                + W_REVOKED * (m.status == "revoked")
                + W_EMBED * emb_scores.get(m.id, 0.0)
            )
            out.append((score, s, m, addr))
        out.sort(key=lambda t: (-t[0], t[2].id))
        return out

    def rulings(
        self,
        text: str,
        *,
        headings: list[str] | None = None,
        k: int = 20,
        before: date | None = None,
        heading_probs: dict[str, float] | None = None,
        snippets: bool = True,
    ) -> list[RulingHit]:
        if not text.strip():
            hits, _ = self.browse("", heading=headings[0] if headings and len(headings) == 1 else None, limit=k)
            if headings:
                hits = [h for h in hits if h.heading in headings]
            return hits[:k]
        raw = self.search_raw(text, headings=headings, k=max(k * 3, 30), before=before)
        ranked = self.rerank(text, raw, heading_probs)[:k]
        if not snippets:
            return [self._hit(m, s, r) for r, s, m, _ in ranked]
        return self._with_passages(text, ranked)

    def _with_passages(self, text: str, ranked) -> list[RulingHit]:
        terms = query_terms(text)
        out = []
        with self._lock:
            searcher = self._ri.searcher()
            q = self._ri.parse_query(" ".join(terms), ["body"]) if terms else None
            gen = tantivy.SnippetGenerator.create(searcher, q, self._rs, "body") if q is not None else None
            if gen is not None:
                gen.set_max_num_chars(240)
            for r, s, m, addr in ranked:
                passages: tuple = ()
                if gen is not None:
                    snip = gen.snippet_from_doc(searcher.doc(addr))
                    frag = snip.fragment()
                    spans = tuple(Span(h.start, h.end) for h in snip.highlighted())
                    if frag:
                        passages = ((frag, spans),)
                out.append(self._hit(m, s, r, passages))
        return out

    def browse(
        self,
        q: str = "",
        *,
        heading: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort: str = "relevance",
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[RulingHit], int]:
        """Paged listing for the Rulings vertical: relevance for a query, newest first otherwise."""
        before = date.fromordinal(date_to.toordinal() + 1) if date_to else None
        query = self._ruling_query(
            q,
            headings=[heading] if heading else None,
            before=before,
            citable_only=False,
            status=status,
            date_from=date_from,
        )
        newest = sort == "newest" or not query_terms(q)
        with self._lock:
            searcher = self._ri.searcher()
            if newest:
                res = searcher.search(query, limit, count=True, order_by_field="issued", offset=offset)
            else:
                res = searcher.search(query, limit, count=True, offset=offset)
            total = getattr(res, "count", 0) or 0
            ranked = []
            for score, addr in res.hits:
                rid = searcher.doc(addr)["id"][0]
                m = self.meta.get(rid)
                if m is not None:
                    ranked.append((0.0 if newest else float(score), 0.0 if newest else float(score), m, addr))
        if query_terms(q):
            return self._with_passages(q, ranked), total
        return [self._hit(m, s, r) for r, s, m, _ in ranked], total

    def ruling(self, ruling_id: str) -> RulingDoc | None:
        rid = " ".join(ruling_id.split()).upper()
        m = self.meta.get(rid)
        if m is None:
            return None
        with self._lock:
            searcher = self._ri.searcher()
            res = searcher.search(tantivy.Query.term_query(self._rs, "id", rid), 1, count=False)
            if not res.hits:
                return None
            doc = searcher.doc(res.hits[0][1])
        body = (doc.to_dict().get("body") or [""])[0]
        codes = tuple(sorted({re.sub(r"\D", "", c) for c in corpus_mod.CODE_ANY.findall(body)}))
        related = tuple(sorted({f"{a} {b}" for a, b in corpus_mod.RULING_REF.findall(body)} - {rid}))
        if m.status_by and m.status_by not in related:
            related = (m.status_by, *related)
        num = rid.split()[-1].lstrip("?")
        return RulingDoc(
            ruling_id=rid,
            issued=m.issued or _EPOCH,
            category="Classification" if m.holding or m.noted else "Other",
            code=m.code,
            codes=codes or ((m.code,) if m.code else ()),
            subject=m.subject,
            text=body,
            status=m.status,  # type: ignore[arg-type]
            status_by=m.status_by,
            status_date=m.status_date,
            related=related,
            source_url=f"https://rulings.cbp.gov/ruling/{num}" if "?" not in rid else "",
        )

    # ── tariff text ─────────────────────────────────────────────────────────────────────────────────────
    def tariff(
        self,
        text: str,
        *,
        country: Country,
        under: str | None = None,
        k: int = 20,
        levels: tuple[str, ...] | None = None,
    ) -> list[TariffLine]:
        sched = self.schedule(country)
        digits = re.sub(r"\D", "", text)
        if digits and len(digits) >= 4 and not query_terms(text):
            line = sched.line(digits)
            return [line] if line else sched.kids(digits)[:k]
        terms = query_terms(text)
        must: list[tuple[tantivy.Occur, tantivy.Query]] = [
            (tantivy.Occur.Must, tantivy.Query.term_query(self._ts, "country", country))
        ]
        if terms:
            must.append(
                (
                    tantivy.Occur.Must,
                    self._ti.parse_query(" ".join(terms), ["text", "full_text"], field_boosts={"text": 2.0}),
                )
            )
        if under:
            u = re.sub(r"\D", "", under)
            must.append((tantivy.Occur.Must, tantivy.Query.term_query(self._ts, "heading", u[:4])))
        if levels:
            must.append((tantivy.Occur.Must, tantivy.Query.term_set_query(self._ts, "level", list(levels))))
        q = tantivy.Query.boolean_query(must)
        out: list[TariffLine] = []
        with self._lock:
            searcher = self._ti.searcher()
            for _, addr in searcher.search(
                q, k * 3 if under and len(re.sub(r"\D", "", under)) > 4 else k, count=False
            ).hits:
                code = searcher.doc(addr)["code"][0]
                line = sched.lines.get(code)
                if line is None:
                    continue
                if under and not code.startswith(re.sub(r"\D", "", under)):
                    continue
                out.append(line)
        return out[:k]

    def tariff_line(self, country: Country, code: str) -> TariffLine | None:
        return self.schedule(country).line(code)

    def tariff_children(self, country: Country, code: str) -> list[TariffLine]:
        return self.schedule(country).kids(code)


# ── construction ────────────────────────────────────────────────────────────────────────────────────────
def _cfg() -> dict:
    return settings.TARIFF_COMPASS


def load_schedules(sample: bool = False) -> tuple[tariff_mod.Schedule, tariff_mod.Schedule]:
    cfg = _cfg()
    us_path, ca_path = Path(str(cfg["HTS_PATH"])), Path(str(cfg["CA_TARIFF_PATH"]))
    fixtures = Path(str(cfg["TARIFF_SAMPLE_DIR"]))
    if sample or not us_path.exists():
        us_path = fixtures / "hts_sample.jsonl"
    if sample or not ca_path.exists():
        ca_path = fixtures / "ca_tariff_sample.jsonl"
    return tariff_mod.load_us(tariff_mod.read_jsonl(us_path)), tariff_mod.load_ca(tariff_mod.read_jsonl(ca_path))


def clean_corpus_path() -> Path:
    return Path(_cfg()["RULINGS_PATH"]).with_name("rulings_clean.jsonl")


def load_corpus(sample: bool = False) -> tuple[list[corpus_mod.CleanRuling], corpus_mod.CleanReport | None, bool]:
    """The cleaned corpus: data/rulings/rulings_clean.jsonl when built, else cleaned on the fly from the
    download or the committed sample. Returns (rulings, report or None when read from disk, is_sample)."""
    cfg = _cfg()
    raw = Path(str(cfg["RULINGS_PATH"]))
    if not sample and clean_corpus_path().exists():
        return corpus_mod.load(clean_corpus_path()), None, False
    if not sample and raw.exists():
        rulings, rep = corpus_mod.clean(corpus_mod.iter_jsonl(raw))
        return rulings, rep, False
    rulings, rep = corpus_mod.clean(corpus_mod.iter_jsonl(Path(str(cfg["RULINGS_SAMPLE"]))))
    return rulings, rep, True


def index_dir(sample: bool = False) -> Path:
    base = Path(_cfg()["INDEX_DIR"])
    return base / ("sample" if sample else "full")


_build_lock = threading.Lock()
_tmp_dirs: list[tempfile.TemporaryDirectory] = []


def build_retriever(sample: bool | None = None) -> TantivyRetriever:
    """The retriever over the full index when built (manage.py build_index), else over the committed sample,
    indexed on first use into data/index/sample (or a temporary directory when data/ isn't writable)."""
    full = index_dir(False)
    if sample is not True and (full / "info.json").exists():
        us, ca = load_schedules()
        return TantivyRetriever(full, us, ca, embeddings=_embeddings())
    with _build_lock:
        target = index_dir(True)
        if not (target / "info.json").exists() or _stale(target):
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                rulings, _, _ = load_corpus(sample=True)
                us, ca = load_schedules(sample=True)
                build_indexes(rulings, us, ca, target, heap=32_000_000)
            except OSError:
                tmp = tempfile.TemporaryDirectory(prefix="tc-index-")
                _tmp_dirs.append(tmp)
                target = Path(tmp.name) / "sample"
                rulings, _, _ = load_corpus(sample=True)
                us, ca = load_schedules(sample=True)
                build_indexes(rulings, us, ca, target, heap=32_000_000)
        us, ca = load_schedules(sample=True)
        return TantivyRetriever(target, us, ca, embeddings=_embeddings())


def _stale(target: Path) -> bool:
    sample = Path(_cfg()["RULINGS_SAMPLE"])
    try:
        info = json.loads((target / "info.json").read_text())
        return info.get("version") != VERSION or sample.stat().st_mtime > (target / "info.json").stat().st_mtime
    except (OSError, ValueError):
        return True


def _embeddings():
    if _cfg().get("EMBEDDINGS", "fake") == "fake":
        from tariffcompass.adapters.embeddings import FakeEmbeddings

        return FakeEmbeddings()
    return None
