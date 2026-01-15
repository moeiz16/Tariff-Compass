"""A deterministic, offline stand-in for a cloud LM, used by the DSPy program and by GEPA (ADR 0003).

It is a DSPy *engine* (`complete(Request) -> Response`), so the DSPy program, its adapters, GEPA and the
optimised-program JSON all run exactly as they would against a real LM, with no key and no network.

Format: DSPy chooses the adapter (XML-style field tags by default, `[[ ## field ## ]]` markers for the chat
adapter, JSON as the fallback); `field_in()` reads input fields in any of them and `render()` answers in the
format the prompt asked for. Behaviour: a `Policy` decides each signature's outputs from the inputs and the
current instructions. The task policy follows only what the instructions actually say (GEPA's proposed
instructions change its behaviour); the reflection policy writes new instructions from the metric's feedback.
Both are pure functions of the prompt text, so runs are reproducible: same data, seed and budget give the same
optimised program. The classification workstream supplies the tariff-specific policies.

Honesty rule: numbers produced with this simulator are labelled "offline simulator" everywhere (answers, Lab,
eval/RESULTS.md); they measure the pipeline, not a language model's reasoning.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Literal

import dspy
from dspy.lm15 import Message, Response, TextPart, Usage

Role = Literal["task", "reflection"]
# A policy maps (signature output field names, inputs by name, full prompt text) to output values.
Policy = Callable[[list[str], dict[str, str], str], dict[str, str]]

_OUTPUTS_RE = re.compile(r"Your output fields are:\n(.*?)(?:\n[A-Z]|\Z)", re.S)
_INPUTS_RE = re.compile(r"Your input fields are:\n(.*?)\nYour output fields are:", re.S)
_FIELD_RE = re.compile(r"^\d+\.\s+`([A-Za-z_][A-Za-z0-9_]*)`", re.M)


def text_of(parts) -> str:
    return "".join(p.text for p in parts if isinstance(p, TextPart))


def field_names(system: str, which: Literal["input", "output"]) -> list[str]:
    m = (_INPUTS_RE if which == "input" else _OUTPUTS_RE).search(system)
    return _FIELD_RE.findall(m.group(1)) if m else []


def field_in(text: str, name: str) -> str | None:
    """Read an input field written by any DSPy adapter (XML tags or [[ ## name ## ]] markers)."""
    for pat in (rf"<{name}>\s*(.*?)\s*</{name}>", rf"\[\[ ## {name} ## \]\]\s*(.*?)\s*(?=\[\[ ## |\Z)"):
        m = re.search(pat, text, re.S)
        if m:
            return m.group(1)
    return None


def render(prompt: str, fields: dict[str, str]) -> str:
    """Answer in whichever output format the adapter asked for."""
    if "Outputs will be a JSON object" in prompt or "Respond with a JSON object" in prompt:
        return json.dumps(fields)
    if "[[ ## completed ## ]]" in prompt:
        return "\n\n".join(f"[[ ## {k} ## ]]\n{v}" for k, v in fields.items()) + "\n\n[[ ## completed ## ]]"
    return "\n".join(f"<{k}>\n{v}\n</{k}>" for k, v in fields.items())


def echo_policy(outputs: list[str], inputs: dict[str, str], prompt: str) -> dict[str, str]:
    """Placeholder policy: fills every output with an empty value (replaced by the tariff policies)."""
    return dict.fromkeys(outputs, "")


def keep_instruction_policy(outputs: list[str], inputs: dict[str, str], prompt: str) -> dict[str, str]:
    """Placeholder reflection policy: proposes the current instruction unchanged."""
    return {name: inputs.get("current_instruction", "") for name in outputs}


class SimulatorEngine:
    """DSPy engine that routes each request to the task or reflection policy."""

    def __init__(self, task: Policy = echo_policy, reflection: Policy = keep_instruction_policy) -> None:
        self.task, self.reflection = task, reflection

    def complete(self, request):
        system = request.system if isinstance(request.system, str) else text_of(request.system or [])
        user = "\n".join(text_of(m.parts) for m in request.messages)
        prompt = f"{system}\n{user}"
        outputs = field_names(system, "output") or ["answer"]
        inputs = {n: v for n in field_names(system, "input") if (v := field_in(user, n)) is not None}
        policy = self.reflection if "new_instruction" in outputs else self.task
        out = render(prompt, policy(outputs, inputs, prompt))
        n_in, n_out = max(1, len(prompt) // 4), max(1, len(out) // 4)
        return Response(
            id=None,
            model="offline-simulator",
            message=Message.assistant([TextPart(out)]),
            finish_reason="stop",
            usage=Usage(input_tokens=n_in, output_tokens=n_out, total_tokens=n_in + n_out),
        )


class SimulatorLM(dspy.BaseLM):
    """`dspy.BaseLM` backed by the simulator engine; `role` picks the default policies."""

    def __init__(self, role: Role = "task", engine: SimulatorEngine | None = None) -> None:
        super().__init__(model=f"offline/simulator-{role}", cache=False, engine=engine or SimulatorEngine())
        self.role = role
