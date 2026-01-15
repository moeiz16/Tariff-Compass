"""Toolchain smoke: a DSPy program optimised by GEPA, fully offline.

Proves three things on Python 3.13 without any key or network:
1. a custom DSPy engine can stand in for a cloud LM (the deterministic simulator pattern);
2. dspy.GEPA runs end to end with that engine as both the task LM and the reflection LM;
3. the reflection step can read the metric's feedback and change the program's instructions,
   so the optimised program measurably beats the seed program on the same examples.

The real simulator lives in tariffcompass/adapters/lm_sim.py; this file stays tiny on purpose.
"""

from __future__ import annotations

import json
import re
import sys
import time

import dspy
from dspy.lm15 import Message, Response, TextPart, Usage

RULE = re.compile(r"RULE:\s*'([^']+)'\s*->\s*(\d{4})")


def _text(parts) -> str:
    return "".join(p.text for p in parts if isinstance(p, TextPart))


def render(prompt: str, fields: dict[str, str]) -> str:
    """Answer in whichever output format the DSPy adapter asked for (JSON, [[ ## ]] markers or XML tags)."""
    if "Outputs will be a JSON object" in prompt or "Respond with a JSON object" in prompt:
        return json.dumps(fields)
    if "[[ ## completed ## ]]" in prompt:
        return "\n\n".join(f"[[ ## {k} ## ]]\n{v}" for k, v in fields.items()) + "\n\n[[ ## completed ## ]]"
    return "\n".join(f"<{k}>\n{v}\n</{k}>" for k, v in fields.items())


def field_in(prompt: str, name: str) -> str | None:
    """Read an input field in any adapter format."""
    for pat in (rf"<{name}>\s*(.*?)\s*</{name}>", rf"\[\[ ## {name} ## \]\]\s*(.*?)\s*(?=\[\[ ## |\Z)"):
        m = re.search(pat, prompt, re.S)
        if m:
            return m.group(1)
    return None


class SimEngine:
    """Answers by applying the 'RULE:' lines it finds in the instructions; reflects by writing new rules."""

    def complete(self, request):
        system = request.system if isinstance(request.system, str) else _text(request.system or [])
        user = "\n".join(_text(m.parts) for m in request.messages)
        prompt = f"{system}\n{user}"
        out = self._reflect(prompt, user) if "new_instruction" in system else self._answer(prompt, user)
        n_in, n_out = len(prompt) // 4, len(out) // 4
        return Response(
            id=None,
            model="sim",
            message=Message.assistant([TextPart(out)]),
            finish_reason="stop",
            usage=Usage(input_tokens=n_in, output_tokens=n_out, total_tokens=n_in + n_out),
        )

    @staticmethod
    def _answer(prompt: str, user: str) -> str:
        desc = (field_in(user, "description") or user).lower()
        heading = "9999"
        for term, code in RULE.findall(prompt):
            if term in desc:
                heading = code
                break
        return render(prompt, {"heading": heading})

    @staticmethod
    def _reflect(prompt: str, user: str) -> str:
        current = field_in(user, "current_instruction")
        base = (current or "Classify the product.").strip()
        learned = sorted(set(re.findall(r"Expected heading (\d{4}); deciding term '([^']+)'", user)))
        rules = [f"RULE: '{term}' -> {code}" for code, term in learned if f"'{term}'" not in base]
        body = "\n".join([base, *rules])
        return render(prompt, {"new_instruction": body})


class SimLM(dspy.BaseLM):
    def __init__(self) -> None:
        super().__init__(model="sim/offline", cache=False, engine=SimEngine())


class Classify(dspy.Signature):
    """Classify the product into its four-digit tariff heading."""

    description: str = dspy.InputField()
    heading: str = dspy.OutputField()


DATA = [
    ("double-wall vacuum insulated stainless tumbler", "9617", "vacuum"),
    ("vacuum flask with screw lid, 750 ml", "9617", "vacuum"),
    ("rechargeable led bicycle headlight", "8512", "bicycle"),
    ("bicycle tail light, usb charging", "8512", "bicycle"),
    ("knitted cotton pullover sweater", "6110", "pullover"),
    ("men's pullover, 100% cotton knit", "6110", "pullover"),
    ("lithium-ion power bank 10000 mah", "8507", "lithium"),
    ("lithium-ion battery pack for camp lantern", "8507", "lithium"),
]


def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    ok = (pred.heading or "").strip() == gold.heading
    fb = "Correct." if ok else f"Expected heading {gold.heading}; deciding term '{gold.term}'."
    return dspy.Prediction(score=1.0 if ok else 0.0, feedback=fb)


def accuracy(program, data) -> float:
    return sum(metric(ex, program(description=ex.description)).score for ex in data) / len(data)


def main() -> int:
    examples = [dspy.Example(description=d, heading=h, term=t).with_inputs("description") for d, h, t in DATA]
    lm = SimLM()
    dspy.configure(lm=lm)
    seed = dspy.Predict(Classify)
    before = accuracy(seed, examples)
    t0 = time.perf_counter()
    gepa = dspy.GEPA(
        metric=metric,
        reflection_lm=lm,
        max_metric_calls=120,
        reflection_minibatch_size=4,
        num_threads=1,
        seed=7,
        track_stats=False,
    )
    optimised = gepa.compile(seed, trainset=examples, valset=examples)
    after = accuracy(optimised, examples)
    instr = optimised.signature.instructions
    print(
        f"dspy {dspy.__version__}  GEPA offline: accuracy {before:.2f} -> {after:.2f} in {time.perf_counter() - t0:.1f}s"
    )
    print("optimised instructions:\n" + instr)
    return 0 if after > before else 1


if __name__ == "__main__":
    sys.exit(main())
