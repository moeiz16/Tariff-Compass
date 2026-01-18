# ADR 0006: A classical first stage, and an evaluation that only counts rulings the classifier hasn't seen

**Status:** accepted

## Context

The DSPy program reasons over a handful of candidate headings, not 1,200. Something fast and measurable must narrow
the field, and the program must prove it beats a simple baseline. Rulings are dated, and newer rulings are what
the product will face, so the evaluation must respect time.

## Decision

1. **First stage = word matching, done properly** (`classify/first_stage.py`): TF-IDF (word 1–2 grams and character
   3–5 grams) → logistic regression and a calibrated linear SVM as the baseline; LightGBM on reduced TF-IDF
   features plus simple text facts as the challenger, tuned with Optuna. Outputs are calibrated top-k chapters and
   headings with the words that drove them (coefficients, LightGBM contributions). Runs and the registry live in
   MLflow (`mlruns/`, SQLite store). The baseline is what the Lab calls "word matching".
2. **Labels from the letters.** Training and test labels are re-derived from each ruling's own holding; rulings
   whose holding disagrees with the stated code at the heading, or that state no classification, are not labelled
   examples (docs/DATA.md).
3. **Splits by date.** Newest rulings are the test set; the slice before them validates; older rulings train.
   Broker corrections join training only.
4. **What we measure** (eval/, gates in CI, tables in `eval/RESULTS.md`):
   - accuracy at chapter, heading, six digits and ten digits for word matching, the unoptimised program and the
     GEPA-optimised program, per LM;
   - top-k accuracy of the first stage, a confusion view by chapter, and calibration of "Needs a broker" (how often
     "Strong match" was right, how often "Needs a broker" caught a wrong first guess);
   - citation precision (do cited rulings share the answer's heading, never a revoked one as support);
   - landed cost exact on a hand-checked set of 20 products;
   - drift: chapter-mix PSI between training and the newest rulings, and detection of a simulated tariff revision;
   - latency: first stage p95 < 150 ms; full answer < 1 s offline.
5. **Promotion is a sign-off, not a script.** A round goes live only if its checks pass and two people sign.

## Consequences

- The program has to beat a strong, honest baseline on future rulings, not on a random split.
- Coverage is uneven: some headings have few rulings (the corpus has two in heading 9617 since 2014). Per-chapter
  tables make that visible instead of averaging it away.
- The first stage is also the fallback the product can explain when no LM is configured.
