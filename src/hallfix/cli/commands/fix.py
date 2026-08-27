"""``hallfix repair`` / ``hallfix fix <diagnostic-id>`` (spec §43).

Always diagnoses first — both commands run the full doctor pass before
touching anything, per spec §43's "Always diagnose first." A fix is
applied through the identical Planner -> SafetyPolicy -> confirmation ->
Executor -> History path as a tool/profile install; there is no separate
"apply a fix" mechanism (spec §84: never bypass the Planner).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console

from hallfix.application.doctor import run_doctor
from hallfix.application.executor import Executor
from hallfix.application.planner import Planner
from hallfix.cli.confirmation import resolve_confirmation
from hallfix.cli.history_recording import build_action_outcomes
from hallfix.cli.rendering import render_execution_result, render_plan_human
from hallfix.detectors.system import SystemDetector
from hallfix.domain.diagnostics.engine import aggregate_health
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import Severity
from hallfix.domain.models.system import SystemContext
from hallfix.domain.registries.fix_registry import FixRegistry
from hallfix.domain.safety.policy import SafetyPolicy
from hallfix.infrastructure.commands.runner import PrivilegedCommandRunner, SubprocessCommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.history_store import HistoryStore


def _detect_system() -> SystemContext:
    return SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()


def _fixable_results() -> tuple[DiagnosticResult, ...]:
    results = run_doctor(command_runner=SubprocessCommandRunner())
    return tuple(r for r in results if r.fix_available and r.fix_id)


def _apply_fix(ctx: typer.Context, fix_id: str, diagnostic_id: str) -> bool:
    """Returns True if the fix succeeded (or was a no-op requiring no action)."""
    cli_ctx = ctx.obj
    registry = FixRegistry()
    fix = registry.get(fix_id)
    if fix is None:
        typer.secho(f"No fix registered for {fix_id!r}.", fg=typer.colors.RED, err=True)
        return False

    system_context = _detect_system()
    planner = Planner(command_runner=SubprocessCommandRunner())
    plan = planner.plan_fix(fix, system_context)

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    history = HistoryStore()
    command_label = f"fix {diagnostic_id}"

    if plan.is_noop:
        console.print(plan.description)
        history.append(
            command=command_label,
            plan_id=plan.id,
            plan_description=plan.description,
            dry_run=False,
            plan_reversible=plan.reversible,
        )
        return True

    dry_run = bool(cli_ctx and cli_ctx.dry_run)
    if dry_run:
        render_plan_human(console, plan)
        history.append(
            command=command_label,
            plan_id=plan.id,
            plan_description=plan.description,
            dry_run=True,
            plan_reversible=plan.reversible,
        )
        return True

    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(
        plan, decision, yes=bool(cli_ctx and cli_ctx.yes), console=console
    )
    if not outcome.proceed:
        typer.secho(outcome.reason or "Aborted.", fg=typer.colors.YELLOW, err=True)
        return False

    running_as_root = system_context.sudo.running_as_root
    command_runner = PrivilegedCommandRunner(
        inner=SubprocessCommandRunner(), running_as_root=running_as_root
    )
    executor = Executor(command_runner=command_runner, tool_registry=load_tool_registry())
    result = executor.execute_plan(plan, dry_run=False)

    history.append(
        command=command_label,
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

    return result.fully_succeeded


def repair(ctx: typer.Context) -> None:
    """Diagnose, then apply every automatically-fixable LOW-risk issue found."""
    fixable = _fixable_results()
    if not fixable:
        typer.echo("No automatically-fixable issues detected.")
        return

    typer.echo("Detected:\n")
    for result in fixable:
        typer.echo(f"{result.id}  {result.title}: {result.description}")
    typer.echo("")

    all_ok = True
    for result in fixable:
        if not _apply_fix(ctx, result.fix_id or "", result.id):  # fix_id checked by fix_available
            all_ok = False

    if not all_ok:
        raise typer.Exit(code=1)


def fix(ctx: typer.Context, diagnostic_id: str) -> None:
    """Diagnose, then apply the fix for one specific issue."""
    results = run_doctor(command_runner=SubprocessCommandRunner())
    result = next((r for r in results if r.id == diagnostic_id), None)

    if result is None:
        typer.secho(f"No such diagnostic: {diagnostic_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if result.severity in (Severity.OK, Severity.INFO):
        # Nothing is actually wrong — this is a success state, not a
        # limitation, so it must not be conflated with "Hallfix can't fix
        # this category of problem" below.
        typer.echo(f"{diagnostic_id}: {result.description}")
        typer.echo("Nothing to fix.")
        return

    if not result.fix_available or not result.fix_id:
        health = aggregate_health((result,))
        typer.echo(f"{diagnostic_id}: {result.description} (severity {result.severity.value})")
        typer.echo(f"No automated fix available for this issue (health impact: {health.value}).")
        raise typer.Exit(code=1)

    if not _apply_fix(ctx, result.fix_id, diagnostic_id):
        raise typer.Exit(code=1)
