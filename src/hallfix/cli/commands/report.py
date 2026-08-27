"""``hallfix report`` (spec §55). Read-only — a report is only ever a
view over data other commands already produced (detection, diagnostics,
StateStore, HistoryStore); generating one never modifies anything.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer

from hallfix.application.report_generator import build_report
from hallfix.cli.report_rendering import render_html, render_txt
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner

_FORMATS = ("txt", "json", "html")


def report(
    ctx: typer.Context,
    format: str = typer.Option("txt", "--format", help="txt, json, or html."),
    output: Path | None = typer.Option(  # noqa: B008 - standard Typer idiom; ruff mis-flags Path options
        None, "--output", help="Write to this file, not stdout."
    ),
) -> None:
    """Generate a system report combining detection, diagnostics, managed
    tools, and recent history."""
    cli_ctx = ctx.obj
    effective_format = "json" if (cli_ctx is not None and cli_ctx.json_output) else format.lower()
    if effective_format not in _FORMATS:
        typer.secho(
            f"Unknown format: {format!r} (expected one of {', '.join(_FORMATS)})",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    rep = build_report(command_runner=SubprocessCommandRunner())

    if effective_format == "txt":
        content = render_txt(rep)
    elif effective_format == "html":
        content = render_html(rep)
    else:
        content = json.dumps(dataclasses.asdict(rep), default=str, indent=2)

    if output is not None:
        output.write_text(content, encoding="utf-8")
        typer.echo(f"Report written to {output}")
    else:
        typer.echo(content)
