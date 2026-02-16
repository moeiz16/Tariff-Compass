from __future__ import annotations

import pytest

from tariffcompass.platform import audit, roles
from tariffcompass.platform.models import AuditEvent, Organisation


def test_every_role_grant_is_a_known_permission():
    for role in roles.ROLES:
        assert roles.permissions_for(role) <= set(roles.ALL_PERMISSIONS), role
        assert role in roles.ROLE_LABELS


def test_only_brokers_and_compliance_sign_training_rounds():
    signers = {r for r in roles.ROLES if roles.has_permission(r, "lab:sign")}
    assert signers == {"broker", "compliance"}


def test_only_brokers_decide_reviews():
    assert {r for r in roles.ROLES if roles.has_permission(r, "review:decide")} == {"broker"}


@pytest.mark.django_db
def test_audit_chain_verifies_and_detects_tampering():
    org = Organisation.objects.create(name="Northbound Goods Co.", slug="northbound")
    for i in range(3):
        audit.record(org, "product.classified", f"Classified product {i}", target_type="product", target_id=str(i))
    check = audit.verify(org)
    assert check.ok and check.events == 3
    second = AuditEvent.objects.filter(org=org).order_by("id")[1]
    AuditEvent.objects.filter(id=second.id).update(summary="Edited after the fact")
    broken = audit.verify(org)
    assert not broken.ok and broken.broken_at == second.id


@pytest.mark.django_db
def test_chains_are_per_organisation():
    a = Organisation.objects.create(name="A", slug="a")
    b = Organisation.objects.create(name="B", slug="b")
    first_a = audit.record(a, "x", "first in A")
    first_b = audit.record(b, "x", "first in B")
    assert first_a.prev_hash == first_b.prev_hash == audit.GENESIS
    assert len(audit.fingerprint(first_a.hash)) == 14


def test_client_ip_trusts_the_forwarded_address_only_from_the_local_proxy():
    from django.test import RequestFactory

    from tariffcompass.platform.context import client_ip

    rf = RequestFactory()
    via_proxy = rf.get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.7")
    direct = rf.get("/", REMOTE_ADDR="198.51.100.4", HTTP_X_FORWARDED_FOR="203.0.113.7")
    assert client_ip(via_proxy) == "203.0.113.7" and client_ip(direct) == "198.51.100.4"
    assert client_ip(rf.get("/", REMOTE_ADDR="127.0.0.1")) == "127.0.0.1"
