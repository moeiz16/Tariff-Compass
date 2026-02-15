"""Training rounds in plain words, and the two-person sign-off (API_CONTRACT §1.12).

Every figure comes from the round's stored report (produced by the classification core on rulings the
classifier hasn't seen). A round goes live only when it passed its five checks and two different people with
`lab:sign` have signed; the live round it replaces is retired and stays one step away. Approved answers keep
their codes and nothing is re-filed.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from tariffcompass import clock, services
from tariffcompass.api import labels
from tariffcompass.api.routers.common import day_month
from tariffcompass.core.errors import Problem
from tariffcompass.lab.models import SignOff, TrainingRound
from tariffcompass.platform import roles
from tariffcompass.platform.context import Ctx
from tariffcompass.platform.models import Organisation
from tariffcompass.review.models import TrainingExample

LEVELS = (("chapter", "Chapter"), ("heading", "Heading"), ("subheading", "Subheading"), ("full_code", "Full code"))
REQUIRED = 2


def pct(x: float | None) -> float | None:
    return None if x is None else round(float(x) * 100, 1)


def _depth(report: dict[str, Any], system: str) -> dict[str, Any] | None:
    return next((d for d in report.get("by_depth", []) if d["system"] == system), None)


def status_label(r: TrainingRound) -> str:
    if r.status == "live" and r.live_from:
        return f"Live since {day_month(r.live_from)}"
    return labels.ROUND_STATUSES.get(r.status, r.status)


def strip(r: TrainingRound) -> dict[str, Any]:
    return {"n": r.n, "status": r.status, "status_label": status_label(r), "trained_on": r.trained_on, "note": r.note}


def lab_out(org: Organisation) -> dict[str, Any]:
    from tariffcompass.lab.live import signed_live

    rounds = list(TrainingRound.objects.filter(org=org).order_by("n"))
    live_round = signed_live(org)
    candidate = next((r.n for r in reversed(rounds) if r.status in ("waiting_signoff", "training")), None)
    waiting = TrainingExample.objects.filter(org=org, used_in_round__isnull=True).count()
    return {
        "rounds": [strip(r) for r in rounds],
        "live": live_round.n if live_round else None,
        "candidate": candidate,
        "corrections_waiting": waiting,
        "in_use": in_use(rounds, live_round),
    }


def in_use(rounds: list[TrainingRound], live: TrainingRound | None) -> dict[str, Any]:
    """What answers today: the signed-off live round, or word matching (the classical first stage)."""
    if live is not None:
        cand = _depth(live.report or {}, "optimised") or {}
        names = " and ".join(s.user.full_name for s in live.signoffs.select_related("user").order_by("signed_at"))
        full, heading = pct(cand.get("full_code")), pct(cand.get("heading"))
        return {
            "kind": "round",
            "round": live.n,
            "label": f"Round {live.n}",
            "full_code": full,
            "heading": heading,
            "sentence": f"In use: round {live.n}, signed off by {names}. It gets the full ten-digit code right "
            f"{round(full or 0)} in 100 rulings it hasn't seen.",
        }
    latest = next((r for r in reversed(rounds) if r.report), None)
    words = _depth(latest.report or {}, "word_matching") if latest else None
    full = pct(words["full_code"]) if words else None
    heading = pct(words["heading"]) if words else None
    sentence = "In use: word matching. No training round has passed its five checks and been signed off yet."
    if words:
        sentence = (
            f"In use: word matching, which gets the full ten-digit code right {round(full or 0)} in 100 "
            f"rulings it hasn't seen ({round(heading or 0)} in 100 at the heading). No training round has "
            "passed its five checks and been signed off yet, so every round below is a challenger."
        )
    sentence += _in_use_word_note()
    return {
        "kind": "word_matching",
        "round": None,
        "label": "Word matching",
        "full_code": full,
        "heading": heading,
        "sentence": sentence,
    }


def _in_use_word_note() -> str:
    """When word matching's confidence word can't clear its bar on validation, say so: every answer goes to a broker."""
    import json

    from tariffcompass.classify.recalibrate import report_path

    try:
        rep = json.loads(report_path().read_text())
    except (OSError, ValueError):
        return ""
    if float(rep.get("threshold", 0)) <= 1.0:
        return ""
    return (
        " Its confidence word can't yet show “Strong match” right at least 90 times in 100 with a safe margin, so "
        "every answer it gives says “Needs a broker”."
    )


def get_round(org: Organisation, n: int) -> TrainingRound:
    r = TrainingRound.objects.filter(org=org, n=n).first()
    if r is None:
        raise Problem(404, "not_found", "There's no training round with that number.")
    return r


def _confidence(report: dict[str, Any]) -> dict[str, Any]:
    cal = report.get("calibration") or {}
    strong = cal.get("strong") or {}
    broker = cal.get("broker") or {}
    s_said, s_right = int(strong.get("said", 0)), int(strong.get("right", 0))
    b_said, b_wrong = int(broker.get("said", 0)), int(broker.get("firstGuessWrong", 0))
    s100 = round(100 * s_right / s_said) if s_said else 0
    b100 = round(100 * b_wrong / b_said) if b_said else 0
    return {
        "strong": {
            "said": s_said,
            "right": s_right,
            "per100": s100,
            "sentence": f"When it said Strong match ({s_said:,} times): right {s100} times in 100",
        },
        "broker": {
            "said": b_said,
            "right": b_wrong,
            "per100": b100,
            "sentence": f"When it said Needs a broker ({b_said:,} times): its first guess was wrong "
            f"{b100} times in 100",
        },
    }


def _chapters(report: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for c in report.get("by_chapter", []):
        before, after = pct(c.get("before")) or 0.0, pct(c.get("after")) or 0.0
        change = round(after - before, 1)
        label = f"▲ {abs(change):g}" if change > 0 else (f"▼ {abs(change):g}" if change < 0 else "= 0")
        out.append(
            {
                "chapter": str(c.get("chapter", "")),
                "title": c.get("title", ""),
                "tested": int(c.get("tested", 0)),
                "before": before,
                "after": after,
                "change": change,
                "change_label": label,
                "new_rulings": int(c.get("newRulings", 0)),
                "moving": bool(c.get("moving", False)),
            }
        )
    return out


def _drift(report: dict[str, Any]) -> dict[str, Any]:
    """Scalars only on the wire: a list of chapters reads "61, 84, 95"."""
    out: dict[str, Any] = {}
    for k, v in (report.get("drift_psi") or {}).items():
        out[k] = ", ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else v
    return out


def _checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "key": g.get("key", ""),
            "label": g.get("label", g.get("plain", "")),
            "passed": bool(g.get("passed")),
            "value": str(g.get("value", "")),
            "threshold": str(g.get("threshold", "")),
        }
        for g in report.get("gates", [])
    ]


def checks_pass(r: TrainingRound) -> bool:
    checks = _checks(r.report or {})
    return bool(checks) and all(c["passed"] for c in checks)


def _lede(r: TrainingRound, report: dict[str, Any]) -> str:
    cand, live, words = _depth(report, "optimised"), _depth(report, "live"), _depth(report, "word_matching")
    if cand is None:
        return f"Round {r.n} has no results yet."
    text = (
        f"Round {r.n} gets the full ten-digit code right for {round(cand['full_code'] * 100)} in 100 rulings it "
        "hasn't seen"
    )
    if live is not None:
        text += f", {'up' if cand['full_code'] >= live['full_code'] else 'down'} from {round(live['full_code'] * 100)}"
    text += "."
    if words is not None:
        text += f" Word matching alone gets {round(words['full_code'] * 100)}."
    return text


def round_out(r: TrainingRound, ctx: Ctx | None) -> dict[str, Any]:
    report = r.report or {}
    cand, live = _depth(report, "optimised") or {}, _depth(report, "live")
    words, unopt = _depth(report, "word_matching") or {}, _depth(report, "unoptimised")
    window = report.get("test_window") or [None, None]
    sigs = list(r.signoffs.select_related("user").order_by("signed_at"))
    signed_ids = {s.user_id for s in sigs}
    can_sign = bool(
        ctx
        and ctx.can("lab:sign")
        and r.status == "waiting_signoff"
        and ctx.user.pk not in signed_ids
        and checks_pass(r)
    )
    prev_live = (
        TrainingRound.objects.filter(org=r.org, status="live").exclude(pk=r.pk).values_list("n", flat=True).first()
    )
    note = (
        f"Round {prev_live} stays one step away. " if prev_live else ""
    ) + "Answers already approved keep their codes; nothing is re-filed."
    return {
        "n": r.n,
        "status": r.status,
        "status_label": status_label(r),
        "trained_on": r.trained_on,
        "test_count": int(cand.get("n", 0)),
        "test_from": window[0] or clock.today(),
        "test_to": window[1] or clock.today(),
        "snapshot": (report.get("data_snapshot") or r.data_snapshot or "")[:12],
        "rerun_note": f"Same rulings, seed {report.get('seed', r.seed)} and budget give the same round.",
        "lede": _lede(r, report),
        "by_depth": [
            {
                "level": key,
                "level_label": label,
                "word_matching": pct(words.get(key)) or 0.0,
                "live": pct(live[key]) if live else None,
                "candidate": pct(cand.get(key)) or 0.0,
                "unoptimised": pct(unopt[key]) if unopt else None,
            }
            for key, label in LEVELS
        ],
        "confidence": _confidence(report),
        "by_chapter": _chapters(report),
        "learned": list(report.get("learned", [])),
        "drift": _drift(report),
        "checks": _checks(report),
        "sign_off": {
            "required": REQUIRED,
            "signatures": [
                {
                    "name": s.user.full_name,
                    "role": s.role,
                    "role_label": roles.ROLE_LABELS.get(s.role, ""),
                    "signed_at": s.signed_at,
                    "statement": s.statement,
                }
                for s in sigs
            ],
            "can_sign": can_sign,
            "will_promote": can_sign and len(sigs) == REQUIRED - 1,
            "note": note,
        },
        "run_by": report.get("lm_label") or r.lm_label,
    }


def sign(ctx: Ctx, r: TrainingRound, statement: str) -> TrainingRound:
    if r.status != "waiting_signoff":
        raise Problem(409, "conflict", f"Round {r.n} isn't waiting for sign-off.")
    if not checks_pass(r):
        raise Problem(409, "gates_failed", f"Round {r.n} didn't pass its five checks, so it can't be made live.")
    if r.signoffs.filter(user=ctx.user).exists():
        raise Problem(409, "same_person", "The second signature must come from someone else.")
    if " ".join(statement.split()).lower() != " ".join(ctx.user.full_name.split()).lower():
        raise Problem(
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=[{"field": "statement", "message": "Type your full name to sign."}],
        )
    with transaction.atomic():
        try:
            SignOff.objects.create(
                round=r, user=ctx.user, role=ctx.role, statement=statement.strip(), checks=_checks(r.report or {})
            )
        except IntegrityError as exc:
            raise Problem(409, "same_person", "The second signature must come from someone else.") from exc
        count = r.signoffs.values("user").distinct().count()
        ctx.audit(
            "lab.signed",
            f"{ctx.user.full_name} signed training round {r.n} ({count} of {REQUIRED})",
            target_type="round",
            target_id=str(r.n),
            details={"round": r.n, "signatures": count},
        )
        if count >= REQUIRED:
            promote(ctx, r)
    r.refresh_from_db()
    return r


def promote(ctx: Ctx, r: TrainingRound) -> None:
    now = clock.now()
    previous = list(TrainingRound.objects.filter(org=r.org, status="live").exclude(pk=r.pk))
    for p in previous:
        p.status, p.live_to = "retired", now
        p.save(update_fields=["status", "live_to"])
    r.status, r.live_from = "live", now
    r.save(update_fields=["status", "live_from"])
    names = " and ".join(s.user.full_name for s in r.signoffs.select_related("user").order_by("signed_at"))
    ctx.audit(
        "lab.made_live",
        f"Training round {r.n} went live, signed by {names}" + (f"; round {previous[0].n} retired" if previous else ""),
        target_type="round",
        target_id=str(r.n),
        details={"round": r.n, "retired": [p.n for p in previous]},
    )
    transaction.on_commit(lambda: _go_live(r.n))


def _go_live(n: int) -> None:
    """Round `n` now answers: drop the core's cached instances so it re-reads the signed-off live round."""
    services.reset()  # the core re-reads lab.live.live_round() on its next answer
