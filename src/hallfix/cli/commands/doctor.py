"""``hallfix doctor`` (spec §40). Read-only — runs diagnostics, never fixes
anything (there is no FixRegistry yet, Phase 10).
"""

from __future__ import annotations

import dataclasses
import json

import typer
from rich.console import Console

from hallfix.application.doctor import run_doctor
from hallfix.domain.diagnostics.engine import aggregate_health
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner

app = typer.Typer(name="doctor", help="Run system health diagnostics.")

_SYMBOL_BY_SEVERITY = {
    Severity.OK: "✓",
    Severity.INFO: "✓",
    Severity.WARNING: "⚠",
    Severity.ERROR: "✗",
    Severity.CRITICAL: "✗",
}

_UNHEALTHY_STATES = {HealthState.UNHEALTHY, HealthState.CRITICAL}


@app.callback(invoke_without_command=True)
def doctor(ctx: typer.Context) -> None:
    """Run full system diagnostics and report overall health."""
    cli_ctx = ctx.obj
    results = run_doctor(command_runner=SubprocessCommandRunner())
    health = aggregate_health(results)

    if cli_ctx is not None and cli_ctx.json_output:
        payload = {
            "health": health.value,
            "results": [dataclasses.asdict(r) for r in results],
        }
        typer.echo(json.dumps(payload, default=str, indent=2))
    else:
        console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
        _render(console, results, health)

    if health in _UNHEALTHY_STATES:
        raise typer.Exit(code=1)


def _render(console: Console, results: tuple[DiagnosticResult, ...], health: HealthState) -> None:
    console.print("[bold]SYSTEM HEALTH[/bold]\n")
    for result in results:
        console.print(f"{_SYMBOL_BY_SEVERITY[result.severity]} {result.title}")
        if result.severity in (Severity.WARNING, Severity.ERROR, Severity.CRITICAL):
            console.print(f"  {result.description}")
            if result.recommendation:
                console.print(f"  → {result.recommendation}")
    console.print(f"\nOverall state: {health.value}")
