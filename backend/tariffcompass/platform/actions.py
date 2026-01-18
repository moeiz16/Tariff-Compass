"""Plain words for every audited action (Settings › Activity). Keys are `AuditEvent.action`."""

from __future__ import annotations

ACTION_LABELS: dict[str, str] = {
    "org.created": "Created the organisation",
    "auth.login": "Signed in",
    "auth.login_failed": "Failed sign-in",
    "auth.logout": "Signed out",
    "auth.password_changed": "Changed password",
    "auth.org_switched": "Switched organisation",
    "member.invited": "Invited someone",
    "member.invitation_revoked": "Withdrew an invitation",
    "member.joined": "Joined",
    "member.changed": "Changed a role",
    "member.removed": "Removed someone",
    "settings.changed": "Changed settings",
    "product.created": "Added a product",
    "product.updated": "Changed a product",
    "product.hidden": "Hid a product",
    "evidence.added": "Added evidence",
    "answer.created": "Classified a product",
    "answer.saved": "Saved to the binder",
    "answer.sent_to_broker": "Sent to the broker",
    "answer.fact_confirmed": "Confirmed a fact",
    "answer.citation_flagged": "Flagged a ruling",
    "review.opened": "Opened a review",
    "review.approved": "Approved a code",
    "review.corrected": "Corrected a code",
    "review.asked": "Asked the importer",
    "review.answered": "Answered the broker",
    "rule.created": "Added a review rule",
    "rule.changed": "Changed a review rule",
    "rule.removed": "Removed a review rule",
    "binder.exported": "Exported a binder",
    "binder.rechecked": "Re-checked a binder",
    "watch.scanned": "Checked for changes",
    "lab.round_started": "Started a training round",
    "lab.round_finished": "Finished a training round",
    "lab.signed": "Signed a training round",
    "lab.made_live": "Made a round live",
    "seed.loaded": "Loaded the sample data",
}


def label(action: str) -> str:
    return ACTION_LABELS.get(action, action.split(".")[-1].replace("_", " ").capitalize())
