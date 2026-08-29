from __future__ import annotations

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import PackageManagerKind
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import (
    InstallPackageAction,
    RemovePackageAction,
    RepairPackageManagerAction,
    UpdatePackageIndexAction,
    UpgradeSystemAction,
)
from hallfix.domain.planning.risk_evaluator import RiskEvaluator

evaluator = RiskEvaluator()


def test_install_package_inherits_tool_risk_and_is_reversible() -> None:
    action = InstallPackageAction(
        tool_id="docker",
        package="docker.io",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.MEDIUM,
    )
    risk = evaluator.evaluate(action)
    assert risk.risk_level == RiskLevel.MEDIUM
    assert risk.requires_root is True
    assert risk.requires_network is True
    assert risk.reversible is True
    assert risk.rollback_strategy == "remove_package"


def test_remove_package_is_not_claimed_reversible() -> None:
    action = RemovePackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    risk = evaluator.evaluate(action)
    assert risk.requires_network is False
    assert risk.reversible is False
    assert risk.rollback_strategy is None


def test_update_package_index_is_always_low_risk() -> None:
    action = UpdatePackageIndexAction(strategy=InstallationStrategy.DNF)
    risk = evaluator.evaluate(action)
    assert risk.risk_level == RiskLevel.LOW
    assert risk.requires_root is True
    assert risk.requires_network is True
    assert risk.reversible is True


def test_repair_package_manager_uses_fix_declared_risk_level() -> None:
    action = RepairPackageManagerAction(
        fix_id="fix.package_broken_state",
        manager_kind=PackageManagerKind.APT,
        fix_risk_level=RiskLevel.LOW,
    )
    risk = evaluator.evaluate(action)
    assert risk.risk_level == RiskLevel.LOW
    assert risk.requires_root is True
    assert risk.requires_network is False
    assert risk.reversible is False
    assert risk.rollback_strategy is None


def test_upgrade_system_is_medium_risk_and_not_reversible() -> None:
    action = UpgradeSystemAction(strategy=InstallationStrategy.APT)
    risk = evaluator.evaluate(action)
    assert risk.risk_level == RiskLevel.MEDIUM
    assert risk.requires_root is True
    assert risk.requires_network is True
    assert risk.reversible is False
    assert risk.rollback_strategy is None
