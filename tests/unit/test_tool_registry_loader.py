"""Loads the *real* shipped tool YAML files — a regression test that our
own data/tools/*.yaml stay parseable and pass registry validation. No
filesystem fakery here on purpose: this is the actual data Hallfix ships.
"""

from __future__ import annotations

from hallfix.domain.models.tool import InstallationStrategy
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry


def test_default_tool_registry_loads_without_error() -> None:
    registry = load_tool_registry()
    assert len(registry) >= 6


def test_default_registry_contains_expected_tools() -> None:
    registry = load_tool_registry()
    for tool_id in ("git", "curl", "python3", "htop", "docker", "black"):
        assert tool_id in registry, f"expected tool {tool_id!r} in default registry"


def test_black_uses_pip_strategy_only() -> None:
    registry = load_tool_registry()
    black = registry.require("black")
    assert black.installation_strategies == (InstallationStrategy.PIP,)


def test_python3_pacman_package_name_differs_from_others() -> None:
    registry = load_tool_registry()
    python3 = registry.require("python3")
    assert python3.package_mappings[InstallationStrategy.PACMAN] == "python"
    assert python3.package_mappings[InstallationStrategy.APT] == "python3"
