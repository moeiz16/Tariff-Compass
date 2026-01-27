"""The product binder: the append-only reasonable-care record (API_CONTRACT §1.9).

`append()` is the only way a product's codes or standing change: it writes an audit event and a binder
version that links to it, in one transaction. `binder_out()` builds the revision matrix (each version with the
rows that changed since the one before), the approval stamp, entries, retention and the record fingerprint.
"""

from __future__ import annotations

import hashlib
from typing import Any

from django.db import transaction
from django.db.models import Count, Max, Q

from tariffcompass import clock, codes
from tariffcompass.api import labels
from tariffcompass.catalog import retention
from tariffcompass.catalog.evidence import evidence_out
from tariffcompass.catalog.models import BinderVersion, Entry, Product
from tariffcompass.platform import audit, roles
from tariffcompass.platform.context import Ctx
from tariffcompass.platform.models import AuditEvent, Organisation, User
from tariffcompass.platform.present import person_ref

DECIDED_KINDS = ("approved", "corrected", "re_approved")
MATRIX_ROWS = ("us_code", "ca_code", "standing", "deciding_fact", "evidence", "rulings_relied", "decided_by", "why")


def fmt(code: str) -> str | None:
    return codes.fmt(code) if code else None


def ruling_key(ruling_id: str) -> str:
    return ruling_id.lower().replace(" ", "-")


def ruling_url(ruling_id: str) -> str:
    return f"https://rulings.cbp.gov/ruling/{ruling_id.split()[-1]}"


def append(
    product: Product,
    kind: str,
    *,
    actor: User | None,
    actor_role: str = "",
    us_code: str | None = None,
    ca_code: str | None = None,
    standing: str | None = None,
    deciding_fact: dict[str, Any] | None = None,
    evidence: list[str] | None = None,
    rulings_relied: list[str] | None = None,
    why: str = "",
    answer: Any = None,
    action: str = "",
    summary: str = "",
    ip: str = "",
    at: Any = None,
) -> BinderVersion:
    """Append one version (inheriting unchanged fields from the previous one) and move the product with it."""
    with transaction.atomic():
        prev = product.versions.order_by("-n").first()
        n = (prev.n if prev else 0) + 1
        us = codes.digits(us_code) if us_code is not None else (prev.us_code if prev else product.us_code)
        ca = codes.digits(ca_code) if ca_code is not None else (prev.ca_code if prev else product.ca_code)
        standing = standing or {"proposed": "proposed", "question_answered": "proposed", "withdrawn": "withdrawn"}.get(
            kind, "approved"
        )
        decided = actor if kind in DECIDED_KINDS or kind == "withdrawn" else None
        event = audit.record(
            product.org,
            action or f"binder.{kind}",
            summary or f"{labels.VERSION_KINDS[kind]} {product.sku} v{n}",
            actor=actor,
            actor_role=actor_role,
            target_type="product",
            target_id=str(product.pk),
            details={"label": product.sku, "version": n, "kind": kind, "us": us, "ca": ca},
            ip=ip,
            at=at,
        )
        version = BinderVersion.objects.create(
            org=product.org,
            product=product,
            n=n,
            kind=kind,
            at=at or event.created_at,
            us_code=us,
            ca_code=ca,
            standing=standing,
            deciding_fact=deciding_fact if deciding_fact is not None else (prev.deciding_fact if prev else None),
            evidence=evidence if evidence is not None else (list(prev.evidence) if prev else []),
            rulings_relied=rulings_relied
            if rulings_relied is not None
            else (list(prev.rulings_relied) if prev else []),
            decided_by=decided,
            decided_role=actor_role if decided else "",
            why=why,
            answer=answer,
            audit_event=event,
        )
        product.us_code, product.ca_code, product.standing = us, ca, standing
        product.updated_at = clock.now()
        product.save(update_fields=["us_code", "ca_code", "standing", "updated_at"])
    return version


def append_from_ctx(product: Product, kind: str, ctx: Ctx, **kw: Any) -> BinderVersion:
    return append(product, kind, actor=ctx.user, actor_role=ctx.role, ip=ctx.ip, **kw)


# ── Presentation ────────────────────────────────────────────────────────────────────────────────────────
def summaries(qs) -> list[dict[str, Any]]:
    from tariffcompass.review.models import OPEN_STATUSES

    rows = qs.annotate(
        n_versions=Count("versions", distinct=True),
        last_decided=Max("versions__at", filter=Q(versions__kind__in=DECIDED_KINDS)),
        open_reviews=Count("reviews", filter=Q(reviews__status__in=OPEN_STATUSES), distinct=True),
    )
    return [summary(p) for p in rows]


def summary(p: Product) -> dict[str, Any]:
    if not hasattr(p, "n_versions"):
        from tariffcompass.review.models import OPEN_STATUSES

        p.n_versions = p.versions.count()  # type: ignore[attr-defined]
        last = p.versions.filter(kind__in=DECIDED_KINDS).order_by("-at").first()
        p.last_decided = last.at if last else None  # type: ignore[attr-defined]
        p.open_reviews = p.reviews.filter(status__in=OPEN_STATUSES).count()  # type: ignore[attr-defined]
    return {
        "id": str(p.pk),
        "sku": p.sku,
        "title": p.title,
        "category": p.category,
        "category_label": labels.CATEGORIES.get(p.category, p.category),
        "made_in": p.made_in,
        "made_in_label": labels.ORIGINS.get(p.made_in, p.made_in),
        "us_code": fmt(p.us_code),
        "ca_code": fmt(p.ca_code),
        "standing": p.standing,
        "standing_label": labels.STANDINGS.get(p.standing, p.standing),
        "versions": p.n_versions,  # type: ignore[attr-defined]
        "last_decided_at": p.last_decided,  # type: ignore[attr-defined]
        "in_review": bool(p.open_reviews),  # type: ignore[attr-defined]
    }


def _role_of(user: User | None, org: Organisation, fallback: str = "") -> str:
    if fallback or user is None:
        return fallback
    m = user.memberships.filter(org=org).first()
    return m.role if m else ""


def _deciding_cell(fact: dict[str, Any] | None) -> dict[str, str] | None:
    if not fact:
        return None
    return {"label": fact.get("label", ""), "value": fact.get("value", ""), "source_note": fact.get("source_note", "")}


def _ruling_refs(ids: list[str]) -> list[dict[str, str]]:
    from tariffcompass.catalog.rulings import status_of

    out = []
    for rid in ids:
        st = status_of(rid)
        out.append({"id": rid, "key": ruling_key(rid), "status_label": st["kind_label"]})
    return out


def version_out(v: BinderVersion, prev: BinderVersion | None, current: bool) -> dict[str, Any]:
    changed: list[str] = []
    if prev is not None:
        for row in MATRIX_ROWS:
            a = getattr(prev, row + ("_id" if row == "decided_by" else ""))
            b = getattr(v, row + ("_id" if row == "decided_by" else ""))
            if a != b:
                changed.append(
                    {
                        "us_code": "usCode",
                        "ca_code": "caCode",
                        "deciding_fact": "decidingFact",
                        "rulings_relied": "rulingsRelied",
                        "decided_by": "decidedBy",
                    }.get(row, row)
                )
    return {
        "n": v.n,
        "kind": v.kind,
        "kind_label": labels.VERSION_KINDS.get(v.kind, v.kind),
        "at": v.at,
        "us_code": fmt(v.us_code),
        "ca_code": fmt(v.ca_code),
        "standing": v.standing,
        "standing_label": labels.STANDINGS.get(v.standing, v.standing),
        "deciding_fact": _deciding_cell(v.deciding_fact),
        "evidence": list(v.evidence or []),
        "rulings_relied": _ruling_refs(list(v.rulings_relied or [])),
        "decided_by": person_ref(v.decided_by, _role_of(v.decided_by, v.org, v.decided_role)),
        "why": v.why,
        "fingerprint": audit.fingerprint(v.audit_event.hash) if v.audit_event else "",
        "current": current,
        "changed": changed,
    }


def record_fingerprint(product: Product) -> tuple[str, int]:
    """SHA-256 over the hashes of every audit event about this product, in order (short form, and the count)."""
    hashes = list(
        AuditEvent.objects.filter(org=product.org, target_type="product", target_id=str(product.pk))
        .order_by("id")
        .values_list("hash", flat=True)
    )
    digest = hashlib.sha256("".join(hashes).encode()).hexdigest()
    return audit.fingerprint(digest), len(hashes)


def approval_sentence(v: BinderVersion, org: Organisation) -> str:
    role = _role_of(v.decided_by, org, v.decided_role)
    who = v.decided_by.full_name if v.decided_by else "Tariff Compass"
    role_words = roles.ROLE_LABELS.get(role, "").lower()
    firm = ""
    if role == "broker" and v.decided_by is not None:
        m = v.decided_by.memberships.filter(org=org).select_related("engagement__broker_org").first()
        if m and m.engagement:
            firm = f", {m.engagement.broker_org.name.split()[0]}"
    loc = clock.local(v.at)
    verb = {"approved": "Approved", "re_approved": "Re-approved", "corrected": "Corrected"}[v.kind]
    return (
        f"{verb} by {who}{', ' + role_words if role_words else ''}{firm} · "
        f"{loc.day} {loc.strftime('%b %Y, %H:%M')} PT · version {v.n}"
    )


def entries_out(product: Product) -> list[dict[str, Any]]:
    return [
        {
            "entry_number": e.entry_number,
            "country": e.country,
            "entered_on": e.entered_on,
            "code": codes.fmt(e.code),
            "duty_paid": {"amount": f"{e.duty_paid:.2f}", "currency": e.currency},
        }
        for e in product.entries.all()
    ]


def keep_until(product: Product):
    versions = list(product.versions.all())
    last = max((v.at for v in versions), default=product.created_at)
    entries = [(e.country, e.entered_on) for e in Entry.objects.filter(product=product)]
    return retention.kept_until(entries=entries, last_decision=clock.local(last).date(), into=product.into or [])


def advance_ruling_note(product: Product) -> str | None:
    if "CA" not in (product.into or []):
        return None
    return (
        f"Draft a CBSA advance ruling request for {product.title} (Memorandum D11-11-3): the binder's facts, "
        "evidence and rulings relied on are filled in for you to review and send."
    )


def binder_out(product: Product, *, chain_ok: bool, checked_at) -> dict[str, Any]:
    versions = list(product.versions.select_related("decided_by", "audit_event", "org").order_by("n"))
    out_versions = []
    for i, v in enumerate(versions):
        out_versions.append(version_out(v, versions[i - 1] if i else None, i == len(versions) - 1))
    decided = [v for v in versions if v.kind in DECIDED_KINDS]
    approval = None
    if decided:
        v = decided[-1]
        approval = {
            "by": person_ref(v.decided_by, _role_of(v.decided_by, product.org, v.decided_role)),
            "at": v.at,
            "version": v.n,
            "sentence": approval_sentence(v, product.org),
        }
        if approval["by"] is None:
            approval = None
    until, rule = keep_until(product)
    fp, events = record_fingerprint(product)
    opened = clock.local(versions[0].at).date() if versions else clock.local(product.created_at).date()
    return {
        "product": summary(product),
        "opened_on": opened,
        "kept_until": until,
        "retention_note": retention.note(until, rule),
        "versions": out_versions,
        "approval": approval,
        "evidence": [evidence_out(e) for e in product.evidence.select_related("uploaded_by").all()],
        "entries": entries_out(product),
        "record": {"chain_verified": chain_ok, "checked_at": checked_at, "events": events, "fingerprint": fp},
        "advance_ruling": advance_ruling_note(product),
    }
