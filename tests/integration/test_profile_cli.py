"""Integration: real registry + real detection + real reads against this
host. Only exercises paths guaranteed not to modify the system — see
test_tool_install_cli.py for why real mutation is never run from an
automated test.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_profile_list_runs() -> None:
    result = runner.invoke(app, ["profile", "list"])
    assert result.exit_code == 0
    assert "developer" in result.stdout


def test_profile_show_runs() -> None:
    result = runner.invoke(app, ["profile", "show", "developer"])
    assert result.exit_code == 0
    assert "Developer" in result.stdout


def test_profile_show_unknown_fails_cleanly() -> None:
    result = runner.invoke(app, ["profile", "show", "not-a-real-profile"])
    assert result.exit_code != 0


def test_profile_diff_runs_and_never_modifies() -> None:
    result = runner.invoke(app, ["profile", "diff", "developer"])
    assert result.exit_code == 0
    assert "Developer Profile" in result.stdout


def test_dry_run_profile_install_shows_plan() -> None:
    result = runner.invoke(app, ["--dry-run", "profile", "install", "devops"])
    assert result.exit_code == 0
    assert "HALLFIX EXECUTION PLAN" in result.stdout
    assert "No changes were made." in result.stdout


def test_custom_profile_without_tools_fails_cleanly() -> None:
    result = runner.invoke(app, ["profile", "install", "custom"])
    assert result.exit_code == 1


def test_dry_run_custom_profile_with_tools_shows_plan() -> None:
    # docker is not installed on the CI/dev host at this point in the
    # suite (see test_tool_install_cli.py) — picking an uninstalled,
    # natively-resolvable tool so the plan actually contains an action
    # instead of taking the no-op short-circuit like git/curl would.
    result = runner.invoke(app, ["--dry-run", "profile", "install", "custom", "--tools", "docker"])
    assert result.exit_code == 0
    assert "HALLFIX EXECUTION PLAN" in result.stdout


def test_profile_install_unknown_profile_fails_cleanly() -> None:
    result = runner.invoke(app, ["profile", "install", "not-a-real-profile"])
    assert result.exit_code != 0
