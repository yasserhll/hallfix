"""RiskEvaluator: the single place that decides an action's risk metadata.

Pure — no I/O, no CommandRunner. Takes an already-built ``Action`` (which
itself already carries the declaring tool's risk_level, copied in by the
Planner at construction time) and returns structural risk facts derived
from the *action type*: does this kind of action need root, does it touch
the network, can Hallfix actually reverse it.
"""

from __future__ import annotations

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.planning.action import (
    Action,
    ActionRisk,
    InstallPackageAction,
    RemovePackageAction,
    RepairPackageManagerAction,
    UpdatePackageIndexAction,
)


class RiskEvaluator:
    def evaluate(self, action: Action) -> ActionRisk:
        if isinstance(action, InstallPackageAction):
            return ActionRisk(
                risk_level=action.tool_risk_level,
                requires_root=True,
                requires_network=True,
                reversible=True,
                rollback_strategy="remove_package",
            )
        if isinstance(action, RemovePackageAction):
            # Not claimed reversible: Hallfix doesn't yet track the exact
            # prior version/config to restore (spec §11: never claim
            # rollback is available when it is not).
            return ActionRisk(
                risk_level=action.tool_risk_level,
                requires_root=True,
                requires_network=False,
                reversible=False,
                rollback_strategy=None,
            )
        if isinstance(action, UpdatePackageIndexAction):
            return ActionRisk(
                risk_level=RiskLevel.LOW,
                requires_root=True,
                requires_network=True,
                reversible=True,
                rollback_strategy=None,
            )
        if isinstance(action, RepairPackageManagerAction):
            # Not claimed reversible: "un-configuring" packages back to a
            # half-installed state isn't a real rollback (spec §11).
            return ActionRisk(
                risk_level=action.fix_risk_level,
                requires_root=True,
                requires_network=False,
                reversible=False,
                rollback_strategy=None,
            )
        msg = f"RiskEvaluator: no rule for action type {type(action).__name__}"  # pragma: no cover
        raise NotImplementedError(msg)  # pragma: no cover
