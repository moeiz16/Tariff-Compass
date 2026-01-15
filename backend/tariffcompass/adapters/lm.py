"""The language-model adapter for the DSPy program and its GEPA reflection step (ADR 0003).

`task_lm()` and `reflection_lm()` return DSPy LMs. Offline (`LLM_FAKE=true`, the default) both are the
deterministic simulator in `lm_sim`. With `LLM_FAKE=false` and a free-tier key they are `dspy.LM(LITELLM_MODEL)`:
DSPy 3.5 routes `groq/…`, `gemini/…` and `openrouter/…` through its own bundled client (no LiteLLM needed);
any other provider prefix needs the optional `ai` extra (LiteLLM). `lm_label()` is stored on every answer and
training round so the Lab can say which numbers came from which LM.
"""

from __future__ import annotations

import os

import dspy
from django.conf import settings

from tariffcompass.adapters.lm_sim import SimulatorLM

_KEYS = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}


def _cfg() -> dict:
    return settings.TARIFF_COMPASS


def is_fake() -> bool:
    if _cfg()["LLM_FAKE"]:
        return True
    provider = _cfg()["LITELLM_MODEL"].split("/", 1)[0]
    key = _KEYS.get(provider)
    return bool(key) and not os.environ.get(key or "")  # no key → stay offline rather than fail


def lm_label(role: str = "task") -> str:
    if is_fake():
        return "offline simulator"
    return _cfg()["LITELLM_MODEL"] if role == "task" else _cfg()["LITELLM_REFLECTION_MODEL"]


def task_lm() -> dspy.BaseLM:
    if is_fake():
        return SimulatorLM(role="task")
    return dspy.LM(_cfg()["LITELLM_MODEL"], temperature=0.0, max_tokens=2000, cache=True)


def reflection_lm() -> dspy.BaseLM:
    if is_fake():
        return SimulatorLM(role="reflection")
    return dspy.LM(_cfg()["LITELLM_REFLECTION_MODEL"], temperature=1.0, max_tokens=8000, cache=True)
