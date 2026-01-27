"""Fixtures for API tests: two importers (tenant isolation), a broker firm engaged by the first, one user per
role, and a JSON client that carries the session cookie and the CSRF header."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.test import Client

from tariffcompass.platform.context import SESSION_ORG, SESSION_SEEN, SESSION_STARTED, SESSION_USER
from tariffcompass.platform.models import Engagement, Membership, Organisation, User

PASSWORD = "long-enough-sample-pass-2026"


class Api:
    """A test client speaking JSON with CSRF, like the web app."""

    def __init__(self, client: Client | None = None) -> None:
        self.c = client or Client(enforce_csrf_checks=True)
        self.c.get("/api/v1/auth/csrf")

    @property
    def csrf(self) -> str:
        return self.c.cookies["tc_csrf"].value

    def _send(self, method: str, path: str, body: Any = None, **extra: Any):
        url = path if path.startswith("/") else f"/api/v1/{path}"
        headers = {"HTTP_X_CSRFTOKEN": self.csrf, **extra}
        fn = getattr(self.c, method)
        if body is None:
            return fn(url, **headers)
        return fn(url, data=json.dumps(body), content_type="application/json", **headers)

    def get(self, path: str, **params: Any):
        url = path if path.startswith("/") else f"/api/v1/{path}"
        return self.c.get(url, params)

    def post(self, path: str, body: Any = None, **extra: Any):
        return self._send("post", path, {} if body is None else body, **extra)

    def patch(self, path: str, body: Any = None):
        return self._send("patch", path, body or {})

    def delete(self, path: str):
        return self._send("delete", path)

    def sign_in(self, user: User, org: Organisation | None = None) -> Api:
        s = SessionStore()
        now = time.time()
        s[SESSION_USER] = str(user.pk)
        s[SESSION_ORG] = str(org.pk) if org else None
        s[SESSION_STARTED] = now
        s[SESSION_SEEN] = now
        s.create()
        self.c.cookies["tc_session"] = s.session_key
        return self


@dataclass
class World:
    north: Organisation
    other: Organisation
    drift: Organisation
    importer: User
    compliance: User
    admin: User
    broker: User
    broker2: User
    outsider: User  # admin of the other importer

    def api(self, who: str = "compliance", org: Organisation | None = None) -> Api:
        user: User = getattr(self, who)
        if org is None:
            org = self.north if who != "outsider" else self.other
        return Api().sign_in(user, org)


def make_user(email: str, name: str, licence: str = "") -> User:
    return User.objects.create_user(email, PASSWORD, full_name=name, licence=licence)


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def fast_hasher(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def world(db, fast_hasher) -> World:
    north = Organisation.objects.create(
        name="Northbound Goods Co.", slug="nb-test", locations=["Vancouver, BC", "Seattle, WA"]
    )
    other = Organisation.objects.create(name="Harbourline Home", slug="harbourline-test")
    drift = Organisation.objects.create(name="Driftwood Customs Brokers", slug="drift-test", kind="broker")
    eng = Engagement.objects.create(
        broker_org=drift, importer_org=north, countries=["US", "CA"], started_on=date(2025, 3, 1)
    )
    importer = make_user("jordan@nb.example", "Jordan Tse")
    compliance = make_user("maya@nb.example", "Maya Lindqvist")
    admin = make_user("priscilla@nb.example", "Priscilla Mensah")
    broker = make_user("dana@dw.example", "Dana Whitlock", "Licensed customs broker (US), licence 34812")
    broker2 = make_user("rafael@dw.example", "Rafael Ouellet", "Licensed customs broker (Canada)")
    outsider = make_user("ola@hh.example", "Ola Berg")
    for u, role in ((importer, "importer"), (compliance, "compliance"), (admin, "admin")):
        Membership.objects.create(org=north, user=u, role=role)
    for u in (broker, broker2):
        Membership.objects.create(org=drift, user=u, role="broker")
        Membership.objects.create(org=north, user=u, role="broker", engagement=eng)
    Membership.objects.create(org=other, user=outsider, role="admin")
    Membership.objects.create(org=other, user=make_user("kim@hh.example", "Kim Park"), role="compliance")
    return World(north, other, drift, importer, compliance, admin, broker, broker2, outsider)


@pytest.fixture
def fake_core(monkeypatch, settings, tmp_path):
    """The deterministic core fakes (tariffcompass.fakes), with uploads and exports in a temp folder."""
    from tariffcompass import services
    from tariffcompass.catalog import rulings

    monkeypatch.setenv("CORE_BACKEND", "fake")
    settings.MEDIA_ROOT = tmp_path / "uploads"
    services.reset()
    rulings.clear()
    yield
    services.reset()
    rulings.clear()


def make_product(
    org: Organisation,
    sku: str = "NB-KT-0412",
    *,
    us: str = "9617001000",
    ca: str = "9617000000",
    title: str = "20 oz vacuum tumbler",
    made_in: str = "CN",
    material: str = "stainless steel",
    value: str = "12500.00",
    category: str = "kitchen",
):
    from tariffcompass.catalog.models import Product

    return Product.objects.create(
        org=org,
        sku=sku,
        title=title,
        category=category,
        made_in=made_in,
        into=["US", "CA"],
        listing_text="20 oz double-wall stainless steel tumbler, vacuum insulated, sliding lid.",
        material=material,
        shipment={"value": value, "currency": "USD", "quantity": 1000, "transport": "ocean"},
        us_code="",
        ca_code="",
    )


@pytest.fixture
def catalogue(world, fake_core):
    """A proposed tumbler in Northbound (v1) and a product in the other importer."""
    from tariffcompass.catalog import binder

    p = make_product(world.north)
    binder.append(
        p,
        "proposed",
        actor=world.importer,
        actor_role="importer",
        us_code="9617001000",
        ca_code="9617000000",
        rulings_relied=["NY N321134"],
        deciding_fact={
            "key": "between_walls",
            "label": "Between the walls",
            "value": "A vacuum",
            "source_note": "read from 'insulated'",
        },
    )
    foreign = make_product(world.other, "HH-0001", title="Foreign kettle")
    return {"tumbler": p, "foreign": foreign}
