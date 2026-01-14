"""Roles and permissions: the single source of truth for RBAC (docs/API_CONTRACT.md §1.3).

`/auth/session` returns `membership.permissions` from this table. Views check permissions, never role names.
A broker firm's people act inside an importer's organisation through a broker membership (see Engagement).
Promoting a training round needs two `lab:sign` signatures from two different people (one compliance, one broker).
"""

from __future__ import annotations

from typing import Final, Literal

Role = Literal["importer", "broker", "compliance", "admin"]
ROLES: Final[tuple[str, ...]] = ("importer", "broker", "compliance", "admin")

ROLE_LABELS: Final[dict[str, str]] = {
    "importer": "Importer",
    "broker": "Licensed customs broker",
    "compliance": "Compliance lead",
    "admin": "Administrator",
}

ROLE_DESCRIPTIONS: Final[dict[str, str]] = {
    "importer": "Classifies products, keeps binders and answers the broker's questions.",
    "broker": "Reviews, approves and corrects codes, and co-signs new training rounds.",
    "compliance": "Owns the reasonable-care record, the always-review rules and the training rounds.",
    "admin": "Manages people, roles and organisation settings.",
}

ALL_PERMISSIONS: Final[tuple[str, ...]] = (
    "classify:run",
    "classify:read",
    "rulings:read",
    "tariff:read",
    "products:read",
    "products:write",
    "binder:export",
    "review:read",
    "review:submit",
    "review:decide",
    "review:answer",
    "rules:manage",
    "watch:read",
    "watch:manage",
    "lab:read",
    "lab:run",
    "lab:sign",
    "settings:read",
    "settings:manage",
    "members:manage",
    "audit:read",
    "org:admin",
)

_READ = {"classify:read", "rulings:read", "tariff:read", "products:read", "review:read", "watch:read", "settings:read"}

ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    "importer": frozenset(
        _READ | {"classify:run", "products:write", "binder:export", "review:submit", "review:answer"}
    ),
    "broker": frozenset(
        _READ | {"classify:run", "binder:export", "review:decide", "rules:manage", "lab:read", "lab:sign"}
    ),
    "compliance": frozenset(
        _READ
        | {
            "classify:run",
            "products:write",
            "binder:export",
            "review:submit",
            "review:answer",
            "rules:manage",
            "watch:manage",
            "lab:read",
            "lab:run",
            "lab:sign",
            "settings:manage",
            "audit:read",
        }
    ),
    "admin": frozenset(_READ | {"lab:read", "settings:manage", "members:manage", "audit:read", "org:admin"}),
}


def permissions_for(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for(role)
