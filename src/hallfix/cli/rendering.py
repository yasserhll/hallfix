"""Shared plan/result rendering, used by ``tool.py``, ``plan.py``, and
``profile.py`` — pure presentation, no business logic.
"""

from __future__ import annotations

from rich.console import Console

from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.planning.execution_result import PlanExecutionResult


def render_plan_human(console: Console, plan: ExecutionPlan) -> None:
    console.print("[bold]HALLFIX EXECUTION PLAN[/bold]\n")
    console.print(f"Plan: {plan.id}")
    console.print(plan.description)

    if plan.notes:
        console.print("\nNotes:")
        for note in plan.notes:
            console.print(f"  - {note}")

    if plan.is_noop:
        console.print("\nNo actions required. No changes were made.")
        return

    console.print("\nActions:\n")
    for planned in plan.planned_actions:
        console.print(f"[{planned.risk.risk_level.value}] {planned.description}")
    console.print(f"\nRequires administrator privileges: {'YES' if plan.requires_root else 'NO'}")
    console.print(f"Requires Internet: {'YES' if plan.requires_network else 'NO'}")
    console.print(f"Reversible: {'YES' if plan.reversible else 'NO'}")
    console.print("\nNo changes were made.")


def render_execution_result(console: Console, result: PlanExecutionResult) -> None:
    for action_result in result.action_results:
        marker = "✓" if action_result.succeeded else "✗"
        console.print(
            f"{marker} {action_result.message.strip() or action_result.action.type.value}"
        )
        if action_result.verification is not None:
            v = action_result.verification
            if v.executable_found:
                console.print(f"  ✓ Executable found (version {v.installed_version or 'unknown'})")
            else:
                console.print("  ✗ Executable not found after installation")

    console.print(f"\nSuccessful: {result.succeeded_count}  Failed: {result.failed_count}")
    if not result.fully_succeeded:
        console.print("Completed with warnings.")
