from __future__ import annotations

from datetime import UTC, datetime

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import ActionRisk, UpdatePackageIndexAction
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.safety.policy import SafetyPolicy

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
policy = SafetyPolicy()


def _plan_with_risk(risk_level: RiskLevel) -> ExecutionPlan:
    action = UpdatePackageIndexAction(strategy=InstallationStrategy.APT)
    risk = ActionRisk(
        risk_level=risk_level,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy=None,
    )
    planned = PlannedAction(action=action, risk=risk, description="test")
    return ExecutionPlan(id="HF-1", created_at=_NOW, description="d", planned_actions=(planned,))


def test_noop_plan_never_requires_confirmation() -> None:
    plan = ExecutionPlan(id="HF-1", created_at=_NOW, description="nothing")
    decision = policy.evaluate_plan(plan)
    assert not decision.requires_confirmation
    assert not decision.blocked


def test_low_risk_does_not_require_confirmation() -> None:
    decision = policy.evaluate_plan(_plan_with_risk(RiskLevel.LOW))
    assert not decision.requires_confirmation


def test_medium_risk_requires_confirmation() -> None:
    decision = policy.evaluate_plan(_plan_with_risk(RiskLevel.MEDIUM))
    assert decision.requires_confirmation
    assert decision.reasons


def test_high_risk_requires_confirmation() -> None:
    decision = policy.evaluate_plan(_plan_with_risk(RiskLevel.HIGH))
    assert decision.requires_confirmation


def test_critical_risk_requires_confirmation() -> None:
    decision = policy.evaluate_plan(_plan_with_risk(RiskLevel.CRITICAL))
    assert decision.requires_confirmation


def test_allows_auto_confirm_for_low_and_medium_only() -> None:
    assert policy.allows_auto_confirm(_plan_with_risk(RiskLevel.LOW))
    assert policy.allows_auto_confirm(_plan_with_risk(RiskLevel.MEDIUM))
    assert not policy.allows_auto_confirm(_plan_with_risk(RiskLevel.HIGH))
    assert not policy.allows_auto_confirm(_plan_with_risk(RiskLevel.CRITICAL))
