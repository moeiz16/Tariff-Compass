"""Training rounds: GEPA optimises the program's instructions on rulings + broker corrections (ADR 0003).

Reproducible by construction: a round records its seed, the metric-call budget, the LMs used, and a SHA-256 of
the train/val/test ruling ids and texts. Test rulings are the newest by date and never seen in training. The
optimised program is saved as JSON (classify/artifacts/program_round_<n>.json) and the RoundReport goes to the Lab.
"""

from __future__ import annotations

from tariffcompass.contracts import Optimizer


def build_optimizer() -> Optimizer:
    raise NotImplementedError("optimiser not built yet")
