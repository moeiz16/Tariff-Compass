"""RoundReport ⇄ JSON. The classification core writes each round's report with `dump` (committed demo rounds
live in `classify/artifacts/rounds/round-<n>.report.json`); the Lab stores and serves it with `load`.

Format: `dataclasses.asdict(report)` with dates as ISO strings and `test_window` as `[from, to]`.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date
from pathlib import Path
from typing import Any

from tariffcompass.contracts import DepthAccuracy, RoundReport
from tariffcompass.platform.config import tc


def _plain(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def dump(report: RoundReport) -> dict[str, Any]:
    return _plain(dataclasses.asdict(report))


def load(data: dict[str, Any]) -> RoundReport:
    window = data.get("test_window") or [None, None]
    return RoundReport(
        round_n=int(data["round_n"]),
        data_snapshot=str(data.get("data_snapshot", "")),
        test_window=(date.fromisoformat(window[0]), date.fromisoformat(window[1])),
        by_depth=tuple(DepthAccuracy(**d) for d in data.get("by_depth", [])),
        by_chapter=tuple(data.get("by_chapter", [])),
        calibration=dict(data.get("calibration", {})),
        citation_precision=float(data.get("citation_precision", 0.0)),
        latency_ms=dict(data.get("latency_ms", {})),
        drift_psi=dict(data.get("drift_psi", {})),
        learned=tuple(data.get("learned", [])),
        gates=tuple(data.get("gates", [])),
        program_path=str(data.get("program_path", "")),
        lm_label=str(data.get("lm_label", "offline simulator")),
        reflection_lm_label=str(data.get("reflection_lm_label", "offline simulator")),
        seed=int(data.get("seed", 7)),
    )


def artifact_dir() -> Path:
    return Path(tc()["ARTIFACT_DIR"]) / "rounds"


def committed(n: int) -> dict[str, Any] | None:
    """A demo round's committed report, validated by a round trip through `load`, or None."""
    path = artifact_dir() / f"round-{n}.report.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text())
    return dump(load(data))
