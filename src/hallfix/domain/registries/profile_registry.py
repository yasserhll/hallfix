"""``ProfileRegistry``: validates and indexes already-loaded profile definitions.

Same shape as ``domain/registries/tool_registry.py`` — pure, takes
already-parsed dicts, fails loudly at construction (spec §25's "validate
at startup" applies equally to profiles). Deliberately does not
cross-validate that every referenced tool id exists in a ``ToolRegistry``:
that would couple load order between the two registries. An unknown tool
id inside a profile is instead reported clearly wherever the profile is
actually resolved (``profile show``/``diff``/``install``), not silently
dropped and not a hard load-time failure.
"""

from __future__ import annotations

import re
from typing import Any

from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.profile import ProfileDefinition

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


def _require_str(raw: dict[str, Any], key: str, *, profile_id: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"profile {profile_id!r}: field {key!r} must be a non-empty string"
        raise RegistryError(msg)
    return value


def _str_tuple(raw: dict[str, Any], key: str, *, profile_id: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"profile {profile_id!r}: field {key!r} must be a list of strings"
        raise RegistryError(msg)
    return tuple(value)


def parse_profile_definition(raw: dict[str, Any]) -> ProfileDefinition:
    profile_id = raw.get("id")
    if not isinstance(profile_id, str) or not _ID_PATTERN.match(profile_id):
        msg = f"profile definition has invalid or missing 'id': {profile_id!r}"
        raise RegistryError(msg)

    tools = _str_tuple(raw, "tools", profile_id=profile_id)
    if not tools:
        msg = f"profile {profile_id!r}: 'tools' must be a non-empty list"
        raise RegistryError(msg)

    return ProfileDefinition(
        id=profile_id,
        name=_require_str(raw, "name", profile_id=profile_id),
        description=_require_str(raw, "description", profile_id=profile_id),
        categories=_str_tuple(raw, "categories", profile_id=profile_id),
        tools=tools,
    )


class ProfileRegistry:
    def __init__(self, raw_definitions: list[dict[str, Any]]) -> None:
        profiles: dict[str, ProfileDefinition] = {}
        for raw in raw_definitions:
            profile = parse_profile_definition(raw)
            if profile.id in profiles:
                msg = f"duplicate profile id: {profile.id!r}"
                raise RegistryError(msg)
            profiles[profile.id] = profile
        self._profiles = profiles

    def get(self, profile_id: str) -> ProfileDefinition | None:
        return self._profiles.get(profile_id)

    def require(self, profile_id: str) -> ProfileDefinition:
        profile = self._profiles.get(profile_id)
        if profile is None:
            msg = f"no such profile: {profile_id!r}"
            raise RegistryError(msg)
        return profile

    def list_all(self) -> tuple[ProfileDefinition, ...]:
        return tuple(sorted(self._profiles.values(), key=lambda p: p.id))

    def __len__(self) -> int:
        return len(self._profiles)

    def __contains__(self, profile_id: str) -> bool:
        return profile_id in self._profiles
