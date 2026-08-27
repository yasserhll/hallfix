"""Integration: real registry + real detection + real reads against this
host. Runs `tool install git` (a no-op on a host where git is already
installed — never mutates anything) then checks it shows up in history.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_noop_install_is_recorded_in_history() -> None:
    install_result = runner.invoke(app, ["tool", "install", "git"])
    assert install_result.exit_code == 0

    history_result = runner.invoke(app, ["history"])
    assert history_result.exit_code == 0
    assert "tool install git" in history_result.stdout


def test_history_empty_message_when_nothing_recorded() -> None:
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "No history recorded yet." in result.stdout


def test_history_show_unknown_id_fails_cleanly() -> None:
    result = runner.invoke(app, ["history", "show", "HF-999"])
    assert result.exit_code == 1


def test_dry_run_install_is_recorded_and_shown() -> None:
    dry_run_result = runner.invoke(app, ["--dry-run", "tool", "install", "docker"])
    assert dry_run_result.exit_code == 0

    history_result = runner.invoke(app, ["history"])
    assert "dry-run" in history_result.stdout

    # find the assigned id from the JSON listing to check `history show`
    json_result = runner.invoke(app, ["--json", "history"])
    records = json.loads(json_result.stdout)
    assert len(records) == 1
    show_result = runner.invoke(app, ["history", "show", records[0]["id"]])
    assert show_result.exit_code == 0
    assert "tool install docker" in show_result.stdout
