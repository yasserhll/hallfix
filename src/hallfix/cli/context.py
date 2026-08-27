"""Shared CLI invocation context.

Built once in the root Typer callback and threaded through ``typer.Context``
so every subcommand sees the same global flags without re-parsing them.
"""

from __future__ import annotations

from dataclasses import dataclass

from hallfix.config.schema import HallfixConfig


@dataclass(frozen=True, slots=True)
class CliContext:
    dry_run: bool
    yes: bool
    verbose: bool
    quiet: bool
    no_color: bool
    json_output: bool
    language: str
    config: HallfixConfig
