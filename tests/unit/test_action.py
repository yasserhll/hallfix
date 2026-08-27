from __future__ import annotations

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import (
    ActionType,
    InstallPackageAction,
    RemovePackageAction,
    UpdatePackageIndexAction,
)


def test_install_package_action_tags_itself() -> None:
    action = InstallPackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    assert action.type == ActionType.INSTALL_PACKAGE


def test_remove_package_action_tags_itself() -> None:
    action = RemovePackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    assert action.type == ActionType.REMOVE_PACKAGE


def test_update_package_index_action_tags_itself() -> None:
    action = UpdatePackageIndexAction(strategy=InstallationStrategy.APT)
    assert action.type == ActionType.UPDATE_PACKAGE_INDEX


def test_action_type_cannot_be_overridden_at_construction() -> None:
    action = InstallPackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    # `type` has init=False — constructing with a mismatched type is not
    # even possible via the constructor, which is the point.
    import dataclasses

    assert "type" not in {f.name for f in dataclasses.fields(action) if f.init}
