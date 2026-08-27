"""Confirmation: the boundary between SafetyPolicy's decision and the user's consent.

Added per the Phase 0 architecture review — the reference spec's own
diagram places Confirmation between SafetyPolicy and Executor, but never
gives it a component of its own, which risks the CLI ending up owning
confirmation logic (violating "CLI must not contain business logic").

Only the interface exists yet: a concrete interactive (CLI-prompt) and a
non-interactive (``--yes``, gated by ``SafetyPolicy.allows_auto_confirm``)
implementation arrive with the Executor in Phase 6, which is the first
component that actually needs to ask.
"""

from __future__ import annotations

from typing import Protocol

from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.safety.policy import PolicyDecision


class ConfirmationPrompt(Protocol):
    def confirm(self, plan: ExecutionPlan, decision: PolicyDecision) -> bool: ...
