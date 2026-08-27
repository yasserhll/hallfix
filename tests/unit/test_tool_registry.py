from __future__ import annotations

from typing import Any

import pytest

from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import DistributionFamily
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.registries.tool_registry import ToolRegistry, parse_tool_definition


def _valid_git() -> dict[str, Any]:
    return {
        "id": "git",
        "name": "Git",
        "description": "Distributed version control system.",
        "category": "essentials",
        "profiles": ["developer"],
        "installation_strategies": ["APT", "DNF"],
        "package_mappings": {"APT": "git", "DNF": "git"},
        "verification": {
            "executable": "git",
            "version_command": ["git", "--version"],
            "version_regex": r"(\d+\.\d+(?:\.\d+)?)",
        },
        "supported_distributions": ["DEBIAN", "REDHAT"],
        "risk_level": "LOW",
    }


def test_parses_valid_definition() -> None:
    tool = parse_tool_definition(_valid_git())
    assert tool.id == "git"
    assert tool.installation_strategies == (InstallationStrategy.APT, InstallationStrategy.DNF)
    assert tool.package_mappings[InstallationStrategy.APT] == "git"
    assert tool.supported_distributions == (DistributionFamily.DEBIAN, DistributionFamily.REDHAT)
    assert tool.risk_level == RiskLevel.LOW
    assert tool.requires_root is True  # default
    assert tool.optional is False  # default


def test_defaults_applied_when_optional_fields_absent() -> None:
    raw = _valid_git()
    del raw["risk_level"]
    tool = parse_tool_definition(raw)
    assert tool.risk_level == RiskLevel.LOW


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw.pop("id"),
        lambda raw: raw.__setitem__("id", "Not-Valid-ID"),
        lambda raw: raw.__setitem__("id", "1-starts-with-digit"),
    ],
)
def test_invalid_id_raises(mutate: object) -> None:
    raw = _valid_git()
    mutate(raw)  # type: ignore[operator]
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


def test_missing_required_field_raises() -> None:
    raw = _valid_git()
    del raw["name"]
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


def test_empty_installation_strategies_raises() -> None:
    raw = _valid_git()
    raw["installation_strategies"] = []
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


def test_unknown_installation_strategy_raises() -> None:
    raw = _valid_git()
    raw["installation_strategies"] = ["APT", "HOMEBREW"]
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


def test_strategy_without_package_mapping_raises() -> None:
    raw = _valid_git()
    raw["installation_strategies"] = ["APT", "PACMAN"]
    raw["package_mappings"] = {"APT": "git"}  # PACMAN missing
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


def test_missing_verification_raises() -> None:
    raw = _valid_git()
    del raw["verification"]
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


def test_unknown_distribution_family_raises() -> None:
    raw = _valid_git()
    raw["supported_distributions"] = ["MACOS"]
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


def test_unknown_risk_level_raises() -> None:
    raw = _valid_git()
    raw["risk_level"] = "EXTREME"
    with pytest.raises(RegistryError):
        parse_tool_definition(raw)


class TestToolRegistry:
    def test_get_and_require(self) -> None:
        registry = ToolRegistry([_valid_git()])
        assert registry.get("git") is not None
        assert registry.require("git").id == "git"
        assert registry.get("missing") is None
        with pytest.raises(RegistryError):
            registry.require("missing")

    def test_duplicate_id_raises(self) -> None:
        with pytest.raises(RegistryError):
            ToolRegistry([_valid_git(), _valid_git()])

    def test_list_all_sorted_by_id(self) -> None:
        curl = _valid_git()
        curl["id"] = "curl"
        registry = ToolRegistry([_valid_git(), curl])
        assert [t.id for t in registry.list_all()] == ["curl", "git"]

    def test_list_by_category_and_profile(self) -> None:
        registry = ToolRegistry([_valid_git()])
        assert [t.id for t in registry.list_by_category("essentials")] == ["git"]
        assert [t.id for t in registry.list_by_category("other")] == []
        assert [t.id for t in registry.list_by_profile("developer")] == ["git"]
        assert [t.id for t in registry.list_by_profile("devops")] == []

    def test_search_matches_id_name_and_description(self) -> None:
        registry = ToolRegistry([_valid_git()])
        assert [t.id for t in registry.search("git")] == ["git"]
        assert [t.id for t in registry.search("version control")] == ["git"]
        assert registry.search("nonexistent") == ()

    def test_len_and_contains(self) -> None:
        registry = ToolRegistry([_valid_git()])
        assert len(registry) == 1
        assert "git" in registry
        assert "missing" not in registry
