"""Catalog tables (owner: platform/API workstream). Planned per docs/API_CONTRACT.md Part 2:

- Product: org, sku, title, category, made_in (ISO-3166 alpha-2), ships_to (US/CA), unit_value, currency,
  listing_text, status, current codes (us_code, ca_code), created_at.
- Evidence: product, kind (listing|spec_sheet|photo|supplier_email|other), file path under data/uploads,
  sha256, extracted_text, uploaded_by, created_at.
- Answer: an immutable snapshot of one classification answer (the full AnswerOut JSON), with the program
  version and first-stage model version that produced it, the LM label ("offline simulator" or the cloud model)
  and timings.
- BinderVersion: product, n (v1…), kind (proposed|question_answered|approved|corrected|re_approved|withdrawn),
  us_code, ca_code, standing, deciding_fact, rulings_relied (list), evidence ids, decided_by, licence, why,
  audit_event (FK to platform.AuditEvent: the fingerprint), created_at. Append-only.
- Entry: product, entry_number, country, entered_on, code_used, duty_paid (for "entries using this code").
"""
