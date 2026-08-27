"""SafetyPolicy (spec §44): the single, central place safety checks live.

Pure — evaluates already-computed ``ActionRisk``/``ExecutionPlan`` data,
no I/O. HIGH and CRITICAL risk always require confirmation and this is
not configurable (spec §58: "Do NOT allow configuration to disable
mandatory safety rules") — there is deliberately no parameter here that
could turn that off.
"""

from __future__ import annotations

from dataclasses import dataclass

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.planning.execution_plan import ExecutionPlan

_CONFIRMATION_REQUIRED_AT = frozenset({RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL})


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    requires_confirmation: bool
    blocked: bool
    reasons: tuple[str, ...]


class SafetyPolicy:
    def evaluate_plan(self, plan: ExecutionPlan) -> PolicyDecision:
        if plan.is_noop:
            return PolicyDecision(requires_confirmation=False, blocked=False, reasons=())

        reasons: list[str] = []
        risk = plan.risk_level
        if risk in _CONFIRMATION_REQUIRED_AT:
            reasons.append(f"{risk.value} risk actions require explicit confirmation")
        if plan.requires_root:
            reasons.append("administrator privileges are required")

        return PolicyDecision(
            requires_confirmation=risk in _CONFIRMATION_REQUIRED_AT,
            blocked=False,
            reasons=tuple(reasons),
        )

    def allows_auto_confirm(self, plan: ExecutionPlan) -> bool:
        """Whether ``--yes`` may bypass the confirmation prompt for this plan.

        spec §60: ``--yes`` must NOT bypass HIGH/CRITICAL confirmations.
        """
        return plan.risk_level not in (RiskLevel.HIGH, RiskLevel.CRITICAL)
