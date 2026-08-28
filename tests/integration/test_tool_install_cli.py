"""Integration: real registry + real detection + real reads against this
host.

Deliberately only exercises paths that are guaranteed not to modify the
system: the idempotent no-op path (git is already installed on the CI/dev
host by this point in the test suite) and ``--dry-run``. A real mutating
install/remove is never run from an automated test — that's a decision
for a human to make on their own machine, not something a test suite
should do to whatever box it happens to run on.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_install_already_installed_tool_is_a_noop() -> None:
    result = runner.invoke(app, ["tool", "install", "git"])
    assert result.exit_code == 0
    assert "already installed" in result.stdout.lower()
    assert "No changes were made." in result.stdout


def test_dry_run_install_shows_plan_without_prompting() -> None:
    # Whether docker is already present depends on the real host (e.g.
    # GitHub Actions' ubuntu-latest ships Docker pre-installed, unlike a
    # typical dev machine) — both outcomes are valid and safe; only the
    # invariant that holds either way is worth asserting.
    result = runner.invoke(app, ["--dry-run", "tool", "install", "docker"])
    assert result.exit_code == 0
    assert "No changes were made." in result.stdout
    if "already installed" not in result.stdout.lower():
        assert "HALLFIX EXECUTION PLAN" in result.stdout


def test_dry_run_remove_shows_plan_without_prompting() -> None:
    result = runner.invoke(app, ["--dry-run", "tool", "remove", "git"])
    assert result.exit_code == 0
    assert "HALLFIX EXECUTION PLAN" in result.stdout


def test_install_unknown_tool_fails_cleanly() -> None:
    result = runner.invoke(app, ["tool", "install", "not-a-real-tool"])
    assert result.exit_code == 1
