"""``hallfix config`` (spec §58). Read-only: shows the effective
configuration (defaults merged with ``~/.config/hallfix/config.toml``) and
where it's loaded from. There is no ``config set`` yet — spec §58 describes
the settings surface, not a write UX, and the config file format (TOML) is
meant to be hand-edited directly.
"""

from __future__ import annotations

import dataclasses
import json

import typer
from rich.console import Console
from rich.table import Table

from hallfix.config.manager import ConfigurationManager


def config(ctx: typer.Context) -> None:
    """Show the effective Hallfix configuration and where it's loaded from."""
    cli_ctx = ctx.obj
    manager = ConfigurationManager()
    cfg = cli_ctx.config if cli_ctx is not None else manager.load()

    if cli_ctx is not None and cli_ctx.json_output:
        payload = {
            "path": str(manager.path),
            "exists": manager.path.is_file(),
            "config": dataclasses.asdict(cfg),
        }
        typer.echo(json.dumps(payload, default=str, indent=2))
        return

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    console.print(f"[bold]Configuration file:[/bold] {manager.path}")
    console.print(f"Exists: {'yes' if manager.path.is_file() else 'no (using defaults)'}\n")

    table = Table()
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("language", cfg.language)
    table.add_row("color", str(cfg.color))
    table.add_row("verbose", str(cfg.verbose))
    table.add_row("report_format", cfg.report_format)
    table.add_row("preferred_editor", cfg.preferred_editor or "(not set)")
    table.add_row("disk_thresholds.warning", f"{cfg.disk_thresholds.warning}%")
    table.add_row("disk_thresholds.high", f"{cfg.disk_thresholds.high}%")
    table.add_row("disk_thresholds.critical", f"{cfg.disk_thresholds.critical}%")
    console.print(table)
