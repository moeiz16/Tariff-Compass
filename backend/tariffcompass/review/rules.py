"""Always-review rules: products a broker must see whatever the classifier says.

Kinds: heading / chapter (code prefix), material (the product's material or the description), value_over
(entry value in USD), origin (made in), keyword (words in the description).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from tariffcompass import codes
from tariffcompass.catalog.models import Product
from tariffcompass.review.models import AlwaysReviewRule


def shipment_value(product: Product) -> Decimal | None:
    raw = (product.shipment or {}).get("value")
    try:
        return Decimal(str(raw)) if raw not in (None, "") else None
    except InvalidOperation:
        return None


def matches(
    rule: AlwaysReviewRule, product: Product, *, us_code: str = "", text: str = "", value: Decimal | None = None
) -> bool:
    if not rule.active:
        return False
    v = rule.value.strip().lower()
    code = codes.digits(us_code or product.us_code)
    words = f"{product.title} {product.listing_text} {text}".lower()
    if rule.kind in ("heading", "chapter"):
        return bool(code) and code.startswith(codes.digits(v))
    if rule.kind == "material":
        return v in (product.material or "").lower() or v in words
    if rule.kind == "keyword":
        return v in words
    if rule.kind == "origin":
        return product.made_in.lower() == v
    if rule.kind == "value_over":
        amount = value if value is not None else shipment_value(product)
        try:
            return amount is not None and amount > Decimal(codes.digits(v) or "0")
        except InvalidOperation:
            return False
    return False


def first_match(
    product: Product, *, us_code: str = "", text: str = "", value: Decimal | None = None
) -> AlwaysReviewRule | None:
    for rule in AlwaysReviewRule.objects.filter(org=product.org, active=True).order_by("created_at"):
        if matches(rule, product, us_code=us_code, text=text, value=value):
            return rule
    return None


def count_matches(rule: AlwaysReviewRule) -> int:
    return sum(1 for p in Product.objects.filter(org=rule.org, hidden_at__isnull=True) if matches(rule, p))
