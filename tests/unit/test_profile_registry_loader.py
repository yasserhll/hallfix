"""Loads the *real* shipped profile YAML files — a regression test that
our own data/profiles/*.yaml stay parseable and reference tool ids that
actually exist in the tool registry.
"""

from __future__ import annotations

from hallfix.infrastructure.registries.profile_registry_loader import load_profile_registry
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry


def test_default_profile_registry_loads_without_error() -> None:
    registry = load_profile_registry()
    assert len(registry) >= 2


def test_default_registry_contains_expected_profiles() -> None:
    registry = load_profile_registry()
    for profile_id in (
        "developer",
        "devops",
        "cybersecurity",
        "network-engineer",
        "system-administrator",
        "data-ai",
        "full-stack-developer",
    ):
        assert profile_id in registry


def test_every_referenced_tool_exists_in_tool_registry() -> None:
    profiles = load_profile_registry()
    tools = load_tool_registry()
    for profile in profiles.list_all():
        for tool_id in profile.tools:
            assert tool_id in tools, f"{profile.id} references unknown tool {tool_id!r}"
