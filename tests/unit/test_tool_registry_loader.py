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


def test_default_registry_contains_phase13_tools() -> None:
    registry = load_tool_registry()
    for tool_id in (
        "wireshark",
        "tcpdump",
        "lsof",
        "strace",
        "binutils",
        "iproute2",
        "traceroute",
        "mtr",
        "ethtool",
        "dig",
        "wget",
        "rsync",
        "nodejs",
        "php",
        "composer",
        "postgresql-client",
        "jupyter",
    ):
        assert tool_id in registry, f"expected tool {tool_id!r} in default registry"


def test_jupyter_uses_pip_strategy_only() -> None:
    registry = load_tool_registry()
    jupyter = registry.require("jupyter")
    assert jupyter.installation_strategies == (InstallationStrategy.PIP,)


def test_iproute2_dnf_package_name_differs_from_others() -> None:
    """Fedora's package is named "iproute", not "iproute2" like everywhere else."""
    registry = load_tool_registry()
    tool = registry.require("iproute2")
    assert tool.package_mappings[InstallationStrategy.DNF] == "iproute"
    assert tool.package_mappings[InstallationStrategy.APT] == "iproute2"


def test_mtr_apt_package_name_differs_from_others() -> None:
    """Debian/Ubuntu ship the CLI-only build as "mtr-tiny"."""
    registry = load_tool_registry()
    tool = registry.require("mtr")
    assert tool.package_mappings[InstallationStrategy.APT] == "mtr-tiny"
    assert tool.package_mappings[InstallationStrategy.DNF] == "mtr"


def test_dig_package_name_differs_across_every_manager() -> None:
    registry = load_tool_registry()
    tool = registry.require("dig")
    assert tool.package_mappings[InstallationStrategy.APT] == "dnsutils"
    assert tool.package_mappings[InstallationStrategy.DNF] == "bind-utils"
    assert tool.package_mappings[InstallationStrategy.PACMAN] == "bind"
    assert tool.package_mappings[InstallationStrategy.ZYPPER] == "bind-utils"


def test_black_uses_pip_strategy_only() -> None:
    registry = load_tool_registry()
    black = registry.require("black")
    assert black.installation_strategies == (InstallationStrategy.PIP,)


def test_python3_pacman_package_name_differs_from_others() -> None:
    registry = load_tool_registry()
    python3 = registry.require("python3")
    assert python3.package_mappings[InstallationStrategy.PACMAN] == "python"
    assert python3.package_mappings[InstallationStrategy.APT] == "python3"
