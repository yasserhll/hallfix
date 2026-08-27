"""``hallfix profile`` command group (spec §27/§35/§37).

``install`` reuses the exact same Planner -> SafetyPolicy -> confirmation
-> Executor path as ``tool install`` — spec §35: custom profiles (and, by
the same reasoning, every profile) must never get a second installation
system. ``profile remove`` deliberately does not exist yet: spec §37's
shared-dependency safety check ("Docker is also used by: Developer,
DevOps") needs a notion of "is this profile currently considered
installed" that Hallfix doesn't track yet — out of scope for this phase.
"""

from __future__ import annotations

import dataclasses
import json
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
from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.system import SystemContext
from hallfix.domain.registries.compatibility import assess_compatibility
from hallfix.domain.registries.profile_diff import compute_profile_diff
from hallfix.domain.registries.profile_registry import ProfileRegistry
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.domain.safety.policy import SafetyPolicy
from hallfix.infrastructure.commands.runner import PrivilegedCommandRunner, SubprocessCommandRunner
from hallfix.infrastructure.registries.profile_registry_loader import load_profile_registry
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.history_store import HistoryStore
from hallfix.infrastructure.state.store import StateStore

app = typer.Typer(name="profile", help="Browse and install professional profiles.")


def _load_profile_registry() -> ProfileRegistry:
    try:
        return load_profile_registry()
    except RegistryError as exc:
        typer.secho(f"Profile registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _load_tool_registry() -> ToolRegistry:
    try:
        return load_tool_registry()
    except RegistryError as exc:
        typer.secho(f"Tool registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _detect_system() -> SystemContext:
    return SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()


def _require_profile(registry: ProfileRegistry, profile_id: str) -> ProfileDefinition:
    profile = registry.get(profile_id)
    if profile is None:
        typer.secho(f"No such profile: {profile_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    return profile


@app.command("list")
def list_profiles() -> None:
    """List available profiles."""
    registry = _load_profile_registry()
    table = Table(title=f"Profiles ({len(registry)})")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Tools")
    table.add_column("Description")
    for profile in registry.list_all():
        table.add_row(profile.id, profile.name, str(len(profile.tools)), profile.description)
    Console().print(table)


@app.command("show")
def show(profile_id: str) -> None:
    """Show a profile's tools and their compatibility with this system."""
    profile = _require_profile(_load_profile_registry(), profile_id)
    tool_registry = _load_tool_registry()
    ctx = _detect_system()

    console = Console()
    console.print(f"[bold]{profile.name}[/bold] ({profile.id})")
    console.print(profile.description)
    if profile.categories:
        console.print(f"Categories: {', '.join(profile.categories)}")

    table = Table()
    table.add_column("Tool")
    table.add_column("Compatibility")
    for tool_id in profile.tools:
        tool = tool_registry.get(tool_id)
        if tool is None:
            table.add_row(tool_id, "UNKNOWN TOOL")
            continue
        table.add_row(tool.name, assess_compatibility(tool, ctx).value)
    console.print(table)


@app.command("diff")
def diff(profile_id: str) -> None:
    """Show installed/missing/version-mismatched tools. Never modifies the system."""
    profile = _require_profile(_load_profile_registry(), profile_id)
    tool_registry = _load_tool_registry()
    verifier = ToolVerifier(command_runner=SubprocessCommandRunner())

    verifications = {}
    for tool_id in profile.tools:
        tool = tool_registry.get(tool_id)
        if tool is not None:
            verifications[tool_id] = verifier.verify(tool)

    result = compute_profile_diff(profile, tool_registry, verifications)

    console = Console()
    console.print(f"[bold]{profile.name} Profile[/bold]\n")
    if result.installed:
        console.print("Installed:")
        for entry in result.installed:
            console.print(f"✓ {entry.tool_name}")
        console.print()
    if result.missing:
        console.print("Missing:")
        for entry in result.missing:
            console.print(f"✗ {entry.tool_name}")
        console.print()
    if result.version_mismatches:
        console.print("Version mismatch:")
        for entry in result.version_mismatches:
            console.print(f"⚠ {entry.tool_name} {entry.installed_version}")
            console.print(f"  Recommended >= {entry.recommended_version}")
        console.print()
    if result.unknown_tools:
        console.print("Unknown tools (not in registry):")
        for entry in result.unknown_tools:
            console.print(f"? {entry.tool_id}")


@app.command("install")
def install(
    ctx: typer.Context,
    profile_id: str,
    tools: str = typer.Option(
        "", "--tools", help="Comma-separated tool ids (required for the 'custom' profile)."
    ),
) -> None:
    """Install a profile: Planner -> SafetyPolicy -> confirmation -> Executor."""
    if profile_id == "custom":
        tool_ids = tuple(t.strip() for t in tools.split(",") if t.strip())
        if not tool_ids:
            typer.secho(
                "The 'custom' profile requires --tools (comma-separated tool ids).",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        profile = ProfileDefinition(
            id="custom", name="Custom", description="User-selected tools.", tools=tool_ids
        )
    else:
        profile = _require_profile(_load_profile_registry(), profile_id)

    cli_ctx = ctx.obj
    tool_registry = _load_tool_registry()
    system_context = _detect_system()
    planner = Planner(command_runner=SubprocessCommandRunner())
    plan = planner.plan_profile_install(profile, tool_registry, system_context)

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    history = HistoryStore()
    command_label = f"profile install {profile_id}"

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

    running_as_root = system_context.sudo.running_as_root
    command_runner = PrivilegedCommandRunner(
        inner=SubprocessCommandRunner(), running_as_root=running_as_root
    )
    executor = Executor(
        command_runner=command_runner, tool_registry=tool_registry, state_store=StateStore()
    )
    result = executor.execute_plan(plan, dry_run=False, profile_id=profile.id)

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
