from __future__ import annotations

from typer.testing import CliRunner

from hallfix import __version__
from hallfix.cli.app import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Hallfix" in result.stdout


def test_no_args_shows_help() -> None:
    # Click's no_args_is_help convention: help text is printed, but the
    # exit code is still 2 (usage error), not 0.
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "Usage" in result.stdout


def test_verbose_and_quiet_are_mutually_exclusive() -> None:
    result = runner.invoke(app, ["--verbose", "--quiet", "version"])
    assert result.exit_code != 0
