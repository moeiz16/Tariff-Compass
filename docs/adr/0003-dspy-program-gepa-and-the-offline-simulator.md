# ADR 0003: A DSPy program optimised with GEPA, and a deterministic offline LM simulator

**Status:** accepted

## Context

Classification is a chain of judgements a broker would recognise: which headings could hold the product, which
rule decides between them, which subheading at each level, which rulings support each sentence, and whether the
answer is sure enough to stand without a broker. We want those steps explicit, their instructions improved
against real rulings rather than hand-tuned, and the whole pipeline runnable with no key and no network.

## Decision

1. **A DSPy program with five modules** (`classify/program.py`): CandidateHeadings → GriReasoning →
   ChooseSubheading (US and Canada) → SelectCitations → Confidence. The classical first stage (ADR 0006) narrows
   the 97 chapters to a few candidate headings first; the search engine (ADR 0004) supplies the rulings and tariff
   texts each module reads.
2. **GEPA optimises the instructions.** A training round runs `dspy.GEPA` with a feedback metric that scores an
   answer at chapter, heading, subheading and full-code depth and explains in words what went wrong (wrong heading,
   neighbour not set aside, a revoked ruling cited as support). Training examples are rulings (labels from each
   letter's holding) plus broker corrections; validation and test sets are newer rulings. The optimised program is
   saved as JSON; the round records seed, budget, data snapshot hash and the LMs used.
3. **One LM adapter, offline by default** (`adapters/lm.py`). With `LLM_FAKE=true` (default) both the task LM and
   GEPA's reflection LM are a **deterministic simulator** (`adapters/lm_sim.py`): a DSPy engine that reads the
   prompt's fields in whatever format DSPy's adapter used (XML tags, `[[ ## ]]` markers or JSON) and answers in the
   same format through two policies:
   - the **task policy** is a fixed, inspectable procedure over the inputs the program passes (candidate headings
     and their texts, the first stage's ranking, retrieved holdings) that follows only what the current
     instructions say. Rules GEPA writes into the instructions (for example "double-wall alone does not mean
     vacuum; require 'vacuum' or 'air removed'") change its behaviour, so optimisation is real optimisation of
     instructions;
   - the **reflection policy** reads GEPA's examples-with-feedback and writes new instructions from the corrections
     and failures it sees, deterministically.
   Same data, seed and budget give the same optimised program, byte for byte.
4. **Live runs are opt-in.** With `LLM_FAKE=false` and a free-tier key, `dspy.LM(LITELLM_MODEL)` is used (Groq
   or OpenRouter for the task, Gemini for reflection by default). DSPy 3.5 reaches these providers with its own
   client; LiteLLM is optional.
5. **Honest labelling.** Every answer stores the LM that wrote it; every round report carries `lm_label` and
   `reflection_lm_label`; `eval/RESULTS.md` has one table per LM. Numbers produced with the simulator are labelled
   "offline simulator" and describe the pipeline and the optimisation loop, not a language model's reasoning. The
   committed demo rounds say which LM produced them.

## Consequences

- CI and the demo run the full program, GEPA included, in seconds with no network.
- The simulator is code we own and test; its policies are part of the classification core and can be read like any
  other module. It does not pretend to be a language model: the Lab says "Answers written by: offline simulator".
- A live run against a free tier is rate-limited and slower (budget: < 6 s per answer); the training round's metric
  budget is kept small enough for free-tier quotas and is recorded in the report.
- The program's signatures are a contract between the program and the simulator policies; changing a field means
  changing both, with tests.

## How the simulator behaves (as built)

The task policies (`adapters/lm_sim.py`) read only the prompt DSPy renders: the product text, the candidate
headings with the first stage's probability, the share of retrieved rulings under each heading ("precedent"), a
tariff-text search rank, the heading texts and the words of their lines, the notes that relate headings (Section
XV Note 1(m), Section XVII Note 2(f)), the numbered rulings with their holdings, and the tariff lines. Gold labels
never reach them; GEPA's feedback, which does name the right code for training examples, reaches only the
reflection policy, as it would reach a real reflection LM.

- **Defaults an unoptimised LM would plausibly have:** trust the first stage most, precedent some, the heading's
  own words a little; walk the subheadings level by level (GRI 6), with "Other" as the residual; cite the rulings
  under the chosen heading and one neighbour for contrast; say "Strong match" when the first two headings are a
  little apart or the deciding fact is stated.
- **Imperfection, on purpose:** deterministic noise on every score (± 0.03–0.05, from a hash of the product and the
  option); a citation slip (a top-listed neighbouring ruling cited as support in 30% of the cases, unless told
  otherwise); a small, fixed reader's vocabulary (bicycle = cycle, polyester is a man-made fibre, "air removed" =
  vacuum, "insulated" weakly suggests vacuum unless "air-insulated", negations drop the word).
- **Instructions it understands:** a fixed grammar of `RULE:` sentences (precedent weights, heading-term weight,
  "prefer A over B when the product mentions 'x'", "in heading H choose C when …", the precedent-following
  threshold, "cite as support only rulings under the chosen heading", the confidence thresholds). Anything else in
  the instructions is read and ignored.
- **Reflection:** writes those sentences from the feedback on a minibatch: preference rules from the words that
  point to the expected heading in the training rulings, precedent weights when precedent pointed the right way,
  the citation rule after a slip, and the confidence thresholds that minimise "a wrong Strong match costs three
  needless broker reviews" on the minibatch.

So an optimisation round really changes behaviour, and the change can be read in the saved program's instructions;
but the numbers measure this pipeline with a rule-following stand-in, not a language model's reasoning.
