"""Embeddings only through a cloud adapter (Jina or Cohere free tiers); a deterministic fake by default.

The search engine is BM25 first (Tantivy); embeddings are an optional reranking signal. The fake is a
feature-hashing bag of words (256 dims, L2-normalised): deterministic, offline and honest about being lexical.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

_TOKEN = re.compile(r"[a-z0-9]+")


@runtime_checkable
class EmbeddingAdapter(Protocol):
    dims: int
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbeddings:
    name = "offline hashing embeddings"

    def __init__(self, dims: int = 256) -> None:
        self.dims = dims

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dims
        for tok in _TOKEN.findall(text.lower()):
            h = int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "big")
            vec[h % self.dims] += 1.0 if (h >> 63) & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))
