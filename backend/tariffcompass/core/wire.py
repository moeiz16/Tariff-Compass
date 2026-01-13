"""Wire casing: every API shape is camelCase JSON on the wire and snake_case in Python.

`Wire` is the base for every request/response schema; `WireRouter` serialises by alias by default, so a
view returns plain Python objects and the client sees `effectiveFrom`, `chapter99`, `roleLabel`…
"""

from __future__ import annotations

from typing import Any

from ninja import Router, Schema
from ninja.constants import NOT_SET
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class Wire(Schema):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class WireRouter(Router):
    """A Router whose operations serialise by alias (camelCase) unless told otherwise."""

    def api_operation(self, methods: list[str], path: str, *, by_alias: bool | None = None, **kwargs: Any):
        return super().api_operation(methods, path, by_alias=True if by_alias is None else by_alias, **kwargs)


__all__ = ["NOT_SET", "Wire", "WireRouter"]
