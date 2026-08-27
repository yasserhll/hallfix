"""``hallfix history`` — lists and shows recorded operations (spec §9).

Read-only. Never modifies ``history.jsonl``.
"""

from __future__ import annotations

import dataclasses
import json

import typer
from rich.console import Console
from rich.table import Table

from hallfix.domain.models.history import OperationRecord
from hallfix.infrastructure.state.history_store import HistoryStore

app = typer.Typer(name="history", help="Show past Hallfix operations.")


def _summary(record: OperationRecord) -> str:
    if record.dry_run:
        return "dry-run"
    if not record.action_outcomes:
        return "no changes"
    if record.failed_count:
        return f"{record.succeeded_count} ok, {record.failed_count} failed"
    return f"{record.succeeded_count} ok"


@app.callback(invoke_without_command=True)
def list_history(ctx: typer.Context) -> None:
    """List recorded operations, most recent first."""
    if ctx.invoked_subcommand is not None:
        return

    cli_ctx = ctx.obj
    records = tuple(reversed(HistoryStore().list_all()))

    if cli_ctx is not None and cli_ctx.json_output:
        typer.echo(json.dumps([dataclasses.asdict(r) for r in records], default=str, indent=2))
        return

    if not records:
        typer.echo("No history recorded yet.")
        return

    table = Table()
    table.add_column("ID")
    table.add_column("Command")
    table.add_column("Timestamp")
    table.add_column("Result")
    for record in records:
        table.add_row(record.id, record.command, record.timestamp.isoformat(), _summary(record))
    Console().print(table)


@app.command("show")
def show(ctx: typer.Context, operation_id: str) -> None:
    """Show full detail for one operation."""
    record = HistoryStore().get(operation_id)
    if record is None:
        typer.secho(f"No such operation: {operation_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    cli_ctx = ctx.obj
    if cli_ctx is not None and cli_ctx.json_output:
        typer.echo(json.dumps(dataclasses.asdict(record), default=str, indent=2))
        return

    console = Console()
    console.print(f"[bold]{record.id}[/bold]  {record.timestamp.isoformat()}")
    console.print(f"Command: {record.command}")
    console.print(f"Plan: {record.plan_id} — {record.plan_description}")
    console.print(f"Dry-run: {'YES' if record.dry_run else 'NO'}")
    if not record.action_outcomes:
        console.print("No actions were executed.")
        return
    for outcome in record.action_outcomes:
        marker = "✓" if outcome.succeeded else "✗"
        console.print(f"{marker} [{outcome.action_type}] {outcome.message.strip()}")
    console.print(f"\nSuccessful: {record.succeeded_count}  Failed: {record.failed_count}")
