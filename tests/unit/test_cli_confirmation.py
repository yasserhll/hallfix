from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rich.console import Console
from rich.prompt import Confirm

from hallfix.cli.confirmation import resolve_confirmation
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import ActionRisk, UpdatePackageIndexAction
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.safety.policy import SafetyPolicy

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


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


def test_no_confirmation_needed_proceeds_without_prompting() -> None:
    plan = _plan_with_risk(RiskLevel.LOW)
    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(plan, decision, yes=False, console=Console())
    assert outcome.proceed


def test_yes_bypasses_medium_risk() -> None:
    plan = _plan_with_risk(RiskLevel.MEDIUM)
    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(plan, decision, yes=True, console=Console())
    assert outcome.proceed


def test_yes_cannot_bypass_high_risk() -> None:
    plan = _plan_with_risk(RiskLevel.HIGH)
    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(plan, decision, yes=True, console=Console())
    assert not outcome.proceed
    assert outcome.reason is not None and "cannot bypass" in outcome.reason


def test_yes_cannot_bypass_critical_risk() -> None:
    plan = _plan_with_risk(RiskLevel.CRITICAL)
    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(plan, decision, yes=True, console=Console())
    assert not outcome.proceed


def test_interactive_prompt_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Confirm, "ask", lambda *a, **kw: True)
    plan = _plan_with_risk(RiskLevel.MEDIUM)
    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(plan, decision, yes=False, console=Console())
    assert outcome.proceed


def test_interactive_prompt_declined(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Confirm, "ask", lambda *a, **kw: False)
    plan = _plan_with_risk(RiskLevel.MEDIUM)
    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(plan, decision, yes=False, console=Console())
    assert not outcome.proceed
