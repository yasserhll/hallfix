"""Resolves whether a plan may proceed, given SafetyPolicy and ``--yes``.

The one place the CLI decides "do we have consent" — implements the
``ConfirmationPrompt`` protocol from ``domain/safety/confirmation.py``
against a real terminal. spec §60: ``--yes`` must never bypass HIGH/
CRITICAL confirmations; that's enforced by ``SafetyPolicy.allows_auto_confirm``,
not re-derived here.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.prompt import Confirm

from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.safety.policy import PolicyDecision, SafetyPolicy


@dataclass(frozen=True, slots=True)
class ConfirmationOutcome:
    proceed: bool
    reason: str | None = None


def resolve_confirmation(
    plan: ExecutionPlan,
    decision: PolicyDecision,
    *,
    yes: bool,
    console: Console,
) -> ConfirmationOutcome:
    if not decision.requires_confirmation:
        return ConfirmationOutcome(proceed=True)

    if yes:
        if SafetyPolicy().allows_auto_confirm(plan):
            return ConfirmationOutcome(proceed=True)
        return ConfirmationOutcome(
            proceed=False,
            reason=(
                f"{plan.risk_level.value} risk actions always require explicit, "
                f"interactive confirmation — --yes cannot bypass this."
            ),
        )

    console.print("\nThis plan requires confirmation:")
    for reason in decision.reasons:
        console.print(f"  - {reason}")
    if Confirm.ask("Proceed?", default=False):
        return ConfirmationOutcome(proceed=True)
    return ConfirmationOutcome(proceed=False, reason="Not confirmed by user.")
