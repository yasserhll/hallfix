"""``hallfix logs`` (spec §57). Read-only view of Hallfix's own structured
JSON-lines log file. Every line was already redacted at write time
(``RedactingFilter``, attached to the handler itself in
``infrastructure/logging/logger.py``) — this command never redacts
anything itself, it only displays already-safe data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from hallfix.utils.paths import log_dir

_LOG_FILENAME = "hallfix.log"


def _read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    return entries


def logs(
    ctx: typer.Context,
    lines: int = typer.Option(
        50, "--lines", "-n", help="Number of most recent log entries to show."
    ),
) -> None:
    """Show the most recent Hallfix log entries."""
    cli_ctx = ctx.obj
    path = log_dir() / _LOG_FILENAME
    entries = _read_entries(path)
    recent = entries[-lines:] if lines > 0 else entries

    if cli_ctx is not None and cli_ctx.json_output:
        typer.echo(json.dumps(recent, default=str, indent=2))
        return

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    if not recent:
        console.print(f"No log entries found at {path}.")
        return

    for entry in recent:
        timestamp = entry.get("timestamp", "?")
        level = str(entry.get("level", "?"))
        message = entry.get("message", "")
        console.print(f"[dim]{timestamp}[/dim] [bold]{level:<8}[/bold] {message}")
    console.print(f"\n{len(recent)} of {len(entries)} entries shown. Log file: {path}")
