"""Typed actions (spec §5) — never arbitrary shell strings.

Only the action types Hallfix can actually construct and (eventually)
execute are defined here. Spec §5 enumerates 18 action types; the rest
(repository/signing-key/filesystem/service/backup actions) get their own
dataclass the phase that implements their executor adds them — declaring
an empty shape now for actions nothing can build or run yet would be dead
code, not architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import PackageManagerKind
from hallfix.domain.models.tool import InstallationStrategy


class ActionType(StrEnum):
    INSTALL_PACKAGE = "INSTALL_PACKAGE"
    REMOVE_PACKAGE = "REMOVE_PACKAGE"
    UPDATE_PACKAGE_INDEX = "UPDATE_PACKAGE_INDEX"
    REPAIR_PACKAGE_MANAGER = "REPAIR_PACKAGE_MANAGER"
    UPGRADE_SYSTEM_PACKAGES = "UPGRADE_SYSTEM_PACKAGES"


@dataclass(frozen=True, slots=True)
class InstallPackageAction:
    tool_id: str
    package: str
    strategy: InstallationStrategy
    tool_risk_level: RiskLevel
    type: ActionType = field(default=ActionType.INSTALL_PACKAGE, init=False)


@dataclass(frozen=True, slots=True)
class RemovePackageAction:
    tool_id: str
    package: str
    strategy: InstallationStrategy
    tool_risk_level: RiskLevel
    type: ActionType = field(default=ActionType.REMOVE_PACKAGE, init=False)


@dataclass(frozen=True, slots=True)
class UpdatePackageIndexAction:
    strategy: InstallationStrategy
    type: ActionType = field(default=ActionType.UPDATE_PACKAGE_INDEX, init=False)


@dataclass(frozen=True, slots=True)
class RepairPackageManagerAction:
    fix_id: str
    manager_kind: PackageManagerKind
    fix_risk_level: RiskLevel
    type: ActionType = field(default=ActionType.REPAIR_PACKAGE_MANAGER, init=False)


@dataclass(frozen=True, slots=True)
class UpgradeSystemAction:
    """spec §54's ``hallfix update system`` — a full, native package-manager
    upgrade (``apt-get upgrade`` / ``dnf upgrade`` / ``pacman -Syu`` /
    ``zypper update``), distinct from ``UpdatePackageIndexAction`` (which
    only refreshes metadata, never installs anything)."""

    strategy: InstallationStrategy
    type: ActionType = field(default=ActionType.UPGRADE_SYSTEM_PACKAGES, init=False)


Action = (
    InstallPackageAction
    | RemovePackageAction
    | UpdatePackageIndexAction
    | RepairPackageManagerAction
    | UpgradeSystemAction
)


@dataclass(frozen=True, slots=True)
class ActionRisk:
    """Risk metadata for one action — always computed by RiskEvaluator,
    never hand-set on the action itself (spec §5's fields belong on the
    plan/action *evaluation*, not stored redundantly where they could
    drift from what the action actually does)."""

    risk_level: RiskLevel
    requires_root: bool
    requires_network: bool
    reversible: bool
    rollback_strategy: str | None
