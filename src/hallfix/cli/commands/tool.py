"""``hallfix tool`` command group — read-only for now.

``install``/``remove`` aren't here yet: they require Planner + SafetyPolicy
+ Executor (Phase 5/6), and Hallfix never bypasses the Planner for
convenience (spec §84). This group only reads the registry, resolves
compatibility, and verifies what's already on the system.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from hallfix.detectors.system import SystemDetector
from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.system import SystemContext
from hallfix.domain.models.tool import ToolDefinition
from hallfix.domain.registries.compatibility import (
    assess_compatibility,
    resolve_installation_strategy,
)
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry

app = typer.Typer(name="tool", help="Browse and inspect available tools.")


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


@app.command("info")
def info(tool_id: str) -> None:
    """Show detail for one tool, including compatibility and current install state."""
    registry = _load_registry()
    tool = registry.get(tool_id)
    if tool is None:
        typer.secho(f"No such tool: {tool_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    _print_tool_info(Console(), tool, _detect_system())
