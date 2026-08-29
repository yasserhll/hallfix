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
    # Whether docker is already present depends on the real host (e.g.
    # GitHub Actions' ubuntu-latest ships Docker pre-installed, unlike a
    # typical dev machine) — both outcomes are valid; only the invariant
    # that holds either way ("no changes were made") is worth asserting
    # unconditionally.
    result = runner.invoke(app, ["--dry-run", "profile", "install", "custom", "--tools", "docker"])
    assert result.exit_code == 0
    assert "No changes were made." in result.stdout
    if "already installed" not in result.stdout.lower():
        assert "HALLFIX EXECUTION PLAN" in result.stdout


def test_profile_install_unknown_profile_fails_cleanly() -> None:
    result = runner.invoke(app, ["profile", "install", "not-a-real-profile"])
    assert result.exit_code != 0


def test_profile_remove_runs_and_never_modifies() -> None:
    # Real host, real StateStore: nothing here is Hallfix-managed, so every
    # tool is skipped via notes rather than actually removed — exercises the
    # full command path (real Planner/StateStore reads) without mutating
    # anything.
    result = runner.invoke(app, ["profile", "remove", "developer"])
    assert result.exit_code == 0
    assert "No changes were made." in result.stdout


def test_profile_remove_unknown_profile_fails_cleanly() -> None:
    result = runner.invoke(app, ["profile", "remove", "not-a-real-profile"])
    assert result.exit_code != 0


def test_profile_remove_custom_without_tools_fails_cleanly() -> None:
    result = runner.invoke(app, ["profile", "remove", "custom"])
    assert result.exit_code == 1
