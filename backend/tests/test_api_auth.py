"""Sign-in, demo sign-in, sessions, CSRF, the sign-in pause, password policy, switching organisation."""

from __future__ import annotations

import time

import pytest

from tariffcompass.platform.context import SESSION_SEEN, SESSION_STARTED
from tariffcompass.platform.models import AuditEvent, LoginFailure, User
from tests.platform_fixtures import PASSWORD, Api

pytestmark = pytest.mark.django_db


def test_csrf_endpoint_sets_the_readable_cookie(client):
    res = client.get("/api/v1/auth/csrf")
    assert res.status_code == 204
    assert "tc_csrf" in res.cookies and not res.cookies["tc_csrf"]["httponly"]


def test_login_returns_me_with_permissions_and_session_times(world):
    api = Api()
    res = api.post("auth/login", {"email": "MAYA@nb.example", "password": PASSWORD})
    assert res.status_code == 200, res.content
    me = res.json()
    assert me["user"]["fullName"] == "Maya Lindqvist"
    assert me["activeOrg"]["name"] == "Northbound Goods Co."
    assert me["membership"]["role"] == "compliance" and "lab:sign" in me["membership"]["permissions"]
    assert me["session"]["expiresAt"] < me["session"]["absoluteExpiresAt"]
    assert res.cookies["tc_session"]["httponly"]
    assert api.get("auth/session").json()["me"]["user"]["email"] == "maya@nb.example"
    assert AuditEvent.objects.filter(org=world.north, action="auth.login").exists()


def test_login_without_csrf_header_is_refused(world, client):
    client.get("/api/v1/auth/csrf")
    res = client.post(
        "/api/v1/auth/login", {"email": "maya@nb.example", "password": PASSWORD}, content_type="application/json"
    )
    assert res.status_code == 403 and res.json()["code"] == "csrf_failed"


def test_wrong_password_is_generic_and_counts_down(world):
    api = Api()
    res = api.post("auth/login", {"email": "maya@nb.example", "password": "nope"})
    assert res.status_code == 401
    body = res.json()
    assert body["code"] == "invalid_credentials" and body["triesLeft"] == 4
    assert res["Content-Type"] == "application/problem+json" and res["X-Tariff-Compass-Now"]
    unknown = api.post("auth/login", {"email": "nobody@nb.example", "password": "nope"}).json()
    assert unknown["code"] == "invalid_credentials"
    assert AuditEvent.objects.filter(action="auth.login_failed").count() == 1  # only for a real account


def test_five_failures_pause_the_email(world):
    api = Api()
    codes = [api.post("auth/login", {"email": "dana@dw.example", "password": "x"}).status_code for _ in range(5)]
    assert codes == [401, 401, 401, 401, 423]
    res = api.post("auth/login", {"email": "dana@dw.example", "password": PASSWORD})
    assert res.status_code == 423
    assert res.json()["code"] == "sign_in_paused" and res.json()["retryAfterSeconds"] > 0
    # other emails are unaffected
    assert api.post("auth/login", {"email": "maya@nb.example", "password": PASSWORD}).status_code == 200


def test_success_clears_failures(world):
    api = Api()
    api.post("auth/login", {"email": "maya@nb.example", "password": "x"})
    assert api.post("auth/login", {"email": "maya@nb.example", "password": PASSWORD}).status_code == 200
    assert not LoginFailure.objects.filter(email="maya@nb.example").exists()


def test_auth_rate_limit(world):
    api = Api()
    codes = [api.post("auth/login", {"email": f"x{i}@nb.example", "password": "x"}).status_code for i in range(11)]
    assert codes[-1] == 429
    assert codes[:10].count(429) == 0


def test_passwords_are_argon2(db):
    user = User.objects.create_user("argon@nb.example", PASSWORD, full_name="A")
    assert user.password.startswith("argon2$argon2id$")


def test_signup_creates_org_with_admin_and_rejects_weak_passwords(db, fast_hasher):
    api = Api()
    weak = api.post(
        "auth/signup",
        {"email": "new@co.example", "password": "password1234", "fullName": "New Person", "orgName": "New Co"},
    )
    assert weak.status_code == 422 and weak.json()["code"] == "weak_password"
    res = api.post(
        "auth/signup",
        {
            "email": "new@co.example",
            "password": "a-quite-long-phrase-77",
            "fullName": "New Person",
            "orgName": "New Co",
        },
    )
    assert res.status_code == 201
    me = res.json()
    assert me["membership"]["role"] == "admin" and me["activeOrg"]["slug"] == "new-co"
    dup = api.post(
        "auth/signup",
        {"email": "new@co.example", "password": "a-quite-long-phrase-77", "fullName": "X", "orgName": "Y"},
    )
    assert dup.status_code == 422


def test_logout_ends_the_session(world):
    api = world.api("importer")
    assert api.post("auth/logout").status_code == 204
    assert api.get("auth/session").json()["me"] is None
    assert api.get("org/members").status_code == 401


def test_signed_out_requests_are_401(db, client):
    res = client.get("/api/v1/settings")
    assert res.status_code == 401 and res.json()["code"] == "not_authenticated"


def test_idle_session_expires(world):
    api = world.api("importer")
    s = api.c.session
    s[SESSION_SEEN] = time.time() - 31 * 60
    s.save()
    res = api.get("settings")
    assert res.status_code == 401 and res.json()["code"] == "session_expired"
    assert api.get("auth/session").status_code == 200  # visitors still get 200


def test_absolute_session_expires(world):
    api = world.api("importer")
    s = api.c.session
    s[SESSION_STARTED] = time.time() - 13 * 3600
    s.save()
    assert api.get("settings").json()["code"] == "session_expired"


def test_refresh_extends_idle_expiry(world):
    api = world.api("importer")
    res = api.post("auth/refresh")
    assert res.status_code == 200 and "absoluteExpiresAt" in res.json()


def test_broker_lands_in_the_client_and_can_switch(world):
    api = Api()
    me = api.post("auth/login", {"email": "dana@dw.example", "password": PASSWORD}).json()
    assert me["activeOrg"]["name"] == "Northbound Goods Co."
    orgs = {o["name"]: o for o in me["orgs"]}
    assert orgs["Northbound Goods Co."]["viaBroker"] == "Driftwood Customs Brokers"
    assert orgs["Driftwood Customs Brokers"]["viaBroker"] is None
    switched = api.post("auth/switch-org", {"orgId": str(world.drift.pk)}).json()
    assert switched["activeOrg"]["kind"] == "broker" and switched["activeOrg"]["kindLabel"] == "Customs broker firm"
    assert AuditEvent.objects.filter(action="auth.org_switched").exists()


def test_switching_to_a_foreign_org_is_404(world):
    api = world.api("importer")
    res = api.post("auth/switch-org", {"orgId": str(world.other.pk)})
    assert res.status_code == 404
    assert api.post("auth/switch-org", {"orgId": "not-a-uuid"}).status_code == 404


def test_password_change_checks_current_and_strength(world):
    api = world.api("importer")
    assert api.post("auth/password", {"currentPassword": "wrong", "newPassword": "x" * 12}).status_code == 422
    weak = api.post("auth/password", {"currentPassword": PASSWORD, "newPassword": "jordan@nb.example"})
    assert weak.status_code == 422
    other = world.api("importer")  # a second session for the same person
    ok = api.post("auth/password", {"currentPassword": PASSWORD, "newPassword": "harbour-light-tumbler-88"})
    assert ok.status_code == 204
    assert other.get("settings").status_code == 401  # other sessions ended
    assert api.get("settings").status_code == 200


def test_demo_sign_in_needs_the_sample_org(world):
    res = Api().post("auth/demo", {"role": "broker"})
    assert res.status_code == 404
    assert Api().get("auth/session").json()["demoSignIn"] is False
