"""Outcome of actually running a plan (spec §50/§67).

Pure data — the Executor (application layer) populates these; nothing
here performs I/O. Kept separate per action (``ActionExecutionResult``) so
partial failure is representable: one action failing does not collapse
the whole result into an undifferentiated "it broke".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hallfix.domain.models.tool import ToolVerificationResult
from hallfix.domain.planning.action import Action


@dataclass(frozen=True, slots=True)
class ActionExecutionResult:
    action: Action
    succeeded: bool
    already_satisfied: bool
    message: str
    dry_run: bool
    verification: ToolVerificationResult | None = None


@dataclass(frozen=True, slots=True)
class PlanExecutionResult:
    plan_id: str
    dry_run: bool
    action_results: tuple[ActionExecutionResult, ...] = field(default_factory=tuple)

    @property
    def succeeded_count(self) -> int:
        return sum(1 for r in self.action_results if r.succeeded)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.action_results if not r.succeeded)

    @property
    def fully_succeeded(self) -> bool:
        return all(r.succeeded for r in self.action_results)
