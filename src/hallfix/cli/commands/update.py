"""``hallfix update`` command group (spec §54): three distinct operations,
never mixed automatically — "Distinguish: Hallfix update / System update /
Tool update ... Never mix all three automatically."

``system``/``tools`` go through the exact same
Planner -> SafetyPolicy -> confirmation -> Executor path as every other
mutating command. ``hallfix`` (self-update) is honestly reported as
unavailable rather than faked — spec §84: "Never invent support that has
not been tested," and Hallfix has no packaging/distribution channel yet
(source install only).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console

from hallfix.application.executor import Executor
from hallfix.application.planner import Planner
from hallfix.cli.confirmation import resolve_confirmation
from hallfix.cli.history_recording import build_action_outcomes
from hallfix.cli.rendering import render_execution_result, render_plan_human
from hallfix.detectors.system import SystemDetector
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.system import SystemContext
from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.domain.safety.policy import SafetyPolicy
from hallfix.infrastructure.commands.runner import PrivilegedCommandRunner, SubprocessCommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.history_store import HistoryStore
from hallfix.infrastructure.state.store import StateStore

app = typer.Typer(
    name="update", help="Update Hallfix itself, the system, or Hallfix-managed tools."
)

_SELF_UPDATE_MESSAGE = (
    "Hallfix has no distribution channel yet (source install only) — "
    "self-update isn't available. To update from source, run `git pull` "
    "in your clone, then `pip install -e .` again. See docs/installation.md."
)


def _detect_system() -> SystemContext:
    return SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()


def _load_registry() -> ToolRegistry:
    try:
        return load_tool_registry()
    except RegistryError as exc:
        typer.secho(f"Tool registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _run_plan(
    ctx: typer.Context,
    plan: ExecutionPlan,
    *,
    command_label: str,
    system_context: SystemContext,
    tool_registry: ToolRegistry,
) -> None:
    cli_ctx = ctx.obj
    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    history = HistoryStore()

    if plan.is_noop:
        console.print(plan.description)
        for note in plan.notes:
            console.print(f"  - {note}")
        console.print("No changes were made.")
        history.append(
            command=command_label,
            plan_id=plan.id,
            plan_description=plan.description,
            dry_run=False,
            plan_reversible=plan.reversible,
        )
        return

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
        return

    decision = SafetyPolicy().evaluate_plan(plan)
    outcome = resolve_confirmation(
        plan, decision, yes=bool(cli_ctx and cli_ctx.yes), console=console
    )
    if not outcome.proceed:
        typer.secho(outcome.reason or "Aborted.", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)

    command_runner = PrivilegedCommandRunner(
        inner=SubprocessCommandRunner(), running_as_root=system_context.sudo.running_as_root
    )
    executor = Executor(
        command_runner=command_runner, tool_registry=tool_registry, state_store=StateStore()
    )
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

    if not result.fully_succeeded:
        raise typer.Exit(code=1)


@app.command("system")
def system(ctx: typer.Context) -> None:
    """Upgrade all system packages via the native package manager."""
    system_context = _detect_system()
    tool_registry = _load_registry()
    planner = Planner(command_runner=SubprocessCommandRunner())
    plan = planner.plan_system_upgrade(system_context)
    _run_plan(
        ctx,
        plan,
        command_label="update system",
        system_context=system_context,
        tool_registry=tool_registry,
    )


@app.command("tools")
def tools(ctx: typer.Context) -> None:
    """Update every Hallfix-managed tool to the latest available version."""
    system_context = _detect_system()
    tool_registry = _load_registry()
    planner = Planner(command_runner=SubprocessCommandRunner())
    plan = planner.plan_tools_update(tool_registry, system_context, StateStore())
    _run_plan(
        ctx,
        plan,
        command_label="update tools",
        system_context=system_context,
        tool_registry=tool_registry,
    )


@app.command("hallfix")
def update_hallfix(ctx: typer.Context) -> None:
    """Update Hallfix itself. Not available yet — see docs/installation.md."""
    cli_ctx = ctx.obj
    if cli_ctx is not None and cli_ctx.json_output:
        typer.echo(json.dumps({"available": False, "message": _SELF_UPDATE_MESSAGE}, indent=2))
        return
    Console().print(_SELF_UPDATE_MESSAGE)
