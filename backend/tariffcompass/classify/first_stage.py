"""The classical first stage (STANDARDS §3b): narrows 97 chapters to a few candidate headings in < 150 ms.

Models (trained by `manage.py train`, tracked in MLflow under mlruns/, artefacts in classify/artifacts/):
- baseline: TF-IDF (word 1–2 grams + char 3–5 grams) → logistic regression, and a linear SVM, both calibrated;
- challenger: LightGBM on the TF-IDF features (SVD-reduced) + simple text facts, tuned with Optuna;
- splits by ruling date: the newest rulings are the test set (no leakage across time);
- outputs top-k chapters and headings with calibrated probabilities and the words that drove them.
"""

from __future__ import annotations

from tariffcompass.contracts import FirstStage


def load_first_stage() -> FirstStage:
    raise NotImplementedError("first stage not trained yet")
