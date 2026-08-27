"""``hallfix tool`` command group.

``list``/``search``/``info`` are read-only. ``install``/``remove`` are the
first commands in Hallfix that can actually modify the system — they go
through Planner -> SafetyPolicy -> confirmation -> Executor and nothing
else; Hallfix never bypasses that path for convenience (spec §84).
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from hallfix.application.executor import Executor
from hallfix.application.planner import Planner
from hallfix.cli.confirmation import resolve_confirmation
from hallfix.cli.history_recording import build_action_outcomes
from hallfix.cli.rendering import render_execution_result, render_plan_human
from hallfix.detectors.system import SystemDetector
from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.system import SystemContext
from hallfix.domain.models.tool import ToolDefinition
from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.registries.compatibility import (
    assess_compatibility,
    resolve_installation_strategy,
)
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.domain.safety.policy import SafetyPolicy
from hallfix.infrastructure.commands.runner import PrivilegedCommandRunner, SubprocessCommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.history_store import HistoryStore
from hallfix.infrastructure.state.store import StateStore

app = typer.Typer(name="tool", help="Browse, install, and remove tools.")


def _load_registry() -> ToolRegistry:
    try:
        return load_tool_registry()
    except RegistryError as exc:
        typer.secho(f"Tool registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _detect_system() -> SystemContext:
    return SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()


@app.command("list")
def list_tools(
    category: str | None = typer.Option(None, "--category", help="Filter by category."),
    profile: str | None = typer.Option(None, "--profile", help="Filter by profile."),
) -> None:
    """List tools in the registry, with compatibility for this system."""
    registry = _load_registry()
    system_context = _detect_system()

    tools = registry.list_all()
    if category:
        tools = tuple(t for t in tools if t.category == category)
    if profile:
        tools = tuple(t for t in tools if profile in t.profiles)

    table = Table(title=f"Tools ({len(tools)})")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Compatibility")
    for tool in tools:
        support = assess_compatibility(tool, system_context)
        table.add_row(tool.id, tool.name, tool.category, support.value)
    Console().print(table)


@app.command("search")
def search_tools(query: str) -> None:
    """Search tools by id, name, or description."""
    registry = _load_registry()
    results = registry.search(query)
    if not results:
        typer.echo(f"No tools matched {query!r}.")
        return
    for tool in results:
        typer.echo(f"{tool.id:<15} {tool.name} — {tool.description}")


def _print_tool_info(console: Console, tool: ToolDefinition, ctx: SystemContext) -> None:
    console.print(f"[bold]{tool.name}[/bold] ({tool.id})")
    console.print(tool.description)
    console.print(
        f"Category: {tool.category}  Risk: {tool.risk_level.value}  "
        f"Requires root: {tool.requires_root}  Optional: {tool.optional}"
    )

    support = assess_compatibility(tool, ctx)
    strategy = resolve_installation_strategy(tool, ctx)
    console.print(f"Compatibility on this system: {support.value}")
    if strategy is not None:
        package = tool.package_mappings[strategy]
        console.print(f"Would install via: {strategy.value} (package: {package})")
    else:
        console.print("No usable installation strategy for this system.")

    verifier = ToolVerifier(command_runner=SubprocessCommandRunner())
    verification = verifier.verify(tool)
    if verification.executable_found:
        console.print(
            f"Currently installed: yes (version {verification.installed_version or 'unknown'})"
        )
    else:
        console.print("Currently installed: no")

    tool_state = StateStore().get_tool_state(tool.id)
    if tool_state is None:
        console.print("Managed by Hallfix: unknown (not yet observed by Hallfix)")
    elif tool_state.installed_by_hallfix:
        console.print("Managed by Hallfix: yes (Hallfix installed this)")
    else:
        console.print("Managed by Hallfix: no (was already present before Hallfix)")


@app.command("info")
def info(tool_id: str) -> None:
    """Show detail for one tool, including compatibility and current install state."""
    registry = _load_registry()
    tool = registry.get(tool_id)
    if tool is None:
        typer.secho(f"No such tool: {tool_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    _print_tool_info(Console(), tool, _detect_system())


_PlanBuilder = Callable[[Planner, ToolDefinition, SystemContext], ExecutionPlan]


def _run_mutation(
    ctx: typer.Context,
    tool_id: str,
    *,
    command_label: str,
    build_plan: _PlanBuilder,
) -> None:
    cli_ctx = ctx.obj
    registry = _load_registry()
    tool = registry.get(tool_id)
    if tool is None:
        typer.secho(f"No such tool: {tool_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    system_context = _detect_system()
    planner = Planner(command_runner=SubprocessCommandRunner())
    plan = build_plan(planner, tool, system_context)

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    history = HistoryStore()

    if plan.is_noop:
        console.print(plan.description)
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

    running_as_root = system_context.sudo.running_as_root
    command_runner = PrivilegedCommandRunner(
        inner=SubprocessCommandRunner(), running_as_root=running_as_root
    )
    executor = Executor(
        command_runner=command_runner, tool_registry=registry, state_store=StateStore()
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


@app.command("install")
def install(ctx: typer.Context, tool_id: str) -> None:
    """Install a tool: Planner -> SafetyPolicy -> confirmation -> Executor."""
    _run_mutation(
        ctx,
        tool_id,
        command_label=f"tool install {tool_id}",
        build_plan=lambda planner, tool, sc: planner.plan_tool_install(tool, sc),
    )


@app.command("remove")
def remove(ctx: typer.Context, tool_id: str) -> None:
    """Remove a tool: Planner -> SafetyPolicy -> confirmation -> Executor."""
    _run_mutation(
        ctx,
        tool_id,
        command_label=f"tool remove {tool_id}",
        build_plan=lambda planner, tool, sc: planner.plan_tool_remove(tool, sc),
    )
