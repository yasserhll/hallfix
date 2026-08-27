"""HistoryStore domain models (spec §9).

Pure data — ``infrastructure/state/history_store.py`` does the actual
append/read I/O. ``plan_reversible`` is recorded as descriptive metadata
about the plan's actions only; it is deliberately **not** the same claim
as "rollback is available" (spec §11) — there is no RollbackManager yet
(Phase 11), so nothing in Hallfix should present a reversible plan as
something the user can actually roll back today.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ActionOutcome:
    action_type: str
    succeeded: bool
    already_satisfied: bool
    message: str


@dataclass(frozen=True, slots=True)
class OperationRecord:
    id: str
    timestamp: datetime
    command: str
    plan_id: str
    plan_description: str
    dry_run: bool
    plan_reversible: bool
    action_outcomes: tuple[ActionOutcome, ...] = field(default_factory=tuple)

    @property
    def succeeded_count(self) -> int:
        return sum(1 for o in self.action_outcomes if o.succeeded)

    @property
    def failed_count(self) -> int:
        return sum(1 for o in self.action_outcomes if not o.succeeded)
