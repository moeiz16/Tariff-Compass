"""Landed cost from dated duty layers (duties/data/layers.json): no rate without a source and an effective date.

US stacking: MFN (or the USMCA preference) + Section 301 + Section 232 (on metal content for derivatives) +
IEEPA duties (fentanyl / reciprocal / Mexico / Canada, with their exclusions: 232 goods leave reciprocal,
USMCA goods leave the Mexico and Canada duties) + MPF + HMF (ocean). They add on the same customs value; they
don't compound. Canada: MFN or the preferential treatment (MXT, CEUT, CPTPT) + any surtax order + GST 5% on
value plus duties. Layers not applied are listed with why (e.g. de minimis suspended 29 Aug 2025).
"""

from __future__ import annotations

from tariffcompass.contracts import DutyEngine


def build_engine() -> DutyEngine:
    raise NotImplementedError("duty engine not built yet")
