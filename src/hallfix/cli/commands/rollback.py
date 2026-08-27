"""``hallfix rollback [operation-id]`` (spec §11).

Rollback goes through the identical Planner -> SafetyPolicy ->
confirmation -> Executor -> History path as everything else (spec §84).
Rollback itself creates a new history operation — it never edits or
removes the record being rolled back.
"""

from __future__ import annotations

import dataclasses
import json

import typer
from rich.console import Console

from hallfix.application.executor import Executor
from hallfix.application.planner import Planner
from hallfix.cli.confirmation import resolve_confirmation
from hallfix.cli.history_recording import build_action_outcomes
from hallfix.cli.rendering import render_execution_result, render_plan_human
from hallfix.detectors.system import SystemDetector
from hallfix.domain.models.history import OperationRecord
from hallfix.domain.safety.policy import SafetyPolicy
from hallfix.infrastructure.commands.runner import PrivilegedCommandRunner, SubprocessCommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.history_store import HistoryStore
from hallfix.infrastructure.state.store import StateStore


def _most_recent_rollback_eligible(records: tuple[OperationRecord, ...]) -> OperationRecord | None:
    # Excludes rollback operations themselves — undoing an undo isn't the
    # intended default target; a user can still target one explicitly by id.
    for record in reversed(records):
        if record.command.startswith("rollback "):
            continue
        if record.is_rollback_eligible:
            return record
    return None


def rollback(ctx: typer.Context, operation_id: str | None = typer.Argument(None)) -> None:
    """Undo the most recent rollback-eligible operation, or a specific one by id."""
    cli_ctx = ctx.obj
    history = HistoryStore()
    records = history.list_all()

    if operation_id is None:
        record = _most_recent_rollback_eligible(records)
        if record is None:
            typer.echo("No rollback-eligible operations found in history.")
            return
    else:
        record = next((r for r in records if r.id == operation_id), None)
        if record is None:
            typer.secho(f"No such operation: {operation_id!r}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        if not record.is_rollback_eligible:
            typer.echo(f"{record.id} has nothing that can be automatically rolled back.")
            raise typer.Exit(code=1)

    planner = Planner(command_runner=SubprocessCommandRunner())
    plan = planner.plan_rollback(record)

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)

    if plan.is_noop:
        console.print(plan.description)
        raise typer.Exit(code=1)

    dry_run = bool(cli_ctx and cli_ctx.dry_run)
    if dry_run:
        render_plan_human(console, plan)
        return

    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(
        plan, decision, yes=bool(cli_ctx and cli_ctx.yes), console=console
    )
    if not outcome.proceed:
        typer.secho(outcome.reason or "Aborted.", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)

    system = SystemDetector(command_runner=SubprocessCommandRunner()).detect()
    command_runner = PrivilegedCommandRunner(
        inner=SubprocessCommandRunner(), running_as_root=system.sudo.running_as_root
    )
    executor = Executor(
        command_runner=command_runner,
        tool_registry=load_tool_registry(),
        state_store=StateStore(),
    )
    result = executor.execute_plan(plan, dry_run=False)

    # Rollback creates a *new* history operation — the record being rolled
    # back is never edited or removed (spec §11).
    history.append(
        command=f"rollback {record.id}",
        plan_id=plan.id,
        plan_description=plan.description,
        dry_run=False,
        plan_reversible=plan.reversible,
        action_outcomes=build_action_outcomes(plan, result),
    )

    if cli_ctx is not None and cli_ctx.json_output:
        typer.echo(json.dumps(dataclasses.asdict(result), default=str, indent=2))
    else:
        render_execution_result(console, result)

    if not result.fully_succeeded:
        raise typer.Exit(code=1)
