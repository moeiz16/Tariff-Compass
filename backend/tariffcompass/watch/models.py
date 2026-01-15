"""Watch tables (owner: platform/API workstream). Planned per docs/API_CONTRACT.md Part 2:

- Change: kind (legal_pending|duty_layer|ruling_modified|ruling_revoked|new_rulings|schedule_revision),
  dated (date) or pending_label ("argued 5 Nov 2025"), headline, body, knows[], unknowns[], source_url,
  layer_id / ruling_id / hts_release, created_at.
- AffectedProduct: change, product, effect (plain sentence), recheck_status (unchanged|needs_review|re_approved),
  duty_before, duty_after.
"""
