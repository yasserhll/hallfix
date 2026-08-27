from __future__ import annotations

from hallfix.domain.models.enums import SupportLevel
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from hallfix.domain.models.tool import InstallationStrategy, ToolDefinition, VerificationSpec
from hallfix.domain.registries.compatibility import (
    assess_compatibility,
    resolve_installation_strategy,
)
from tests.fixtures.system_context_factory import make_system_context as _make_context


def _tool(
    *,
    strategies: tuple[InstallationStrategy, ...],
    mappings: dict[InstallationStrategy, str],
    supported_distributions: tuple[DistributionFamily, ...] = (),
    supported_architectures: tuple[str, ...] = (),
) -> ToolDefinition:
    return ToolDefinition(
        id="thing",
        name="Thing",
        description="A thing.",
        category="misc",
        installation_strategies=strategies,
        package_mappings=mappings,
        verification=VerificationSpec(executable="thing"),
        supported_distributions=supported_distributions,
        supported_architectures=supported_architectures,
    )


def test_resolves_native_strategy_matching_system_manager() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.APT, InstallationStrategy.PACMAN),
        mappings={InstallationStrategy.APT: "git", InstallationStrategy.PACMAN: "git"},
    )
    ctx = _make_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
    assert resolve_installation_strategy(tool, ctx) == InstallationStrategy.APT


def test_native_strategy_for_different_manager_is_unusable() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.PACMAN,),
        mappings={InstallationStrategy.PACMAN: "git"},
    )
    ctx = _make_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
    assert resolve_installation_strategy(tool, ctx) is None


def test_falls_back_to_language_ecosystem_strategy() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.PIP,), mappings={InstallationStrategy.PIP: "black"}
    )
    ctx = _make_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
    assert resolve_installation_strategy(tool, ctx) == InstallationStrategy.PIP


def test_native_strategy_preferred_over_language_ecosystem() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.PIP, InstallationStrategy.APT),
        mappings={InstallationStrategy.PIP: "git", InstallationStrategy.APT: "git"},
    )
    ctx = _make_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
    assert resolve_installation_strategy(tool, ctx) == InstallationStrategy.APT


def test_assess_compatibility_supported_when_family_explicitly_declared() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.APT,),
        mappings={InstallationStrategy.APT: "git"},
        supported_distributions=(DistributionFamily.DEBIAN,),
    )
    ctx = _make_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
    assert assess_compatibility(tool, ctx) == SupportLevel.SUPPORTED


def test_assess_compatibility_detected_only_when_family_not_declared() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.PACMAN,),
        mappings={InstallationStrategy.PACMAN: "git"},
        supported_distributions=(DistributionFamily.DEBIAN,),
    )
    ctx = _make_context(manager_kind=PackageManagerKind.PACMAN, family=DistributionFamily.ARCH)
    assert assess_compatibility(tool, ctx) == SupportLevel.DETECTED_ONLY


def test_assess_compatibility_experimental_when_no_distributions_declared() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.PIP,), mappings={InstallationStrategy.PIP: "black"}
    )
    ctx = _make_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
    assert assess_compatibility(tool, ctx) == SupportLevel.EXPERIMENTAL


def test_assess_compatibility_unsupported_when_no_strategy_resolves() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.PACMAN,),
        mappings={InstallationStrategy.PACMAN: "git"},
    )
    ctx = _make_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
    assert assess_compatibility(tool, ctx) == SupportLevel.UNSUPPORTED


def test_assess_compatibility_unsupported_when_architecture_mismatch() -> None:
    tool = _tool(
        strategies=(InstallationStrategy.APT,),
        mappings={InstallationStrategy.APT: "git"},
        supported_distributions=(DistributionFamily.DEBIAN,),
        supported_architectures=("aarch64",),
    )
    ctx = _make_context(
        manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN, architecture="x86_64"
    )
    assert assess_compatibility(tool, ctx) == SupportLevel.UNSUPPORTED
