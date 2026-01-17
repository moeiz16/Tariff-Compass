"""Review tables (Platform & API). Planned per docs/API_CONTRACT.md Part 2:

- ReviewItem: org, product, answer, kind (unsure|differs|ruling_changed|always_review|requested),
  reason_detail, into (US|CA|both), proposed_us, proposed_ca, value_usd, status (waiting|approved|corrected|
  asked|answered|withdrawn), assigned_to, created_at, decided_at.
- Decision: item, action (approve|correct|ask), final_us, final_ca, reason_kind (facts_differ|ruling_elsewhere|
  heading_misread|other), reason_text, ruling_relied, decided_by, licence, created_at.
- Question: item, asked_by, text, options, answer, answered_by, answered_at.
- TrainingExample: from a Decision: description, final codes, deciding fact, the broker's lesson sentence
  ("what the next training round will learn"), used_in_round (nullable).
- AlwaysReviewRule: org, kind (heading|chapter|material|value_over|origin|keyword), value, plain_label,
  active, created_by, created_at.
"""
