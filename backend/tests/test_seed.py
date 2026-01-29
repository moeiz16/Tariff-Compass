"""The sample seed: counts, the story it tells, and the rules it must never break (real rulings only, real tariff
lines only, an intact activity chain, dates inside the demo window, legal status left open).

These run against the real classification core (search engine, program, duty engine) where it is installed,
and fall back to the deterministic fakes otherwise, as `services` does."""

from __future__ import annotations

import re
from datetime import date, datetime

import pytest
from django.core.management import call_command

from tariffcompass import clock, services
from tariffcompass.catalog import rulings
from tariffcompass.catalog.models import Answer, BinderVersion, Product
from tariffcompass.lab import reports
from tariffcompass.lab.models import TrainingRound
from tariffcompass.platform import audit
from tariffcompass.platform.models import AuditEvent, Organisation
from tariffcompass.review.models import Decision, ReviewItem, TrainingExample
from tariffcompass.seed import build
from tariffcompass.seed.catalog import PRODUCTS, all_ruling_ids
from tariffcompass.seed.people import DEMO_PEOPLE
from tariffcompass.watch.models import Change
from tests.platform_fixtures import Api

pytestmark = pytest.mark.django_db
RULING_ID = re.compile(r"\b(?:NY|HQ) [A-Z]?\d{5,6}\b")


@pytest.fixture(scope="module")
def seeded(django_db_setup, django_db_blocker, tmp_path_factory):
    from django.conf import settings

    media = settings.MEDIA_ROOT
    settings.MEDIA_ROOT = tmp_path_factory.mktemp("seed") / "uploads"
    services.reset()
    rulings.clear()
    with django_db_blocker.unblock():
        result = build.build()
    yield result
    with django_db_blocker.unblock():
        call_command("flush", interactive=False, verbosity=0)
    settings.MEDIA_ROOT = media


def north() -> Organisation:
    return Organisation.objects.get(slug="northbound-goods")


def test_counts(seeded):
    assert 115 <= seeded["products"] <= 125
    assert seeded["docket"] == 15
    assert seeded["corrections_waiting"] == 23
    org = north()
    assert Product.objects.filter(org=org).count() == len(PRODUCTS)
    assert {p.category for p in Product.objects.filter(org=org)} == {
        "kitchen",
        "electronics",
        "apparel",
        "outdoor",
        "bags",
    }
    assert {p.made_in for p in Product.objects.filter(org=org)} >= {"CN", "VN", "MX", "DE", "IT", "PT"}


def test_docket_story(seeded):
    open_items = ReviewItem.objects.filter(org=north(), status__in=("waiting", "asked", "answered"))
    kinds = {i.kind for i in open_items}
    assert kinds == {"unsure", "differs", "ruling_changed", "always_review", "requested"}
    assert open_items.filter(into="CA").count() >= 2 and open_items.filter(status="asked").count() == 1
    ages = [(clock.today() - clock.local(i.created_at).date()).days for i in open_items]
    assert min(ages) == 0 and max(ages) <= 6
    changed = open_items.get(kind="ruling_changed")
    assert changed.ruling_change["by_id"] == "HQ H289250"
    relied = changed.product.versions.filter(kind="approved").first().rulings_relied
    assert relied == ["NY N284187"]


def test_this_weeks_history(seeded):
    d = Api().sign_in(*_dana()).get("review").json()
    assert d["week"] == {"approved": 31, "corrected": 9, "questions": 4}
    assert d["nextRound"]["correctionsWaiting"] == 23


def _dana():
    from tariffcompass.platform.models import User

    return User.objects.get(email=DEMO_PEOPLE["broker"]["email"]), north()


def test_corrections_include_heading_changes_and_lessons(seeded):
    corrections = Decision.objects.filter(org=north(), action="correct")
    heading_changes = [d for d in corrections if d.item.proposed_us[:4] != d.final_us[:4]]
    assert len(heading_changes) >= 2
    assert all(d.lesson and d.reason for d in corrections)
    assert TrainingExample.objects.filter(org=north()).count() == corrections.count()
    assert set(TrainingExample.objects.filter(org=north()).values_list("used_in_round", flat=True)) <= {None, 7}


def test_hero_binder(seeded):
    p = Product.objects.get(org=north(), sku="NB-KT-0412")
    kinds = list(p.versions.order_by("n").values_list("kind", flat=True))
    assert kinds == ["proposed", "question_answered", "approved", "re_approved"]
    v1 = p.versions.get(n=1)
    assert v1.rulings_relied[:2] == ["NY N321134", "HQ H303684"]
    assert clock.local(v1.at).date() == date(2026, 1, 12) and p.us_code == "9617001000"
    assert p.versions.get(n=4).decided_by.full_name == "Dana Whitlock"
    assert p.entries.count() == 3 and {e.country for e in p.entries.all()} == {"US", "CA"}
    assert p.evidence.count() == 3


def _cited_ids() -> set[str]:
    ids: set[str] = set()
    for v in BinderVersion.objects.all():
        ids |= set(v.rulings_relied or [])
    ids |= {d.ruling_relied for d in Decision.objects.exclude(ruling_relied="")}
    for a in Answer.objects.all():
        ids |= {r["id"] for r in a.payload.get("rulings", [])}
    for i in ReviewItem.objects.exclude(ruling_change=None):
        ids.add(i.ruling_change["by_id"])
    ids |= {c.ruling_id for c in Change.objects.exclude(ruling_id="")}
    for text in (
        list(BinderVersion.objects.values_list("why", flat=True))
        + list(ReviewItem.objects.values_list("detail", flat=True))
        + list(Change.objects.values_list("body", flat=True))
        + list(Change.objects.values_list("headline", flat=True))
    ):
        ids |= set(RULING_ID.findall(text or ""))
    return ids


def test_no_invented_rulings(seeded):
    retr = services.retriever()
    cited = _cited_ids() | all_ruling_ids() | {"NY N284187", "HQ H289250"}
    if type(retr).__name__ == "FakeRetriever":
        pytest.skip("the real search engine isn't installed; the fake knows only three rulings")
    missing = sorted(r for r in cited if retr.ruling(r) is None)
    assert missing == []
    noted = sorted(r for r in cited if (retr.ruling(r).text or "").startswith("The letter for"))
    assert noted == []  # never cite a noted record as a letter


def test_codes_are_tariff_lines(seeded):
    retr = services.retriever()
    if type(retr).__name__ == "FakeRetriever":
        pytest.skip("the real search engine isn't installed")
    bad = [
        (p.sku, c, code)
        for p in Product.objects.filter(org=north())
        for c, code in (("US", p.us_code), ("CA", p.ca_code))
        if code and retr.tariff_line(c, code) is None
    ]
    assert bad == []


def test_activity_chain_and_dates(seeded):
    org = north()
    assert audit.verify(org).ok
    events = AuditEvent.objects.filter(org=org).order_by("id")
    assert events.count() > 200
    now = clock.now()
    window = datetime(2025, 11, 1, tzinfo=now.tzinfo)
    assert all(window <= e.created_at <= now for e in events)
    assert BinderVersion.objects.filter(at__gt=now).count() == 0


def test_demo_sign_in_for_every_role(seeded):
    api = Api()
    session = api.get("auth/session").json()
    assert session["demoSignIn"] and {p["role"] for p in session["demoPeople"]} == set(DEMO_PEOPLE)
    for role, person in DEMO_PEOPLE.items():
        me = Api().post("auth/demo", {"role": role}).json()
        assert me["user"]["fullName"] == person["full_name"]
        assert me["activeOrg"]["name"] == "Northbound Goods Co."
    dana = Api().post("auth/demo", {"role": "broker"}).json()
    assert any(o["viaBroker"] == "Driftwood Customs Brokers" for o in dana["orgs"])


def test_ieepa_layers_stay_pending(seeded):
    api = Api()
    api.post("auth/demo", {"role": "compliance"})
    layers = api.get("duty-layers", country="US").json()
    if not layers:
        pytest.skip("the real duty engine isn't installed")
    ieepa = [ly for ly in layers if ly["id"].startswith("US-IEEPA")]
    assert ieepa and all(ly["legalStatusOpen"] for ly in ieepa)
    watch = api.get("watch").json()
    assert watch["items"][0]["dateLabel"] == "PENDING"


def test_lab_rounds_come_only_from_committed_reports(seeded):
    made = set(TrainingRound.objects.filter(org=north()).values_list("n", flat=True))
    committed = {n for n in (4, 5, 6, 7) if reports.committed(n) is not None}
    assert made == committed
    for r in TrainingRound.objects.filter(org=north()):
        assert r.report == reports.committed(r.n)
    if 7 in made:
        seven = TrainingRound.objects.get(org=north(), n=7)
        assert seven.status == "waiting_signoff"
        assert [s.user.full_name for s in seven.signoffs.all()] == ["Maya Lindqvist"]


def test_seed_is_idempotent(seeded, capsys):
    call_command("seed")
    assert "already loaded" in capsys.readouterr().out
    assert Organisation.objects.filter(slug="northbound-goods").count() == 1


def test_round_corrections_match_the_seeded_examples(seeded):
    from tariffcompass.seed.plan import corrections_for_round

    seeded_round7 = {e.payload["id"]: e.payload for e in TrainingExample.objects.filter(used_in_round=7)}
    planned = {c["id"]: c for c in corrections_for_round(7)}
    assert seeded_round7 == planned and len(planned) == 8
    assert all(str(e.pk) == e.payload["id"] for e in TrainingExample.objects.filter(signal="correction"))
