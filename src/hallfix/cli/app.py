"""CLI skeleton.

Per spec §3, the CLI must not contain business logic — this module only
parses global options, builds the shared ``CliContext``, wires up config
and logging, and dispatches to subcommands. Phase 1 ships only ``version``;
the rest of the command tree in spec §60 arrives with the phases that
implement the functionality behind it.
"""

from __future__ import annotations

import typer
from rich.console import Console

from hallfix import __version__
from hallfix.cli.commands import doctor as doctor_commands
from hallfix.cli.commands import history as history_commands
from hallfix.cli.commands import network as network_commands
from hallfix.cli.commands import plan as plan_commands
from hallfix.cli.commands import profile as profile_commands
from hallfix.cli.commands import system as system_commands
from hallfix.cli.commands import tool as tool_commands
from hallfix.cli.context import CliContext
from hallfix.config.manager import ConfigurationManager
from hallfix.domain.exceptions import ConfigurationError
from hallfix.infrastructure.logging.logger import setup_logging

app = typer.Typer(
    name="hallfix",
    help="Hallfix — Safe Linux System Doctor & Environment Manager.",
    no_args_is_help=True,
)
app.add_typer(system_commands.app, name="system")
app.add_typer(tool_commands.app, name="tool")
app.add_typer(plan_commands.app, name="plan")
app.add_typer(history_commands.app, name="history")
app.add_typer(profile_commands.app, name="profile")
app.add_typer(doctor_commands.app, name="doctor")
app.add_typer(network_commands.app, name="network")


@app.callback()
def main_callback(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen; change nothing."
    ),
    yes: bool = typer.Option(False, "--yes", help="Auto-confirm LOW/MEDIUM risk prompts."),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-essential output."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    language: str = typer.Option("en", "--language", help="Interface language (en, fr)."),
) -> None:
    """Global options shared by every Hallfix command."""
    if verbose and quiet:
        raise typer.BadParameter("--verbose and --quiet are mutually exclusive")

    try:
        config = ConfigurationManager().load()
    except ConfigurationError as exc:
        typer.secho(f"Configuration error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    setup_logging(verbose=verbose, quiet=quiet)

    ctx.obj = CliContext(
        dry_run=dry_run,
        yes=yes,
        verbose=verbose,
        quiet=quiet,
        no_color=no_color,
        json_output=json_output,
        language=language or config.language,
        config=config,
    )


@app.command()
def version() -> None:
    """Print the Hallfix version."""
    Console().print(f"Hallfix {__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
