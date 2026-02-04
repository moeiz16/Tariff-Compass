"""A deterministic, offline stand-in for a cloud LM, used by the DSPy program and by GEPA (ADR 0003).

It is a DSPy *engine* (`complete(Request) -> Response`), so the DSPy program, its adapters, GEPA and the
optimised-program JSON all run exactly as they would against a real LM, with no key and no network.

Format: DSPy chooses the adapter (XML-style field tags by default, `[[ ## field ## ]]` markers for the chat
adapter, JSON as the fallback); `field_in()` reads input fields in any of them and `render()` answers in the
format the prompt asked for. Behaviour: a `Policy` decides each signature's outputs from the inputs and the
current instructions. The task policy follows only what the instructions actually say (GEPA's proposed
instructions change its behaviour); the reflection policy writes new instructions from the metric's feedback.
Both are pure functions of the prompt text, so runs are reproducible: same data, seed and budget give the same
optimised program. The classification core supplies the tariff-specific policies.

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
    for pat in (
        rf"<{name}>\s*(.*?)\s*</{name}>",
        rf"\[\[ ## {name} ## \]\]\s*(.*?)\s*(?=\[\[ ## |\n\nRespond with the corresponding output fields|\Z)",
    ):
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
        super().__init__(model=f"offline/simulator-{role}", cache=False, engine=engine or default_engine())
        self.role = role


# ════════════════════════════════════════════════════════════════════════════════════════════════════════
# The tariff policies (classification core). They read only what the program puts in the prompt: the
# product text, the candidate headings with the first stage's probabilities and the precedent share, the
# heading texts and notes, the numbered rulings with their holdings and similarity, the tariff lines, and the
# current instructions. They never see a gold label. GEPA's feedback (which does describe the right answer
# for *training* examples) reaches only the reflection policy, exactly as it reaches a real reflection LM.
#
# What makes the simulator imperfect, on purpose and documented:
# - fixed default weights an unoptimised LM would plausibly use (trust the first stage most, precedent some);
# - deterministic noise: each score gets ± up to NOISE[module] from a hash of (product, option, module), so
#   close calls flip the way an LM's close calls do; same prompt → same answer;
# - a citation habit: without an instruction against it, a top-listed ruling under a neighbouring heading is
#   cited as support in CITE_SLIP of the cases (decided by the hash), as a hurried reader would;
# - it understands only a fixed vocabulary of instruction sentences ("RULE: …", listed in RULE_GRAMMAR); any
#   other instruction text is read but has no effect.
# ════════════════════════════════════════════════════════════════════════════════════════════════════════
import hashlib  # noqa: E402

NOISE = {"candidates": 0.04, "gri": 0.05, "subheading": 0.03}
CITE_SLIP = 0.3
CANDIDATE_TERMS_WEIGHT = 0.6  # how much the candidate step reads the heading texts themselves
TARIFF_TEXT_WEIGHT = 0.1  # how much the candidate step trusts a heading found by searching the tariff text
SIM_SEED = "tariff-compass-sim-1"
DEFAULTS = {
    "candidates.precedent": 0.3,
    "gri.precedent": 0.3,
    "gri.terms": 0.35,
    "subheading.follow": 0.5,  # follow the closest ruling's line when its similarity is at least this
    "confidence.margin": 0.10,
    "confidence.agree": 1,
    "confidence.precedent": 0.0,
}
RULE_GRAMMAR = (
    r"RULE: weigh precedent at (?P<w>[\d.]+) when ranking candidates",
    r"RULE: weigh precedent at (?P<w>[\d.]+) when choosing the heading",
    r"RULE: weigh heading terms at (?P<w>[\d.]+)",
    r"RULE: prefer (?P<a>\d{4}) over (?P<b>\d{4}) when the product mentions '(?P<t>[^']+)'",
    r"RULE: follow the closest ruling's line when its similarity is at least (?P<w>[\d.]+)",
    r"RULE: in heading (?P<h>\d{4}) choose (?P<c>\d{10}) when the product mentions '(?P<t>[^']+)'",
    r"RULE: cite as support only rulings under the chosen heading",
    r"RULE: say broker when the margin is below (?P<w>[\d.]+)",
    r"RULE: say broker when fewer than (?P<n>\d+) cited rulings agree",
    r"RULE: say broker when the precedent share is below (?P<w>[\d.]+)",
)
_WORD = re.compile(r"[a-z][a-z0-9-]+")
_STOP_WORDS = (
    "the a an and or of for with to in on by at from as is are be it its this that these those which other than "
    "not no any all each into per such use used thereof parts kind whether made heading headings subheading "
    "subheadings chapter chapters note notes statistical"
)
_STOP = frozenset(_STOP_WORDS.split())
# What any reader knows without being told (kept small on purpose).
SYNONYMS = {
    "bicycle": "cycle",
    "bike": "cycle",
    "headlight": "light",
    "taillight": "light",
    "lantern": "lamp",
    "aluminium": "aluminum",
    "fibre": "fiber",
}
EXPANSIONS = {  # what a reader files a word under, in the tariff's broader terms
    "polyester": ("man-made", "synthetic"),
    "nylon": ("man-made", "synthetic"),
    "acrylic": ("man-made", "synthetic"),
    "cotton": ("textile",),
    "wool": ("textile",),
    "polypropylene": ("plastic",),
    "polyethylene": ("plastic",),
    "silicone": ("plastic",),
    "cookware": ("kitchen", "household"),
    "pan": ("kitchen", "household"),
    "pot": ("kitchen", "household"),
    "saucepan": ("kitchen", "household"),
    "skillet": ("kitchen", "household"),
    "tumbler": ("household", "table"),
    "mug": ("household", "table"),
    "backpack": ("travel", "sport"),
    "rucksack": ("travel", "sport"),
    "knapsack": ("travel", "sport"),
    "duffel": ("travel", "sport"),
}
PHRASES = (  # phrases read as the tariff's word
    (re.compile(r"\bpower bank\b", re.I), "lithium-ion battery"),
    (re.compile(r"\bair (?:has been |is )?removed|evacuated\b", re.I), "vacuum"),
)
READS = {"insulat": "vacuum"}  # keys are stems
GENERIC_WORDS = (
    "steel iron article plastic household table kitchen metal base part accessory electric electrical "
    "equipment other material good product"
)
GENERIC = frozenset(GENERIC_WORDS.split())  # words too common in heading texts to decide anything
_RULED_OUT = re.compile(r"\bair[- ]insulated|only air|no vacuum|not vacuum|without (?:a )?vacuum\b", re.I)


def _noise(*key: str) -> float:
    h = hashlib.blake2b("|".join((SIM_SEED, *key)).encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") / 2**64 * 2 - 1  # uniform in [-1, 1)


def _stem(w: str) -> str:
    from tariffcompass.classify.evidence import stem

    return stem(w)


_EXCEPT = re.compile(r"\b(?:other than|excluding|except)\b[^;:]*", re.I)
RESIDUAL = re.compile(r"^(?:Other|Articles? of|Parts and accessories)\b", re.I)
_NEGATED = re.compile(r"\b(?:no|not|without|non)[- ](\w+)", re.I)


def _stems(text: str, expand: bool = True) -> set[str]:
    out = set()
    text = _NEGATED.sub(" ", text)  # "no vacuum" says nothing in favour of vacuum vessels
    for pat, words in PHRASES:
        if pat.search(text):
            text = f"{text} {words}"
    for w in _WORD.findall(text.lower()):
        if w in _STOP or len(w) < 3:
            continue
        w = SYNONYMS.get(w, w)
        w = _stem(w)
        out.add(SYNONYMS.get(w, w))
        if expand:
            out.update(EXPANSIONS.get(w, ()))
    return out


def instructions(prompt: str) -> str:
    m = re.search(r"your objective is:\s*(.*?)(?=\[\[ ## |\Z)", prompt, re.S)
    return m.group(1) if m else prompt


def knob(instr: str, key: str) -> float:
    pats = {
        "candidates.precedent": r"RULE: weigh precedent at ([\d.]+) when ranking candidates",
        "gri.precedent": r"RULE: weigh precedent at ([\d.]+) when choosing the heading",
        "gri.terms": r"RULE: weigh heading terms at ([\d.]+)",
        "subheading.follow": r"RULE: follow the closest ruling's line when its similarity is at least ([\d.]+)",
        "confidence.margin": r"RULE: say broker when the margin is below ([\d.]+)",
        "confidence.agree": r"RULE: say broker when fewer than (\d+) cited rulings agree",
        "confidence.precedent": r"RULE: say broker when the precedent share is below ([\d.]+)",
    }
    found = re.findall(pats[key], instr)
    return float(found[-1]) if found else float(DEFAULTS[key])


def _fields(line: str) -> list[str]:
    return [p.strip() for p in line.split("|")]


def _kv(parts: list[str]) -> dict[str, str]:
    return {k: v for p in parts if "=" in p for k, v in [p.split("=", 1)]}


def _candidates(inputs: dict[str, str], instr: str) -> dict[str, str]:
    product = inputs.get("product", "")
    w = knob(instr, "candidates.precedent")
    pst = _stems(product)
    read = set() if _RULED_OUT.search(product) else {v for k, v in READS.items() if k in pst and v not in pst}
    rows = []
    for line in inputs.get("candidates", "").splitlines():
        parts = _fields(line)
        if not parts or not re.fullmatch(r"\d{4}", parts[0]):
            continue
        kv = _kv(parts[1:-1])
        hst = _stems(_EXCEPT.sub("", parts[-1])) - GENERIC
        lst = _stems(kv.get("lines", "").replace(",", " ")) - GENERIC - hst
        terms = min(len(pst & hst) + len(pst & lst) + 0.5 * len(read & hst), 2.0) / 2.0
        if RESIDUAL.match(parts[-1]):
            terms *= 0.3  # "Other articles of …" holds what no other heading names
        score = (
            float(kv.get("p", 0))
            + w * float(kv.get("precedent", 0))
            + TARIFF_TEXT_WEIGHT * float(kv.get("tariff_text", 0))
            + CANDIDATE_TERMS_WEIGHT * terms
            + NOISE["candidates"] * _noise(product, parts[0], "cand")
        )
        rows.append((score, parts[0], parts[-1]))
    rows.sort(key=lambda r: -r[0])
    return {
        "headings": ", ".join(h for _, h, _ in rows),
        "rationale": "\n".join(f"{h}: the heading covers “{t[:90]}”." for _, h, t in rows[:4]),
    }


def _gri(inputs: dict[str, str], instr: str) -> dict[str, str]:
    product = inputs.get("product", "")
    pst = _stems(product)
    read = set() if _RULED_OUT.search(product) else {v for k, v in READS.items() if k in pst and v not in pst}
    low = product.lower()
    w_prec, w_terms = knob(instr, "gri.precedent"), knob(instr, "gri.terms")
    cands: list[dict] = []
    for line in inputs.get("headings", "").splitlines():
        parts = _fields(line)
        if not parts or not re.fullmatch(r"\d{4}", parts[0]):
            continue
        kv = _kv(parts[1:-1])
        text = parts[-1]
        hst = _stems(_EXCEPT.sub("", text))  # "… other than glass inners" names what the heading leaves out
        lst = _stems(kv.get("lines", "").replace(",", " ")) - GENERIC - hst
        overlap = min(len((pst & hst) - GENERIC) + 0.7 * len(pst & lst) + 0.5 * len(read & hst), 3.0) / 3.0
        if RESIDUAL.match(text):
            overlap *= 0.3
        rank = int(kv.get("rank", 9))
        cands.append(
            {
                "h": parts[0],
                "text": text,
                "excludes": [x for x in kv.get("excludes", "none").split(",") if x and x != "none"],
                "notes": kv.get("notes", "none"),
                "overlap": overlap,
                "key": len(((pst | read) & (hst | lst)) - GENERIC),
                "score": 0.4 / rank
                + w_terms * overlap
                + w_prec * float(kv.get("precedent", 0))
                + NOISE["gri"] * _noise(product, parts[0], "gri"),
            }
        )
    if not cands:
        return {"heading": "", "gri": "GRI 1", "set_aside": "", "facts": ""}
    present = {c["h"] for c in cands}
    reasons: dict[str, str] = {}
    # notes and heading exclusions (GRI 1): a heading whose terms match, protected by a note, wins
    for c in cands:
        if c["notes"] != "none" and c["key"] > 0:
            m = re.search(
                r"(Section [IVX]+, Note \d+\([a-z]\)|Section [IVX]+, Note \d+) excludes chapters (\d+)-(\d+)",
                c["notes"],
            )
            if m:
                lo, hi = int(m.group(2)), int(m.group(3))
                for o in cands:
                    if o["h"] != c["h"] and lo <= int(o["h"][:2]) <= hi:
                        o["score"] -= 1.0
                        reasons[o["h"]] = f"Set aside: excluded by {m.group(1)}"
        for x in c["excludes"]:
            for o in cands:
                if o["h"] == x and o["key"] > 0:  # the product fits the heading this one excludes
                    c["score"] -= 0.5
                    reasons.setdefault(c["h"], f"Set aside: heading {c['h']} excludes goods of heading {x}")
    for a, b, t in re.findall(r"RULE: prefer (\d{4}) over (\d{4}) when the product mentions '([^']+)'", instr):
        if a in present and b in present and t.lower() in low:
            for c in cands:
                if c["h"] == a:
                    c["score"] += 0.8
            reasons.setdefault(b, f"Set aside: the product mentions “{t}”, which points to heading {a}")
    cands.sort(key=lambda c: -c["score"])
    best = cands[0]
    # numbered rulings: the first one filed under the chosen heading, cited against each neighbour
    rid: dict[str, str] = {}
    for line in inputs.get("rulings", "").splitlines():
        m = re.match(r"\[(\d+)\]\s+(\S+ \S+)\s+\|\s+(\d{4})", line)
        if m and m.group(3) == best["h"]:
            rid.setdefault(best["h"], m.group(2))
    aside = []
    for c in cands[1:4]:
        why = reasons.get(c["h"]) or f"Set aside: its terms (“{c['text'][:70]}”) describe the product less closely"
        aside.append(f"{c['h']} | {why} | {rid.get(best['h'], 'none')}")
    gri = (
        "GRI 1"
        if best["overlap"] > 0 or best["score"] - (cands[1]["score"] if len(cands) > 1 else 0) > 0.2
        else "GRI 3(a)"
    )
    return {"heading": best["h"], "gri": gri, "set_aside": "\n".join(aside), "facts": ""}


def _capacity_l(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(fl\.?\s*oz|oz|ounces?|ml|millilit\w*|l\b|lit\w*)", text, re.I)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2).lower()
    return n * 0.0295735 if unit.startswith(("oz", "fl", "ounce")) else (n / 1000 if unit.startswith("m") else n)


def _capacity_fit(line: str, cap: float | None) -> float:
    if cap is None:
        return 0.0
    t = line.lower()
    nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?) lit", t)]
    if "not exceeding" in t and "exceeding" in t.replace("not exceeding", "", 1) and len(nums) >= 2:
        return 0.6 if nums[0] < cap <= nums[1] else -0.3
    if "not exceeding" in t and nums:
        return 0.6 if cap <= nums[0] else -0.3
    if "exceeding" in t and nums:
        return 0.6 if cap > nums[0] else -0.3
    return 0.0


def _subheading(inputs: dict[str, str], instr: str) -> dict[str, str]:
    product = inputs.get("product", "")
    pst = _stems(product)
    low = product.lower()
    follow = knob(instr, "subheading.follow")
    cap = _capacity_l(product)
    lines, prec, us_code = [], [], ""
    for line in inputs.get("lines", "").splitlines():
        if line.startswith("precedent:"):
            m = re.match(r"precedent: (\S+ \S+) → (\d+) \(sim ([\d.]+)\)", line)
            if m:
                prec.append((m.group(1), m.group(2), float(m.group(3))))
            continue
        if line.startswith("us_code:"):
            us_code = line.split(":", 1)[1].strip()
            continue
        parts = _fields(line)
        if len(parts) >= 2 and re.fullmatch(r"\d{8,10}", parts[0]):
            lines.append((parts[0], parts[1]))
    if not lines:
        return {"code": "", "why": "none"}
    codes_ = [c for c, _ in lines]
    rules = re.findall(r"RULE: in heading (\d{4}) choose (\d{10}) when the product mentions '([^']+)'", instr)
    for _h, c, t in rules:
        if c in codes_ and t.lower() in low:
            return {"code": c, "why": f"The product mentions “{t}”, which matches this line."}
    for rid, c, sim in prec:
        c10 = c if len(c) == 10 else c + "00"
        if sim >= follow and c10 in codes_:
            return {"code": c10, "why": f"The closest ruling, {rid}, holds this line for a similar article."}
    # GRI 6: walk down the levels, comparing only lines at the same level
    pool = [(c, [seg.strip() for seg in t.split(": ")]) for c, t in lines]
    if us_code:  # Canada: stay inside the US line's six-digit subheading when the Canadian tariff has it
        same6 = [x for x in pool if x[0][:6] == us_code[:6]]
        pool = same6 or pool
    common = _stems(pool[0][1][0]) if pool and pool[0][1] else set()  # the heading's own words count less here
    direct = _stems(product, expand=False)

    def ov(seg: str) -> float:
        """Matched words (the heading's own words count 0.3), less a little for each word the line adds that the
        description doesn't use."""
        ss = _stems(seg)
        hit = len((direct - common) & ss) + 0.5 * len((pst - direct - common) & ss) + 0.3 * len(pst & common & ss)
        miss = len(ss - pst - common - GENERIC)
        return hit - min(0.05 * miss, 0.5) if hit else 0.0

    depth = 1
    chosen_segs: list[str] = []
    while len(pool) > 1 and depth < 8:
        groups: dict[str, list] = {}
        for c, segs in pool:
            groups.setdefault(segs[depth] if depth < len(segs) else "", []).append((c, segs))
        if len(groups) == 1:
            depth += 1
            continue
        scored = []
        for seg, members in groups.items():
            own = ov(seg)
            deeper = max((sum(ov(x) for x in segs[depth + 1 :]) for _, segs in members), default=0)
            sc = own + 0.6 * deeper + _capacity_fit(seg, cap)
            if own <= 0 and not seg.lower().startswith("other") and seg:
                sc -= 0.2  # a specific line whose terms the description doesn't use
            sc += NOISE["subheading"] * _noise(product, members[0][0], seg, "sub")
            scored.append((sc, seg, members))
        scored.sort(key=lambda x: -x[0])
        chosen_segs.append(scored[0][1])
        pool = scored[0][2]
        depth += 1
    code = pool[0][0]
    fit = next(
        (s for s in reversed(chosen_segs) if s and s.lower().rstrip(":") != "other"),
        chosen_segs[-1] if chosen_segs else "",
    )
    return {"code": code, "why": f"Comparing lines at the same level (GRI 6), “{fit[:90]}” fits the product."}


def _dotted(code: str) -> str:
    d = re.sub(r"\D", "", code)
    return ".".join(p for p in (d[:4], d[4:6], d[6:8], d[8:10]) if p)


def _decision(text: str) -> dict[str, str]:
    return _kv(_fields(text))


def _cite(inputs: dict[str, str], instr: str) -> dict[str, str]:
    product = inputs.get("product", "")
    d = _decision(inputs.get("decision", ""))
    heading = d.get("heading", "")
    strict = "RULE: cite as support only rulings under the chosen heading" in instr
    rows = []
    for line in inputs.get("rulings", "").splitlines():
        m = re.match(r"\[(\d+)\]\s+(\S+ \S+)\s+\|\s+(\d{4})\s+\|\s+(\w+)", line)
        if m:
            rows.append((int(m.group(1)), m.group(2), m.group(3), m.group(4)))
    same = [r for r in rows if r[2] == heading and r[3] != "revoked"]
    other = [r for r in rows if r[2] != heading]
    support = [r[0] for r in same[:3]]
    first_listed = other and other[0][3] != "revoked" and other[0][0] < (same[0][0] if same else 99)
    if not strict and first_listed and (_noise(product, "slip") + 1) / 2 < CITE_SLIP:
        support = sorted({*support, other[0][0]})
    cites = "".join(f"[{n}]" for n in support)
    out = [
        f"The product is classified in heading {heading} under {d.get('gri', 'GRI 1')}{(' ' + cites) if cites else ''}."
    ]
    if d.get("us"):
        out.append(
            f"Within the heading, the line {_dotted(d['us'])} fits at each level of the "
            f"subheadings{(' ' + cites[:3]) if cites else ''}."
        )
    contrast = next((r for r in other if r[0] not in support), None)
    if contrast is not None:
        out.append(
            f"By contrast, rulings on articles placed in heading {contrast[2]} turned on different facts "
            f"[{contrast[0]}]."
        )
    return {"sentences": "\n".join(out)}


def _confidence(inputs: dict[str, str], instr: str) -> dict[str, str]:
    a = _kv(_fields(inputs.get("agreement", "")))
    margin = float(a.get("margin", 0))
    agreeing = int(float(a.get("agreeing", 0)))
    t_margin, t_agree = knob(instr, "confidence.margin"), knob(instr, "confidence.agree")
    deciding = a.get("deciding", "none")
    settled = (margin >= t_margin and float(a.get("precedent", 0)) >= knob(instr, "confidence.precedent")) or (
        deciding == "stated_for"
    )
    strong = settled and agreeing >= t_agree and deciding not in ("stated_against", "read", "unclear")
    runner = a.get("runner_up", "none")
    if strong:
        return {"verdict": "strong", "deciding_fact": "none", "question": "none"}
    return {
        "verdict": "broker",
        "deciding_fact": "heading_terms" if runner != "none" else "none",
        "question": "none",
    }


def tariff_task_policy(outputs: list[str], inputs: dict[str, str], prompt: str) -> dict[str, str]:
    instr = instructions(prompt)
    keys = set(outputs)
    if {"headings", "rationale"} <= keys:
        out = _candidates(inputs, instr)
    elif "set_aside" in keys:
        out = _gri(inputs, instr)
    elif "code" in keys:
        out = _subheading(inputs, instr)
    elif "sentences" in keys:
        out = _cite(inputs, instr)
    elif "verdict" in keys:
        out = _confidence(inputs, instr)
    else:
        out = {}
    return {k: out.get(k, "") for k in outputs}


# ── reflection: new instructions from GEPA's examples-with-feedback ─────────────────────────────────────
_FB = re.compile(r"FB\[(\w+)\]((?: \w+=[^\s\"\\]+)+)")
MAX_NEW_RULES = 3


def _feedback_items(text: str) -> list[tuple[str, dict[str, str]]]:
    out = []
    for kind, body in _FB.findall(text):
        out.append((kind, dict(p.split("=", 1) for p in body.split())))
    return out


def _set_knob(instr: str, pattern: str, sentence: str) -> str:
    lines = [ln for ln in instr.splitlines() if not re.match(pattern, ln.strip())]
    return "\n".join([*lines, sentence]).strip()


COMPONENT_MARKERS = (
    ("candidate tariff headings", "candidates"),
    ("General Rules of Interpretation", "gri"),
    ("subheadings at the same level", "subheading"),
    ("three or four plain sentences", "cite"),
    ("strong match or needs a broker", "confidence"),
)


def component_of(instruction: str) -> str:
    """Which module an instruction belongs to, from the signature's own first sentence (kept by every rewrite)."""
    for marker, name in COMPONENT_MARKERS:
        if marker in instruction:
            return name
    return ""


def tariff_reflection_policy(outputs: list[str], inputs: dict[str, str], prompt: str) -> dict[str, str]:
    """Write the next instruction from the current one and the feedback on a minibatch (deterministic)."""
    current = (inputs.get("current_instruction") or inputs.get("current_instruction_doc") or "").strip()
    items = _feedback_items(inputs.get("examples_with_feedback") or inputs.get("dataset_with_feedback") or prompt)
    new = current
    added = 0
    component = component_of(current)
    # each module learns only from the feedback that concerns it
    allowed = {
        "candidates": {"candidates"},
        "gri": {"heading"},
        "subheading": {"line"},
        "cite": {"cite"},
        "confidence": {"confidence"},
    }.get(component, set())
    kinds = {k for k, _ in items} & allowed
    if "heading" in kinds:
        wrong = [d for k, d in items if k == "heading"]
        for d in wrong:
            for term in (d.get("words") or "").split(","):
                term = term.replace("_", " ").strip()
                if not term or term == "none" or added >= MAX_NEW_RULES:
                    continue
                rule = f"RULE: prefer {d['expected']} over {d['chose']} when the product mentions '{term}'"
                if rule not in new:
                    new = f"{new}\n{rule}"
                    added += 1
                    break
        prec = [d for d in wrong if float(d.get("precedent_expected", 0)) > float(d.get("precedent_chose", 0))]
        if len(prec) * 2 >= len(wrong) and wrong:
            w = round(min(knob(new, "gri.precedent") + 0.2, 1.2), 2)
            new = _set_knob(
                new,
                r"RULE: weigh precedent at [\d.]+ when choosing the heading",
                f"RULE: weigh precedent at {w} when choosing the heading",
            )
    if "candidates" in kinds:
        miss = [d for k, d in items if k == "candidates"]
        if any(float(d.get("precedent_expected", 0)) > 0 for d in miss):
            w = round(min(knob(new, "candidates.precedent") + 0.2, 1.2), 2)
            new = _set_knob(
                new,
                r"RULE: weigh precedent at [\d.]+ when ranking candidates",
                f"RULE: weigh precedent at {w} when ranking candidates",
            )
    if "line" in kinds:
        lines = [d for k, d in items if k == "line"]
        sims = [
            float(d["precedent_sim"])
            for d in lines
            if d.get("precedent_held") == d.get("expected") and d.get("precedent_sim")
        ]
        if sims:
            w = round(max(min(min(sims), knob(new, "subheading.follow")) - 0.02, 0.3), 2)
            new = _set_knob(
                new,
                r"RULE: follow the closest ruling's line when its similarity is at least [\d.]+",
                f"RULE: follow the closest ruling's line when its similarity is at least {w}",
            )
        for d in lines:
            term = (d.get("words") or "").split(",")[0].replace("_", " ").strip()
            term = "" if term == "none" else term
            if term and added < MAX_NEW_RULES and d.get("expected", "").isdigit() and len(d["expected"]) == 10:
                rule = f"RULE: in heading {d['expected'][:4]} choose {d['expected']} when the product mentions '{term}'"
                if rule not in new:
                    new = f"{new}\n{rule}"
                    added += 1
    if "cite" in kinds and "RULE: cite as support only rulings under the chosen heading" not in new:
        new = f"{new}\nRULE: cite as support only rulings under the chosen heading"
    if "confidence" in kinds:
        obs = [
            (float(d.get("margin", 0)), float(d.get("precedent", 0)), d.get("right") == "yes")
            for k, d in items
            if k == "confidence"
        ]
        grid_m = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]
        grid_p = [0.0, 0.2, 0.4, 0.6, 0.8]

        def cost(tm: float, tp: float) -> tuple[int, float, float]:
            # a "strong" that is wrong costs three times a needless "broker"
            c = 0
            for m, pr, right in obs:
                strong = m >= tm and pr >= tp
                c += 3 if (strong and not right) else (1 if (not strong and right) else 0)
            return (-c, -tm, -tp)

        tm, tp = max(((m, p) for m in grid_m for p in grid_p), key=lambda x: cost(*x))
        new = _set_knob(
            new, r"RULE: say broker when the margin is below [\d.]+", f"RULE: say broker when the margin is below {tm}"
        )
        new = _set_knob(
            new,
            r"RULE: say broker when the precedent share is below [\d.]+",
            f"RULE: say broker when the precedent share is below {tp}",
        )
    return dict.fromkeys(outputs, new)


def default_engine() -> SimulatorEngine:
    return SimulatorEngine(task=tariff_task_policy, reflection=tariff_reflection_policy)
