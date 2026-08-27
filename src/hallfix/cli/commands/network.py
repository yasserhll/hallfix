"""``hallfix network`` command group (spec §18). Read-only.

Never performs a scan, remote probe, or any offensive action — ``info``
just reports already-detected local configuration; ``doctor`` interprets
it plus two local connectivity probes (raw TCP to a fixed IP, DNS
resolution of a fixed hostname) that never touch anything but the
network stack itself.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console

from hallfix.application.doctor import build_diagnostic_context
from hallfix.detectors.system import SystemDetector
from hallfix.domain.diagnostics.engine import DiagnosticEngine, aggregate_health
from hallfix.domain.diagnostics.registry import NETWORK_CHECKS, DiagnosticRegistry
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner

app = typer.Typer(name="network", help="Network information and diagnostics.")

_SYMBOL_BY_SEVERITY = {
    Severity.OK: "✓",
    Severity.INFO: "✓",
    Severity.WARNING: "⚠",
    Severity.ERROR: "✗",
    Severity.CRITICAL: "✗",
}
_UNHEALTHY_STATES = {HealthState.UNHEALTHY, HealthState.CRITICAL}


@app.command("info")
def info(ctx: typer.Context) -> None:
    """Show detected network configuration."""
    cli_ctx = ctx.obj
    system = SystemDetector(root=Path("/"), command_runner=SubprocessCommandRunner()).detect()
    network = system.network

    if cli_ctx is not None and cli_ctx.json_output:
        typer.echo(json.dumps(dataclasses.asdict(network), default=str, indent=2))
        return

    console = Console()
    for interface in network.interfaces:
        addresses = ", ".join(interface.ipv4_addresses + interface.ipv6_addresses) or "no address"
        state = "up" if interface.is_up else "down"
        console.print(f"{interface.name} ({state}): {addresses}")
    console.print(f"Default gateway: {network.default_gateway or 'none'}")
    console.print(f"DNS servers: {', '.join(network.dns_servers) or 'none configured'}")


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    """Run network-focused diagnostics."""
    cli_ctx = ctx.obj
    context = build_diagnostic_context(command_runner=SubprocessCommandRunner())
    results = DiagnosticEngine(DiagnosticRegistry(NETWORK_CHECKS)).run(context)
    health = aggregate_health(results)

    if cli_ctx is not None and cli_ctx.json_output:
        payload = {"result": health.value, "results": [dataclasses.asdict(r) for r in results]}
        typer.echo(json.dumps(payload, default=str, indent=2))
    else:
        _render(Console(), results, health)

    if health in _UNHEALTHY_STATES:
        raise typer.Exit(code=1)


def _render(console: Console, results: tuple[DiagnosticResult, ...], health: HealthState) -> None:
    console.print("[bold]NETWORK DIAGNOSTIC[/bold]\n")
    for result in results:
        console.print(
            f"{_SYMBOL_BY_SEVERITY[result.severity]} {result.title}: {result.description}"
        )
    console.print(f"\nResult: {health.value}")

    failing = [r for r in results if r.recommendation]
    if failing:
        console.print("\nRecommended actions:")
        for i, result in enumerate(failing, start=1):
            console.print(f"{i}. {result.recommendation}")
