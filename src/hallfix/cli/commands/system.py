"""``hallfix system`` command group.

Thin rendering layer only — all detection logic lives in
``hallfix.detectors``. This module builds a ``SystemDetector`` with real
infrastructure (subprocess-backed ``CommandRunner``, real internet check)
and prints/serializes its result; it makes no decisions of its own.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from hallfix.detectors.system import SystemDetector
from hallfix.domain.models.system import SystemContext
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner

app = typer.Typer(name="system", help="System detection and information.")


def _detect() -> SystemContext:
    return SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()


def _render_human(console: Console, ctx: SystemContext) -> None:
    console.print(f"[bold]{ctx.distribution.pretty_name or ctx.distribution.id}[/bold]")
    console.print(f"Kernel: {ctx.kernel}  Architecture: {ctx.architecture}")
    console.print(f"Environment: {ctx.environment.kind.value}")
    console.print(f"Hostname: {ctx.hostname}  User: {ctx.username}")

    table = Table(title="Hardware")
    table.add_column("Component")
    table.add_column("Detail")
    table.add_row("CPU", f"{ctx.cpu.model or 'unknown'} ({ctx.cpu.cores}c/{ctx.cpu.threads}t)")
    table.add_row("Memory", f"{ctx.memory.total_bytes / (1024**3):.1f} GiB total")
    # squashfs (snap packages, etc.) is a fixed-size read-only image and is
    # always ~100% "used" by design — real, but not useful disk-space signal
    # for a human glance. Full detail is still in --json output.
    for fs in ctx.disk.filesystems:
        if fs.filesystem_type == "squashfs":
            continue
        table.add_row(f"Disk {fs.mount_point}", f"{fs.usage_percent}% used ({fs.filesystem_type})")
    console.print(table)

    console.print(
        f"Package manager: {ctx.package_manager.kind.value}  "
        f"Sudo available: {ctx.sudo.available}  "
        f"Internet: {ctx.capabilities.internet_access}"
    )


@app.command("info")
def info(
    ctx: typer.Context,
) -> None:
    """Detect and display system information."""
    cli_ctx = ctx.obj
    system_context = _detect()

    if cli_ctx is not None and cli_ctx.json_output:
        payload = dataclasses.asdict(system_context)
        typer.echo(json.dumps(payload, default=str, indent=2))
        return

    _render_human(Console(no_color=cli_ctx.no_color if cli_ctx else False), system_context)
