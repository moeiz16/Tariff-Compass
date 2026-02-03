"""Landed cost from dated duty layers (duties/data/layers.json): no rate without a source and an effective date.

`layers.json` is the record of each layer (authority, Chapter 99 numbers, scope, legal status, sources);
`rules.json` restates the scope as data the engine can apply (which lines are on which list, which rate held over
which dates). The tariff's own rates (MFN, preferences) come from the schedules (HTSUS 2026 Revision 3, Customs
Tariff T2026).

US stacking: MFN (or the USMCA preference) + Section 301 + Section 232 (on the metal content for derivatives) +
IEEPA duties (fentanyl / reciprocal / Mexico / Canada, with their exclusions: the 232 metal content leaves the
reciprocal duty, USMCA goods leave the Mexico and Canada duties, 232 goods leave the Mexico and Canada duties)
+ MPF + HMF (ocean). They add on the same customs value; they don't compound. Canada: MFN or the preferential
treatment (MXT, CEUT, CPTPT) + any surtax order + GST 5% on value plus duties and surtaxes. Every layer that does
not apply is listed with why (e.g. de minimis suspended 29 Aug 2025). Each line is rounded to the cent,
half up, and totals are sums of rounded lines.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from pathlib import Path

from django.conf import settings

from tariffcompass import clock
from tariffcompass.contracts import (
    Country,
    DutyLayer,
    LandedCost,
    LandedCostQuery,
    LayerLine,
    NotApplied,
    OriginQuestion,
)

CENT = Decimal("0.01")
ZERO = Decimal("0")
VERSION = "duties-2026-02-19-1"
PENDING = "Pending at the Supreme Court (argued 5 Nov 2025)"
COUNTRY_NAMES = {
    "CN": "China",
    "HK": "Hong Kong",
    "VN": "Vietnam",
    "MX": "Mexico",
    "CA": "Canada",
    "US": "the United States",
    "DE": "Germany",
    "IT": "Italy",
    "FR": "France",
    "ES": "Spain",
    "NL": "the Netherlands",
    "PT": "Portugal",
    "IN": "India",
    "TW": "Taiwan",
}
_PCT = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%\s*$")


class DutyDataError(ValueError):
    """A layer without a source or an effective date, or a rate the engine cannot read."""


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def pct(rate: Decimal) -> str:
    s = f"{(rate * 100).normalize():f}"
    return f"{s}%"


def parse_rate(text: str) -> Decimal | None:
    """'7.2%' → 0.072, 'Free' → 0; anything specific or compound (¢/kg, 'each') → None."""
    t = (text or "").strip()
    if t.lower() == "free":
        return ZERO
    m = _PCT.match(t)
    return Decimal(m.group(1)) / 100 if m else None


_SPECIFIC = re.compile(r"(\$)?\s*(\d+(?:\.\d+)?)\s*(¢)?\s*(each|/\s*[a-z0-9.]+)", re.I)
PER_ITEM = {
    "each": Decimal(1),
    "/no.": Decimal(1),
    "/doz.": Decimal(1) / 12,
    "/doz": Decimal(1) / 12,
    "/pr.": Decimal(1),
}


@dataclass(frozen=True)
class Compound:
    """A column 1 rate read into parts: '0.4¢ each + 6.1%' → ad valorem 0.061 + 0.004 USD per item."""

    ad_valorem: Decimal
    per_item: Decimal  # USD per item (each, per dozen as a twelfth)
    unmeasured: tuple[str, ...]  # specific parts that need a measure the query doesn't carry (kg, m², litres)


def parse_compound(text: str) -> Compound | None:
    t = (text or "").strip()
    simple = parse_rate(t)
    if simple is not None:
        return Compound(simple, ZERO, ())
    adv, per, unmeasured = ZERO, ZERO, []
    for part in [p.strip() for p in t.split("+")]:
        r = parse_rate(part)
        if r is not None:
            adv += r
            continue
        m = _SPECIFIC.fullmatch(part)
        if not m:
            return None
        amount = Decimal(m.group(2)) / (100 if m.group(3) else 1)
        unit = m.group(4).lower().replace(" ", "")
        if unit in PER_ITEM:
            per += amount * PER_ITEM[unit]
        else:
            unmeasured.append(part)
    return Compound(adv, per, tuple(unmeasured))


def _date(s) -> date | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


@dataclass
class _Ctx:
    q: LandedCostQuery
    as_of: date
    lines: list[LayerLine]
    not_applied: list[NotApplied]
    questions: list[OriginQuestion]

    def answer(self, key: str) -> bool | None:
        return dict(self.q.usmca_answers).get(key)


class LayeredDutyEngine:
    version = VERSION

    def __init__(self, layers_path: Path, rules_path: Path, schedules=None) -> None:
        raw = json.loads(layers_path.read_text())
        self.as_of_data = date.fromisoformat(raw["asOf"])
        self.layers: dict[str, dict] = {}
        for layer in raw["layers"]:
            if layer.get("effectiveFrom") and not layer.get("sources"):
                raise DutyDataError(f"layer {layer['id']} has no source")
            self.layers[layer["id"]] = layer
        self.rules = json.loads(rules_path.read_text())
        self._schedules = schedules
        self.snapshot = "HTSUS 2026 Revision 3 · Customs Tariff T2026 · duty layers as of 19 Feb 2026"

    @cached_property
    def schedules(self):
        if self._schedules is not None:
            return self._schedules
        from tariffcompass.search.engine import load_schedules

        return load_schedules()

    # ── the record ──────────────────────────────────────────────────────────────────────────────────────
    def layer(self, layer_id: str) -> dict:
        rec = self.layers.get(layer_id)
        if rec is None:
            raise DutyDataError(f"unknown layer {layer_id}")
        if not rec.get("effectiveFrom") or not rec.get("sources"):
            raise DutyDataError(f"layer {layer_id} lacks an effective date or a source")
        return rec

    def layers_in_force(self, country: Country, as_of: date) -> list[DutyLayer]:
        out = []
        for rec in self.layers.values():
            start = _date(rec.get("effectiveFrom"))
            if rec["country"] != country or start is None or not rec.get("sources") or start > as_of:
                continue
            end = _date(rec.get("effectiveTo"))
            if end and end < as_of:
                continue
            ch99 = tuple(rec.get("chapter99") or ())
            status = rec.get("legalStatus")
            out.append(
                DutyLayer(
                    id=rec["id"],
                    country=country,
                    kind=rec["kind"],
                    name=rec["name"],
                    authority=rec.get("legalAuthority", ""),
                    chapter99=ch99,
                    effective_from=start,
                    effective_to=end,
                    legal_status=PENDING if "IEEPA" in rec["id"] else status,
                    sources=tuple(rec["sources"]),
                )
            )
        return out

    def _not_in_force(self, ctx: _Ctx, layer_id: str, name: str) -> bool:
        """True (and a 'not applied' line) when the layer isn't in force on the query's date."""
        rec = self.layer(layer_id)
        start, end = _date(rec.get("effectiveFrom")), _date(rec.get("effectiveTo"))
        if start and ctx.as_of < start:
            ctx.not_applied.append(NotApplied(name, f"Not in force yet on this date (from {start:%-d %b %Y})."))
            return True
        if end and ctx.as_of > end:
            ctx.not_applied.append(NotApplied(name, f"No longer in force on this date (ended {end:%-d %b %Y})."))
            return True
        return False

    def _period(self, country: str, layer_id: str, as_of: date) -> dict | None:
        for p in self.rules[country.lower()]["periods"].get(layer_id, []):
            if _date(p["from"]) <= as_of and (p["to"] is None or as_of <= _date(p["to"])):  # type: ignore[operator]
                return p
        return None

    def _line(
        self,
        ctx: _Ctx,
        layer_id: str,
        name: str,
        rate_label: str,
        amount: Decimal,
        plain: str,
        *,
        chapter99: str | None = None,
        source: str | None = None,
    ) -> None:
        rec = self.layer(layer_id)
        country = rec["country"].lower()
        legal = PENDING if "IEEPA" in layer_id else None
        ctx.lines.append(
            LayerLine(
                letter=chr(ord("a") + len(ctx.lines)),
                layer_id=layer_id,
                kind=rec["kind"],
                name=name,
                rate=rate_label,
                amount=money(amount),
                plain=plain,
                source=source or self.rules[country]["sources"].get(layer_id, rec.get("legalAuthority", "")),
                source_url=rec["sources"][0],
                chapter99=chapter99,
                effective_from=_date(rec["effectiveFrom"]),  # type: ignore[arg-type]
                effective_to=_date(rec.get("effectiveTo")),
                legal_status=legal,
            )
        )

    # ── the calculation ─────────────────────────────────────────────────────────────────────────────────
    def landed_cost(self, query: LandedCostQuery) -> LandedCost:
        as_of = query.as_of or clock.today()
        q = replace(query, code=re.sub(r"\D", "", query.code), made_in=query.made_in.upper(), as_of=as_of)
        lc = self._compute(q)
        return replace(lc, what_could_change=self._what_could_change(q, lc))

    def _compute(self, q: LandedCostQuery) -> LandedCost:
        ctx = _Ctx(q, q.as_of or clock.today(), [], [], [])
        if q.country == "US":
            self._us(ctx)
        else:
            self._ca(ctx)
        duties = sum((ln.amount for ln in ctx.lines if ln.kind not in ("fee", "tax")), ZERO)
        charges = sum((ln.amount for ln in ctx.lines), ZERO)
        landed = q.customs_value + charges
        return LandedCost(
            query=q,
            lines=tuple(ctx.lines),
            not_applied=tuple(ctx.not_applied),
            charges_total=money(charges),
            landed_total=money(landed),
            per_unit=money(landed / max(q.quantity, 1)),
            effective_rate=(duties / q.customs_value).quantize(Decimal("0.0001"), ROUND_HALF_UP)
            if q.customs_value
            else ZERO,
            questions=tuple(ctx.questions),
            what_could_change=(),
            tariffs_as_of=ctx.as_of,
            snapshot=self.snapshot,
        )

    def _what_could_change(self, q: LandedCostQuery, lc: LandedCost) -> tuple[tuple[str, Decimal], ...]:
        out: list[tuple[str, Decimal]] = []
        if any(ln.legal_status for ln in lc.lines):
            ieepa = sum((ln.amount for ln in lc.lines if ln.legal_status), ZERO)
            out.append(("If the pending emergency duties end", money(lc.landed_total - ieepa)))
        alts: list[tuple[str, tuple[tuple[str, bool], ...], str]]
        if q.country == "US":
            alts = [("CN", (), "If made in China"), ("VN", (), "If made in Vietnam")]
            yes = tuple((k["key"], True) for k in self.rules["us"]["usmcaQuestions"])
            alts += [
                ("MX", yes, "If made in Mexico and it qualifies under USMCA"),
                ("MX", (), "If made in Mexico without a USMCA claim"),
            ]
        else:
            alts = [
                ("CN", (), "If made in China"),
                ("VN", (("cptpp_origin", True),), "If made in Vietnam with CPTPP origin"),
                ("MX", (("cusma_origin", True),), "If made in Mexico with CUSMA origin"),
            ]
        for origin, answers, label in alts:
            if origin == q.made_in and (origin != "MX" or bool(answers) == self._usmca_claimed(q)):
                continue
            try:
                other = self._compute(replace(q, made_in=origin, usmca_answers=answers))
            except DutyDataError:
                continue
            out.append((label, other.landed_total))
        return tuple(out)

    def _usmca_claimed(self, q: LandedCostQuery) -> bool:
        ans = dict(q.usmca_answers)
        return all(ans.get(k["key"]) is True for k in self.rules["us"]["usmcaQuestions"])

    # ── United States ───────────────────────────────────────────────────────────────────────────────────
    def _us(self, ctx: _Ctx) -> None:
        q, r = ctx.q, self.rules["us"]
        value, origin, code = q.customs_value, q.made_in, q.code
        line = self.schedules[0].line(code)
        if line is None:
            raise DutyDataError(f"{code} is not a line of the HTSUS 2026 Revision 3")
        if self.as_of_data < ctx.as_of:
            ctx.not_applied.append(
                NotApplied(
                    "Duty layers after 19 Feb 2026",
                    "The duty layers were verified as of 19 Feb 2026; later changes are not included.",
                )
            )
        usmca_country = origin in r["usmcaCountries"]
        claimed = usmca_country and self._usmca_claimed(q)
        if usmca_country:
            ans = dict(q.usmca_answers)
            ctx.questions.extend(
                OriginQuestion(k["key"], k["question"], ans.get(k["key"])) for k in r["usmcaQuestions"]
            )

        # a. normal duty (MFN), or the USMCA preference
        comp = parse_compound(line.general_rate)
        if comp is None:
            raise DutyDataError(f"{code}: column 1 rate '{line.general_rate}' could not be read")
        mfn_amount = value * comp.ad_valorem + comp.per_item * q.quantity
        mfn = (mfn_amount / value) if value else comp.ad_valorem  # the rate actually paid, for the EU floor
        for part in comp.unmeasured:
            ctx.not_applied.append(
                NotApplied(
                    f"Normal duty, specific part ({part})", "Needs the shipment's weight or measure; not included."
                )
            )
        special = line.special or ""
        if (claimed and re.search(r"\bS\+?\b", special.replace("(", " ").replace(",", " ").replace(")", " "))) or (
            claimed and mfn == 0
        ):
            ctx.not_applied.append(
                NotApplied(
                    f"Normal duty ({line.general_rate})",
                    "USMCA preference claimed: the special rate for USMCA goods is Free.",
                )
            )
            self._line(
                ctx,
                "US-USMCA-PREF",
                "USMCA preference",
                "Free",
                ZERO,
                "Originating under USMCA and claimed at entry, so no normal duty.",
                chapter99="9903.01.04" if origin == "MX" else "9903.01.14",
            )
            mfn_paid = ZERO
        else:
            self._line(
                ctx,
                "US-MFN",
                "Normal duty",
                line.general_rate if mfn_amount else "Free",
                mfn_amount,
                f"The tariff's own rate for {_fmt(code)}" + (f", on {q.quantity:,} items." if comp.per_item else "."),
                source=f"HTSUS 2026 Rev. 3, {_fmt(code[:8])}",
            )
            mfn_paid = mfn

        # b. Section 232 (steel and aluminium derivatives: on the metal content)
        metal_232 = ZERO
        hit232 = None
        for layer_id, rule in r["section232"].items():
            ch99 = next((v for p, v in rule["prefixes"].items() if code.startswith(p)), None)
            if ch99:
                hit232 = (layer_id, rule, ch99)
        if hit232 and self._not_in_force(ctx, hit232[0], "Section 232 steel and aluminium"):
            hit232 = None
            metal_232 = ZERO
        elif hit232:
            layer_id, rule, ch99 = hit232
            content = q.metal_content_value if q.metal_content_value is not None else value
            if q.metal_content_value is None:
                ctx.questions.append(
                    OriginQuestion(
                        "metal_content_value",
                        f"What is the value of the {rule['material']} content? Without it, the duty is "
                        "shown on the full value.",
                        None,
                    )
                )
            metal_232 = min(content, value)
            rate = Decimal(rule["rate"])
            self._line(
                ctx,
                layer_id,
                f"Section 232 {rule['material']} duty",
                f"{pct(rate)} of the {rule['material']} content",
                metal_232 * rate,
                f"A listed {rule['material']} derivative: the duty is charged on the value of its "
                f"{rule['material']} content (${money(metal_232):,}).",
                chapter99=ch99,
            )
        else:
            ctx.not_applied.append(
                NotApplied(
                    "Section 232 steel and aluminium",
                    f"{_fmt(code[:4])} isn't on a steel or aluminium derivative list.",
                )
            )
        non_metal = value - metal_232

        # c. Section 301 (China)
        if origin in r["chinaCountries"]:
            self._us_301(ctx, code, value)
        else:
            ctx.not_applied.append(
                NotApplied(
                    "Section 301",
                    f"Applies to products of China; this one is made in {COUNTRY_NAMES.get(origin, origin)}.",
                )
            )

        # d. IEEPA duties (legal status open)
        self._us_ieepa(ctx, origin, value, non_metal, mfn_paid, claimed, bool(hit232))

        # e. fees
        mpf = self._period("US", "US-MPF", ctx.as_of)
        if claimed:
            ctx.not_applied.append(
                NotApplied("Merchandise Processing Fee", "Goods originating under USMCA are exempt from the MPF.")
            )
        elif mpf:
            raw = value * Decimal(mpf["rate"])
            lo, hi = Decimal(mpf["min"]), Decimal(mpf["max"])
            amt = min(max(raw, lo), hi)
            bound = " (the minimum)" if raw < lo else (" (the maximum)" if raw > hi else "")
            self._line(
                ctx,
                "US-MPF",
                "Merchandise Processing Fee",
                f"{pct(Decimal(mpf['rate']))} (min ${lo}, max ${hi})",
                amt,
                f"CBP's fee on a formal entry, FY2026 rates{bound}.",
            )
        hmf = self._period("US", "US-HMF", ctx.as_of)
        if q.transport == "ocean" and hmf:
            self._line(
                ctx,
                "US-HMF",
                "Harbor Maintenance Fee",
                pct(Decimal(hmf["rate"])),
                value * Decimal(hmf["rate"]),
                "Charged on cargo unloaded from a vessel at a US port.",
            )
        else:
            ctx.not_applied.append(
                NotApplied("Harbor Maintenance Fee", f"Ocean shipments only; this one travels by {q.transport}.")
            )
        ctx.not_applied.append(
            NotApplied(
                "De minimis ($800)",
                "Suspended for every country from 29 Aug 2025 (EO 14324): duties apply whatever the value.",
            )
        )

    def _us_301(self, ctx: _Ctx, code: str, value: Decimal) -> None:
        r = self.rules["us"]
        tables = r["section301"]
        eight = code[:8]
        battery = tables["US-301-4YR-BATTERY"]
        if any(code.startswith(p) for p in battery["prefixes"]):
            p = self._period("US", "US-301-4YR-BATTERY", ctx.as_of)
            if p:
                rate = Decimal(p["rate"])
                self._line(
                    ctx,
                    "US-301-4YR-BATTERY",
                    "Section 301 duty (lithium-ion batteries)",
                    pct(rate),
                    value * rate,
                    "The four-year review raised lithium-ion batteries other than for vehicles to 25% from 1 Jan 2026.",
                    chapter99=battery["chapter99"],
                )
                return
        for exc in r["section301Exclusions"]:
            if code.startswith(exc["code"]):
                ans = ctx.answer(exc["key"])
                ctx.questions.append(OriginQuestion(exc["key"], exc["question"], ans))
                if ans is True:
                    ctx.not_applied.append(NotApplied("Section 301 duty (List 3)", exc["plain"]))
                    return
        for layer_id, label in (("US-301-L1-L3", "List 3"), ("US-301-L4A", "List 4A")):
            t = tables[layer_id]
            if eight in t["lines"]:
                if self._not_in_force(ctx, layer_id, f"Section 301 duty ({label})"):
                    return
                rate = Decimal(t["rate"])
                self._line(
                    ctx,
                    layer_id,
                    f"Section 301 duty ({label})",
                    pct(rate),
                    value * rate,
                    f"{_fmt(eight)} is on {label} of the China Section 301 action.",
                    chapter99=t["chapter99"],
                )
                return
        if eight in tables["US-301-L4B-NOT-APPLIED"]["lines"]:
            ctx.not_applied.append(
                NotApplied(
                    "Section 301 duty (List 4B)",
                    f"{_fmt(eight)} is only on List 4B, which is suspended: no duty is collected.",
                )
            )
            return
        ctx.not_applied.append(
            NotApplied(
                "Section 301 duty",
                f"{_fmt(eight)} isn't on the lists checked for this estimate; a broker should confirm "
                "against HTSUS Chapter 99, note 20.",
            )
        )

    def _us_ieepa(
        self, ctx: _Ctx, origin: str, value: Decimal, non_metal: Decimal, mfn: Decimal, claimed: bool, is_232: bool
    ) -> None:
        r = self.rules["us"]

        def emit(
            layer_id: str, name: str, base: Decimal, plain: str, rate: Decimal | None = None, label: str | None = None
        ) -> None:
            p = self._period("US", layer_id, ctx.as_of)
            if p is None:
                ctx.not_applied.append(NotApplied(name, "No verified rate for this date."))
                return
            rt = rate if rate is not None else Decimal(p["rate"])
            self._line(ctx, layer_id, name, label or pct(rt), base * rt, plain, chapter99=p.get("chapter99"))

        metal_note = " on the value outside the Section 232 metal content" if non_metal < value else ""
        if origin in r["chinaCountries"]:
            emit(
                "US-IEEPA-CN-FENTANYL",
                "Emergency duty: synthetic opioids (China)",
                value,
                "An emergency duty on products of China, cut from 20% to 10% on 10 Nov 2025.",
            )
            emit(
                "US-IEEPA-RECIP-CN",
                "Emergency duty: reciprocal (China)",
                non_metal,
                f"The reciprocal duty on products of China{metal_note}; the 34% country rate is suspended "
                "until 10 Nov 2026.",
            )
        elif origin in r["reciprocalCountryRates"]:
            spec = r["reciprocalCountryRates"][origin]
            emit(
                spec["layer"],
                f"Emergency duty: reciprocal ({COUNTRY_NAMES.get(origin, origin)})",
                non_metal,
                f"The reciprocal duty on products of {COUNTRY_NAMES.get(origin, origin)}{metal_note}.",
            )
        elif origin in r["euCountries"]:
            floor = Decimal("0.15")
            if mfn >= floor:
                ctx.not_applied.append(
                    NotApplied(
                        "Emergency duty: reciprocal (EU)",
                        f"The normal duty ({pct(mfn)}) is already at least 15%, so the EU reciprocal duty "
                        "adds nothing (9903.02.19).",
                    )
                )
            else:
                top = floor - mfn
                emit(
                    "US-IEEPA-RECIP-EU",
                    "Emergency duty: reciprocal (EU)",
                    non_metal,
                    f"Tops the normal duty up to 15% all-in for EU products{metal_note}.",
                    rate=top,
                    label=f"{pct(top)} (15% less the normal duty)",
                )
        elif origin in ("MX", "CA"):
            layer_id = "US-IEEPA-MX" if origin == "MX" else "US-IEEPA-CA"
            name = f"Emergency duty: {COUNTRY_NAMES[origin].replace('the ', '')}"
            if claimed:
                ctx.not_applied.append(NotApplied(name, "USMCA goods claimed at entry are exempt."))
            elif is_232:
                ctx.not_applied.append(
                    NotApplied(
                        name, "Goods subject to Section 232 steel or aluminium duties are not charged this duty."
                    )
                )
            else:
                emit(
                    layer_id,
                    name,
                    value,
                    f"An emergency duty on products of {COUNTRY_NAMES[origin]} that don't qualify under USMCA.",
                )
            ctx.not_applied.append(
                NotApplied(
                    "Emergency duty: reciprocal",
                    f"Products of {COUNTRY_NAMES[origin]} are not subject to the reciprocal duty.",
                )
            )
        elif origin != "US":
            emit(
                "US-IEEPA-RECIP-BASE",
                "Emergency duty: reciprocal (baseline)",
                non_metal,
                f"The 10% baseline reciprocal duty{metal_note}.",
            )

    # ── Canada ──────────────────────────────────────────────────────────────────────────────────────────
    def _ca(self, ctx: _Ctx) -> None:
        q, r = ctx.q, self.rules["ca"]
        value, origin, code = q.customs_value, q.made_in, q.code
        sched = self.schedules[1]
        line = sched.line(code) or sched.line(code[:8])
        if line is None:
            raise DutyDataError(f"{code} is not a tariff item of the Customs Tariff T2026")
        mfn = parse_rate(line.general_rate)
        if mfn is None:
            raise DutyDataError(f"{code}: MFN rate '{line.general_rate}' is not ad valorem")
        group = "EU" if origin in self.rules["us"]["euCountries"] else origin
        pref = r["preferences"].get(group)
        duty_rate, duty_layer, duty_name = mfn, "CA-MFN-T2026", "Customs duty (MFN)"
        if pref:
            ans = ctx.answer(pref["key"])
            ctx.questions.append(OriginQuestion(pref["key"], pref["question"], ans))
            free = _treatment_free(line.special, pref["treatment"])
            if ans is True and free is not None:
                duty_rate, duty_layer, duty_name = free, pref["layer"], f"Customs duty ({pref['treatment']})"
                ctx.not_applied.append(
                    NotApplied(
                        f"MFN duty ({line.general_rate})", f"Preference claimed: {pref['treatment']} applies instead."
                    )
                )
        if duty_layer == "CA-MFN-T2026":
            label = line.general_rate if duty_rate else "Free"
            self._line(
                ctx,
                duty_layer,
                duty_name,
                label,
                value * duty_rate,
                f"The Customs Tariff's most-favoured-nation rate for {_fmt(code[:8])}.",
                source=f"Customs Tariff T2026, {_fmt(code[:8])}",
            )
        else:
            self._line(
                ctx,
                duty_layer,
                duty_name,
                pct(duty_rate) if duty_rate else "Free",
                value * duty_rate,
                "The preferential rate for originating goods, claimed with proof of origin.",
            )
        duty_total = money(value * duty_rate)

        surtax_total = ZERO
        applied: list[str] = []
        for layer_id, rule in r["surtaxes"].items():
            if not any(code.startswith(p) for p in rule["prefixes"]):
                continue
            if "origins" in rule and origin not in rule["origins"]:
                continue
            if origin in rule.get("originsExcept", []):
                continue
            if any(x in applied for x in rule.get("notStackedOn", [])):
                ctx.not_applied.append(
                    NotApplied(
                        self.layers[layer_id]["name"], "Not stacked on goods already under the China Surtax Order."
                    )
                )
                continue
            if self._not_in_force(ctx, layer_id, self.layers[layer_id]["name"]):
                continue
            rate = Decimal(rule["rate"])
            amt = money(value * rate)
            surtax_total += amt
            applied.append(layer_id)
            self._line(
                ctx,
                layer_id,
                self.layers[layer_id]["name"],
                pct(rate),
                amt,
                f"{_fmt(code[:8])} is listed in the order.",
            )
        if not applied:
            ctx.not_applied.append(
                NotApplied(
                    "Canadian surtaxes",
                    f"{_fmt(code[:4])} isn't listed in the China, steel-derivative or steel and aluminium "
                    "surtax orders.",
                )
            )
        if origin == "US":
            ctx.not_applied.append(
                NotApplied(
                    "Counter-tariffs on US goods",
                    "Not applied: the steel and aluminium order's details were not verified for this estimate.",
                )
            )

        gst = self._period("CA", "CA-GST", ctx.as_of)
        if gst:
            base = value + duty_total + surtax_total
            rate = Decimal(gst["rate"])
            self._line(
                ctx,
                "CA-GST",
                "GST",
                pct(rate),
                base * rate,
                f"5% of the value for duty plus duties and surtaxes (${money(base):,}); registrants can claim it back.",
            )
        lvs = q.transport == "courier" and value <= Decimal("20")
        if not lvs:
            ctx.not_applied.append(
                NotApplied(
                    "Courier low-value relief",
                    "Only for courier shipments of very low value; this is a commercial entry.",
                )
            )


def _treatment_free(special: str, treatment: str) -> Decimal | None:
    """The preferential rate for a treatment from T2026's column ('…, MXT, CEUT, CPTPT, UKT: Free | GPT 3%')."""
    for part in (special or "").split("|"):
        names, _, rate = part.partition(":")
        if treatment in [n.strip() for n in names.split(",")]:
            return parse_rate(rate)
    return None


def _fmt(code: str) -> str:
    from tariffcompass.codes import fmt

    return fmt(code)


def build_engine() -> LayeredDutyEngine:
    base = Path(str(settings.TARIFF_COMPASS["DUTY_LAYERS_PATH"]))
    return LayeredDutyEngine(base, base.with_name("rules.json"))
