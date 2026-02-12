# Model card: the first stage (word matching)

Written from `classify/artifacts/first_stage_report.json` by `manage.py train`; numbers below are measured,
not claimed.

## What it does

Given a product description, it ranks the HTSUS headings that could hold it and passes the top five to the
classifier program, with a calibrated probability for each and the words that pushed each one up. It is also
the classical baseline the program must beat (the Lab calls it “word matching”). It never decides a code on
its own and nothing it says is filed.

## Data

CBP CROSS rulings (NY and HQ letters, 2014 to August 2025) from a public mirror, cleaned as described in
`docs/DATA.md`: labels are re-derived from each letter's own holding, and a ruling becomes a labelled example
only when its holding agrees with the stated tariff number at the heading, all its holdings share one
six-digit subheading and its ruling number can be trusted.

- Letters read: 18,136; with a classification holding: 13,456.
- Holding agrees with the stated number at the heading: 12,947; disagrees (dropped as labels and never cited): 509.
- Holdings across several subheadings (dropped as labels): 1,422.
- Labelled examples: **10,556**.

The model's input is the product as the letter describes it before any legal analysis (the subject line and
the facts, cut at the first sentence that names a heading, a tariff number, the HTSUS or a rule, with all
tariff numbers removed), so the holding never leaks into the features.

## Splits (by date, no leakage across time)

- train < 2024-04-01 ≤ validation < 2025-01-01 ≤ test (by ruling issue date).
- Train 8,399 · validation 1,063 · test 1,094 (test window 2025-01-02 to 2025-08-01).
- The test set was frozen (ids and SHA-256 `db8403dc6ce1ad3e…` in `splits.json`) before any
  tuning. Tuning, model choice, pruning and calibration read only the validation set.
- Headings with fewer than two training rulings are not classes (490 classes); 69 test rulings fall in headings the model has never seen and count as misses.

## Models compared (test set, measured once at the end)

| Model | Heading top-1 | top-3 | top-5 | Chapter top-1 | top-3 |
|---|---|---|---|---|---|
| Shipped: linear svm, pruned + calibrated | 65.4% | 78.9% | 83.3% | 79.4% | 91.8% |
| Logistic regression (TF-IDF), unpruned | 61.3% | 77.0% | 82.6% | 77.3% | 92.7% |
| Linear SVM (TF-IDF), unpruned | 64.5% | 79.4% | 83.4% | 78.5% | 91.6% |
| LightGBM on SVD(160) of the TF-IDF + text facts (chapters only) | – | – | – | 70.8% | 88.3% |

Champion rule: highest validation top-5 heading accuracy, then top-1 (decided before the test set is read). Validation scores: logistic regression top-5 88.1%; linear svm top-5 89.4%.
Optuna studies (seeded TPE): logistic regression C = {'C': 53.9992}, linear SVM C = {'C': 0.7259}, LightGBM {'num_leaves': 8, 'learning_rate': 0.14741032565600595, 'min_child_samples': 20, 'colsample_bytree': 0.8340791066985648, 'reg_lambda': 4.145279984660203}.
Pruning keeps each heading's 4800 strongest weights (the smallest level within half a
point of the unpruned model on validation, or the largest level tried); weights are stored as float16.

## Calibration

temperature scaling on validation (Platt-style, one parameter). Temperature 0.0944. Expected calibration error on validation 0.7154 before → 0.0939 after; on the test set 0.0977.

| Confidence band (test) | Rulings | Mean confidence | Accuracy |
|---|---|---|---|
| 0.00–0.07 | 56 | 0.041 | 0.143 |
| 0.07–0.13 | 82 | 0.096 | 0.256 |
| 0.13–0.20 | 53 | 0.164 | 0.396 |
| 0.20–0.27 | 44 | 0.232 | 0.386 |
| 0.27–0.33 | 47 | 0.303 | 0.234 |
| 0.33–0.40 | 27 | 0.365 | 0.370 |
| 0.40–0.47 | 37 | 0.434 | 0.540 |
| 0.47–0.53 | 33 | 0.498 | 0.545 |
| 0.53–0.60 | 31 | 0.568 | 0.452 |
| 0.60–0.67 | 40 | 0.633 | 0.625 |
| 0.67–0.73 | 35 | 0.702 | 0.629 |
| 0.73–0.80 | 43 | 0.771 | 0.628 |
| 0.80–0.87 | 38 | 0.835 | 0.632 |
| 0.87–0.93 | 73 | 0.904 | 0.794 |
| 0.93–1.00 | 455 | 0.991 | 0.921 |

## Where it goes wrong (test, by chapter of the predicted heading)

Most frequent confusions (gold chapter → predicted chapter): 73→83 (7), 90→85 (6), 84→85 (6), 49→48 (6), 38→90 (6), 90→94 (5), 96→39 (5), 84→87 (5).

## Drift

- Chapter-mix PSI, training vs the newest rulings: 0.3405 (large shift); training vs validation 0.1776.
- Chapters that moved most: 61 (0.082 → 0.022), 84 (0.059 → 0.109), 95 (0.073 → 0.107), 62 (0.044 → 0.011).
- By month as new rulings arrive: 2025-01 0.9604 (n=93), 2025-02 0.7255 (n=87), 2025-03 0.802 (n=128), 2025-04 0.6592 (n=153), 2025-05 0.6882 (n=203), 2025-06 0.8978 (n=202), 2025-07 0.7254 (n=222), 2025-08 6.5985 (n=6). A month with few rulings swings widely; the monthly series is a watch signal, not a verdict.

## Serving

- p95 1.78 ms per description on this laptop (gate: < 150 ms); artefacts 8.6 MB (JSON vocabulary, sparse float16 weights, no pickles).
- Tracked in MLflow (local SQLite store, `mlruns/`, git-ignored); registered as `tariff-compass-first-stage`.

## Champion and challenger

Word matching (this model, with the closest retrieved ruling's line under its top heading and a calibrated
confidence word) is what answers in the product. The DSPy program is a challenger: it can only answer after a
training round passes all five checks against word matching and two people sign it live. With the offline
simulator no round passes (see `eval/RESULTS.md`); a run with a real LM is the honest test of the program.

The simulator's noise model, and why: each score the simulated LM compares gets a deterministic offset of up
to ±0.03 to ±0.05 from a hash of the product and the option, so close calls between two headings or lines can
go either way, as an LM's do, while clear calls never flip; and without an instruction against it, a
top-listed ruling under a neighbouring heading is cited as support in 30 of 100 answers, the commonest
citation slip a hurried reader makes. Nothing in the noise reads a gold label. Details in ADR 0003.

## How the test set was used

Once, for the final measurement above. An earlier end-to-end run of the training command (a pipeline check
with one trial per study) also printed test figures; nothing was chosen from them. The champion rule (top-5
on validation) and every threshold were fixed in code beforehand, and the gates in `eval/gates.toml` predate
both runs. After training, the input normalisation gained a Canadian/British-to-US spelling map
(“aluminium” → “aluminum”); CBP's letters use US spelling, so the measured figures are unaffected. The
program's training rounds and the evaluation read the test set again while the pipeline was being fixed;
the last of those readings, after the final fixes, is the one reported in `eval/RESULTS.md` and was the
final look.

## Limits

- It reads words, not products: an article described with a heading's own words is easy; one described only
  by brand or function is not. The program, the rulings and a broker sit between it and any code.
- Coverage follows CBP's caseload: headings with few rulings are weak or absent (9617 has four letters since
  2014), and the newest rulings lean towards chapters the training years saw less.
- No people are scored, so there is no fairness analysis; nothing personal is a feature.

