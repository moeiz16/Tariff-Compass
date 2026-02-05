"""Watch (dated changes, affected products, scans), home and scope counts, and the Lab (rounds, the five checks
and the two-person sign-off)."""

from __future__ import annotations

from datetime import date

import pytest

from tariffcompass.contracts import DepthAccuracy, RoundReport
from tariffcompass.lab import reports
from tariffcompass.lab.models import TrainingRound
from tariffcompass.platform import audit
from tariffcompass.platform.models import AuditEvent
from tariffcompass.review.models import TrainingExample
from tariffcompass.watch.models import AffectedProduct, Change
from tariffcompass.watch.scan import definitions, ensure_changes

pytestmark = pytest.mark.django_db


def report(n: int, *, full: float = 0.71, live: float | None = 0.58, passed: bool = True) -> dict:
    depth = [
        DepthAccuracy("word_matching", 0.9, 0.7, 0.55, 0.44, 1240),
        DepthAccuracy("unoptimised", 0.92, 0.75, 0.6, 0.5, 1240),
        DepthAccuracy("optimised", 0.95, 0.86, 0.78, full, 1240),
    ]
    if live is not None:
        depth.append(DepthAccuracy("live", 0.94, 0.8, 0.7, live, 1240))
    keys = ("full_code_vs_live", "heading_vs_live", "chapter_regression", "strong_right", "citation_precision")
    gates = tuple(
        {
            "key": k,
            "label": k.replace("_", " "),
            "passed": passed or k != "full_code_vs_live",
            "value": "0.71",
            "threshold": "0.58",
        }
        for k in keys
    )
    return reports.dump(
        RoundReport(
            round_n=n,
            data_snapshot="ab" * 32,
            test_window=(date(2025, 3, 1), date(2025, 8, 1)),
            by_depth=tuple(depth),
            by_chapter=(
                {
                    "chapter": "96",
                    "title": "Miscellaneous",
                    "tested": 40,
                    "before": 0.6,
                    "after": 0.66,
                    "newRulings": 30,
                    "moving": True,
                },
            ),
            calibration={"strong": {"said": 812, "right": 788}, "broker": {"said": 428, "firstGuessWrong": 301}},
            citation_precision=0.97,
            latency_ms={},
            drift_psi={"newRulings": 212, "mostMoved": "85", "psi": 0.14, "sentence": "Chapter 85 moved most."},
            learned=("“Double-wall” alone doesn't mean vacuum.",),
            gates=gates,
            program_path="",
            lm_label="offline simulator",
            reflection_lm_label="offline simulator",
            seed=7,
        )
    )


@pytest.fixture
def rounds(world):
    TrainingRound.objects.create(
        org=world.north, n=6, status="live", report=report(6, full=0.58, live=None), trained_on=date(2026, 1, 28)
    )
    seven = TrainingRound.objects.create(
        org=world.north, n=7, status="waiting_signoff", report=report(7), trained_on=date(2026, 2, 19)
    )
    return seven


def test_report_round_trip():
    data = report(7)
    assert reports.dump(reports.load(data)) == data


def test_lab_overview_and_round_in_plain_words(world, rounds):
    lab = world.api("compliance").get("lab").json()
    assert lab["live"] == 6 and lab["candidate"] == 7 and [r["n"] for r in lab["rounds"]] == [6, 7]
    r = world.api("compliance").get("lab/rounds/7").json()
    assert r["lede"] == (
        "Round 7 gets the full ten-digit code right for 71 in 100 rulings it hasn't seen, up from 58. "
        "Word matching alone gets 44."
    )
    full = next(d for d in r["byDepth"] if d["level"] == "full_code")
    assert full == {
        "level": "full_code",
        "levelLabel": "Full code",
        "wordMatching": 44.0,
        "live": 58.0,
        "candidate": 71.0,
        "unoptimised": 50.0,
    }
    assert (
        r["confidence"]["strong"]["per100"] == 97 and "right 97 times in 100" in r["confidence"]["strong"]["sentence"]
    )
    assert r["byChapter"][0]["changeLabel"] == "▲ 6" and r["drift"]["mostMoved"] == "85"
    assert len(r["checks"]) == 5 and r["runBy"] == "offline simulator"
    assert r["signOff"]["canSign"] and not r["signOff"]["willPromote"] and "Round 6 stays" in r["signOff"]["note"]
    assert world.api("outsider").get("lab/rounds/7").status_code == 404  # another organisation's round
    assert world.api("importer").get("lab").status_code == 403
    assert world.api("compliance").get("lab/rounds/99").status_code == 404


def test_two_different_people_make_a_round_live(world, rounds):
    maya, dana = world.api("compliance"), world.api("broker")
    first = maya.post("lab/rounds/7/sign", {"statement": "Maya Lindqvist"}).json()
    assert first["status"] == "waiting_signoff" and len(first["signOff"]["signatures"]) == 1
    again = maya.post("lab/rounds/7/sign", {"statement": "Maya Lindqvist"})
    assert again.status_code == 409 and again.json()["code"] == "same_person"
    view = dana.get("lab/rounds/7").json()
    assert view["signOff"]["canSign"] and view["signOff"]["willPromote"]
    wrong_name = dana.post("lab/rounds/7/sign", {"statement": "Someone Else"})
    assert wrong_name.status_code == 422
    live = dana.post("lab/rounds/7/sign", {"statement": "dana whitlock"}).json()
    assert live["status"] == "live" and live["statusLabel"].startswith("Live since")
    assert TrainingRound.objects.get(org=world.north, n=6).status == "retired"
    actions = list(AuditEvent.objects.filter(org=world.north).values_list("action", flat=True))
    assert actions.count("lab.signed") == 2 and "lab.made_live" in actions
    assert audit.verify(world.north).ok


def test_importers_cannot_sign_and_failed_checks_block(world, rounds):
    assert world.api("importer").post("lab/rounds/7/sign", {"statement": "Jordan Tse"}).status_code == 403
    TrainingRound.objects.filter(n=7).update(report=report(7, passed=False))
    assert world.api("compliance").get("lab/rounds/7").json()["signOff"]["canSign"] is False
    res = world.api("compliance").post("lab/rounds/7/sign", {"statement": "Maya Lindqvist"})
    assert res.status_code == 409 and res.json()["code"] == "gates_failed"
    TrainingRound.objects.filter(n=7).update(status="live")
    assert world.api("compliance").post("lab/rounds/7/sign", {"statement": "Maya Lindqvist"}).status_code == 409


def test_start_round_runs_the_optimiser_and_uses_corrections(world, fake_core, rounds):
    TrainingRound.objects.filter(n=7).update(status="retired")
    TrainingExample.objects.create(org=world.north, payload={"us_code": "7323930080"}, lesson="x")
    assert world.api("broker").post("lab/rounds", {"note": "x"}).status_code == 403
    res = world.api("compliance").post("lab/rounds", {"note": "After this week's corrections"})
    assert res.status_code == 202
    job = world.api("compliance").get(res.json()["statusUrl"]).json()
    assert job["status"] == "succeeded" and job["result"]["round"] == 8
    r8 = TrainingRound.objects.get(org=world.north, n=8)
    assert r8.status == "waiting_signoff" and r8.report["round_n"] == 8 and r8.corrections_used == 1
    assert TrainingExample.objects.get().used_in_round == 8
    TrainingRound.objects.filter(n=8).update(status="training")
    busy = world.api("compliance").post("lab/rounds", {"note": ""})
    assert busy.status_code == 409


def test_watch_definitions_are_real_dated_events():
    for d in definitions():
        assert d["date"] is None or d["date"] <= date(2026, 2, 19)
        assert d["source_url"].startswith("https://")
    pending = next(d for d in definitions() if d["kind"] == "legal_pending")
    assert pending["date_note"] == "argued 5 Nov 2025"
    text = " ".join([pending["headline"], pending["body"], *pending["knows"], *pending["unknowns"]]).lower()
    for outcome in ("struck down", "upheld", "ruled that", "unlawful", "invalidated"):
        assert outcome not in text


def test_watch_bulletin_affected_and_tenancy(world, catalogue):
    ensure_changes()
    ch = Change.objects.get(key="scotus-ieepa")
    AffectedProduct.objects.create(
        org=world.north,
        change=ch,
        product=catalogue["tumbler"],
        effect="Duty would fall from $3,458.93 to $958.93 if those duties end",
        duty_before="3458.93",
        duty_after="958.93",
    )
    w = world.api("importer").get("watch").json()
    first = w["items"][0]
    assert first["dateLabel"] == "PENDING" and first["kindLabel"] == "Pending decision" and first["affectedCount"] == 1
    assert first["affected"][0]["dutyBefore"]["amount"] == "3458.93" and len(w["checks"]) == 4
    assert [i["date"] for i in w["items"][1:]] == sorted([i["date"] for i in w["items"][1:]], reverse=True)
    assert world.api("outsider").get("watch").json()["items"][0]["affectedCount"] == 0
    one = world.api("importer").get("watch/scotus-ieepa").json()
    assert one["affected"][0]["sku"] == "NB-KT-0412"
    assert world.api("importer").get("watch/nope").status_code == 404
    home = world.api("importer").get("home").json()
    assert home["dateLine"].startswith("Thursday 19 February 2026") and home["changes"][0]["affectedCount"] == 1


def test_watch_scan_job_is_audited(world, catalogue):
    assert world.api("importer").post("watch/scan").status_code == 403
    res = world.api("compliance").post("watch/scan")
    assert res.status_code == 202
    job = world.api("compliance").get(res.json()["statusUrl"]).json()
    assert job["status"] == "succeeded" and job["result"]["products"] == 1
    assert AuditEvent.objects.filter(action="watch.scanned", org=world.north).exists()
    rev3 = AffectedProduct.objects.get(change__key="hts-2026-rev3")
    assert rev3.recheck == "unchanged" and "9617.00.10.00" in rev3.effect


def test_scope_counts(world, catalogue):
    counts = world.api("importer").get("scopes/counts").json()
    assert counts["products"] == 1 and counts["review"] == 0 and counts["rulings"] >= 1
    assert world.api("importer").get("scopes/counts", q="zzzz").json()["products"] == 0


def test_promotion_tells_the_core_which_round_is_live(world, rounds, monkeypatch, django_capture_on_commit_callbacks):
    import tariffcompass.classify.program as program

    seen: list[int | None] = []
    monkeypatch.setattr(program, "set_live", lambda n: seen.append(n))
    world.api("compliance").post("lab/rounds/7/sign", {"statement": "Maya Lindqvist"})
    with django_capture_on_commit_callbacks(execute=True):
        world.api("broker").post("lab/rounds/7/sign", {"statement": "Dana Whitlock"})
    assert seen == [7]
