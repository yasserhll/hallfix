"""Integration: real registry + real detection + real reads against this
host. See test_system_info_cli.py for why this lives here.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_plan_install_git_runs() -> None:
    result = runner.invoke(app, ["plan", "install", "git"])
    assert result.exit_code == 0
    assert "HALLFIX EXECUTION PLAN" in result.stdout
    assert "No changes were made." in result.stdout


def test_plan_install_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "plan", "install", "git"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "id" in payload
    assert "planned_actions" in payload


def test_plan_refresh_runs() -> None:
    result = runner.invoke(app, ["plan", "refresh"])
    assert result.exit_code == 0
    assert "HALLFIX EXECUTION PLAN" in result.stdout


def test_plan_install_unknown_tool_fails_cleanly() -> None:
    result = runner.invoke(app, ["plan", "install", "not-a-real-tool"])
    assert result.exit_code == 1


def test_plan_remove_git_runs() -> None:
    result = runner.invoke(app, ["plan", "remove", "git"])
    assert result.exit_code == 0
    assert "HALLFIX EXECUTION PLAN" in result.stdout
    assert "No changes were made." in result.stdout


def test_plan_remove_unknown_tool_fails_cleanly() -> None:
    result = runner.invoke(app, ["plan", "remove", "not-a-real-tool"])
    assert result.exit_code == 1
