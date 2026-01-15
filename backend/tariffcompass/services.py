"""Where the API gets the five core implementations (contracts.py).

`CORE_BACKEND=fake` (tests that don't need the real core) returns the fakes in `tariffcompass.fakes`;
the default `real` imports the implementations from the search, classify and duties apps, falling back to the
fakes with a log line while those are still being built. Instances are cached per process.
"""

from __future__ import annotations

import os
from functools import cache
from importlib import import_module

import structlog

from tariffcompass import fakes
from tariffcompass.contracts import ClassifierProgram, DutyEngine, FirstStage, Optimizer, Retriever

log = structlog.get_logger("tariffcompass.services")

_REAL = {
    "retriever": ("tariffcompass.search.engine", "build_retriever", fakes.FakeRetriever),
    "first_stage": ("tariffcompass.classify.first_stage", "load_first_stage", fakes.FakeFirstStage),
    "program": ("tariffcompass.classify.program", "load_program", fakes.FakeProgram),
    "duties": ("tariffcompass.duties.engine", "build_engine", fakes.FakeDutyEngine),
    "optimizer": ("tariffcompass.classify.optimize", "build_optimizer", fakes.FakeOptimizer),
}


def _load(name: str):
    module, factory, fake = _REAL[name]
    if os.environ.get("CORE_BACKEND", "real") == "fake":
        return fake()
    try:
        return getattr(import_module(module), factory)()
    except (ImportError, AttributeError, NotImplementedError) as exc:
        log.warning("core_fallback_to_fake", part=name, reason=str(exc))
        return fake()


@cache
def retriever() -> Retriever:
    return _load("retriever")


@cache
def first_stage() -> FirstStage:
    return _load("first_stage")


@cache
def program() -> ClassifierProgram:
    return _load("program")


@cache
def duties() -> DutyEngine:
    return _load("duties")


@cache
def optimizer() -> Optimizer:
    return _load("optimizer")


def reset() -> None:
    """Drop cached instances (after a training round is made live, or in tests)."""
    for fn in (retriever, first_stage, program, duties, optimizer):
        fn.cache_clear()
