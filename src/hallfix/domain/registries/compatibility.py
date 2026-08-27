"""Compatibility validation: does a tool work on this system, and how? (spec §52/§84)

Two pure functions, no I/O — operate entirely on already-detected
``SystemContext`` (Phase 2) and an already-validated ``ToolDefinition``
(this phase).

``resolve_installation_strategy`` picks the highest-trust usable strategy
per spec §24's priority order (native package manager > official vendor
repository > signed binary > language ecosystem package). A native
strategy is only usable if it matches the system's *actual* detected
package manager — declaring APT and PACMAN both doesn't make APT usable
on an Arch system.

``assess_compatibility`` never returns SUPPORTED unless the tool's own
data explicitly lists this distribution family as supported — spec §84:
"never say a distribution is supported merely because its package manager
is recognized." A tool with no `supported_distributions` declared but a
resolvable strategy is EXPERIMENTAL, not SUPPORTED, until someone actually
verifies and declares it.
"""

from __future__ import annotations

from hallfix.domain.models.enums import SupportLevel
from hallfix.domain.models.system import PackageManagerKind, SystemContext
from hallfix.domain.models.tool import (
    NATIVE_INSTALLATION_STRATEGIES,
    InstallationStrategy,
    ToolDefinition,
)

NATIVE_STRATEGY_BY_MANAGER: dict[PackageManagerKind, InstallationStrategy] = {
    PackageManagerKind.APT: InstallationStrategy.APT,
    PackageManagerKind.DNF: InstallationStrategy.DNF,
    PackageManagerKind.PACMAN: InstallationStrategy.PACMAN,
    PackageManagerKind.ZYPPER: InstallationStrategy.ZYPPER,
}

# Lower number = higher trust (spec §24).
_TRUST_RANK: dict[InstallationStrategy, int] = {
    InstallationStrategy.APT: 1,
    InstallationStrategy.DNF: 1,
    InstallationStrategy.PACMAN: 1,
    InstallationStrategy.ZYPPER: 1,
    InstallationStrategy.OFFICIAL_REPOSITORY: 2,
    InstallationStrategy.SIGNED_BINARY: 3,
    InstallationStrategy.PIP: 4,
    InstallationStrategy.PIPX: 4,
    InstallationStrategy.NPM: 4,
    InstallationStrategy.CARGO: 4,
    InstallationStrategy.COMPOSER: 4,
}


def resolve_installation_strategy(
    tool: ToolDefinition, context: SystemContext
) -> InstallationStrategy | None:
    native_strategy = NATIVE_STRATEGY_BY_MANAGER.get(context.package_manager.kind)

    candidates = []
    for strategy in tool.installation_strategies:
        if strategy not in tool.package_mappings:
            continue
        if strategy in NATIVE_INSTALLATION_STRATEGIES and strategy != native_strategy:
            continue  # native strategy for a *different* manager: unusable here
        candidates.append(strategy)

    if not candidates:
        return None
    return min(candidates, key=lambda s: _TRUST_RANK[s])


def assess_compatibility(tool: ToolDefinition, context: SystemContext) -> SupportLevel:
    if tool.supported_architectures and context.architecture not in tool.supported_architectures:
        return SupportLevel.UNSUPPORTED

    strategy = resolve_installation_strategy(tool, context)
    if strategy is None:
        return SupportLevel.UNSUPPORTED

    if not tool.supported_distributions:
        return SupportLevel.EXPERIMENTAL

    if context.distribution.family not in tool.supported_distributions:
        return SupportLevel.DETECTED_ONLY

    return SupportLevel.SUPPORTED
