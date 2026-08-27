"""HistoryStore domain models (spec §9).

Pure data — ``infrastructure/state/history_store.py`` does the actual
append/read I/O. ``plan_reversible`` (on the record) is descriptive
metadata about the plan as a whole; ``reversible``/``rollback_strategy``
(on each outcome) are what ``RollbackManager`` actually acts on — spec
§11: never claim rollback is available when it is not, so eligibility is
checked per action, not assumed from the aggregate flag. ``tool_id``/
``package``/``strategy`` carry just enough detail to reconstruct the
one rollback strategy Hallfix has today (``"remove_package"``); nothing
here is guessed or reverse-engineered from ``message`` text — values not
populated at record time are ``None``.
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
    reversible: bool = False
    rollback_strategy: str | None = None
    tool_id: str | None = None
    package: str | None = None
    strategy: str | None = None
    risk_level: str | None = None

    @property
    def rollback_eligible(self) -> bool:
        return (
            self.succeeded
            and not self.already_satisfied
            and self.reversible
            and self.rollback_strategy is not None
        )


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

    @property
    def rollback_eligible_outcomes(self) -> tuple[ActionOutcome, ...]:
        return tuple(o for o in self.action_outcomes if o.rollback_eligible)

    @property
    def is_rollback_eligible(self) -> bool:
        return not self.dry_run and bool(self.rollback_eligible_outcomes)
