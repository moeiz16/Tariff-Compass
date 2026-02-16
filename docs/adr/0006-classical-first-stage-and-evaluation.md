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
6. **Two kinds of gate** (`eval/gates.toml`). **Release gates** judge what is in use and fail the build (and CI) when
   one fails: the first stage's top-k, the in-use confidence word, the in-use citations, landed cost, drift detection
   and latency. **Promotion checks** decide whether a challenger round may go live: beating word matching and the
   unoptimised program at heading and full code, and its own "Strong match" right at least 90 times in 100. Missing
   one means "not promoted": the round stays a challenger and the Lab says why; it is not a build failure.

## Consequences

- The program has to beat a strong, honest baseline on future rulings, not on a random split.
- Coverage is uneven: some headings have few rulings (the corpus has four letters in heading 9617 since 2014). Per-chapter
  tables make that visible instead of averaging it away.
- The first stage is also the fallback the product can explain when no LM is configured.

## As built

- The champion is chosen on validation top-5 heading accuracy before the test set is read. The linear SVM won
  (validation top-5 0.894 vs 0.881 for logistic regression); it ships pruned to 4,800 weights per heading, in
  float16, with a single temperature fitted on validation. LightGBM, tuned the same way, ranks chapters only and
  stayed a challenger (chapter top-3 on the test set 0.883 vs 0.918 for the shipped model).
- Headings with fewer than two training rulings are not classes; their test rulings count as misses.
- The program's evidence is gathered as of each example's date (validation) or the test window's start (test).
- "Strong match" starts at the lowest threshold where the one-sided 95% Clopper-Pearson lower bound of validation
  precision (six digits) is at least 0.90. For word matching no threshold reaches it (best lower bound 0.874, 121
  right of 131), so the in-use word is always "Needs a broker" and that release gate fails. The threshold was not
  loosened; a better first stage or a real-LM round has to clear it.
- Every figure is in `docs/MODEL_CARD.md`, `classify/artifacts/first_stage_report.json`, the training rounds'
  reports and `eval/RESULTS.md`.
