"""Lab tables (owner: the platform layer persists; the classification core produces the reports).

- TrainingRound: n, status (training|waiting_signoff|live|not_made_live|retired), trained_at, lm_label,
  reflection_lm_label, data_snapshot (sha256 of the train/val/test ruling ids), test_window (from, to),
  seed, report (the RoundReport JSON from contracts.Optimizer), program_path (optimised program JSON),
  live_from, live_to, notes.
- SignOff: round, user, role, signed_at, statement, checks (the five gate results at signing time).
  Promotion needs two SignOffs by different people with `lab:sign` (one compliance, one broker).
"""
