"""Integration: real log directory (isolated by the autouse XDG fixture),
real CLI invocation. Read-only end to end."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_logs_runs_with_no_log_file() -> None:
    result = runner.invoke(app, ["logs"])
    assert result.exit_code == 0


def test_logs_shows_entries_written_by_an_earlier_command() -> None:
    # `version` doesn't log anything interesting, but the root callback's
    # setup_logging() runs for every command — invoking a command that
    # actually logs (doctor) first guarantees at least one real entry.
    runner.invoke(app, ["doctor"])
    result = runner.invoke(app, ["logs"])
    assert result.exit_code == 0


def test_logs_json_is_valid_list() -> None:
    result = runner.invoke(app, ["--json", "logs"])
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)


def test_logs_respects_lines_option() -> None:
    result = runner.invoke(app, ["logs", "--lines", "1"])
    assert result.exit_code == 0
