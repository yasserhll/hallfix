"""Builds ``ActionOutcome`` records for ``HistoryStore`` from a real
execution — the one place that extracts rollback-relevant detail
(package/tool_id/strategy) from an ``Action``, so ``tool.py``/
``profile.py``/``fix.py`` don't each reimplement it.
"""

from __future__ import annotations

from hallfix.domain.models.history import ActionOutcome
from hallfix.domain.planning.action import (
    Action,
    InstallPackageAction,
    RemovePackageAction,
    RepairPackageManagerAction,
    UpdatePackageIndexAction,
    UpgradeSystemAction,
)
from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.planning.execution_result import PlanExecutionResult


def _action_detail(action: Action) -> tuple[str | None, str | None, str | None]:
    """Returns (tool_id, package, strategy) — whatever applies to this action type."""
    if isinstance(action, InstallPackageAction | RemovePackageAction):
        return action.tool_id, action.package, action.strategy.value
    if isinstance(action, UpdatePackageIndexAction | UpgradeSystemAction):
        return None, None, action.strategy.value
    if isinstance(action, RepairPackageManagerAction):
        return None, None, action.manager_kind.value
    return None, None, None  # pragma: no cover - exhaustive over current Action union


def build_action_outcomes(
    plan: ExecutionPlan, result: PlanExecutionResult
) -> tuple[ActionOutcome, ...]:
    outcomes = []
    for planned, action_result in zip(plan.planned_actions, result.action_results, strict=True):
        tool_id, package, strategy = _action_detail(action_result.action)
        outcomes.append(
            ActionOutcome(
                action_type=action_result.action.type.value,
                succeeded=action_result.succeeded,
                already_satisfied=action_result.already_satisfied,
                message=action_result.message,
                reversible=planned.risk.reversible,
                rollback_strategy=planned.risk.rollback_strategy,
                tool_id=tool_id,
                package=package,
                strategy=strategy,
                risk_level=planned.risk.risk_level.value,
            )
        )
    return tuple(outcomes)
