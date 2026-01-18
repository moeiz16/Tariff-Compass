"""Members, invitations, roles, the broker engagement, settings: RBAC and tenant isolation."""

from __future__ import annotations

from datetime import timedelta

import pytest

from tariffcompass import clock
from tariffcompass.platform.models import AuditEvent, Invitation, Membership
from tests.platform_fixtures import Api

pytestmark = pytest.mark.django_db


def test_members_lists_own_org_including_brokers(world):
    rows = world.api("admin").get("org/members").json()
    names = {r["user"]["fullName"]: r for r in rows}
    assert set(names) == {"Jordan Tse", "Maya Lindqvist", "Priscilla Mensah", "Dana Whitlock", "Rafael Ouellet"}
    assert names["Dana Whitlock"]["viaBroker"] == "Driftwood Customs Brokers"
    assert names["Dana Whitlock"]["roleLabel"] == "Licensed customs broker"
    assert "Ola Berg" not in names


@pytest.mark.parametrize(("who", "status"), [("admin", 200), ("compliance", 403), ("importer", 403), ("broker", 403)])
def test_only_admins_manage_members(world, who, status):
    m = Membership.objects.get(org=world.north, user=world.importer)
    res = world.api(who).patch(f"org/members/{m.pk}", {"title": "Ops"})
    assert res.status_code == status


def test_role_change_is_audited(world):
    m = Membership.objects.get(org=world.north, user=world.importer)
    res = world.api("admin").patch(f"org/members/{m.pk}", {"role": "compliance"})
    assert res.json()["role"] == "compliance"
    ev = AuditEvent.objects.get(action="member.changed")
    assert ev.details["role"] == ["importer", "compliance"] and ev.actor_name == "Priscilla Mensah"


def test_last_admin_cannot_be_demoted_or_removed(world):
    api = world.api("admin")
    m = Membership.objects.get(org=world.north, user=world.admin)
    assert api.patch(f"org/members/{m.pk}", {"role": "importer"}).json()["code"] == "last_admin"
    assert api.delete(f"org/members/{m.pk}").status_code == 409


def test_member_of_another_org_is_404(world):
    foreign = Membership.objects.get(org=world.other, user=world.outsider)
    api = world.api("admin")
    assert api.patch(f"org/members/{foreign.pk}", {"title": "x"}).status_code == 404
    assert api.delete(f"org/members/{foreign.pk}").status_code == 404


def test_remove_member(world):
    m = Membership.objects.get(org=world.north, user=world.importer)
    assert world.api("admin").delete(f"org/members/{m.pk}").status_code == 204
    assert not Membership.objects.filter(pk=m.pk).exists()


def test_invitation_flow_for_a_new_person(world):
    admin = world.api("admin")
    res = admin.post("org/invitations", {"email": "sam@nb.example", "role": "importer"})
    assert res.status_code == 201
    link = res.json()["link"]
    assert "/invite/" in link
    listed = admin.get("org/invitations").json()
    assert listed[0]["email"] == "sam@nb.example" and listed[0]["link"] is None  # shown once
    token = link.rsplit("/", 1)[1]
    visitor = Api()
    missing = visitor.post(f"invitations/{token}/accept", {})
    assert missing.status_code == 422
    me = visitor.post(f"invitations/{token}/accept", {"fullName": "Sam Rowe", "password": "tidepool-lantern-41"})
    assert me.status_code == 200 and me.json()["membership"]["role"] == "importer"
    assert visitor.post(f"invitations/{token}/accept", {}).status_code == 404  # used once
    assert {"member.invited", "member.joined"} <= set(AuditEvent.objects.values_list("action", flat=True))
    assert Invitation.objects.get().token_hash != token  # only the hash is stored


def test_expired_invitation_is_410(world):
    admin = world.api("admin")
    token = admin.post("org/invitations", {"email": "late@nb.example", "role": "importer"}).json()["link"]
    Invitation.objects.update(expires_at=clock.now() - timedelta(minutes=1))
    res = Api().post(f"invitations/{token.rsplit('/', 1)[1]}/accept", {"fullName": "L", "password": "x" * 14})
    assert res.status_code == 410 and res.json()["code"] == "expired"


def test_revoke_invitation_and_cross_tenant(world):
    admin = world.api("admin")
    inv_id = admin.post("org/invitations", {"email": "r@nb.example", "role": "importer"}).json()["id"]
    assert world.api("outsider").delete(f"org/invitations/{inv_id}").status_code == 404
    assert admin.delete(f"org/invitations/{inv_id}").status_code == 204
    assert admin.get("org/invitations").json() == []


def test_inviting_an_existing_member_is_refused(world):
    res = world.api("admin").post("org/invitations", {"email": "jordan@nb.example", "role": "importer"})
    assert res.status_code == 422


def test_roles_describe_permissions(world):
    rows = world.api("importer").get("roles").json()
    by = {r["role"]: r for r in rows}
    assert set(by) == {"importer", "broker", "compliance", "admin"}
    assert "review:decide" in by["broker"]["permissions"]


def test_brokers_shows_the_engagement_both_ways(world):
    row = world.api("compliance").get("org/brokers").json()[0]
    assert row["brokerOrg"] == "Driftwood Customs Brokers" and row["countriesLabel"] == "US and Canadian entries"
    assert {p["user"]["fullName"] for p in row["people"]} == {"Dana Whitlock", "Rafael Ouellet"}
    assert world.api("outsider").get("org/brokers").json() == []


def test_settings_read_patch_and_audit(world):
    s = world.api("importer").get("settings").json()
    assert s["into"] == ["US", "CA"] and s["retentionYears"] == 5 and s["retentionYearsCa"] == 6
    assert "D17-1-21" in s["retentionNote"] and "163.4" in s["retentionNote"]
    assert s["brokerName"] == "Driftwood Customs Brokers"
    assert world.api("importer").patch("settings", {"madeIn": "VN"}).status_code == 403
    res = world.api("compliance").patch("settings", {"madeIn": "VN", "alwaysSendToBroker": True})
    assert res.json()["madeIn"] == "VN" and res.json()["alwaysSendToBroker"] is True
    assert AuditEvent.objects.get(action="settings.changed").details["made_in"] == ["CN", "VN"]
    assert world.api("outsider").get("settings").json()["madeIn"] == "CN"  # other tenant untouched


def test_settings_validation(world):
    res = world.api("compliance").patch("settings", {"into": []})
    assert res.status_code == 422 and res.json()["errors"][0]["field"] == "into"
