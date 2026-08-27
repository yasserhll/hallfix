"""``hallfix plan`` — build and display an ExecutionPlan. Never executes it.

There is no Executor yet (Phase 6), so every plan shown here is
inherently a dry-run: building a plan only ever reads system state
(spec §6: dry-run must use the same Planner as real execution — trivially
true right now since nothing *but* dry-run exists).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console

from hallfix.application.planner import Planner
from hallfix.detectors.system import SystemDetector
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.system import SystemContext
from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.safety.policy import SafetyPolicy
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry

app = typer.Typer(name="plan", help="Build and display an execution plan (never applies it).")


def _render_human(console: Console, plan: ExecutionPlan) -> None:
    console.print("[bold]HALLFIX EXECUTION PLAN[/bold]\n")
    console.print(f"Plan: {plan.id}")
    console.print(plan.description)

    if plan.is_noop:
        console.print("\nNo actions required. No changes were made.")
        return

    console.print("\nActions:\n")
    for planned in plan.planned_actions:
        console.print(f"[{planned.risk.risk_level.value}] {planned.description}")

    console.print(f"\nRequires administrator privileges: {'YES' if plan.requires_root else 'NO'}")
    console.print(f"Requires Internet: {'YES' if plan.requires_network else 'NO'}")
    console.print(f"Reversible: {'YES' if plan.reversible else 'NO'}")
    console.print(f"Estimated changes: {plan.estimated_changes}")

    decision = SafetyPolicy().evaluate_plan(plan)
    if decision.requires_confirmation:
        console.print("\nThis plan requires explicit confirmation before it can be applied.")
        for reason in decision.reasons:
            console.print(f"  - {reason}")

    console.print("\nNo changes were made.")


def _render(ctx: typer.Context, plan: ExecutionPlan) -> None:
    cli_ctx = ctx.obj
    if cli_ctx is not None and cli_ctx.json_output:
        payload = dataclasses.asdict(plan)
        typer.echo(json.dumps(payload, default=str, indent=2))
        return
    _render_human(Console(no_color=cli_ctx.no_color if cli_ctx else False), plan)


def _build_planner() -> Planner:
    return Planner(command_runner=SubprocessCommandRunner())


def _detect_system() -> SystemContext:
    return SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()


@app.command("install")
def plan_install(ctx: typer.Context, tool_id: str) -> None:
    """Show the plan to install one tool (does not install it)."""
    try:
        registry = load_tool_registry()
    except RegistryError as exc:
        typer.secho(f"Tool registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    tool = registry.get(tool_id)
    if tool is None:
        typer.secho(f"No such tool: {tool_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    plan = _build_planner().plan_tool_install(tool, _detect_system())
    _render(ctx, plan)


@app.command("remove")
def plan_remove(ctx: typer.Context, tool_id: str) -> None:
    """Show the plan to remove one tool (does not remove it)."""
    try:
        registry = load_tool_registry()
    except RegistryError as exc:
        typer.secho(f"Tool registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    tool = registry.get(tool_id)
    if tool is None:
        typer.secho(f"No such tool: {tool_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    plan = _build_planner().plan_tool_remove(tool, _detect_system())
    _render(ctx, plan)


@app.command("refresh")
def plan_refresh(ctx: typer.Context) -> None:
    """Show the plan to refresh package metadata (does not refresh it)."""
    plan = _build_planner().plan_refresh_metadata(_detect_system())
    _render(ctx, plan)
