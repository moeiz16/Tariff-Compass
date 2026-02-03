# ruff: noqa: N803, N806  (X, P: matrices, by the usual convention)
"""The classical first stage (STANDARDS §3b): narrows 97 chapters to a few candidate headings in < 150 ms.

What ships (classify/artifacts/first_stage/, committed, a few MB):
- TF-IDF features: word 1–2 grams and character 3–5 grams (within word boundaries), vocabularies and IDF weights
  stored as JSON so the model loads without pickles;
- a multinomial logistic regression over headings, its weights pruned to the strongest per heading (the pruning
  level is chosen on validation, and the pruned model is the one that is measured), stored as a sparse matrix;
- one temperature fitted on validation (Platt-style scaling of the logits) so the probabilities are calibrated;
- chapter probabilities are the sums of their headings' probabilities, so the two levels never disagree.

Training, the linear SVM and LightGBM challengers, Optuna tuning, calibration, MLflow tracking and the test
measurement live in `classify/train.py` (`manage.py train`).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from django.conf import settings

from tariffcompass.contracts import Candidate, FirstStage, FirstStageResult, ProductQuery

MODEL_DIR = "first_stage"
_CODE = re.compile(r"\b\d{4}\.\d{2}(?:\.\d{2,4}){0,2}\b")


# Canadian and British spellings read as the US spellings the rulings use (a no-op on CBP's own letters).
SPELLING = {
    "aluminium": "aluminum", "anodised": "anodized", "colour": "color", "coloured": "colored", "fibre": "fiber",
    "fibres": "fibers", "grey": "gray", "jewellery": "jewelry", "metre": "meter", "metres": "meters",
    "litre": "liter", "litres": "liters", "moulded": "molded", "tyre": "tire", "tyres": "tires",
    "polyurethane": "polyurethane", "organiser": "organizer", "vapour": "vapor",
}  # fmt: skip
_SPELL = re.compile(r"\b(" + "|".join(SPELLING) + r")\b")


def normalise(text: str) -> str:
    """The same cleaning at training and at prediction: lower case, tariff numbers removed, US spelling."""
    t = " ".join(_CODE.sub(" ", text).lower().split())
    return _SPELL.sub(lambda m: SPELLING[m.group(1)], t)


@dataclass
class Vectoriser:
    """A frozen TF-IDF (sublinear tf, l2) with a fixed vocabulary: sklearn at training, JSON at rest."""

    word_vocab: dict[str, int]
    word_idf: np.ndarray
    char_vocab: dict[str, int]
    char_idf: np.ndarray

    @classmethod
    def from_sklearn(cls, word, char) -> Vectoriser:
        return cls(
            {k: int(v) for k, v in word.vocabulary_.items()},
            word.idf_.astype(np.float32),
            {k: int(v) for k, v in char.vocabulary_.items()},
            char.idf_.astype(np.float32),
        )

    @property
    def n_word(self) -> int:
        return len(self.word_vocab)

    @property
    def n_features(self) -> int:
        return len(self.word_vocab) + len(self.char_vocab)

    def _word_counts(self, text: str) -> dict[int, float]:
        toks = re.findall(r"(?u)\b\w\w+\b", text)
        counts: dict[int, float] = {}
        for gram in (*toks, *(f"{a} {b}" for a, b in pairwise(toks))):
            j = self.word_vocab.get(gram)
            if j is not None:
                counts[j] = counts.get(j, 0.0) + 1.0
        return counts

    def _char_counts(self, text: str) -> dict[int, float]:
        """scikit-learn's char_wb analyser, step for step (3–5 grams inside padded words)."""
        counts: dict[int, float] = {}
        for w in text.split():
            w = f" {w} "
            w_len = len(w)
            for n in (3, 4, 5):
                offset = 0
                grams = [w[0:n]]
                while offset + n < w_len:
                    offset += 1
                    grams.append(w[offset : offset + n])
                for g in grams:
                    j = self.char_vocab.get(g)
                    if j is not None:
                        counts[j] = counts.get(j, 0.0) + 1.0
                if offset == 0:
                    break
        return counts

    @staticmethod
    def _weigh(counts: dict[int, float], idf: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if not counts:
            return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
        idx = np.fromiter(counts.keys(), dtype=np.int64)
        tf = 1.0 + np.log(np.fromiter(counts.values(), dtype=np.float32))
        val = tf * idf[idx]
        norm = float(np.sqrt((val * val).sum())) or 1.0
        return idx, (val / norm).astype(np.float32)

    def transform_one(self, text: str) -> sp.csr_matrix:
        t = normalise(text)
        wi, wv = self._weigh(self._word_counts(t), self.word_idf)
        ci, cv = self._weigh(self._char_counts(t), self.char_idf)
        idx = np.concatenate([wi, ci + self.n_word])
        val = np.concatenate([wv, cv])
        return sp.csr_matrix((val, (np.zeros(len(idx), dtype=np.int64), idx)), shape=(1, self.n_features))

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "word": sorted(self.word_vocab, key=self.word_vocab.__getitem__),
                    "wordIdf": [round(float(x), 5) for x in self.word_idf],
                    "char": sorted(self.char_vocab, key=self.char_vocab.__getitem__),
                    "charIdf": [round(float(x), 5) for x in self.char_idf],
                },
                ensure_ascii=False,
            )
        )

    @classmethod
    def load(cls, path: Path) -> Vectoriser:
        d = json.loads(path.read_text())
        return cls(
            {w: i for i, w in enumerate(d["word"])},
            np.asarray(d["wordIdf"], dtype=np.float32),
            {w: i for i, w in enumerate(d["char"])},
            np.asarray(d["charIdf"], dtype=np.float32),
        )


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class LinearFirstStage:
    """Pruned multinomial logistic regression over headings, temperature-calibrated."""

    def __init__(
        self,
        vec: Vectoriser,
        coef: sp.csr_matrix,  # (n_features, n_headings)
        intercept: np.ndarray,
        headings: list[str],
        temperature: float,
        version: str,
    ) -> None:
        self.vec = vec
        self.coef = coef.tocsr()
        self.intercept = intercept.astype(np.float32)
        self.headings = headings
        self.temperature = float(temperature)
        self.version = version
        self._word_terms = sorted(vec.word_vocab, key=vec.word_vocab.__getitem__)
        chapters = sorted({h[:2] for h in headings})
        self.chapters = chapters
        self._ch_index = np.asarray([chapters.index(h[:2]) for h in headings])

    def logits(self, X: sp.csr_matrix) -> np.ndarray:
        return np.asarray((X @ self.coef).todense()) + self.intercept

    def proba(self, X: sp.csr_matrix) -> np.ndarray:
        return softmax(self.logits(X) / self.temperature)

    def chapter_proba(self, P: np.ndarray) -> np.ndarray:
        out = np.zeros((P.shape[0], len(self.chapters)), dtype=np.float64)
        np.add.at(out.T, self._ch_index, P.T)  # type: ignore[arg-type]
        return out

    def _why(self, x: sp.csr_matrix, col: int, n: int = 5) -> tuple[tuple[str, float], ...]:
        """The words that pushed this heading up most: tf-idf value × weight, word features only."""
        row = x.tocsr()
        idx, val = row.indices, row.data
        mask = idx < self.vec.n_word
        if not mask.any():
            return ()
        idx, val = idx[mask], val[mask]
        w = np.asarray(self.coef[idx, col].todense()).ravel()
        contrib = val * w
        order = np.argsort(-contrib)[:n]
        return tuple((self._word_terms[idx[i]], round(float(contrib[i]), 4)) for i in order if contrib[i] > 0)

    def predict(self, query: ProductQuery, k: int = 5) -> FirstStageResult:
        t0 = time.perf_counter()
        text = " ".join(
            p for p in (query.text, query.spec_sheet_text, " ".join(query.photo_facts), _facts_text(query)) if p
        )
        x = self.vec.transform_one(text)
        p = self.proba(x)[0]
        top = np.argsort(-p)[:k]
        heads = tuple(Candidate(self.headings[i], "heading", round(float(p[i]), 4), self._why(x, int(i))) for i in top)
        cp = self.chapter_proba(p[None, :])[0]
        ctop = np.argsort(-cp)[:k]
        chaps = tuple(
            Candidate(
                self.chapters[i],
                "chapter",
                round(float(cp[i]), 4),
                next((c.why_terms for c in heads if c.code[:2] == self.chapters[i]), ()),
            )
            for i in ctop
        )
        return FirstStageResult(chaps, heads, self.version, (time.perf_counter() - t0) * 1000)

    def predict_many(self, texts: list[str]) -> np.ndarray:
        X = sp.vstack([self.vec.transform_one(t) for t in texts]).tocsr()
        return self.proba(X)

    # ── persistence ─────────────────────────────────────────────────────────────────────────────────────
    def save(self, d: Path, meta: dict) -> None:
        d.mkdir(parents=True, exist_ok=True)
        self.vec.save(d / "vocab.json")
        c = self.coef.tocsc()
        np.savez_compressed(
            d / "weights.npz",
            data=c.data.astype(np.float16),
            indices=c.indices.astype(np.uint16 if c.shape[0] <= 65_535 else np.int32),
            indptr=c.indptr.astype(np.int32),
            shape=np.asarray(c.shape),
            intercept=self.intercept.astype(np.float32),
        )
        (d / "meta.json").write_text(
            json.dumps(
                {**meta, "headings": self.headings, "temperature": self.temperature, "version": self.version},
                indent=1,
            )
            + "\n"
        )

    @classmethod
    def load(cls, d: Path) -> LinearFirstStage:
        meta = json.loads((d / "meta.json").read_text())
        z = np.load(d / "weights.npz")
        coef = sp.csc_matrix(
            (z["data"].astype(np.float32), z["indices"].astype(np.int32), z["indptr"]),
            shape=tuple(int(x) for x in z["shape"]),
        )
        return cls(
            Vectoriser.load(d / "vocab.json"),
            coef.tocsr(),
            z["intercept"],
            list(meta["headings"]),
            float(meta["temperature"]),
            str(meta["version"]),
        )


def _facts_text(query: ProductQuery) -> str:
    return " ".join(f"{k.replace('_', ' ')} {v}" for k, v in query.confirmed_facts)


def model_dir() -> Path:
    return Path(str(settings.TARIFF_COMPASS["ARTIFACT_DIR"])) / MODEL_DIR


def load_first_stage() -> FirstStage:
    d = model_dir()
    if not (d / "meta.json").exists():
        raise NotImplementedError("first stage not trained yet (manage.py train)")
    return LinearFirstStage.load(d)
