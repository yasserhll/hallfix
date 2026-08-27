"""ExecutionPlan (spec §5) — the single representation of "what will happen".

Every field spec §5 lists as plan-level metadata (``risk_level``,
``requires_root``, ``requires_network``, ``reversible``,
``estimated_changes``) is a *derived property* here, computed from
``planned_actions``, never an independently-settable field — this was the
one non-negotiable change flagged in the Phase 0 architecture review:
letting these drift out of sync with what the actions actually do would
silently defeat SafetyPolicy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.planning.action import Action, ActionRisk

_RISK_RANK: dict[RiskLevel, int] = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


@dataclass(frozen=True, slots=True)
class PlannedAction:
    action: Action
    risk: ActionRisk
    description: str


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    id: str
    created_at: datetime
    description: str
    planned_actions: tuple[PlannedAction, ...] = field(default_factory=tuple)

    @property
    def risk_level(self) -> RiskLevel:
        if not self.planned_actions:
            return RiskLevel.LOW
        return max((pa.risk.risk_level for pa in self.planned_actions), key=_RISK_RANK.__getitem__)

    @property
    def requires_root(self) -> bool:
        return any(pa.risk.requires_root for pa in self.planned_actions)

    @property
    def requires_network(self) -> bool:
        return any(pa.risk.requires_network for pa in self.planned_actions)

    @property
    def reversible(self) -> bool:
        # Vacuously true for a no-op plan: nothing happened, so there is
        # nothing to reverse — consistent with `all()` over an empty
        # sequence, not a special case.
        return all(pa.risk.reversible for pa in self.planned_actions)

    @property
    def estimated_changes(self) -> int:
        return len(self.planned_actions)

    @property
    def is_noop(self) -> bool:
        return not self.planned_actions
