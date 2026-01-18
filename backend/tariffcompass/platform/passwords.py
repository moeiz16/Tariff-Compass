"""Password policy: Argon2id hashes (settings.PASSWORD_HASHERS), at least 12 characters, not common,
not similar to the email or name. Failures become `422 weak_password` with field errors."""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from tariffcompass.core.errors import Problem
from tariffcompass.platform.models import User


def check_strength(password: str, *, email: str = "", full_name: str = "", field: str = "password") -> None:
    probe = User(email=email, full_name=full_name)
    try:
        validate_password(password, user=probe)
    except ValidationError as exc:
        raise Problem(
            422,
            "weak_password",
            "Choose a stronger password.",
            errors=[{"field": field, "message": str(m)} for m in exc.messages],
        ) from exc
