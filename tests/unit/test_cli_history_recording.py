from __future__ import annotations

from datetime import UTC, datetime

from hallfix.cli.history_recording import build_action_outcomes
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import (
    ActionRisk,
    InstallPackageAction,
    UpdatePackageIndexAction,
)
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.planning.execution_result import ActionExecutionResult, PlanExecutionResult

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_build_action_outcomes_extracts_install_detail() -> None:
    action = InstallPackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    risk = ActionRisk(
        risk_level=RiskLevel.LOW,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy="remove_package",
    )
    plan = ExecutionPlan(
        id="HF-PLAN-1",
        created_at=_NOW,
        description="d",
        planned_actions=(PlannedAction(action=action, risk=risk, description="d"),),
    )
    result = PlanExecutionResult(
        plan_id=plan.id,
        dry_run=False,
        action_results=(
            ActionExecutionResult(
                action=action, succeeded=True, already_satisfied=False, message="ok", dry_run=False
            ),
        ),
    )

    (outcome,) = build_action_outcomes(plan, result)
    assert outcome.tool_id == "git"
    assert outcome.package == "git"
    assert outcome.strategy == "APT"
    assert outcome.risk_level == "LOW"
    assert outcome.reversible is True
    assert outcome.rollback_strategy == "remove_package"
    assert outcome.rollback_eligible is True


def test_build_action_outcomes_for_non_install_action_has_no_package_detail() -> None:
    action = UpdatePackageIndexAction(strategy=InstallationStrategy.APT)
    risk = ActionRisk(
        risk_level=RiskLevel.LOW,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy=None,
    )
    plan = ExecutionPlan(
        id="HF-PLAN-1",
        created_at=_NOW,
        description="d",
        planned_actions=(PlannedAction(action=action, risk=risk, description="d"),),
    )
    result = PlanExecutionResult(
        plan_id=plan.id,
        dry_run=False,
        action_results=(
            ActionExecutionResult(
                action=action, succeeded=True, already_satisfied=False, message="ok", dry_run=False
            ),
        ),
    )

    (outcome,) = build_action_outcomes(plan, result)
    assert outcome.tool_id is None
    assert outcome.package is None
    assert outcome.strategy == "APT"
    assert outcome.rollback_eligible is False  # no rollback_strategy


def test_build_action_outcomes_already_satisfied_is_not_rollback_eligible() -> None:
    action = InstallPackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    risk = ActionRisk(
        risk_level=RiskLevel.LOW,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy="remove_package",
    )
    plan = ExecutionPlan(
        id="HF-PLAN-1",
        created_at=_NOW,
        description="d",
        planned_actions=(PlannedAction(action=action, risk=risk, description="d"),),
    )
    result = PlanExecutionResult(
        plan_id=plan.id,
        dry_run=False,
        action_results=(
            ActionExecutionResult(
                action=action, succeeded=True, already_satisfied=True, message="ok", dry_run=False
            ),
        ),
    )

    (outcome,) = build_action_outcomes(plan, result)
    assert outcome.rollback_eligible is False
