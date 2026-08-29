"""``hallfix snapshot`` (spec §10). Builds and persists a point-in-time
record of Hallfix's own state. Never modifies the target system — only
writes to Hallfix's own snapshot store under ``state_home()/snapshots/``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from hallfix.application.snapshot import build_snapshot
from hallfix.detectors.system import SystemDetector
from hallfix.domain.exceptions import RegistryError
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.snapshot_store import SnapshotStore
from hallfix.infrastructure.state.store import StateStore


def snapshot(ctx: typer.Context) -> None:
    """Record a snapshot of Hallfix's current view of this system."""
    cli_ctx = ctx.obj
    try:
        tool_registry = load_tool_registry()
    except RegistryError as exc:
        typer.secho(f"Tool registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    context = SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()
    record = build_snapshot(
        context, tool_registry, StateStore(), command_runner=SubprocessCommandRunner()
    )
    path = SnapshotStore().save(record)

    if cli_ctx is not None and cli_ctx.json_output:
        typer.echo(json.dumps(dataclasses.asdict(record), default=str, indent=2))
        return

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    console.print(f"[bold]Snapshot {record.id}[/bold] saved to {path}")
    console.print(
        f"{context.distribution.pretty_name or context.distribution.id} "
        f"({context.architecture}, kernel {context.kernel})"
    )

    if not record.managed_tools:
        console.print("\nNo Hallfix-managed tools recorded yet.")
        return

    table = Table()
    table.add_column("Tool")
    table.add_column("Version")
    table.add_column("Installed for")
    for entry in record.managed_tools:
        table.add_row(
            entry.tool_id,
            entry.installed_version or "unknown",
            ", ".join(entry.installed_for) or "-",
        )
    console.print(table)
