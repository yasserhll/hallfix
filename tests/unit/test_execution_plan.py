from __future__ import annotations

from datetime import UTC, datetime

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import ActionRisk, UpdatePackageIndexAction
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _planned(
    risk_level: RiskLevel,
    *,
    requires_root: bool = True,
    requires_network: bool = True,
    reversible: bool = True,
) -> PlannedAction:
    action = UpdatePackageIndexAction(strategy=InstallationStrategy.APT)
    risk = ActionRisk(
        risk_level=risk_level,
        requires_root=requires_root,
        requires_network=requires_network,
        reversible=reversible,
        rollback_strategy=None,
    )
    return PlannedAction(action=action, risk=risk, description="test action")


def test_empty_plan_is_noop_with_low_risk() -> None:
    plan = ExecutionPlan(id="HF-1", created_at=_NOW, description="nothing to do")
    assert plan.is_noop
    assert plan.risk_level == RiskLevel.LOW
    assert plan.requires_root is False
    assert plan.requires_network is False
    assert plan.reversible is True
    assert plan.estimated_changes == 0


def test_risk_level_is_max_across_actions() -> None:
    plan = ExecutionPlan(
        id="HF-1",
        created_at=_NOW,
        description="d",
        planned_actions=(
            _planned(RiskLevel.LOW),
            _planned(RiskLevel.HIGH),
            _planned(RiskLevel.MEDIUM),
        ),
    )
    assert plan.risk_level == RiskLevel.HIGH


def test_requires_root_true_if_any_action_requires_it() -> None:
    plan = ExecutionPlan(
        id="HF-1",
        created_at=_NOW,
        description="d",
        planned_actions=(
            _planned(RiskLevel.LOW, requires_root=False),
            _planned(RiskLevel.LOW, requires_root=True),
        ),
    )
    assert plan.requires_root is True


def test_reversible_only_if_all_actions_reversible() -> None:
    plan = ExecutionPlan(
        id="HF-1",
        created_at=_NOW,
        description="d",
        planned_actions=(
            _planned(RiskLevel.LOW, reversible=True),
            _planned(RiskLevel.LOW, reversible=False),
        ),
    )
    assert plan.reversible is False


def test_estimated_changes_counts_actions() -> None:
    plan = ExecutionPlan(
        id="HF-1",
        created_at=_NOW,
        description="d",
        planned_actions=(_planned(RiskLevel.LOW), _planned(RiskLevel.LOW)),
    )
    assert plan.estimated_changes == 2
    assert not plan.is_noop
