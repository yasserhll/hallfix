"""``ToolRegistry``: validates and indexes already-loaded tool definitions.

Pure — takes a list of already-parsed dicts (typically read from YAML by
``infrastructure/registries/tool_registry_loader.py``) and never touches a
filesystem itself, per the domain layer's zero-I/O rule. Every definition
is validated at construction time (spec §25: "Validate all registry data
at startup") — a malformed tool file fails immediately and loudly, not
whenever that tool happens to be looked up later.
"""

from __future__ import annotations

import re
from typing import Any

from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import DistributionFamily
from hallfix.domain.models.tool import (
    InstallationStrategy,
    ToolDefinition,
    VerificationSpec,
)

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


def _require_str(raw: dict[str, Any], key: str, *, tool_id: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"tool {tool_id!r}: field {key!r} must be a non-empty string"
        raise RegistryError(msg)
    return value


def _optional_str(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def _str_tuple(raw: dict[str, Any], key: str, *, tool_id: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"tool {tool_id!r}: field {key!r} must be a list of strings"
        raise RegistryError(msg)
    return tuple(value)


def _parse_installation_strategies(
    raw: dict[str, Any], *, tool_id: str
) -> tuple[InstallationStrategy, ...]:
    values = raw.get("installation_strategies", [])
    if not isinstance(values, list) or not values:
        msg = f"tool {tool_id!r}: 'installation_strategies' must be a non-empty list"
        raise RegistryError(msg)
    strategies = []
    for value in values:
        try:
            strategies.append(InstallationStrategy(str(value).upper()))
        except ValueError as exc:
            msg = f"tool {tool_id!r}: unknown installation strategy {value!r}"
            raise RegistryError(msg) from exc
    return tuple(strategies)


def _parse_package_mappings(
    raw: dict[str, Any],
    strategies: tuple[InstallationStrategy, ...],
    *,
    tool_id: str,
) -> dict[InstallationStrategy, str]:
    values = raw.get("package_mappings", {})
    if not isinstance(values, dict):
        msg = f"tool {tool_id!r}: 'package_mappings' must be a mapping"
        raise RegistryError(msg)
    mappings: dict[InstallationStrategy, str] = {}
    for key, value in values.items():
        try:
            strategy = InstallationStrategy(str(key).upper())
        except ValueError as exc:
            msg = f"tool {tool_id!r}: unknown package_mappings key {key!r}"
            raise RegistryError(msg) from exc
        if not isinstance(value, str) or not value.strip():
            msg = f"tool {tool_id!r}: package_mappings[{key!r}] must be a non-empty string"
            raise RegistryError(msg)
        mappings[strategy] = value

    missing = [s.value for s in strategies if s not in mappings]
    if missing:
        msg = (
            f"tool {tool_id!r}: installation_strategies {missing} have no "
            f"corresponding entry in package_mappings"
        )
        raise RegistryError(msg)
    return mappings


def _parse_verification(raw: dict[str, Any], *, tool_id: str) -> VerificationSpec:
    values = raw.get("verification")
    if not isinstance(values, dict):
        msg = f"tool {tool_id!r}: 'verification' must be a mapping with at least 'executable'"
        raise RegistryError(msg)
    executable = _require_str(values, "executable", tool_id=tool_id)
    version_command_raw = values.get("version_command")
    version_command: tuple[str, ...] | None = None
    if version_command_raw is not None:
        if not isinstance(version_command_raw, list) or not all(
            isinstance(item, str) for item in version_command_raw
        ):
            msg = f"tool {tool_id!r}: verification.version_command must be a list of strings"
            raise RegistryError(msg)
        version_command = tuple(version_command_raw)
    version_regex = _optional_str(values, "version_regex")
    return VerificationSpec(
        executable=executable, version_command=version_command, version_regex=version_regex
    )


def _parse_distribution_families(
    raw: dict[str, Any], *, tool_id: str
) -> tuple[DistributionFamily, ...]:
    values = raw.get("supported_distributions", [])
    if not isinstance(values, list):
        msg = f"tool {tool_id!r}: 'supported_distributions' must be a list"
        raise RegistryError(msg)
    families = []
    for value in values:
        try:
            families.append(DistributionFamily(str(value).upper()))
        except ValueError as exc:
            msg = f"tool {tool_id!r}: unknown distribution family {value!r}"
            raise RegistryError(msg) from exc
    return tuple(families)


def _parse_risk_level(raw: dict[str, Any], *, tool_id: str) -> RiskLevel:
    value = raw.get("risk_level", RiskLevel.LOW.value)
    try:
        return RiskLevel(str(value).upper())
    except ValueError as exc:
        msg = f"tool {tool_id!r}: unknown risk_level {value!r}"
        raise RegistryError(msg) from exc


def parse_tool_definition(raw: dict[str, Any]) -> ToolDefinition:
    tool_id = raw.get("id")
    if not isinstance(tool_id, str) or not _ID_PATTERN.match(tool_id):
        msg = f"tool definition has invalid or missing 'id': {tool_id!r}"
        raise RegistryError(msg)

    strategies = _parse_installation_strategies(raw, tool_id=tool_id)
    mappings = _parse_package_mappings(raw, strategies, tool_id=tool_id)

    return ToolDefinition(
        id=tool_id,
        name=_require_str(raw, "name", tool_id=tool_id),
        description=_require_str(raw, "description", tool_id=tool_id),
        category=_require_str(raw, "category", tool_id=tool_id),
        profiles=_str_tuple(raw, "profiles", tool_id=tool_id),
        dependencies=_str_tuple(raw, "dependencies", tool_id=tool_id),
        installation_strategies=strategies,
        package_mappings=mappings,
        verification=_parse_verification(raw, tool_id=tool_id),
        supported_distributions=_parse_distribution_families(raw, tool_id=tool_id),
        supported_architectures=_str_tuple(raw, "supported_architectures", tool_id=tool_id),
        minimum_version=_optional_str(raw, "minimum_version"),
        recommended_version=_optional_str(raw, "recommended_version"),
        optional=bool(raw.get("optional", False)),
        risk_level=_parse_risk_level(raw, tool_id=tool_id),
        requires_root=bool(raw.get("requires_root", True)),
        documentation_url=_optional_str(raw, "documentation_url"),
    )


class ToolRegistry:
    def __init__(self, raw_definitions: list[dict[str, Any]]) -> None:
        tools: dict[str, ToolDefinition] = {}
        for raw in raw_definitions:
            tool = parse_tool_definition(raw)
            if tool.id in tools:
                msg = f"duplicate tool id: {tool.id!r}"
                raise RegistryError(msg)
            tools[tool.id] = tool
        self._tools = tools

    def get(self, tool_id: str) -> ToolDefinition | None:
        return self._tools.get(tool_id)

    def require(self, tool_id: str) -> ToolDefinition:
        tool = self._tools.get(tool_id)
        if tool is None:
            msg = f"no such tool: {tool_id!r}"
            raise RegistryError(msg)
        return tool

    def list_all(self) -> tuple[ToolDefinition, ...]:
        return tuple(sorted(self._tools.values(), key=lambda t: t.id))

    def list_by_category(self, category: str) -> tuple[ToolDefinition, ...]:
        return tuple(t for t in self.list_all() if t.category == category)

    def list_by_profile(self, profile: str) -> tuple[ToolDefinition, ...]:
        return tuple(t for t in self.list_all() if profile in t.profiles)

    def search(self, query: str) -> tuple[ToolDefinition, ...]:
        lowered = query.lower()
        return tuple(
            t
            for t in self.list_all()
            if lowered in t.id.lower()
            or lowered in t.name.lower()
            or lowered in t.description.lower()
        )

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools
