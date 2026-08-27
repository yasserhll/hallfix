from __future__ import annotations

from typing import Any

import pytest

from hallfix.domain.exceptions import RegistryError
from hallfix.domain.registries.profile_registry import ProfileRegistry, parse_profile_definition


def _valid_developer() -> dict[str, Any]:
    return {
        "id": "developer",
        "name": "Developer",
        "description": "Development workstation.",
        "categories": ["essentials", "languages"],
        "tools": ["git", "python3"],
    }


def test_parses_valid_definition() -> None:
    profile = parse_profile_definition(_valid_developer())
    assert profile.id == "developer"
    assert profile.tools == ("git", "python3")
    assert profile.categories == ("essentials", "languages")


def test_missing_id_raises() -> None:
    raw = _valid_developer()
    del raw["id"]
    with pytest.raises(RegistryError):
        parse_profile_definition(raw)


def test_invalid_id_raises() -> None:
    raw = _valid_developer()
    raw["id"] = "Not Valid"
    with pytest.raises(RegistryError):
        parse_profile_definition(raw)


def test_missing_required_field_raises() -> None:
    raw = _valid_developer()
    del raw["description"]
    with pytest.raises(RegistryError):
        parse_profile_definition(raw)


def test_empty_tools_list_raises() -> None:
    raw = _valid_developer()
    raw["tools"] = []
    with pytest.raises(RegistryError):
        parse_profile_definition(raw)


def test_categories_default_to_empty() -> None:
    raw = _valid_developer()
    del raw["categories"]
    profile = parse_profile_definition(raw)
    assert profile.categories == ()


class TestProfileRegistry:
    def test_get_and_require(self) -> None:
        registry = ProfileRegistry([_valid_developer()])
        assert registry.get("developer") is not None
        assert registry.require("developer").id == "developer"
        assert registry.get("missing") is None
        with pytest.raises(RegistryError):
            registry.require("missing")

    def test_duplicate_id_raises(self) -> None:
        with pytest.raises(RegistryError):
            ProfileRegistry([_valid_developer(), _valid_developer()])

    def test_list_all_sorted_by_id(self) -> None:
        devops = _valid_developer()
        devops["id"] = "devops"
        registry = ProfileRegistry([_valid_developer(), devops])
        assert [p.id for p in registry.list_all()] == ["developer", "devops"]

    def test_len_and_contains(self) -> None:
        registry = ProfileRegistry([_valid_developer()])
        assert len(registry) == 1
        assert "developer" in registry
        assert "missing" not in registry
